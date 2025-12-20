from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends, Request, status
from typing import Optional, Dict, Any, Tuple
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import uuid
import logging
from pathlib import Path
from datetime import datetime

# Import our utility functions
from ..utils.db_utils import update_avatar_url

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router with API prefix to match JavaScript client
router = APIRouter(prefix="/api/avatars", tags=["avatars"])

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Supabase URL or Key not found in environment variables")
    raise ValueError("Supabase URL and Key must be set in environment variables")

# Supabase configuration
BUCKET_NAME = "agent-avatars"  # Name of the Supabase storage bucket
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "svg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def get_supabase(request: Request) -> Client:
    """Get the Supabase client instance from app state."""
    return request.app.state.supabase

def validate_upload_file(file: UploadFile) -> Tuple[bool, str]:
    """
    Validate the uploaded file.
    
    Args:
        file: The uploaded file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file extension
    file_ext = Path(file.filename).suffix.lower().lstrip('.')
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file extension. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Check file size
    if file.size > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.1f}MB"
    
    # Validate content type
    content_types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "svg": "image/svg+xml"
    }
    
    expected_type = content_types.get(file_ext)
    if not expected_type:
        return False, f"Invalid file type. Expected one of: {', '.join(content_types.values())}"
    
    if file.content_type and file.content_type != expected_type:
        return False, f"Invalid content type. Expected: {expected_type}, got: {file.content_type}"
    
    # Check file size
    if file.size > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.1f}MB"
    
    return True, ""

@router.get("/{entity_type}/{entity_id}")
async def get_avatar_url(
    entity_type: str, 
    entity_id: str,
    request: Request
):
    """
    Get avatar URL for a specific entity.
    
    Args:
        entity_type: Type of entity (tool or agent)
        entity_id: ID of the entity
        
    Returns:
        JSON response with avatar URL
    """
    try:
        supabase = get_supabase(request)
        
        # Query the appropriate table based on entity type
        entity_type = entity_type.lower()
        if entity_type == "tool":
            query = supabase.table("tools").select("avatar_url").eq("tool_id", entity_id)
        elif entity_type == "agent":
            query = supabase.table("agents").select("avatar_url").eq("agent_id", entity_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid entity type: {entity_type}"
            )
        
        result = query.execute()
        
        if not result.data or len(result.data) == 0:
            # Generate a default URL based on entity ID
            avatar_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/public/default_{entity_type}_{entity_id}.png"
            return {
                "avatar_url": avatar_url,
                "entity_type": entity_type,
                "entity_id": entity_id
            }
            
        avatar_url = result.data[0].get("avatar_url")
        
        if not avatar_url:
            # Generate a default URL based on entity ID
            avatar_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/public/default_{entity_type}_{entity_id}.png"
        
        return {
            "avatar_url": avatar_url,
            "entity_type": entity_type,
            "entity_id": entity_id
        }
        
    except Exception as e:
        logger.error(f"Error details: {str(e)}", exc_info=True)
        logger.error(f"Supabase URL: {SUPABASE_URL}")
        logger.error(f"Bucket Name: {BUCKET_NAME}")
        logger.error(f"Entity Type: {entity_type}")
        logger.error(f"Entity ID: {entity_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get avatar URL: {str(e)}"
        )

@router.post("/upload/{entity_type}/{entity_id}")
async def upload_avatar(
    entity_type: str,
    entity_id: str,
    request: Request,
    file: UploadFile = File(...),
    is_public: bool = Form(True)
) -> Dict[str, Any]:
    """
    Upload an avatar image for an entity (agent or tool)
    
    Args:
        entity_type: Type of entity (agent or tool)
        entity_id: ID of the entity
        file: Uploaded image file
        is_public: Whether the file should be publicly accessible
        
    Returns:
        Dict with status, URL, and public status of the uploaded avatar
    """
    try:
        # Validate entity type
        entity_type = entity_type.lower()
        if entity_type not in ["agent", "tool"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Entity type must be 'agent' or 'tool'"
            )
        
        # Validate file
        is_valid, error_msg = validate_upload_file(file)
        if not is_valid:
            logger.error(f"File validation failed: {error_msg}")
            logger.error(f"File details - Name: {file.filename}, Size: {file.size}, Content-Type: {file.content_type}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "File validation failed",
                    "details": error_msg,
                    "file_info": {
                        "name": file.filename,
                        "size": file.size,
                        "content_type": file.content_type
                    }
                }
            )
        
        # Generate a unique filename
        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{entity_type}_{entity_id}_{uuid.uuid4()}{file_ext}"
        file_path = f"public/{unique_filename}" if is_public else f"private/{unique_filename}"
        
        # Read file content
        file_content = await file.read()
        
        # Upload the file to Supabase Storage
        try:
            supabase = get_supabase(request)
            upload_result = supabase.storage.from_(BUCKET_NAME).upload(
                file_path,
                file_content,
                {"content-type": file.content_type or "application/octet-stream"}
            )
            
            if hasattr(upload_result, 'error') and upload_result.error:
                raise Exception(f"Upload failed: {upload_result.error}")
                
        except Exception as upload_error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage"
            )
        
        # Get the public URL for the uploaded file
        try:
            if is_public:
                avatar_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{file_path}"
            else:
                response = supabase.storage.from_(BUCKET_NAME).create_signed_url(file_path, 3600)  # 1 hour expiry
                avatar_url = response.signed_url if hasattr(response, 'signed_url') else ""
            
            if not avatar_url:
                raise Exception("Failed to generate file URL")
                
        except Exception as url_error:
            # Try to clean up the uploaded file
            try:
                supabase.storage.from_(BUCKET_NAME).remove([file_path])
            except Exception:
                pass
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate file URL"
            )
        
        # Update the database with the avatar URL
        table_name = 'agents' if entity_type == 'agent' else 'tools'
        id_column = 'agent_id' if entity_type == 'agent' else 'tool_id'
        
        try:
            update_result = await update_avatar_url(
                supabase=supabase,
                table_name=table_name,
                id_column=id_column,
                entity_id=entity_id,
                avatar_url=avatar_url
            )
            
            if not update_result.get('success', False):
                logger.warning(f"Database update warning: {update_result.get('error', 'Unknown error')}")
                
        except Exception as update_error:
            logger.error(f"Failed to update avatar URL in database: {str(update_error)}")
            # Don't fail the operation if the update fails - the file is still uploaded
            logger.warning(f"Continuing with upload despite database update failure: {str(update_error)}")
        
        return {
            "status": "success",
            "url": avatar_url,
            "is_public": is_public,
            "entity_type": entity_type,
            "entity_id": entity_id
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in upload_avatar: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request"
        )

@router.get("/status/{entity_type}/{entity_id}")
async def get_avatar_status(
    entity_type: str,
    entity_id: str,
    request: Request
) -> Dict[str, Any]:
    """
    Get the avatar status for an entity
    
    Args:
        entity_type: Type of entity (agent or tool)
        entity_id: ID of the entity
        
    Returns:
        Dict with avatar status, URL if available, and additional metadata
    """
    # Validate entity type
    entity_type = entity_type.lower()
    if entity_type not in ["agent", "tool"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entity type must be 'agent' or 'tool'"
        )
    
    # Validate entity_id format (basic check for UUID format)
    try:
        uuid.UUID(entity_id)  # This will raise ValueError if not a valid UUID
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entity ID format. Must be a valid UUID."
        ) from exc
    
    try:
        # Get the entity from the appropriate table
        table_name = 'agents' if entity_type == 'agent' else 'tools'
        id_column = 'agent_id' if entity_type == 'agent' else 'tool_id'
        
        # Query the database
        try:
            supabase = get_supabase(request)
            # Execute the query to get entity data
            query = supabase.table(table_name).select('*').eq(id_column, entity_id)
            result = query.execute()
            
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Database error: {result.error}")
                
            if not result.data or len(result.data) == 0:
                return {
                    "status": "not_found",
                    "has_avatar": False,
                    "message": f"No {entity_type} found with ID {entity_id}",
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            entity_data = result.data[0]
            avatar_url = entity_data.get('avatar_url')
            
            if not avatar_url:
                return {
                    "status": "no_avatar",
                    "has_avatar": False,
                    "message": f"No avatar set for {entity_type} with ID {entity_id}",
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "entity_exists": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Check if the URL is a Supabase storage URL and if it's accessible
            is_supabase_url = SUPABASE_URL and SUPABASE_URL in avatar_url
            is_accessible = False
            
            if is_supabase_url:
                try:
                    # For private URLs, we'd need to generate a new signed URL
                    # For now, we'll just check if it's a public URL
                    if avatar_url.startswith('http'):
                        # Simple check - if it's a public URL, we can try to access it
                        # This is a basic check and might not work for all cases
                        is_accessible = True
                except Exception:
                    is_accessible = False
            
            return {
                "status": "success",
                "has_avatar": True,
                "url": avatar_url,
                "is_accessible": is_accessible,
                "is_supabase_url": is_supabase_url,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "entity_exists": True,
                "last_updated": entity_data.get('updated_at') or entity_data.get('created_at'),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as db_error:
            logger.error(f"Database error in get_avatar_status: {str(db_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error accessing the database"
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in get_avatar_status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request"
        )

@router.get("/{entity_type}/{entity_id}/download")
async def get_avatar(
    entity_type: str,
    entity_id: str,
    request: Request
) -> Dict[str, Any]:
    """
    Get the avatar URL for an entity
    
    Args:
        entity_type: Type of entity (agent or tool)
        entity_id: ID of the entity
        
    Returns:
        Dict with the avatar URL, metadata, and cache control headers
    """
    # Validate entity type
    entity_type = entity_type.lower()
    if entity_type not in ["agent", "tool"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entity type must be 'agent' or 'tool'"
        )
    
    # Validate entity_id format
    try:
        uuid.UUID(entity_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entity ID format. Must be a valid UUID."
        ) from exc
    
    try:
        # Get the entity from the appropriate table
        table_name = 'agents' if entity_type == 'agent' else 'tools'
        id_column = 'agent_id' if entity_type == 'agent' else 'tool_id'
        
        # Query the database
        try:
            supabase = get_supabase(request)
            result = supabase.table(table_name)\
                .select('*')\
                .eq(id_column, entity_id)\
                .execute()
                
            if hasattr(result, 'error') and result.error:
                logger.error(f"Database error: {result.error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error accessing the database"
                )
                
            if not result.data or len(result.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{entity_type.capitalize()} not found with ID {entity_id}"
                )
            
            entity_data = result.data[0]
            avatar_url = entity_data.get('avatar_url')
            
            if not avatar_url:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No avatar found for {entity_type} with ID {entity_id}"
                )
            
            # Generate a signed URL if it's a private URL (optional)
            is_private = "private" in avatar_url.lower()
            final_url = avatar_url
            
            # If it's a private URL and we want to generate a signed URL
            if is_private and SUPABASE_URL and SUPABASE_URL in avatar_url:
                try:
                    # Extract the file path from the URL
                    file_path = avatar_url.split(f"{BUCKET_NAME}/")[-1].split("?")[0]
                    # Create a signed URL that's valid for 1 hour
                    signed_url = supabase.storage.from_(BUCKET_NAME).create_signed_url(file_path, 3600)
                    if hasattr(signed_url, 'signed_url') and signed_url.signed_url:
                        final_url = signed_url.signed_url
                except Exception as url_error:
                    logger.warning(f"Could not generate signed URL: {str(url_error)}")
                    # Continue with the original URL if signing fails
            
            # Prepare response with cache control headers
            response_headers = {
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "CDN-Cache-Control": "public, max-age=86400",  # CDN cache for 24 hours
                "Vary": "Accept-Encoding"
            }
            
            return {
                "status": "success",
                "url": final_url,
                "is_private": is_private,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "last_updated": entity_data.get('updated_at') or entity_data.get('created_at'),
                "timestamp": datetime.utcnow().isoformat(),
                "headers": response_headers
            }
            
        except Exception as db_error:
            logger.error(f"Database error in get_avatar: {str(db_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving avatar information"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in get_avatar: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting avatar: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
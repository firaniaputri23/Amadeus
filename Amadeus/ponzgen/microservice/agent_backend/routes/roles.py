from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from typing import List, Optional
from supabase import Client

from microservice.agent_boilerplate.boilerplate.errors import (
    BadRequestError, NotFoundError, ForbiddenError, 
    InternalServerError, ERROR_RESPONSES
)

# Pydantic models for request and response
class RoleBase(BaseModel):
    role_name: str

class RoleResponse(RoleBase):
    role_id: int

# Create router
router = APIRouter(
    prefix="/roles",
    tags=["roles"],
    responses={**ERROR_RESPONSES}
)

# Dependency to get Supabase client
def get_supabase_client(request: Request):
    return request.app.state.supabase

# CRUD operations
@router.get("/", response_model=List[RoleResponse])
async def get_roles(
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get all roles
        try:
            response = (
                supabase.table("roles")
                .select("*")
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching roles: {str(e)}")
        
        return response.data
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get role by ID
        try:
            response = (
                supabase.table("roles")
                .select("*")
                .eq("role_id", role_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching role: {str(e)}")
        
        if not response.data:
            raise NotFoundError(f"Role with ID '{role_id}' not found")
        
        return response.data[0]
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

# Function to initialize roles
async def initialize_roles(supabase: Client):
    try:
        # Check if roles already exist
        try:
            roles_response = (
                supabase.table("roles")
                .select("*")
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error checking existing roles: {str(e)}")
        
        if not roles_response.data:
            # Insert default roles
            roles_to_insert = [
                {"role_name": "super admin"},
                {"role_name": "admin"},
                {"role_name": "staff"},
                {"role_name": "guest"}
            ]
            
            try:
                for role in roles_to_insert:
                    (
                        supabase.table("roles")
                        .insert(role)
                        .execute()
                    )
            except Exception as e:
                raise InternalServerError(f"Error creating default roles: {str(e)}")
            
            print("Default roles created: super admin, admin, staff, guest")
        else:
            print(f"Roles already exist: {len(roles_response.data)} roles found")
    except Exception as e:
        print(f"Error initializing roles: {str(e)}")
        # Just log the error, don't raise it since this is an initialization function
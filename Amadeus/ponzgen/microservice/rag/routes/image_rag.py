"""
Image RAG Routes

Provides endpoints for image-based retrieval augmented generation.
"""

from fastapi import APIRouter, HTTPException, Form, Query
from typing import Optional, List
from pydantic import BaseModel

from ..service.rag._image_rag_utils import (
    retrieval_with_rerank,
    hybrid_search,
    generate_response_with_images,
    get_image_by_id
)

# Initialize router
router = APIRouter(
    prefix="/image-rag",
    tags=["Image RAG"],
)


class ImageQueryRequest(BaseModel):
    """Request model for image query."""
    query: str
    top_k: int = 5
    category: Optional[str] = None
    model_name: str = "custom-vlm"


class HybridSearchRequest(BaseModel):
    """Request model for hybrid search."""
    query: str
    search_text: Optional[str] = None
    category: Optional[str] = None
    top_k: int = 5


class ImageRAGRequest(BaseModel):
    """Request model for full RAG with response generation."""
    query: str
    top_k: int = 5
    category: Optional[str] = None
    model_name: str = "custom-vlm"
    temperature: float = 0.0


@router.post("/search")
async def search_images(request: ImageQueryRequest):
    """
    Search for similar images based on text query.
    
    Args:
        request: Search parameters including query, top_k, and optional category filter
        
    Returns:
        List of matching images with similarity scores and metadata
    """
    try:
        results = retrieval_with_rerank(
            query=request.query,
            top_k=request.top_k,
            category_filter=request.category
        )
        
        # Format results
        formatted_results = []
        for file_id, score, metadata in results:
            formatted_results.append({
                "file_id": file_id,
                "similarity": score,
                "image_id": metadata.get("image_id"),
                "category": metadata.get("category"),
                "caption": metadata.get("caption_raw"),
                "facts": metadata.get("facts"),
                "image_path": metadata.get("image_path")
            })
        
        return {
            "query": request.query,
            "total_results": len(formatted_results),
            "results": formatted_results
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hybrid-search")
async def hybrid_search_images(request: HybridSearchRequest):
    """
    Perform hybrid search combining vector similarity and text matching.
    
    Args:
        request: Hybrid search parameters
        
    Returns:
        List of matching images
    """
    try:
        results = hybrid_search(
            query=request.query,
            search_text=request.search_text,
            category_filter=request.category,
            top_k=request.top_k
        )
        
        formatted_results = []
        for file_id, score, metadata in results:
            formatted_results.append({
                "file_id": file_id,
                "similarity": score,
                "image_id": metadata.get("image_id"),
                "category": metadata.get("category"),
                "caption": metadata.get("caption_raw"),
                "facts": metadata.get("facts"),
                "image_path": metadata.get("image_path")
            })
        
        return {
            "query": request.query,
            "search_text": request.search_text,
            "total_results": len(formatted_results),
            "results": formatted_results
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_with_rag(request: ImageRAGRequest):
    """
    Perform full RAG: retrieve relevant images and generate response.
    
    Args:
        request: RAG request with query and generation parameters
        
    Returns:
        Generated response with retrieved context
    """
    try:
        # Retrieve relevant images
        retrieved_context = retrieval_with_rerank(
            query=request.query,
            top_k=request.top_k,
            category_filter=request.category
        )
        
        if not retrieved_context:
            return {
                "query": request.query,
                "response": "No relevant images found for your query.",
                "retrieved_images": []
            }
        
        # Generate response
        response = generate_response_with_images(
            query=request.query,
            retrieved_context=retrieved_context,
            model_name=request.model_name,
            temperature=request.temperature
        )
        
        # Format retrieved images
        retrieved_images = []
        for file_id, score, metadata in retrieved_context:
            retrieved_images.append({
                "file_id": file_id,
                "similarity": score,
                "image_id": metadata.get("image_id"),
                "category": metadata.get("category"),
                "caption": metadata.get("caption_raw"),
                "image_path": metadata.get("image_path")
            })
        
        return {
            "query": request.query,
            "response": response,
            "model_used": request.model_name,
            "retrieved_images": retrieved_images
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/image/{image_id}")
async def get_image_details(
    image_id: str,
    category: Optional[str] = Query(None, description="Category filter: indoor, outdoor, or street")
):
    """
    Get detailed information about a specific image.
    
    Args:
        image_id: Image identifier (e.g., "F009.jpg")
        category: Optional category to narrow search
        
    Returns:
        Image metadata and details
    """
    try:
        image_data = get_image_by_id(image_id, category)
        
        if not image_data:
            raise HTTPException(status_code=404, detail="Image not found")
        
        return {
            "id": image_data.get("id"),
            "image_id": image_data.get("image_id"),
            "category": image_data.get("category"),
            "caption": image_data.get("caption_raw"),
            "facts": image_data.get("facts") or image_data.get("image_facts"),
            "image_url": image_data.get("image_url"),
            "created_at": image_data.get("created_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_categories():
    """
    Get list of available image categories.
    
    Returns:
        List of categories
    """
    return {
        "categories": [
            {
                "name": "indoor",
                "description": "Indoor scenes including offices, cafes, and classrooms"
            },
            {
                "name": "outdoor",
                "description": "Outdoor scenes and landscapes"
            },
            {
                "name": "street",
                "description": "Street scenes and urban environments"
            }
        ]
    }


@router.get("/stats")
async def get_statistics():
    """
    Get statistics about the image database.
    Works with existing tables: image_indoor, image_outdoor, image_street
    
    Returns:
        Database statistics
    """
    try:
        from supabase import create_client
        import os
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        client = create_client(supabase_url, supabase_key)
        
        # Get counts from each table
        indoor_response = client.table("image_indoor").select("*", count="exact").execute()
        outdoor_response = client.table("image_outdoor").select("*", count="exact").execute()
        street_response = client.table("image_street").select("*", count="exact").execute()
        
        total = (indoor_response.count or 0) + (outdoor_response.count or 0) + (street_response.count or 0)
        
        return {
            "total_images": total,
            "by_category": {
                "indoor": {
                    "total": indoor_response.count or 0
                },
                "outdoor": {
                    "total": outdoor_response.count or 0
                },
                "street": {
                    "total": street_response.count or 0
                }
            },
            "tables": ["image_indoor", "image_outdoor", "image_street"]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

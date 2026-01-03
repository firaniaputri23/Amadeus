#!/usr/bin/env python3
"""
Supabase RAG MCP Server

Exposes image RAG retrieval capabilities as MCP tools for AI agents.
This enables agents to use tool calling to retrieve similar images from Supabase
and augment their responses with visual context.

Tools provided:
- search_similar_images_by_upload: Search by image file
- search_similar_images_by_query: Search by text query
- get_image_details: Get metadata for specific image
"""

import os
import sys
import json
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio

# Add parent directories to path for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP
from PIL import Image
import io

# Import your existing RAG utilities
from microservice.rag.service.rag._image_rag_utils import (
    retrieval_by_image,
    retrieval_with_rerank
)
from microservice.rag.service.embedding._embedding_utils import EmbedderService

# Initialize MCP server
mcp = FastMCP("Supabase RAG Image Search")

# Initialize embedder service
embedder = EmbedderService()


@mcp.tool()
def search_similar_images_by_upload(
    image_path: str,
    top_k: int = 3,
    category_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search for similar images in Supabase database using an uploaded image.
    
    This tool uses CLIP embeddings to find visually similar images from the database
    and returns their captions, facts, and metadata.
    
    Args:
        image_path: Absolute path to the image file to search with
        top_k: Number of similar images to return (default: 3, max: 10)
        category_filter: Optional filter by category ('indoor', 'outdoor', 'street')
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating if search was successful
        - results: List of similar images with scores and metadata
        - count: Number of results returned
        - error: Error message if search failed
    
    Example:
        {
            "success": true,
            "count": 3,
            "results": [
                {
                    "image_id": "img_001.jpg",
                    "similarity_score": 0.8523,
                    "category": "indoor",
                    "caption": "A cozy living room with a blue sofa",
                    "facts": {
                        "q1": "1 sofa, 1 coffee table",
                        "q2": "Living room setup for relaxation",
                        "q3": "Blue sofa, brown table"
                    }
                },
                ...
            ]
        }
    """
    try:
        # Validate image path
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"Image file not found: {image_path}",
                "results": [],
                "count": 0
            }
        
        # Limit top_k to reasonable range
        top_k = max(1, min(top_k, 10))
        
        # Perform retrieval
        retrieved_images = retrieval_by_image(
            image_path=image_path,
            top_k=top_k,
            category_filter=category_filter
        )
        
        if not retrieved_images:
            return {
                "success": True,
                "results": [],
                "count": 0,
                "message": "No similar images found"
            }
        
        # Format results
        formatted_results = []
        for file_id, score, metadata in retrieved_images:
            formatted_results.append({
                "image_id": file_id,
                "similarity_score": round(score, 4),
                "category": metadata.get('category', 'unknown'),
                "caption": metadata.get('caption_raw', ''),
                "facts": metadata.get('facts', {}),
                "image_path": metadata.get('image_path', '')
            })
        
        return {
            "success": True,
            "count": len(formatted_results),
            "results": formatted_results
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {str(e)}",
            "results": [],
            "count": 0
        }


@mcp.tool()
def search_similar_images_by_query(
    query: str,
    top_k: int = 3,
    category_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search for images in Supabase database using a text query.
    
    This tool uses CLIP text embeddings to find images matching the text description
    and returns their captions, facts, and metadata.
    
    Args:
        query: Text description to search for (e.g., "person sitting at desk with laptop")
        top_k: Number of similar images to return (default: 3, max: 10)
        category_filter: Optional filter by category ('indoor', 'outdoor', 'street')
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating if search was successful
        - results: List of matching images with scores and metadata
        - count: Number of results returned
        - query: The original query text
        - error: Error message if search failed
    
    Example:
        {
            "success": true,
            "query": "person working on laptop",
            "count": 2,
            "results": [
                {
                    "image_id": "img_045.jpg",
                    "similarity_score": 0.7892,
                    "category": "indoor",
                    "caption": "Person working on laptop in office",
                    "facts": {...}
                },
                ...
            ]
        }
    """
    try:
        # Validate query
        if not query or not query.strip():
            return {
                "success": False,
                "error": "Query cannot be empty",
                "results": [],
                "count": 0
            }
        
        # Limit top_k to reasonable range
        top_k = max(1, min(top_k, 10))
        
        # Perform retrieval
        retrieved_images = retrieval_with_rerank(
            query=query,
            top_k=top_k,
            category_filter=category_filter
        )
        
        if not retrieved_images:
            return {
                "success": True,
                "query": query,
                "results": [],
                "count": 0,
                "message": "No matching images found"
            }
        
        # Format results
        formatted_results = []
        for file_id, score, metadata in retrieved_images:
            formatted_results.append({
                "image_id": file_id,
                "similarity_score": round(score, 4),
                "category": metadata.get('category', 'unknown'),
                "caption": metadata.get('caption_raw', ''),
                "facts": metadata.get('facts', {}),
                "image_path": metadata.get('image_path', '')
            })
        
        return {
            "success": True,
            "query": query,
            "count": len(formatted_results),
            "results": formatted_results
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {str(e)}",
            "query": query,
            "results": [],
            "count": 0
        }


@mcp.tool()
def get_image_details(
    image_id: str
) -> Dict[str, Any]:
    """
    Get detailed metadata for a specific image from the database.
    
    Args:
        image_id: The ID of the image to retrieve details for
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating if retrieval was successful
        - image_id: The requested image ID
        - details: Image metadata including caption, facts, category
        - error: Error message if retrieval failed
    
    Example:
        {
            "success": true,
            "image_id": "img_001.jpg",
            "details": {
                "category": "indoor",
                "caption": "A cozy living room with a blue sofa",
                "facts": {
                    "q1": "1 sofa, 1 coffee table",
                    "q2": "Living room setup for relaxation",
                    "q3": "Blue sofa, brown table"
                },
                "image_path": "/path/to/image.jpg"
            }
        }
    """
    try:
        from supabase import create_client
        
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            return {
                "success": False,
                "error": "Supabase credentials not configured",
                "image_id": image_id
            }
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Try to find the image in all category tables
        for table_name in ['image_indoor', 'image_outdoor', 'image_street']:
            response = supabase.table(table_name).select("*").eq("file_id", image_id).execute()
            
            if response.data and len(response.data) > 0:
                record = response.data[0]
                return {
                    "success": True,
                    "image_id": image_id,
                    "details": {
                        "category": record.get('category', table_name.replace('image_', '')),
                        "caption": record.get('caption_raw', ''),
                        "facts": record.get('facts', {}),
                        "image_path": record.get('image_path', '')
                    }
                }
        
        # Image not found in any table
        return {
            "success": False,
            "error": f"Image with ID '{image_id}' not found in database",
            "image_id": image_id
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to retrieve image details: {str(e)}",
            "image_id": image_id
        }


@mcp.tool()
def get_database_stats() -> Dict[str, Any]:
    """
    Get statistics about the image database.
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating if retrieval was successful
        - stats: Database statistics by category
        - total_images: Total number of images across all categories
        - error: Error message if retrieval failed
    
    Example:
        {
            "success": true,
            "total_images": 30,
            "stats": {
                "indoor": {"count": 10, "table": "image_indoor"},
                "outdoor": {"count": 10, "table": "image_outdoor"},
                "street": {"count": 10, "table": "image_street"}
            }
        }
    """
    try:
        from supabase import create_client
        
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            return {
                "success": False,
                "error": "Supabase credentials not configured"
            }
        
        supabase = create_client(supabase_url, supabase_key)
        
        stats = {}
        total_count = 0
        
        for table_name in ['image_indoor', 'image_outdoor', 'image_street']:
            category = table_name.replace('image_', '')
            
            # Get count for this table
            response = supabase.table(table_name).select("file_id", count="exact").execute()
            count = response.count if hasattr(response, 'count') else len(response.data)
            
            stats[category] = {
                "count": count,
                "table": table_name
            }
            total_count += count
        
        return {
            "success": True,
            "total_images": total_count,
            "stats": stats
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to retrieve database stats: {str(e)}"
        }


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()

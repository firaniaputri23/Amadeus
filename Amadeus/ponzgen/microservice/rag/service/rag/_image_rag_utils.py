"""
Image RAG utilities for visual question answering.

This module provides functions for:
1. Embedding images and text queries using CLIP
2. Retrieving relevant images from vector database
3. Generating responses using VLM with visual context
"""

from ..storage_database._storage_utils import SupabaseStorageClient
from ..embedding._embedding_utils import EmbedderService
from ....agent_boilerplate.boilerplate.utils.get_llms import get_llms

import os
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from PIL import Image

embedder = EmbedderService()
storage_client = SupabaseStorageClient()


def generate_response_with_images(
    query: str, 
    retrieved_context: List[Tuple[str, float, Dict]], 
    model_name: str = "custom-vlm",
    temperature: float = 0
) -> str:
    """
    Generates a response from VLM based on query and retrieved image context.
    
    Args:
        query: User's question
        retrieved_context: List of (file_id, score, metadata) tuples
        model_name: Name of the model to use
        temperature: Model temperature
        
    Returns:
        Generated response text
    """
    llm = get_llms(model_name=model_name, temperature=temperature)
    
    # Format context with image information
    formatted_context = ""
    image_paths = []
    
    for i, (file_id, score, doc) in enumerate(retrieved_context):
        formatted_context += f"\n{'='*60}\n"
        formatted_context += f"Image {i+1} (ID: {file_id}, Relevance: {score:.4f})\n"
        formatted_context += f"Category: {doc.get('category', 'N/A')}\n"
        formatted_context += f"Caption: {doc.get('caption_raw', 'N/A')}\n"
        
        if doc.get('facts'):
            formatted_context += f"Facts: {doc['facts']}\n"
        
        if doc.get('image_path'):
            image_paths.append(doc['image_path'])
            formatted_context += f"Image Path: {doc['image_path']}\n"
    
    formatted_context += f"\n{'='*60}\n"
    
    # Create prompt for VLM
    prompt = f"""You are a helpful AI assistant with access to a database of images from various locations (indoor, outdoor, and street scenes).

Based on the retrieved images and their descriptions below, please answer the user's question accurately and in detail.

Query: {query}

Retrieved Image Context:
{formatted_context}

Please provide a comprehensive answer based on the visual information and descriptions provided. If the images contain relevant information, reference specific details from them. If you need to see the actual images to answer accurately, mention that.

Answer:"""
    
    # TODO: For actual multimodal input, we need to pass images to the model
    # For now, we'll use text-only context
    response = llm.invoke(prompt)
    return response.content


def retrieval_with_rerank(
    query: str,
    top_k: int = 5,
    category_filter: Optional[str] = None
) -> List[Tuple[str, float, Dict]]:
    """
    Retrieve and rerank images based on query similarity.
    Works with existing tables: image_indoor, image_outdoor, image_street
    
    Args:
        query: Search query
        top_k: Number of top results to return
        category_filter: Optional category filter ('indoor', 'outdoor', 'street')
        
    Returns:
        List of (file_id, similarity_score, metadata) tuples
    """
    from supabase import create_client
    import os
    
    # Generate query embedding
    query_embedding = embedder.embed_query(query)
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    client = create_client(supabase_url, supabase_key)
    
    # Determine which tables to search
    if category_filter:
        tables = [f"image_{category_filter}"]
    else:
        tables = ["image_indoor", "image_outdoor", "image_street"]
    
    all_results = []
    
    for table_name in tables:
        try:
            # Get all records with embeddings from this table
            response = client.table(table_name).select("*").execute()
            
            if not response.data:
                continue
            
            # Calculate cosine similarity for each record
            for record in response.data:
                if not record.get('embedding'):
                    continue
                
                # Calculate cosine similarity
                import numpy as np
                import json
                
                emb1 = np.array(query_embedding)
                # Parse embedding from string if needed
                emb2_raw = record['embedding']
                if isinstance(emb2_raw, str):
                    emb2 = np.array(json.loads(emb2_raw))
                else:
                    emb2 = np.array(emb2_raw)
                
                # Normalize
                emb1_norm = emb1 / np.linalg.norm(emb1)
                emb2_norm = emb2 / np.linalg.norm(emb2)
                
                # Cosine similarity
                similarity = np.dot(emb1_norm, emb2_norm)
                
                # Extract category from table name
                category = table_name.replace('image_', '')
                
                metadata = {
                    "image_id": record.get("image_id"),
                    "category": category,
                    "caption_raw": record.get("caption_raw"),
                    "facts": record.get("facts") or record.get("image_facts"),
                    "content": record.get("caption_raw", ""),
                    "image_path": record.get("image_url")
                }
                
                file_id = f"{category}_{record.get('image_id')}"
                all_results.append((file_id, float(similarity), metadata))
        
        except Exception as e:
            print(f"Error querying {table_name}: {e}")
            continue
    
    # Sort by similarity and return top_k
    all_results.sort(key=lambda x: x[1], reverse=True)
    return all_results[:top_k]


def retrieval_by_image(
    image_path: str,
    top_k: int = 5,
    category_filter: Optional[str] = None
) -> List[Tuple[str, float, Dict]]:
    """
    Retrieve similar images based on an input image.
    Works with existing tables: image_indoor, image_outdoor, image_street
    
    Args:
        image_path: Path to the query image
        top_k: Number of top results to return
        category_filter: Optional category filter ('indoor', 'outdoor', 'street')
        
    Returns:
        List of (file_id, similarity_score, metadata) tuples
    """
    from supabase import create_client
    import os
    
    # Generate image embedding
    image_embedding = embedder.embed_image(image_path)
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    client = create_client(supabase_url, supabase_key)
    
    # Determine which tables to search
    if category_filter:
        tables = [f"image_{category_filter}"]
    else:
        tables = ["image_indoor", "image_outdoor", "image_street"]
    
    all_results = []
    
    for table_name in tables:
        try:
            # Get all records with embeddings from this table
            response = client.table(table_name).select("*").execute()
            
            if not response.data:
                continue
            
            # Calculate cosine similarity for each record
            for record in response.data:
                if not record.get('embedding'):
                    continue
                
                # Calculate cosine similarity
                import numpy as np
                import json
                
                emb1 = np.array(image_embedding)
                # Parse embedding from string if needed
                emb2_raw = record['embedding']
                if isinstance(emb2_raw, str):
                    emb2 = np.array(json.loads(emb2_raw))
                else:
                    emb2 = np.array(emb2_raw)
                
                # Normalize
                emb1_norm = emb1 / np.linalg.norm(emb1)
                emb2_norm = emb2 / np.linalg.norm(emb2)
                
                # Cosine similarity
                similarity = np.dot(emb1_norm, emb2_norm)
                
                # Extract category from table name
                category = table_name.replace('image_', '')
                
                metadata = {
                    "image_id": record.get("image_id"),
                    "category": category,
                    "caption_raw": record.get("caption_raw"),
                    "facts": record.get("facts") or record.get("image_facts"),
                    "content": record.get("caption_raw", ""),
                    "image_path": record.get("image_url")
                }
                
                file_id = f"{category}_{record.get('image_id')}"
                all_results.append((file_id, float(similarity), metadata))
        
        except Exception as e:
            print(f"Error querying {table_name}: {e}")
            continue
    
    # Sort by similarity and return top_k
    all_results.sort(key=lambda x: x[1], reverse=True)
    return all_results[:top_k]


def hybrid_search(
    query: str,
    search_text: Optional[str] = None,
    category_filter: Optional[str] = None,
    top_k: int = 5
) -> List[Tuple[str, float, Dict]]:
    """
    Perform hybrid search combining vector similarity and text search.
    Works with existing tables: image_indoor, image_outdoor, image_street
    
    Args:
        query: Query for embedding-based search
        search_text: Optional text to search in captions/content
        category_filter: Optional category filter
        top_k: Number of results
        
    Returns:
        List of (file_id, similarity_score, metadata) tuples
    """
    from supabase import create_client
    import os
    import numpy as np
    
    query_embedding = embedder.embed_query(query)
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    client = create_client(supabase_url, supabase_key)
    
    # Determine which tables to search
    if category_filter:
        tables = [f"image_{category_filter}"]
    else:
        tables = ["image_indoor", "image_outdoor", "image_street"]
    
    all_results = []
    
    for table_name in tables:
        try:
            # Build query
            query_builder = client.table(table_name).select("*")
            
            # Apply text filter if provided
            if search_text:
                query_builder = query_builder.ilike("caption_raw", f"%{search_text}%")
            
            response = query_builder.execute()
            
            if not response.data:
                continue
            
            # Calculate similarities
            for record in response.data:
                if not record.get('embedding'):
                    continue
                
                emb1 = np.array(query_embedding)
                emb2 = np.array(record['embedding'])
                emb1_norm = emb1 / np.linalg.norm(emb1)
                emb2_norm = emb2 / np.linalg.norm(emb2)
                similarity = np.dot(emb1_norm, emb2_norm)
                
                category = table_name.replace('image_', '')
                
                metadata = {
                    "image_id": record.get("image_id"),
                    "category": category,
                    "caption_raw": record.get("caption_raw"),
                    "facts": record.get("facts") or record.get("image_facts"),
                    "content": record.get("caption_raw", ""),
                    "image_path": record.get("image_url")
                }
                
                file_id = f"{category}_{record.get('image_id')}"
                all_results.append((file_id, float(similarity), metadata))
        
        except Exception as e:
            print(f"Error in hybrid search on {table_name}: {e}")
            continue
    
    # Sort and return top_k
    all_results.sort(key=lambda x: x[1], reverse=True)
    return all_results[:top_k]


def get_image_by_id(image_id: str, category: Optional[str] = None) -> Optional[Dict]:
    """
    Retrieve a specific image by its image_id.
    
    Args:
        image_id: The image identifier (e.g., "F009.jpg")
        category: Optional category to narrow search ('indoor', 'outdoor', 'street')
        
    Returns:
        Dictionary with image metadata or None if not found
    """
    try:
        from supabase import create_client
        import os
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        client = create_client(supabase_url, supabase_key)
        
        # Determine which tables to search
        if category:
            tables = [f"image_{category}"]
        else:
            tables = ["image_indoor", "image_outdoor", "image_street"]
        
        for table_name in tables:
            response = client.table(table_name).select("*").eq("image_id", image_id).execute()
            
            if response.data and len(response.data) > 0:
                record = response.data[0]
                # Add category info
                record['category'] = table_name.replace('image_', '')
                # Normalize field names
                if 'image_facts' in record and 'facts' not in record:
                    record['facts'] = record['image_facts']
                if 'image_url' in record:
                    record['image_path'] = record['image_url']
                return record
        
        return None
    except Exception as e:
        print(f"Error retrieving image: {e}")
        return None


# Legacy function for backward compatibility
def generate_response(query, retrieved_context, model_name="custom-vlm", temperature=0):
    """
    Legacy function wrapper - redirects to generate_response_with_images.
    """
    return generate_response_with_images(query, retrieved_context, model_name, temperature)


if __name__ == "__main__":
    print("Testing Image RAG system...")
    print("=" * 60)
    
    # Test 1: Basic retrieval
    print("\n🔍 Test 1: Basic Retrieval")
    query = "Show me indoor spaces with people working"
    print(f"Query: {query}")
    
    retrieved_context = retrieval_with_rerank(query, top_k=3)
    
    print(f"\nTop {len(retrieved_context)} results:")
    for i, (file_id, score, metadata) in enumerate(retrieved_context, 1):
        print(f"\n{i}. Similarity: {score:.4f}")
        print(f"   File ID: {file_id}")
        print(f"   Category: {metadata.get('category')}")
        print(f"   Caption: {metadata.get('caption_raw', '')[:100]}...")
    
    # Test 2: Category filter
    print("\n" + "=" * 60)
    print("\n🔍 Test 2: Category Filter (outdoor)")
    query = "outdoor scenes"
    print(f"Query: {query}")
    
    retrieved_context = retrieval_with_rerank(query, top_k=3, category_filter="outdoor")
    print(f"\nFound {len(retrieved_context)} outdoor images")
    
    # Test 3: Generate response
    print("\n" + "=" * 60)
    print("\n🤖 Test 3: Generate Response")
    query = "What indoor activities can you see in the images?"
    print(f"Query: {query}")
    
    retrieved_context = retrieval_with_rerank(query, top_k=3, category_filter="indoor")
    response = generate_response_with_images(query, retrieved_context)
    
    print(f"\nResponse:\n{response}")
    
    print("\n" + "=" * 60)
    print("✅ Testing complete!")

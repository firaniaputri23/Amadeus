"""
RAG Router

This module provides routes for file management and retrieval-augmented generation (RAG).
"""

from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from typing import List
from ..service.storage_database._storage_utils import SupabaseStorageClient
from ..service.rag._rag_utils import retrieval_with_rerank, generate_response

# Initialize router
router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)

# Initialize Supabase storage client
storage_client = SupabaseStorageClient()

# Define bucket name for file storage
BUCKET_ID = "users-files"


@router.post("/upload_file")
async def upload_file(
    user_id: str = Form(...),
    uploaded_file: UploadFile = File(...)
):
    """
    Upload a new file to Supabase storage.

    The file will be stored under the 'private/{user_id}/' folder if a user_id is provided,
    otherwise it will be placed under 'public/'.
    """
    try:
        file_name = uploaded_file.filename
        storage_path = f"private/{user_id}/{file_name}" if user_id else f"public/{file_name}"

        # Read the uploaded file into bytes
        file_content = await uploaded_file.read()

        # Upload the file to Supabase storage
        storage_client.upload_file(
            bucket_name=BUCKET_ID,
            storage_path=storage_path,
            file=file_content,
            content_type=uploaded_file.content_type
        )

        return {"status": "success", "path": storage_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update_file")
async def update_file(
    storage_path: str = Form(...),
    uploaded_file: UploadFile = File(...)
):
    """
    Replace an existing file in Supabase storage with a new file.
    """
    try:
        # Read the new file into bytes
        file_content = await uploaded_file.read()

        # Replace the file at the given storage path
        storage_client.replace_file(
            bucket_name=BUCKET_ID,
            storage_path=storage_path,
            file=file_content,
            content_type=uploaded_file.content_type
        )

        return {"status": "success", "path": storage_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/remove_file")
async def remove_file(
    files_path: List[str] = Form(...)
):
    """
    Remove one or more files from Supabase storage.
    """
    try:
        # Delete specified files
        storage_client.delete_files(
            bucket_name=BUCKET_ID,
            files_path=files_path
        )
        return {
            "status": "success",
            "message": f"{len(files_path)} file(s) removed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def run_rag(
    query: str = Form(...)
):
    """
    Perform retrieval-augmented generation (RAG) based on the input query.

    This will retrieve the most relevant context using reranking and generate a response.
    """
    try:
        # Retrieve context
        retrieved_context = retrieval_with_rerank(query=query)

        # Generate response
        response = generate_response(query, retrieved_context)

        return {"query": query, "response": response}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
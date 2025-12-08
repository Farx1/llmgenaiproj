"""Document upload and management API endpoints."""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import os
import aiofiles
from rag.document_processor import document_processor
from rag.vector_store import vector_store
from langchain.schema import Document

router = APIRouter()

# Directory for uploaded documents
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document.
    
    Args:
        file: Uploaded file
    
    Returns:
        Upload result with document IDs
    """
    try:
        # Save file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Process document
        documents = await document_processor.process_file(file_path)
        
        # Add to vector store
        doc_ids = vector_store.add_documents(documents)
        
        return {
            "message": "Document uploaded and processed successfully",
            "filename": file.filename,
            "chunks": len(documents),
            "document_ids": doc_ids
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")


@router.post("/upload-text")
async def upload_text(text: str, metadata: dict = None):
    """
    Upload text content directly.
    
    Args:
        text: Text content
        metadata: Optional metadata
    
    Returns:
        Upload result
    """
    try:
        # Process text
        documents = document_processor.process_text(text, metadata=metadata)
        
        # Add to vector store
        doc_ids = vector_store.add_documents(documents)
        
        return {
            "message": "Text uploaded and processed successfully",
            "chunks": len(documents),
            "document_ids": doc_ids
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading text: {str(e)}")


@router.get("/search")
async def search_documents(query: str, k: int = 4):
    """
    Search documents in the vector store.
    
    Args:
        query: Search query
        k: Number of results
    
    Returns:
        Search results
    """
    try:
        results = vector_store.similarity_search_with_score(query, k=k)
        
        return {
            "query": query,
            "results": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                }
                for doc, score in results
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching documents: {str(e)}")


@router.delete("/collection")
async def delete_collection():
    """Delete the entire collection."""
    try:
        vector_store.delete_collection()
        return {"message": "Collection deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting collection: {str(e)}")


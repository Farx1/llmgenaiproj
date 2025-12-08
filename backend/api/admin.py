"""Admin API endpoints."""
from fastapi import APIRouter
from rag.vector_store import vector_store
from agents.form_agent import FormAgent
import os

router = APIRouter()

# Lazy initialization pour éviter les erreurs au démarrage
_form_agent = None

def get_form_agent():
    """Get or create form agent instance."""
    global _form_agent
    if _form_agent is None:
        _form_agent = FormAgent()
    return _form_agent


@router.get("/stats")
async def get_stats():
    """Get system statistics."""
    try:
        collection_info = vector_store.get_collection_info()
        agent = get_form_agent()
        contacts = agent.get_contacts()
        
        return {
            "vector_store": collection_info,
            "contacts_count": len(contacts),
            "status": "operational"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }


@router.get("/contacts")
async def get_contacts():
    """Get all collected contacts."""
    try:
        agent = get_form_agent()
        contacts = agent.get_contacts()
        return {
            "contacts": contacts,
            "count": len(contacts)
        }
    except Exception as e:
        return {
            "error": str(e),
            "contacts": []
        }


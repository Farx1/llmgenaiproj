"""Chat API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from agents.orchestrator import OrchestratorAgent
from config import settings

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    model: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    answer: str
    metadata: Dict[str, Any]


# Global orchestrator instances (keyed by model name)
_orchestrators: Dict[str, OrchestratorAgent] = {}


def get_orchestrator(model_name: Optional[str] = None) -> OrchestratorAgent:
    """Get or create orchestrator instance for the specified model."""
    model_key = model_name or settings.ollama_default_model
    
    if model_key not in _orchestrators:
        _orchestrators[model_key] = OrchestratorAgent(model_name=model_key)
    
    return _orchestrators[model_key]


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message.
    
    Args:
        request: Chat request with message and history
    
    Returns:
        Chat response with answer and metadata
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Received chat request: model={request.model}, message={request.message[:50]}...")
        orchestrator = get_orchestrator(request.model)
        
        # Convert conversation history to the format expected by the agent
        history = []
        for msg in request.conversation_history:
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        logger.info(f"Processing query with orchestrator (history length: {len(history)})")
        
        # Process the query
        response = await orchestrator.process_query(
            query=request.message,
            conversation_history=history
        )
        
        logger.info(f"Orchestrator response received: answer length={len(response.get('answer', ''))}")
        logger.debug(f"Full response: {response}")
        
        # Ensure response has the correct format
        if not isinstance(response, dict):
            logger.error(f"Unexpected response type: {type(response)}")
            response = {"answer": str(response), "metadata": {}}
        
        if "answer" not in response:
            logger.error(f"Response missing 'answer' key: {response}")
            response["answer"] = "I received an unexpected response format."
        
        if "metadata" not in response:
            response["metadata"] = {}
        
        return ChatResponse(**response)
        
    except Exception as e:
        import traceback
        logger.error(f"Error processing chat: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@router.get("/models")
async def get_available_models():
    """Get list of available models (only installed models)."""
    import httpx
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Récupérer les modèles installés depuis Ollama
    installed_models_full = []
    try:
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            # Extraire les noms de modèles (avec leurs tags complets)
            installed_models_full = [model.get("name", "") for model in data.get("models", [])]
            logger.info(f"Modèles installés détectés depuis Ollama: {installed_models_full}")
        else:
            logger.warning(f"Ollama API returned status {response.status_code}")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des modèles depuis Ollama: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # En cas d'erreur, retourner une liste vide plutôt que les modèles configurés
        # pour éviter d'afficher des modèles qui ne sont pas réellement installés
        return {
            "models": [],
            "default": settings.ollama_default_model
        }
    
    # Si aucun modèle n'est installé, retourner une liste vide
    if not installed_models_full:
        logger.warning("Aucun modèle installé détecté dans Ollama")
        return {
            "models": [],
            "default": settings.ollama_default_model
        }
    
    # Filtrer pour ne garder que les modèles configurés qui sont installés
    # Mais aussi inclure tous les modèles installés si aucun n'est configuré
    available_models = []
    configured_bases = [m.split(":")[0] for m in settings.ollama_available_models]
    
    for installed_model in installed_models_full:
        installed_base = installed_model.split(":")[0]
        # Si le modèle est dans la liste configurée OU si aucun modèle configuré n'est installé
        if installed_base in configured_bases:
            available_models.append(installed_model)
    
    # Si aucun modèle configuré n'est installé, retourner tous les modèles installés
    if not available_models and installed_models_full:
        logger.info("Aucun modèle configuré n'est installé, retour de tous les modèles installés")
        available_models = installed_models_full
    
    # Déterminer le modèle par défaut
    default_model = settings.ollama_default_model
    if default_model not in available_models:
        # Chercher une variante du modèle par défaut
        default_base = default_model.split(":")[0]
        for model in available_models:
            if model.split(":")[0] == default_base:
                default_model = model
                logger.info(f"Modèle par défaut trouvé: {default_model}")
                break
        else:
            # Si aucune variante trouvée, utiliser le premier disponible
            if available_models:
                default_model = available_models[0]
                logger.info(f"Utilisation du premier modèle disponible comme défaut: {default_model}")
            else:
                logger.warning(f"Aucun modèle disponible, utilisation du défaut configuré: {default_model}")
    
    logger.info(f"Modèles disponibles retournés: {available_models}, défaut: {default_model}")
    
    return {
        "models": available_models,
        "default": default_model
    }


"""Chat API endpoints."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, AsyncGenerator
import json
import asyncio
from agents.orchestrator import OrchestratorAgent
from config import settings
import logging

logger = logging.getLogger(__name__)

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
    Process a chat message (non-streaming endpoint for backward compatibility).
    
    Args:
        request: Chat request with message and history
    
    Returns:
        Chat response with answer and metadata
    """
    import time
    start_time = time.time()
    
    logger.info("=" * 70)
    logger.info("DEBUG: ========== CHAT REQUEST RECEIVED ==========")
    logger.info(f"DEBUG: Model: {request.model}")
    logger.info(f"DEBUG: Message (first 100 chars): {request.message[:100]}")
    logger.info(f"DEBUG: History length: {len(request.conversation_history)}")
    logger.info(f"DEBUG: Request received at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    # Flush logs immediately to ensure they appear
    import sys
    sys.stdout.flush()
    
    try:
        logger.info("DEBUG: Getting orchestrator...")
        orchestrator = get_orchestrator(request.model)
        logger.info(f"DEBUG: ✅ Orchestrator retrieved: {type(orchestrator)}")
        
        # Convert conversation history to the format expected by the agent
        history = []
        for msg in request.conversation_history:
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        logger.info(f"DEBUG: Converted history: {len(history)} messages")
        
        logger.info("DEBUG: Calling orchestrator.process_query()...")
        process_start = time.time()
        
        # Process the query with timeout
        try:
            response = await asyncio.wait_for(
                orchestrator.process_query(
                    query=request.message,
                    conversation_history=history
                ),
                timeout=120.0  # 2 minutes timeout
            )
            process_time = time.time() - process_start
            logger.info(f"DEBUG: ✅ Orchestrator response received in {process_time:.2f}s")
            logger.info(f"DEBUG: Answer length: {len(response.get('answer', ''))}")
        except asyncio.TimeoutError:
            logger.error("DEBUG: ❌ Orchestrator timeout after 120 seconds")
            raise HTTPException(status_code=504, detail="Request timeout: The query took too long to process.")
        
        logger.debug(f"DEBUG: Full response keys: {response.keys() if isinstance(response, dict) else 'Not a dict'}")
        
        # Ensure response has the correct format
        if not isinstance(response, dict):
            logger.error(f"DEBUG: ❌ Unexpected response type: {type(response)}")
            response = {"answer": str(response), "metadata": {}}
        
        if "answer" not in response:
            logger.error(f"DEBUG: ❌ Response missing 'answer' key: {response}")
            response["answer"] = "I received an unexpected response format."
        
        if "metadata" not in response:
            response["metadata"] = {}
        
        total_time = time.time() - start_time
        logger.info("=" * 70)
        logger.info(f"DEBUG: ✅ CHAT REQUEST COMPLETED in {total_time:.2f}s")
        logger.info("=" * 70)
        
        return ChatResponse(**response)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        total_time = time.time() - start_time
        logger.error("=" * 70)
        logger.error(f"DEBUG: ❌❌❌ ERROR in chat endpoint after {total_time:.2f}s")
        logger.error(f"DEBUG: Error: {str(e)}")
        logger.error(f"DEBUG: Error type: {type(e)}")
        logger.error(f"DEBUG: Full traceback:\n{traceback.format_exc()}")
        logger.error("=" * 70)
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Process a chat message with streaming response for better memory efficiency.
    
    Args:
        request: Chat request with message and history
    
    Returns:
        Streaming response with chunks of the answer
    """
    import time
    start_time = time.time()
    
    # Log immediately when endpoint is called
    logger.info("=" * 70)
    logger.info("DEBUG: ========== STREAMING CHAT REQUEST RECEIVED ==========")
    logger.info(f"DEBUG: Model: {request.model}")
    logger.info(f"DEBUG: Message (first 100 chars): {request.message[:100]}")
    logger.info(f"DEBUG: History length: {len(request.conversation_history)}")
    logger.info(f"DEBUG: Request received at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    # Flush logs immediately to ensure they appear
    import sys
    sys.stdout.flush()
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            logger.info("DEBUG: Getting orchestrator for streaming...")
            orchestrator = get_orchestrator(request.model)
            logger.info(f"DEBUG: ✅ Orchestrator retrieved: {type(orchestrator)}")
            
            # Convert conversation history to the format expected by the agent
            history = []
            for msg in request.conversation_history:
                history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            logger.info(f"DEBUG: Converted history: {len(history)} messages")
            
            logger.info("DEBUG: Starting streaming query...")
            stream_start = time.time()
            
            # Add a server-side timeout for the streaming process
            timeout_seconds = 90  # 90 seconds timeout for streaming
            
            chunk_count = 0
            # Use streaming version if available, otherwise fallback to regular processing
            if hasattr(orchestrator, 'process_query_stream'):
                logger.info("DEBUG: Using process_query_stream()...")
                try:
                    # Create a wrapper that handles timeout manually
                    stream_gen = orchestrator.process_query_stream(
                        query=request.message,
                        conversation_history=history
                    )
                    
                    # Consume the stream with manual timeout checking
                    last_chunk_time = time.time()
                    async for chunk in stream_gen:
                        # Check for timeout
                        elapsed = time.time() - stream_start
                        if elapsed > timeout_seconds:
                            logger.error(f"DEBUG: ❌ Streaming chat timed out after {elapsed:.2f}s ({timeout_seconds}s limit)")
                            yield f"data: {json.dumps({'type': 'error', 'error': 'Server timed out while generating response. Please try again.'})}\n\n"
                            break
                        
                        chunk_count += 1
                        if chunk_count % 10 == 0:
                            logger.debug(f"DEBUG: Streamed {chunk_count} chunks so far...")
                        yield f"data: {json.dumps(chunk)}\n\n"
                        last_chunk_time = time.time()
                    
                    stream_time = time.time() - stream_start
                    logger.info(f"DEBUG: ✅ Streaming completed: {chunk_count} chunks in {stream_time:.2f}s")
                except asyncio.TimeoutError:
                    stream_time = time.time() - stream_start
                    logger.error(f"DEBUG: ❌ Streaming chat timed out after {stream_time:.2f}s ({timeout_seconds}s limit)")
                    yield f"data: {json.dumps({'type': 'error', 'error': 'Server timed out while generating response. Please try again.'})}\n\n"
                except Exception as e:
                    stream_time = time.time() - stream_start
                    logger.error(f"DEBUG: ❌ Streaming error after {stream_time:.2f}s: {str(e)}")
                    import traceback
                    logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
                    yield f"data: {json.dumps({'type': 'error', 'error': f'Error during streaming: {str(e)}'})}\n\n"
            else:
                logger.info("DEBUG: process_query_stream() not available, using fallback...")
                # Fallback: process normally and stream chunks
                response = await orchestrator.process_query(
                    query=request.message,
                    conversation_history=history
                )
                
                answer = response.get("answer", "")
                metadata = response.get("metadata", {})
                
                # Stream metadata first
                yield f"data: {json.dumps({'type': 'metadata', 'data': metadata})}\n\n"
                
                # Stream answer in chunks
                chunk_size = 50  # Stream in small chunks for better UX
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i:i + chunk_size]
                    chunk_count += 1
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for smoother streaming
                
                stream_time = time.time() - stream_start
                logger.info(f"DEBUG: ✅ Fallback streaming completed: {chunk_count} chunks in {stream_time:.2f}s")
                
                # Stream completion
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
            total_time = time.time() - start_time
            logger.info("=" * 70)
            logger.info(f"DEBUG: ✅ STREAMING REQUEST COMPLETED in {total_time:.2f}s")
            logger.info("=" * 70)
                
        except Exception as e:
            import traceback
            total_time = time.time() - start_time
            logger.error("=" * 70)
            logger.error(f"DEBUG: ❌❌❌ ERROR in streaming chat after {total_time:.2f}s")
            logger.error(f"DEBUG: Error: {str(e)}")
            logger.error(f"DEBUG: Error type: {type(e)}")
            logger.error(f"DEBUG: Full traceback:\n{traceback.format_exc()}")
            logger.error("=" * 70)
            error_chunk = {
                "type": "error",
                "error": f"Error processing chat: {str(e)}"
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
    )


@router.get("/models")
async def get_available_models():
    """
    Get list of available models - only local models effective for RAG agents.
    Excludes cloud models and models that are not suitable for local RAG.
    """
    import httpx
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Liste des modèles recommandés pour un agent RAG local (efficaces et performants)
        # Ces modèles sont optimisés pour le RAG : bon équilibre performance/vitesse, support multilingue
        recommended_rag_models = [
        # Llama 3.x - Excellents pour RAG, bon support français/anglais
        "llama3.1",
        "llama3.1:8b",
        "llama3.1:70b",
        "llama3",
        "llama3:8b",
        "llama3:70b",
        
        # Mistral - Très bon pour le français
        "mistral",
        "mistral:7b",
        "mistral:latest",
        
        # Mixtral - Plus puissant, bon pour RAG complexe
        "mixtral",
        "mixtral:8x7b",
        "mixtral:latest",
        
        # Qwen2.5 - Excellent multilingue, très bon pour RAG
        "qwen2.5",
        "qwen2.5:7b",
        "qwen2.5:14b",
        "qwen2.5:32b",
        "qwen2.5:72b",
        
        # Gemma2 - Google, bon équilibre
        "gemma2",
        "gemma2:9b",
        "gemma2:27b",
        
        # Phi3 - Microsoft, compact et efficace
        "phi3",
        "phi3:medium",
        "phi3:mini",
        
        # DeepSeek - Bon pour RAG
        "deepseek-r1",
        "deepseek-r1:7b",
        "deepseek-r1:14b",
        ]
        
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
        
        # Filtrer pour ne garder que les modèles locaux efficaces pour RAG
        available_models = []
        
        for installed_model in installed_models_full:
            model_name_lower = installed_model.lower()
            model_base = installed_model.split(":")[0].lower()
            
            # Exclure les modèles cloud
            if "cloud" in model_name_lower:
                logger.debug(f"Exclu (cloud): {installed_model}")
                continue
            
            # Exclure les modèles ministral (souvent cloud ou non optimisés)
            if "ministral" in model_name_lower:
                logger.debug(f"Exclu (ministral): {installed_model}")
                continue
            
            # Vérifier si le modèle est dans la liste recommandée
            is_recommended = False
            for recommended in recommended_rag_models:
                recommended_base = recommended.split(":")[0].lower()
                if model_base == recommended_base:
                    is_recommended = True
                    break
            
            if is_recommended:
                available_models.append(installed_model)
                logger.debug(f"Inclus (recommandé): {installed_model}")
            else:
                logger.debug(f"Exclu (non recommandé pour RAG): {installed_model}")
        
        # Si aucun modèle recommandé n'est installé, inclure quand même les modèles locaux
        # (mais toujours exclure les cloud)
        if not available_models:
            logger.info("Aucun modèle recommandé trouvé, inclusion des modèles locaux non-cloud")
            for installed_model in installed_models_full:
                model_name_lower = installed_model.lower()
                if "cloud" not in model_name_lower and "ministral" not in model_name_lower:
                    available_models.append(installed_model)
        
        # Trier les modèles (prioriser les versions latest, puis par taille)
        def sort_key(model):
            parts = model.split(":")
            base = parts[0].lower()
            tag = parts[1].lower() if len(parts) > 1 else ""
            
            # Priorité : latest > versions numériques > autres
            if tag == "latest":
                return (0, base)
            elif tag.replace("b", "").isdigit():
                size = int(tag.replace("b", ""))
                return (1, -size, base)  # Plus grand d'abord
            else:
                return (2, base)
        
        available_models.sort(key=sort_key)
        
        # Déterminer le modèle par défaut
        default_model = settings.ollama_default_model
        if default_model not in available_models:
            # Chercher une variante du modèle par défaut
            default_base = default_model.split(":")[0].lower()
            for model in available_models:
                if model.split(":")[0].lower() == default_base:
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
        
        logger.info(f"Modèles disponibles retournés ({len(available_models)}): {available_models}, défaut: {default_model}")
        
        return {
            "models": available_models,
            "default": default_model
        }
    except Exception as e:
        import traceback
        logger.error(f"Erreur dans get_available_models: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Retourner une réponse par défaut même en cas d'erreur
        return {
            "models": [],
            "default": settings.ollama_default_model
        }


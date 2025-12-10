"""Embeddings factory for creating embedding instances."""
import os
from typing import List
from config import settings


class OllamaEmbeddingsWrapper:
    """Wrapper for Ollama embeddings to work as LangChain embeddings."""
    def __init__(self, model: str, base_url: str):
        import ollama
        self.model = model
        self.base_url = base_url
        self.client = ollama.Client(host=base_url)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        response = self.client.embeddings(
            model=self.model,
            prompt=text
        )
        return response.get("embedding", [])
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents."""
        return [self.embed_query(text) for text in texts]


def get_embeddings(model_name: str = None):
    """
    Get an embeddings instance.
    Uses HuggingFace sentence-transformers by default (more efficient than Ollama, as shown in the notebook).
    Falls back to Ollama if sentence-transformers is not available or if use_ollama_embeddings is True.
    
    Args:
        model_name: Name of the embedding model to use (for Ollama fallback)
    
    Returns:
        Embeddings instance
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Check if we should use Ollama embeddings
    if settings.use_ollama_embeddings:
        logger.info("Using Ollama embeddings (use_ollama_embeddings=True)")
        try:
            from langchain_ollama import OllamaEmbeddings
            return OllamaEmbeddings(
                model=model_name or "llama3",
                base_url=settings.ollama_base_url
            )
        except ImportError:
            return OllamaEmbeddingsWrapper(
                model=model_name or "llama3",
                base_url=settings.ollama_base_url
            )
    
    # Try to use HuggingFace embeddings first (more efficient, as shown in the notebook)
    try:
        # Try new langchain-huggingface package first
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            emb_model = os.environ.get("EMB_MODEL", settings.embedding_model)
            logger.info(f"Using HuggingFaceEmbeddings with model: {emb_model}")
            return HuggingFaceEmbeddings(model_name=emb_model)
        except ImportError:
            # Fallback to langchain-community
            from langchain_community.embeddings import HuggingFaceEmbeddings
            emb_model = os.environ.get("EMB_MODEL", settings.embedding_model)
            logger.info(f"Using HuggingFaceEmbeddings (from langchain-community) with model: {emb_model}")
            return HuggingFaceEmbeddings(model_name=emb_model)
    except ImportError:
        # If sentence-transformers is not available, fallback to Ollama
        logger.warning("sentence-transformers not available, falling back to Ollama embeddings")
        
        # Try to use langchain-ollama if available
        try:
            from langchain_ollama import OllamaEmbeddings
            return OllamaEmbeddings(
                model=model_name or "llama3",
                base_url=settings.ollama_base_url
            )
        except ImportError:
            # Fallback to direct Ollama wrapper
            return OllamaEmbeddingsWrapper(
                model=model_name or "llama3",
                base_url=settings.ollama_base_url
            )


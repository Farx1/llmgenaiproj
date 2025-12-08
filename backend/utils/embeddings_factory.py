"""Embeddings factory for creating embedding instances."""
import ollama
from typing import List
from config import settings


class OllamaEmbeddingsWrapper:
    """Wrapper for Ollama embeddings to work as LangChain embeddings."""
    def __init__(self, model: str, base_url: str):
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


def get_embeddings(model_name: str = "llama3"):
    """
    Get an embeddings instance.
    
    Args:
        model_name: Name of the embedding model to use
    
    Returns:
        Embeddings instance
    """
    # Try to use langchain-ollama if available, otherwise use wrapper
    try:
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            model=model_name,
            base_url=settings.ollama_base_url
        )
    except ImportError:
        # Fallback to direct Ollama wrapper
        return OllamaEmbeddingsWrapper(
            model=model_name,
            base_url=settings.ollama_base_url
        )


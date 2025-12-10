"""Configuration management for the ESILV Smart Assistant."""
import os
from typing import List
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3"
    # Liste des modèles recommandés pour RAG (locaux uniquement, efficaces pour agents)
    # Priorité aux modèles avec grands context windows pour RAG ultra-long
    # Les modèles cloud sont automatiquement exclus par l'API
    ollama_available_models: List[str] = [
        # Ultra-long context (1M+ tokens) - Top pour RAG
        "qwen2.5",
        "qwen2.5:7b",
        "qwen2.5:14b",
        "qwen2.5:32b",
        "qwen2.5:72b",
        "qwen3",
        "qwen3:7b",
        "qwen3:14b",
        "qwen3:32b",
        "qwen3:72b",
        "internlm2.5",
        "internlm2.5:7b",
        "internlm2.5:20b",
        
        # Long context (128K-256K tokens) - Excellents pour RAG
        "llama3.1",
        "llama3.1:8b",
        "llama3.1:70b",
        "llama3.1:405b",
        "deepseek-v2",
        "deepseek-v2:16b",
        "deepseek-v2:236b",
        "deepseek-r1",
        "deepseek-r1:7b",
        "deepseek-r1:14b",
        "deepseek-r1:32b",
        "mistral-nemo",
        "mistral-nemo:12b",
        "mixtral",
        "mixtral:8x7b",
        "mixtral:8x22b",
        "gemma3",
        "gemma3:12b",
        "gemma3:27b",
        "phi3",
        "phi3:mini",
        "phi3:medium",
        "command-r+",
        "command-r+:35b",
        "command-r+:104b",
        
        # Legacy models (smaller context)
        "llama3",
        "llama3:8b",
        "llama3:70b",
        "mistral",
        "mistral:7b",
        "gemma2",
        "gemma2:9b"
    ]
    
    # ChromaDB Configuration
    chroma_persist_directory: str = "./chroma_db"
    chroma_collection_name: str = "esilv_docs"
    
    # Embeddings Configuration
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"  # More efficient than Ollama
    use_ollama_embeddings: bool = False  # Set to True to use Ollama embeddings instead
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # GCP Configuration (Optional)
    google_application_credentials: str = ""
    gcp_project_id: str = ""
    gcp_model_name: str = "gemini-pro"
    use_gcp: bool = False
    
    # ESILV Website
    esilv_base_url: str = "https://www.esilv.fr"
    
    # Crawl4AI Configuration (Open Source - No API Key Required)
    # Crawl4AI is used for web scraping - no API limits or costs
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from .env (like firecrawl_api_key)


settings = Settings()


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
    ollama_default_model: str = "ministral-3"
    ollama_available_models: List[str] = [
        "ministral-3",
        "mistral-large-3:675b-cloud",
        "mistral",
        "mistral:7b",
        "llama3"
    ]
    
    # ChromaDB Configuration
    chroma_persist_directory: str = "./chroma_db"
    chroma_collection_name: str = "esilv_docs"
    
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
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_file_encoding = "utf-8"


settings = Settings()


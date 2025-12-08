"""LLM factory for creating model instances."""
from typing import Optional, List, Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings

# Try to import langchain-ollama, fallback to direct ollama
try:
    from langchain_ollama import ChatOllama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    import ollama


class OllamaChatModel(BaseChatModel):
    """LangChain-compatible chat model using Ollama directly."""
    model: str
    base_url: str
    temperature: float = 0.7
    _client: Any = None  # Préfixe avec _ pour éviter Pydantic
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, model: str, base_url: str, temperature: float = 0.7, **kwargs):
        # Initialiser avec les paramètres requis pour Pydantic
        super().__init__(model=model, base_url=base_url, temperature=temperature, **kwargs)
        # Créer le client Ollama après l'initialisation en utilisant object.__setattr__
        host = base_url.replace("http://", "").replace("https://", "")
        if not OLLAMA_AVAILABLE:
            object.__setattr__(self, '_client', ollama.Client(host=host))
    
    @property
    def client(self):
        """Get the Ollama client."""
        return self._client
    
    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> ChatResult:
        """Generate a response from messages."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Convert LangChain messages to Ollama chat format directly
        ollama_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                ollama_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                ollama_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                ollama_messages.append({"role": "assistant", "content": msg.content})
        
        logger.info(f"Calling Ollama chat API for model {self.model} with {len(ollama_messages)} messages")
        
        try:
            # Use stream=False for non-streaming response and keep_alive to keep model in memory
            response = self._client.chat(
                model=self.model,
                messages=ollama_messages,
                options={"temperature": self.temperature},
                stream=False  # Explicitly disable streaming for better performance
            )
            
            # Extract response from chat API format
            # Ollama returns ChatResponse object with message attribute
            # The message can be a dict or a Message object
            message = response.get("message") if isinstance(response, dict) else getattr(response, "message", None)
            
            # Handle different response formats
            if message is None:
                text = ""
            elif isinstance(message, dict):
                text = message.get("content", "")
            elif hasattr(message, 'content'):
                # Direct access to Message object attribute
                text = message.content or ""
            elif isinstance(message, str):
                text = message
            else:
                # Fallback: try to convert to string and extract content
                text = str(message)
            
            # Fallback to response field if content is empty
            if not text:
                text = response.get("response", "")
            
            # Clean up the text - remove any metadata, HTML attributes, or escaped content
            if text:
                import re
                # Remove HTML-like attributes (e.g., content="...")
                text = re.sub(r'content=["\']([^"\']*)["\']', r'\1', text)
                # Remove common metadata patterns
                text = re.sub(r"role=['\"][^'\"]*['\"]\s*", "", text)
                text = re.sub(r"thinking=None\s*", "", text)
                text = re.sub(r"images=None\s*", "", text)
                text = re.sub(r"tool_name=None\s*", "", text)
                text = re.sub(r"tool_calls=None\s*", "", text)
                # Remove escaped newlines and other escape sequences
                text = text.replace('\\n', '\n').replace('\\t', '\t')
                # Remove any remaining HTML tags
                text = re.sub(r'<[^>]+>', '', text)
                text = text.strip()
            
            logger.info(f"Ollama response received (length: {len(text)})")
            
            message = AIMessage(content=text)
            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])
        except Exception as e:
            logger.error(f"Error calling Ollama: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> ChatResult:
        """Async generate - run sync generate in thread pool to avoid blocking."""
        import asyncio
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Starting async generate (running sync generate in thread pool)")
        # Run the synchronous _generate in a thread pool to avoid blocking
        try:
            result = await asyncio.to_thread(self._generate, messages, stop, **kwargs)
            logger.info("Async generate completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error in async generate: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return a default response instead of raising to avoid crashing
            from langchain_core.messages import AIMessage
            from langchain_core.outputs import ChatGeneration, ChatResult
            error_message = AIMessage(content=f"Erreur lors de la generation de la reponse: {str(e)}")
            generation = ChatGeneration(message=error_message)
            return ChatResult(generations=[generation])
    
    def _messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert LangChain messages to a prompt string."""
        prompt_parts = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                prompt_parts.append(f"Human: {msg.content}")
            elif isinstance(msg, AIMessage):
                prompt_parts.append(f"Assistant: {msg.content}")
            elif isinstance(msg, SystemMessage):
                prompt_parts.append(f"System: {msg.content}")
        return "\n".join(prompt_parts) + "\nAssistant:"
    
    @property
    def _llm_type(self) -> str:
        return "ollama"
    
    def bind_tools(self, tools):
        """Bind tools to the model (required for create_tool_calling_agent)."""
        # For Ollama, we can't bind tools directly, so return self
        # The tools will be handled by the agent executor
        return self


def get_llm(model_name: Optional[str] = None, use_gcp: Optional[bool] = None):
    """
    Get an LLM instance based on configuration.
    
    Args:
        model_name: Name of the model to use (overrides default)
        use_gcp: Whether to use GCP (overrides settings)
    
    Returns:
        LLM instance
    """
    use_gcp = use_gcp if use_gcp is not None else settings.use_gcp
    model_name = model_name or settings.ollama_default_model
    
    if use_gcp and settings.google_application_credentials:
        return ChatGoogleGenerativeAI(
            model=settings.gcp_model_name,
            temperature=0.7,
            google_api_key=settings.google_application_credentials
        )
    else:
        # Try to use langchain-ollama if available, otherwise use custom adapter
        if OLLAMA_AVAILABLE:
            return ChatOllama(
                model=model_name,
                base_url=settings.ollama_base_url,
                temperature=0.7
            )
        else:
            # Fallback to custom Ollama adapter
            return OllamaChatModel(
                model=model_name,
                base_url=settings.ollama_base_url,
                temperature=0.7
            )


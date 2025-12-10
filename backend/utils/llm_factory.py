"""LLM factory for creating model instances."""
from typing import Optional, List, Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings
import re
import logging

logger = logging.getLogger(__name__)

# Try to import langchain-ollama, fallback to direct ollama
try:
    from langchain_ollama import ChatOllama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    import ollama


# Model context window sizes (in tokens)
MODEL_CONTEXT_WINDOWS = {
    # Qwen2.5 / Qwen3 - Ultra-long context
    "qwen2.5": 1_000_000,  # Up to 1M tokens
    "qwen2.5:7b": 1_000_000,
    "qwen2.5:14b": 1_000_000,
    "qwen2.5:32b": 1_000_000,
    "qwen2.5:72b": 1_000_000,
    "qwen3": 2_000_000,  # Up to 2M tokens
    "qwen3:7b": 2_000_000,
    "qwen3:14b": 2_000_000,
    "qwen3:32b": 2_000_000,
    "qwen3:72b": 2_000_000,
    
    # Llama 3.1 - 128K context
    "llama3.1": 131_072,
    "llama3.1:8b": 131_072,
    "llama3.1:70b": 131_072,
    "llama3.1:405b": 131_072,
    
    # DeepSeek-V2 / R1 - Long context
    "deepseek-v2": 262_144,  # 256K
    "deepseek-v2:16b": 262_144,
    "deepseek-v2:236b": 262_144,
    "deepseek-r1": 262_144,
    "deepseek-r1:7b": 262_144,
    "deepseek-r1:14b": 262_144,
    "deepseek-r1:32b": 262_144,
    
    # Mistral Nemo / Mixtral - 128K context
    "mistral-nemo": 131_072,
    "mistral-nemo:12b": 131_072,
    "mixtral": 131_072,
    "mixtral:8x7b": 131_072,
    "mixtral:8x22b": 131_072,
    
    # Gemma 3 / Phi-3 - 128K context
    "gemma3": 131_072,
    "gemma3:12b": 131_072,
    "gemma3:27b": 131_072,
    "phi3": 131_072,
    "phi3:mini": 131_072,
    "phi3:medium": 131_072,
    
    # Command R+ / InternLM2.5 - Long context
    "command-r+": 131_072,
    "command-r+:35b": 131_072,
    "command-r+:104b": 131_072,
    "internlm2.5": 1_000_000,  # Up to 1M
    "internlm2.5:7b": 1_000_000,
    "internlm2.5:20b": 1_000_000,
    
    # Legacy models (default to smaller context)
    "llama3": 8_192,  # Llama 3 base has 8K
    "llama3:8b": 8_192,
    "llama3:70b": 8_192,
    "mistral": 32_768,  # Mistral 7B has 32K
    "mistral:7b": 32_768,
    "gemma2": 8_192,
    "gemma2:9b": 8_192,
}


def get_model_context_window(model_name: str) -> int:
    """
    Get the context window size for a given model.
    
    Args:
        model_name: Name of the model (e.g., "qwen2.5:7b", "llama3.1")
    
    Returns:
        Context window size in tokens (default: 4096 for unknown models)
    """
    if not model_name:
        return 4096  # Default safe value
    
    model_lower = model_name.lower().strip()
    
    # Try exact match first
    if model_lower in MODEL_CONTEXT_WINDOWS:
        return MODEL_CONTEXT_WINDOWS[model_lower]
    
    # Try partial matches (e.g., "qwen2.5:7b-instruct" -> "qwen2.5:7b")
    for key, context_size in MODEL_CONTEXT_WINDOWS.items():
        if model_lower.startswith(key) or key in model_lower:
            return context_size
    
    # Try to detect model family
    if "qwen" in model_lower:
        if "qwen3" in model_lower:
            return 2_000_000  # Qwen3
        return 1_000_000  # Qwen2.5
    elif "llama3.1" in model_lower:
        return 131_072  # 128K
    elif "deepseek" in model_lower:
        return 262_144  # 256K
    elif "mixtral" in model_lower or "mistral-nemo" in model_lower:
        return 131_072  # 128K
    elif "gemma3" in model_lower or "phi3" in model_lower:
        return 131_072  # 128K
    elif "command-r" in model_lower or "internlm2.5" in model_lower:
        return 131_072  # 128K
    elif "llama3" in model_lower:
        return 8_192  # Llama 3 base
    elif "mistral" in model_lower:
        return 32_768  # Mistral 7B
    
    # Default fallback
    logger.warning(f"Unknown model '{model_name}', using default context window of 4096 tokens")
    return 4096


def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text.
    Uses a simple heuristic: ~4 characters per token for English/French.
    More accurate for multilingual content.
    
    Args:
        text: Text to estimate
    
    Returns:
        Estimated number of tokens
    """
    if not text:
        return 0
    # Rough estimate: 1 token ≈ 4 characters for French/English
    # This is conservative and works well for RAG context estimation
    return len(text) // 4


def fix_word_duplication(text: str) -> str:
    """
    Fix word duplication issues including:
    - Character-level: "EEssiilvv" -> "Esilv"
    - Word-level: "LeLe" -> "Le"
    - Partial duplicates: "ParParccoursours" -> "Parcours"
    - Sentence-level: "Le Parcours Quantique est un outil Le Parcours Quantique est un outil" -> "Le Parcours Quantique est un outil"
    - Loop detection: Cut off if a sequence repeats identically
    """
    if not text:
        return text
    
    # Step 0: Detect and cut loops (identical sequences repeating)
    # Check for repeated sequences of 20+ characters
    for seq_len in range(50, 10, -5):  # Check sequences from 50 to 10 chars
        if len(text) < seq_len * 2:
            continue
        for start_pos in range(len(text) - seq_len * 2):
            seq = text[start_pos:start_pos + seq_len]
            next_seq = text[start_pos + seq_len:start_pos + seq_len * 2]
            if seq == next_seq:
                # Found a loop - cut at the start of the repetition
                logger.warning(f"DEBUG: Detected loop at position {start_pos + seq_len}, cutting response")
                text = text[:start_pos + seq_len]
                break
        else:
            continue
        break  # Break outer loop if inner loop found a match
    
    # Step 1: Remove character-level duplicates (e.g., "EEssiilvv" -> "Esilv")
    cleaned = ""
    for i, char in enumerate(text):
        if i == 0 or char != text[i-1]:
            cleaned += char
    text = cleaned
    
    # Step 2: Fix partial word duplicates within words
    def fix_partial_duplicates(text_inner):
        pattern = r'\b([A-Za-z]{2,4})\1([A-Za-z]+)\2?\b'
        
        def replace_dup(match):
            prefix = match.group(1)
            rest = match.group(2)
            if len(rest) > len(prefix) and rest.startswith(prefix.lower()):
                return prefix + rest[len(prefix):]
            return prefix + rest
        
        for _ in range(3):
            text_inner = re.sub(pattern, replace_dup, text_inner)
        return text_inner
    
    text = fix_partial_duplicates(text)
    
    # Step 3: Remove duplicate sentences/phrases (check for repeated sentence patterns)
    # Split by sentences (periods, exclamation, question marks)
    sentences = re.split(r'([.!?]\s+)', text)
    deduplicated_sentences = []
    seen_sentences = set()
    
    i = 0
    while i < len(sentences):
        sentence = sentences[i].strip()
        if not sentence:
            i += 1
            continue
        
        # Check if this sentence (or a significant part of it) was already seen
        # Normalize: lowercase, remove extra spaces
        normalized = re.sub(r'\s+', ' ', sentence.lower().strip())
        
        # Skip if we've seen this sentence before (or a very similar one)
        if normalized in seen_sentences:
            # Skip this sentence and its punctuation if present
            if i + 1 < len(sentences) and sentences[i + 1] in ['. ', '! ', '? ']:
                i += 2
            else:
                i += 1
            continue
        
        # Check for partial sentence duplication (e.g., sentence starts with previous sentence)
        is_duplicate = False
        for seen in seen_sentences:
            # If current sentence starts with a seen sentence (or vice versa), it's likely a duplicate
            if len(normalized) > 20 and len(seen) > 20:
                if normalized.startswith(seen[:30]) or seen.startswith(normalized[:30]):
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            deduplicated_sentences.append(sentence)
            if i + 1 < len(sentences) and sentences[i + 1] in ['. ', '! ', '? ']:
                deduplicated_sentences.append(sentences[i + 1])
            seen_sentences.add(normalized)
        
        i += 1
    
    text = ''.join(deduplicated_sentences)
    
    # Step 4: Remove duplicate words (final pass)
    words = text.split()
    deduplicated_words = []
    for i, word in enumerate(words):
        if i > 0 and len(word) > 1:
            prev_word = words[i-1]
            if word.startswith(prev_word) and len(word) > len(prev_word):
                continue
            if word == prev_word:
                continue
            if len(prev_word) > 3 and word.startswith(prev_word[:len(prev_word)//2]):
                continue
        deduplicated_words.append(word)
    
    return " ".join(deduplicated_words)


class OllamaChatModel(BaseChatModel):
    """LangChain-compatible chat model using Ollama directly."""
    model: str
    base_url: str
    temperature: float = 0.0
    _client: Any = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, model: str, base_url: str, temperature: float = 0.0, **kwargs):
        super().__init__(model=model, base_url=base_url, temperature=temperature, **kwargs)
        host = base_url.replace("http://", "").replace("https://", "")
        if not OLLAMA_AVAILABLE:
            object.__setattr__(self, '_client', ollama.Client(host=host))
    
    @property
    def client(self):
        """Get the Ollama client."""
        return self._client
    
    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> ChatResult:
        """Generate a response from messages."""
        # Convert LangChain messages to Ollama chat format
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
            # Optimized parameters to prevent duplication and ensure RAG usage
            # Based on Llama3 best practices: temperature 0.7-0.9, repeat_penalty 1.1-1.2
            response = self._client.chat(
                model=self.model,
                messages=ollama_messages,
                options={
                    "temperature": 0.8,  # Increased from 0.0 to prevent repetition loops (Llama3 best practice)
                    "num_ctx": 4096,  # Large context for RAG
                    "num_predict": 1024,  # Allow detailed responses
                    "repeat_penalty": 1.15,  # Reduced from 1.5 to 1.15 (Llama3 best practice: 1.1-1.2)
                    "repeat_last_n": 64,  # Reduced from 128 to 64 (less aggressive lookback)
                    "top_p": 0.9,  # Slightly reduced from 0.95 for better diversity
                    "top_k": 40,  # Reduced from 50 to 40 (Llama3 recommendation)
                    "tfs_z": 1.0,  # Tail free sampling
                    "typical_p": 1.0,  # Typical sampling
                    "keep_alive": "2m"
                },
                stream=False  # No streaming for simplicity
            )
            
            # Extract response content
            message = response.get("message") if isinstance(response, dict) else getattr(response, "message", None)
            
            if message is None:
                text = ""
            elif isinstance(message, dict):
                text = message.get("content", "")
            elif hasattr(message, 'content'):
                text = message.content or ""
            elif isinstance(message, str):
                text = message
            else:
                text = str(message)
            
            # Fallback to response field if content is empty
            if not text:
                text = response.get("response", "")
            
            # Clean up the text
            if text:
                # Remove HTML-like attributes and metadata
                text = re.sub(r'content=["\']([^"\']*)["\']', r'\1', text)
                text = re.sub(r"role=['\"][^'\"]*['\"]\s*", "", text)
                text = re.sub(r"thinking=None\s*", "", text)
                text = re.sub(r"images=None\s*", "", text)
                text = re.sub(r"tool_name=None\s*", "", text)
                text = re.sub(r"tool_calls=None\s*", "", text)
                text = text.replace('\\n', '\n').replace('\\t', '\t')
                text = re.sub(r'<[^>]+>', '', text)
                text = text.strip()
            
            # Apply word duplication fix (includes loop detection)
            original_length = len(text)
            text = fix_word_duplication(text)
            if len(text) < original_length:
                logger.warning(f"DEBUG: Post-processing removed {original_length - len(text)} chars due to duplication/loops")
            
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
        """Async generate - run sync generate in thread pool."""
        import asyncio
        logger.info("Starting async generate (running sync generate in thread pool)")
        try:
            result = await asyncio.to_thread(self._generate, messages, stop, **kwargs)
            logger.info("Async generate completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error in async generate: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
        """Bind tools to the model."""
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
                temperature=0.8,  # Increased to prevent repetition loops
                num_ctx=4096,
                num_predict=1024,
                repeat_penalty=1.15,  # Llama3 best practice: 1.1-1.2
                repeat_last_n=64,
                top_p=0.9,
                top_k=40
            )
        else:
            # Fallback to custom Ollama adapter
            return OllamaChatModel(
                model=model_name,
                base_url=settings.ollama_base_url,
                temperature=0.0  # Use low temperature for deterministic output
            )

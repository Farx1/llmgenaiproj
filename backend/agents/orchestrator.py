"""Orchestration agent that coordinates multiple specialized agents."""
import asyncio
import logging
try:
    from langchain.agents import create_agent
except ImportError:
    try:
        from langchain.agents import create_tool_calling_agent
        create_agent = None  # Will use create_tool_calling_agent instead
    except ImportError:
        create_agent = None
        create_tool_calling_agent = None

try:
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:
    from langchain.prompts import ChatPromptTemplate
from typing import Dict, Any
from utils.llm_factory import get_llm
from agents.retrieval_agent import RetrievalAgent
from agents.web_scraper_agent import WebScraperAgent
from agents.form_agent import FormAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Orchestrates multiple agents to handle complex queries."""
    
    def __init__(self, model_name: str = None):
        """
        Initialize the orchestrator.
        
        Args:
            model_name: Name of the model to use
        """
        self.llm = get_llm(model_name=model_name)
        self.retrieval_agent = RetrievalAgent(model_name=model_name)
        self.web_scraper_agent = WebScraperAgent(model_name=model_name)
        self.form_agent = FormAgent(model_name=model_name)
        
        # Define tools for the orchestrator
        self.tools = [
            self.retrieval_agent.get_tool(),
            self.web_scraper_agent.get_tool(),
            self.form_agent.get_tool(),
        ]
        
        # Create the orchestrator agent
        # Use SimpleAgent by default as it works with all LLMs including Ollama
        # create_tool_calling_agent requires bind_tools which Ollama models don't support
        self.agent = self._create_simple_agent()
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the orchestrator."""
        return """Assistant ESILV. Coordonne les agents pour répondre aux questions sur les programmes, admissions et informations ESILV. Utilise retrieval_agent pour la documentation, web_scraper_agent pour les actualités, form_agent pour les contacts. Réponds en français."""
    
    def _create_simple_agent(self):
        """Create a simple agent wrapper when create_agent is not available."""
        orchestrator_ref = self
        
        class SimpleAgent:
            def __init__(self, llm, tools, system_prompt):
                self.llm = llm
                self.tools = {tool.name: tool for tool in tools if hasattr(tool, 'name')}
                self.system_prompt = system_prompt
            
            async def ainvoke(self, input_dict):
                """Invoke the agent with input."""
                # Support both {"input": "..."} and {"messages": [...]} formats
                if "input" in input_dict:
                    user_message = input_dict["input"]
                else:
                    messages = input_dict.get("messages", [])
                    if not messages:
                        return {"output": ""}
                    user_message = messages[-1].get("content", "") if isinstance(messages[-1], dict) else str(messages[-1])
                
                # Try to use tools based on query
                query_lower = user_message.lower()
                result = ""
                
                # Route to appropriate agent
                import logging
                logger = logging.getLogger(__name__)
                
                if any(word in query_lower for word in ["contact", "register", "sign up", "email", "phone", "follow-up"]):
                    # Use form agent
                    logger.info("Routing to form_agent")
                    form_result = await orchestrator_ref.form_agent.process_query(user_message)
                    result = form_result.get("answer", "")
                elif any(word in query_lower for word in ["news", "update", "latest", "recent", "event"]):
                    # Use web scraper agent
                    logger.info("Routing to web_scraper_agent")
                    scraper_result = await orchestrator_ref.web_scraper_agent.process_query(user_message)
                    result = scraper_result.get("answer", "")
                else:
                    # Use retrieval agent by default
                    logger.info("Routing to retrieval_agent (default)")
                    retrieval_result = await orchestrator_ref.retrieval_agent.process_query(user_message)
                    result = retrieval_result.get("answer", "")
                    logger.info(f"Retrieval agent returned answer (length: {len(result) if result else 0})")
                
                return {"output": result}
        
        return SimpleAgent(self.llm, self.tools, self._get_system_prompt())
    
    async def process_query(
        self,
        query: str,
        conversation_history: list = None
    ) -> Dict[str, Any]:
        """
        Process a user query using the orchestrator.
        
        Args:
            query: User's query
            conversation_history: Previous conversation messages
        
        Returns:
            Response dictionary with answer and metadata
        """
        import time
        start_time = time.time()
        
        logger.info("=" * 70)
        logger.info("DEBUG: ========== ORCHESTRATOR.process_query() ==========")
        logger.info(f"DEBUG: Query: {query[:100]}")
        logger.info(f"DEBUG: History length: {len(conversation_history) if conversation_history else 0}")
        logger.info("=" * 70)
        
        messages = conversation_history or []
        messages.append({"role": "user", "content": query})
        
        try:
            # Convert conversation history to input format
            logger.info("DEBUG: Converting conversation history...")
            input_text = query
            if conversation_history:
                # Build context from history
                history_text = "\n".join([
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    for msg in conversation_history[:-1]  # Exclude current query
                ])
                if history_text:
                    input_text = f"{history_text}\nuser: {query}"
            
            logger.info("DEBUG: Invoking agent...")
            agent_start = time.time()
            # Invoke agent with proper format
            response = await self.agent.ainvoke({"input": input_text})
            agent_time = time.time() - agent_start
            logger.info(f"DEBUG: ✅ Agent invoked in {agent_time:.2f}s")
            logger.info(f"DEBUG: Response type: {type(response)}")
            
            # Extract answer from response
            logger.info("DEBUG: Extracting answer from response...")
            answer = ""
            if isinstance(response, dict):
                # AgentExecutor returns {"output": "..."}
                answer = response.get("output", "")
                logger.info(f"DEBUG: Got answer from 'output' key: {len(answer)} chars")
                if not answer:
                    # Fallback: try to get from messages if present
                    messages_list = response.get("messages", [])
                    if messages_list:
                        last_msg = messages_list[-1]
                        if isinstance(last_msg, dict):
                            answer = last_msg.get("content", "")
                        else:
                            answer = str(last_msg)
                        logger.info(f"DEBUG: Got answer from messages: {len(answer)} chars")
            else:
                answer = str(response)
                logger.info(f"DEBUG: Got answer from string conversion: {len(answer)} chars")
            
            if not answer:
                logger.warning("DEBUG: ⚠️ Empty answer, using default message")
                answer = "I received an empty response. Please try again."
            
            total_time = time.time() - start_time
            logger.info("=" * 70)
            logger.info(f"DEBUG: ✅ ORCHESTRATOR.process_query() COMPLETED in {total_time:.2f}s")
            logger.info(f"DEBUG: Answer length: {len(answer)} chars")
            logger.info("=" * 70)
            
            return {
                "answer": answer,
                "metadata": {
                    "agent": "orchestrator",
                    "tools_used": response.get("intermediate_steps", []) if isinstance(response, dict) else [],
                    "model": getattr(self.llm, 'model', 'unknown') if hasattr(self.llm, 'model') else "unknown"
                }
            }
        except Exception as e:
            import traceback
            total_time = time.time() - start_time
            error_details = traceback.format_exc()
            logger.error("=" * 70)
            logger.error(f"DEBUG: ❌❌❌ ERROR in ORCHESTRATOR.process_query() after {total_time:.2f}s")
            logger.error(f"DEBUG: Error: {str(e)}")
            logger.error(f"DEBUG: Error type: {type(e)}")
            logger.error(f"DEBUG: Full traceback:\n{error_details}")
            logger.error("=" * 70)
            return {
                "answer": f"I encountered an error processing your query: {str(e)}",
                "metadata": {
                    "agent": "orchestrator",
                    "error": str(e),
                    "traceback": error_details
                }
            }
    
    async def process_query_stream(
        self,
        query: str,
        conversation_history: list = None
    ):
        """
        Process a user query with streaming response for better memory efficiency.
        
        Args:
            query: User's query
            conversation_history: Previous conversation messages
        
        Yields:
            Chunks of the response as they are generated
        """
        import logging
        logger = logging.getLogger(__name__)
        
        messages = conversation_history or []
        messages.append({"role": "user", "content": query})
        
        try:
            # Determine which agent to use
            query_lower = query.lower()
            
            # Route to appropriate agent and stream response
            if any(word in query_lower for word in ["contact", "register", "sign up", "email", "phone", "follow-up"]):
                logger.info("Streaming: Routing to form_agent")
                form_result = await self.form_agent.process_query(query)
                answer = form_result.get("answer", "")
                # Stream in chunks
                chunk_size = 50
                for i in range(0, len(answer), chunk_size):
                    yield {"type": "chunk", "content": answer[i:i + chunk_size]}
            elif any(word in query_lower for word in ["news", "update", "latest", "recent", "event"]):
                logger.info("Streaming: Routing to web_scraper_agent")
                scraper_result = await self.web_scraper_agent.process_query(query)
                answer = scraper_result.get("answer", "")
                chunk_size = 50
                for i in range(0, len(answer), chunk_size):
                    yield {"type": "chunk", "content": answer[i:i + chunk_size]}
            else:
                # Use retrieval agent by default - this can use streaming LLM
                logger.info("Streaming: Routing to retrieval_agent (default)")
                
                # Use streaming LLM if available
                from langchain_core.messages import HumanMessage, SystemMessage
                
                # Get context from retrieval agent (synchronous call for speed)
                # The retrieval agent now handles k dynamically based on query type
                # No need to override k here - let the agent decide
                tool_result = self.retrieval_agent.tool.invoke(query)
                
                # Build prompt following LangChain RAG best practices - ULTRA STRICT format
                if tool_result and "Aucune documentation" not in tool_result and "collection est vide" not in tool_result:
                    # Check if user wants detailed answer
                    query_lower = query.lower()
                    wants_details = any(word in query_lower for word in [
                        "détails", "détail", "explique", "expliquer", "développe", "développer",
                        "plus d'infos", "plus d'informations", "en détail", "en profondeur",
                        "complètement", "complet", "tout", "tous", "liste", "lister"
                    ])
                    
                    # Ultra-minimal prompt for better output quality
                    prompt = f"""Assistant ESILV - Réponds aux questions sur les programmes, admissions et informations ESILV.

Contexte:
{tool_result}

Question: {query}

Réponds en français en utilisant uniquement le contexte ci-dessus. Si l'information n'est pas dans le contexte, dis: "Information non trouvée dans la documentation ESILV."

Réponse:"""
                else:
                    prompt = f"""Assistant ESILV.

Question: {query}

Aucune information trouvée dans la documentation. Réponds en français avec tes connaissances générales sur ESILV.

Réponse:"""
                
                # Generate response (no streaming for simplicity)
                yield {"type": "metadata", "data": {"agent": "retrieval", "model": getattr(self.llm, 'model', 'unknown')}}
                
                try:
                    # Log the context to verify it's being passed
                    logger.info(f"DEBUG: Context length: {len(tool_result) if tool_result else 0}")
                    logger.info(f"DEBUG: Context preview (first 500 chars): {tool_result[:500] if tool_result else 'None'}")
                    
                    # Put EVERYTHING in a single HumanMessage to force the model to read it
                    # Some models ignore SystemMessage, so we put everything in the user message
                    full_prompt = prompt  # prompt already contains context + question
                    messages = [HumanMessage(content=full_prompt)]
                    
                    logger.info(f"DEBUG: Sending {len(messages)} messages to LLM")
                    logger.info(f"DEBUG: First message length: {len(full_prompt)}")
                    
                    result = await self.llm.ainvoke(messages)
                    answer = result.content if hasattr(result, 'content') else str(result)
                    
                    logger.info(f"DEBUG: Received answer length: {len(answer)}")
                    logger.info(f"DEBUG: Answer preview (first 200 chars): {answer[:200]}")
                    
                    # Stream the complete answer in chunks for frontend compatibility
                    chunk_size = 50
                    for i in range(0, len(answer), chunk_size):
                        yield {"type": "chunk", "content": answer[i:i + chunk_size]}
                        await asyncio.sleep(0.01)  # Small delay for smooth streaming
                except Exception as gen_error:
                    logger.error(f"Error in generation: {gen_error}")
                    yield {"type": "error", "error": f"Erreur lors de la generation: {str(gen_error)}"}
            
            yield {"type": "done"}
            
        except Exception as e:
            import traceback
            logger.error(f"Error in streaming query: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            yield {"type": "error", "error": f"I encountered an error processing your query: {str(e)}"}


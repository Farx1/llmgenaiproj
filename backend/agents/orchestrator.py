"""Orchestration agent that coordinates multiple specialized agents."""
try:
    from langchain.agents import create_agent
except ImportError:
    try:
        from langchain.agents import create_tool_calling_agent
        create_agent = None  # Will use create_tool_calling_agent instead
    except ImportError:
        create_agent = None
        create_tool_calling_agent = None

from langchain.prompts import ChatPromptTemplate
from typing import Dict, Any
from utils.llm_factory import get_llm
from agents.retrieval_agent import RetrievalAgent
from agents.web_scraper_agent import WebScraperAgent
from agents.form_agent import FormAgent


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
        return """You are the ESILV Smart Assistant orchestrator. Your role is to coordinate multiple specialized agents to answer user queries.

Available agents:
1. **retrieval_agent**: Use this for questions about ESILV programs, admissions, courses, and documentation. This agent searches through vectorized documentation.
2. **web_scraper_agent**: Use this to get the latest news and updates from the ESILV website.
3. **form_agent**: Use this when users want to provide contact information, register, or request follow-up.

Your workflow:
- Analyze the user's query to determine which agent(s) to use
- If the query is about documentation/programs/admissions → use retrieval_agent
- If the query is about news/updates → use web_scraper_agent
- If the user wants to provide contact info → use form_agent
- You can use multiple agents if needed
- Always provide clear, helpful responses based on the agent results

Be conversational, helpful, and accurate. If you're unsure, use the retrieval_agent first as it has the most comprehensive information."""
    
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
        messages = conversation_history or []
        messages.append({"role": "user", "content": query})
        
        try:
            # Convert conversation history to input format
            input_text = query
            if conversation_history:
                # Build context from history
                history_text = "\n".join([
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    for msg in conversation_history[:-1]  # Exclude current query
                ])
                if history_text:
                    input_text = f"{history_text}\nuser: {query}"
            
            # Invoke agent with proper format
            response = await self.agent.ainvoke({"input": input_text})
            
            # Extract answer from response
            answer = ""
            if isinstance(response, dict):
                # AgentExecutor returns {"output": "..."}
                answer = response.get("output", "")
                if not answer:
                    # Fallback: try to get from messages if present
                    messages_list = response.get("messages", [])
                    if messages_list:
                        last_msg = messages_list[-1]
                        if isinstance(last_msg, dict):
                            answer = last_msg.get("content", "")
                        else:
                            answer = str(last_msg)
            else:
                answer = str(response)
            
            if not answer:
                answer = "I received an empty response. Please try again."
            
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
            error_details = traceback.format_exc()
            return {
                "answer": f"I encountered an error processing your query: {str(e)}",
                "metadata": {
                    "agent": "orchestrator",
                    "error": str(e),
                    "traceback": error_details
                }
            }


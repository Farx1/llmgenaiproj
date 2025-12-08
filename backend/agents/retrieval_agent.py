"""Retrieval agent for RAG queries."""
try:
    from langchain.agents import create_agent
except ImportError:
    try:
        from langchain.agents import create_tool_calling_agent
        create_agent = None
    except ImportError:
        create_agent = None
        create_tool_calling_agent = None

from langchain.tools import tool
from langchain.prompts import ChatPromptTemplate
from typing import Dict, Any
from utils.llm_factory import get_llm
from rag.vector_store import vector_store


class RetrievalAgent:
    """Agent specialized in retrieval-augmented generation."""
    
    def __init__(self, model_name: str = None):
        """
        Initialize the retrieval agent.
        
        Args:
            model_name: Name of the model to use
        """
        self.llm = get_llm(model_name=model_name)
        self.vector_store = vector_store
        self.tool = self._create_retrieval_tool()
        
        # Use SimpleAgent by default as it works with all LLMs including Ollama
        self.agent = self._create_simple_agent()
    
    def _create_retrieval_tool(self):
        """Create the retrieval tool."""
        vector_store_ref = self.vector_store
        
        @tool
        def search_documentation(query: str) -> str:
            """Search ESILV documentation for information about programs, admissions, courses, and policies.
            
            Args:
                query: The search query about ESILV programs, admissions, courses, etc.
            
            Returns:
                Relevant documentation excerpts
            """
            try:
                # Search for similar documents
                docs = vector_store_ref.similarity_search(query, k=4)
                
                if not docs or len(docs) == 0:
                    return "Aucune documentation pertinente trouvee dans la base de connaissances. Vous pouvez utiliser vos connaissances generales pour repondre a la question."
                
                # Combine document contents - handle different document formats
                results = []
                for i, doc in enumerate(docs, 1):
                    try:
                        # Try to get page_content attribute
                        if hasattr(doc, 'page_content'):
                            content = doc.page_content
                        elif hasattr(doc, 'content'):
                            content = doc.content
                        elif isinstance(doc, dict):
                            content = doc.get('page_content', doc.get('content', str(doc)))
                        else:
                            content = str(doc)
                        
                        if content:
                            results.append(f"[Document {i}]\n{content}\n")
                    except Exception as doc_error:
                        # Skip this document if there's an error accessing it
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Error accessing document {i}: {str(doc_error)}")
                        continue
                
                if not results:
                    return "Aucune documentation pertinente trouvee dans la base de connaissances. Vous pouvez utiliser vos connaissances generales pour repondre a la question."
                
                return "\n".join(results)
            except Exception as e:
                import logging
                import traceback
                logger = logging.getLogger(__name__)
                logger.error(f"Error in search_documentation: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return "Aucune documentation pertinente trouvee dans la base de connaissances. Vous pouvez utiliser vos connaissances generales pour repondre a la question."
        
        return search_documentation
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the retrieval agent."""
        return """Tu es un assistant specialise pour l'ecole d'ingenieurs ESILV. Ton role est de repondre aux questions sur:
- Les programmes academiques et specialisations (majeures)
- Les conditions d'admission et processus
- Les descriptions de cours et curriculum
- Les politiques et procedures de l'ecole
- Les informations generales sur ESILV

Utilise l'outil search_documentation pour trouver des informations pertinentes dans la documentation vectorisee. Si aucune documentation n'est trouvee, utilise tes connaissances generales pour repondre de maniere utile et precise. Reponds toujours en francais de maniere claire et professionnelle."""
    
    def _create_simple_agent(self):
        """Create a simple agent when create_agent is not available."""
        tool_ref = self.tool
        llm_ref = self.llm
        system_prompt = self._get_system_prompt()
        
        class SimpleAgent:
            async def ainvoke(self, input_dict):
                """Invoke the agent."""
                import logging
                logger = logging.getLogger(__name__)
                
                # Support both {"input": "..."} and {"messages": [...]} formats
                if "input" in input_dict:
                    user_message = input_dict["input"]
                else:
                    messages = input_dict.get("messages", [])
                    if not messages:
                        return {"output": ""}
                    user_message = messages[-1].get("content", "") if isinstance(messages[-1], dict) else str(messages[-1])
                
                logger.info(f"Retrieval agent processing query: {user_message[:50]}...")
                
                # Use the tool directly
                try:
                    logger.info("Calling retrieval tool...")
                    tool_result = tool_ref.invoke(user_message) if hasattr(tool_ref, 'invoke') else tool_ref(user_message)
                    logger.info(f"Tool result received (length: {len(str(tool_result))})")
                    
                    # Use LLM to format the response
                    from langchain_core.messages import HumanMessage
                    prompt_messages = [
                        HumanMessage(content=f"{system_prompt}\n\nUser query: {user_message}\n\nTool result: {tool_result}\n\nProvide a helpful answer based on the tool result:")
                    ]
                    
                    logger.info("Calling LLM to format response...")
                    if hasattr(llm_ref, 'ainvoke'):
                        llm_response = await llm_ref.ainvoke(prompt_messages)
                    else:
                        llm_response = llm_ref.invoke(prompt_messages) if hasattr(llm_ref, 'invoke') else str(llm_ref)
                    
                    logger.info("LLM response received")
                    
                    # Extract content properly - handle different response formats
                    answer = ""
                    if hasattr(llm_response, 'content'):
                        answer = llm_response.content
                    elif isinstance(llm_response, str):
                        answer = llm_response
                    elif hasattr(llm_response, 'text'):
                        answer = llm_response.text
                    else:
                        # Try to extract from dict or other formats
                        answer = str(llm_response)
                        # Remove metadata if present (like role='assistant', thinking=None, etc.)
                        import re
                        # If answer contains metadata format, extract just the content
                        content_match = re.search(r"content=['\"](.*?)['\"]", answer, re.DOTALL)
                        if content_match:
                            answer = content_match.group(1)
                        # Clean up any remaining metadata patterns
                        answer = re.sub(r"role=['\"][^'\"]*['\"]\s*", "", answer)
                        answer = re.sub(r"thinking=None\s*", "", answer)
                        answer = re.sub(r"images=None\s*", "", answer)
                        answer = re.sub(r"tool_name=None\s*", "", answer)
                        answer = re.sub(r"tool_calls=None\s*", "", answer)
                        answer = answer.strip()
                    
                    logger.info(f"Answer extracted (length: {len(answer)})")
                    
                    return {"output": answer}
                except Exception as e:
                    import traceback
                    logger.error(f"Error in retrieval agent: {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    return {"output": f"Error: {str(e)}"}
        
        return SimpleAgent()
    
    def get_tool(self):
        """Get the retrieval tool for use by other agents."""
        return self.tool
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a retrieval query.
        
        Args:
            query: User's query
        
        Returns:
            Response dictionary with answer and metadata
        """
        try:
            response = await self.agent.ainvoke({"input": query})
            
            # Extract answer from response
            answer = ""
            if isinstance(response, dict):
                answer = response.get("output", "")
                if not answer:
                    messages = response.get("messages", [])
                    if messages:
                        last_msg = messages[-1]
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
                    "agent": "retrieval",
                    "model": getattr(self.llm, 'model', 'unknown') if hasattr(self.llm, 'model') else "unknown"
                }
            }
        except Exception as e:
            return {
                "answer": f"I encountered an error: {str(e)}",
                "metadata": {
                    "agent": "retrieval",
                    "error": str(e)
                }
            }


"""Form-filling agent for contact collection."""
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
from typing import Dict, Any, Optional
from utils.llm_factory import get_llm
import json
import os
from datetime import datetime


class FormAgent:
    """Agent specialized in collecting and managing contact information."""
    
    def __init__(self, model_name: str = None):
        """
        Initialize the form agent.
        
        Args:
            model_name: Name of the model to use
        """
        self.llm = get_llm(model_name=model_name)
        self.contacts_file = "contacts.json"
        self.tool = self._create_form_tool()
        
        # Use SimpleAgent by default as it works with all LLMs including Ollama
        self.agent = self._create_simple_agent()
    
    def _create_form_tool(self):
        """Create the form collection tool."""
        contacts_file_ref = self.contacts_file
        
        @tool
        def collect_contact_info(
            name: str,
            email: str,
            phone: Optional[str] = None,
            interest: Optional[str] = None,
            message: Optional[str] = None
        ) -> str:
            """Collect contact information from users for follow-up or registration.
            
            Args:
                name: Full name of the person
                email: Email address
                phone: Phone number (optional)
                interest: Area of interest (e.g., "admissions", "programs") (optional)
                message: Additional message (optional)
            
            Returns:
                Confirmation message
            """
            try:
                # Load existing contacts
                contacts = []
                if os.path.exists(contacts_file_ref):
                    with open(contacts_file_ref, 'r', encoding='utf-8') as f:
                        contacts = json.load(f)
                
                # Create new contact entry
                new_contact = {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "interest": interest,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
                
                contacts.append(new_contact)
                
                # Save contacts
                with open(contacts_file_ref, 'w', encoding='utf-8') as f:
                    json.dump(contacts, f, indent=2, ensure_ascii=False)
                
                return f"Thank you {name}! Your contact information has been saved. We'll get back to you at {email} soon."
                
            except Exception as e:
                return f"Error saving contact information: {str(e)}"
        
        return collect_contact_info
    
    def _create_simple_agent(self):
        """Create a simple agent when create_agent is not available."""
        tool_ref = self.tool
        llm_ref = self.llm
        system_prompt = self._get_system_prompt()
        
        class SimpleAgent:
            async def ainvoke(self, input_dict):
                """Invoke the agent."""
                # Support both {"input": "..."} and {"messages": [...]} formats
                if "input" in input_dict:
                    user_message = input_dict["input"]
                else:
                    messages = input_dict.get("messages", [])
                    if not messages:
                        return {"output": ""}
                    user_message = messages[-1].get("content", "") if isinstance(messages[-1], dict) else str(messages[-1])
                
                try:
                    tool_result = tool_ref.invoke(user_message) if hasattr(tool_ref, 'invoke') else tool_ref(user_message)
                    
                    from langchain_core.messages import HumanMessage
                    prompt_messages = [
                        HumanMessage(content=f"{system_prompt}\n\nUser query: {user_message}\n\nTool result: {tool_result}\n\nProvide a helpful answer:")
                    ]
                    
                    if hasattr(llm_ref, 'ainvoke'):
                        llm_response = await llm_ref.ainvoke(prompt_messages)
                    else:
                        llm_response = llm_ref.invoke(prompt_messages) if hasattr(llm_ref, 'invoke') else str(llm_ref)
                    
                    answer = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
                    
                    return {"output": answer}
                except Exception as e:
                    return {"output": f"Error: {str(e)}"}
        
        return SimpleAgent()
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the form agent."""
        return """You are a specialized form-filling agent for ESILV engineering school. Your role is to help users provide their contact information for:
- Follow-up inquiries
- Registration requests
- Information requests
- Event sign-ups

When a user wants to provide contact information, use the collect_contact_info tool. Be friendly and conversational while collecting the necessary information. Always confirm what information was collected."""
    
    def get_tool(self):
        """Get the form tool for use by other agents."""
        return self.tool
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a form-related query.
        
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
                    "agent": "form",
                    "model": getattr(self.llm, 'model', 'unknown') if hasattr(self.llm, 'model') else "unknown"
                }
            }
        except Exception as e:
            return {
                "answer": f"I encountered an error: {str(e)}",
                "metadata": {
                    "agent": "form",
                    "error": str(e)
                }
            }
    
    def get_contacts(self) -> list:
        """Get all collected contacts."""
        try:
            if os.path.exists(self.contacts_file):
                with open(self.contacts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error reading contacts: {e}")
            return []


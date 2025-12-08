"""Web scraping agent for ESILV website news."""
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
from typing import Dict, Any, List
from utils.llm_factory import get_llm
from config import settings
import httpx
from bs4 import BeautifulSoup


class WebScraperAgent:
    """Agent specialized in web scraping ESILV website."""
    
    def __init__(self, model_name: str = None):
        """
        Initialize the web scraper agent.
        
        Args:
            model_name: Name of the model to use
        """
        self.llm = get_llm(model_name=model_name)
        self.base_url = settings.esilv_base_url
        self.tool = self._create_scraping_tool()
        
        # Use SimpleAgent by default as it works with all LLMs including Ollama
        self.agent = self._create_simple_agent()
    
    def _create_scraping_tool(self):
        """Create the web scraping tool."""
        base_url_ref = self.base_url
        
        @tool
        def scrape_esilv_news(query: str = "") -> str:
            """Scrape the latest news and updates from the ESILV website.
            
            Args:
                query: Optional search query to filter news (e.g., "admissions", "events")
            
            Returns:
                Latest news and updates from ESILV website
            """
            try:
                # Try to scrape the news page
                news_url = f"{base_url_ref}/actualites"  # Common news URL pattern
                
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(news_url)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract news articles (adjust selectors based on actual website structure)
                    articles = []
                    
                    # Try common selectors for news articles
                    article_elements = soup.select('article, .news-item, .post, .actualite')
                    
                    if not article_elements:
                        # Fallback: look for any links with news-related text
                        article_elements = soup.find_all(['a', 'div'], class_=lambda x: x and ('news' in x.lower() or 'actualite' in x.lower() or 'article' in x.lower()))
                    
                    for element in article_elements[:10]:  # Limit to 10 articles
                        title = element.find(['h1', 'h2', 'h3', 'h4', 'a'])
                        if title:
                            title_text = title.get_text(strip=True)
                            link = element.find('a')
                            link_url = link.get('href', '') if link else ''
                            
                            if link_url and not link_url.startswith('http'):
                                link_url = f"{base_url_ref}{link_url}"
                            
                            description = element.find(['p', 'div'])
                            desc_text = description.get_text(strip=True) if description else ""
                            
                            article_info = f"Title: {title_text}\n"
                            if desc_text:
                                article_info += f"Description: {desc_text[:200]}...\n"
                            if link_url:
                                article_info += f"Link: {link_url}\n"
                            
                            articles.append(article_info)
                    
                    if not articles:
                        return f"Could not find news articles on the ESILV website. Please visit {base_url_ref} for the latest updates."
                    
                    result = f"Latest news from ESILV:\n\n" + "\n---\n".join(articles)
                    
                    # Filter by query if provided
                    if query:
                        result = f"News related to '{query}':\n\n" + result
                    
                    return result
                    
            except Exception as e:
                return f"Error scraping ESILV website: {str(e)}. Please visit {base_url_ref} for the latest updates."
        
        return scrape_esilv_news
    
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
        """Get the system prompt for the web scraper agent."""
        return """You are a specialized web scraping agent for ESILV engineering school. Your role is to fetch and summarize the latest news, events, and updates from the ESILV website.

Use the scrape_esilv_news tool to get current information. Provide clear, concise summaries of the news items."""
    
    def get_tool(self):
        """Get the scraping tool for use by other agents."""
        return self.tool
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a web scraping query.
        
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
                    "agent": "web_scraper",
                    "model": getattr(self.llm, 'model', 'unknown') if hasattr(self.llm, 'model') else "unknown"
                }
            }
        except Exception as e:
            return {
                "answer": f"I encountered an error: {str(e)}",
                "metadata": {
                    "agent": "web_scraper",
                    "error": str(e)
                }
            }


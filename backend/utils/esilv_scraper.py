"""ESILV website scraper to extract and index content."""
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
from rag.vector_store import vector_store
from rag.document_processor import document_processor
from config import settings
import logging
import re
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class ESILVScraper:
    """Scraper for ESILV website to extract and index content."""
    
    def __init__(self):
        """Initialize the scraper."""
        self.base_url = settings.esilv_base_url
        self.visited_urls = set()
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)
    
    def clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep French accents
        text = text.strip()
        return text
    
    def extract_text_from_element(self, element) -> str:
        """Extract clean text from a BeautifulSoup element."""
        if element is None:
            return ""
        
        # Remove script and style elements
        for script in element(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        text = element.get_text(separator=' ', strip=True)
        return self.clean_text(text)
    
    def scrape_page(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a single page and extract content.
        
        Args:
            url: URL to scrape
        
        Returns:
            Dictionary with title, content, and metadata, or None if error
        """
        if url in self.visited_urls:
            return None
        
        try:
            logger.info(f"Scraping: {url}")
            response = self.client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = ""
            title_elem = soup.find('title')
            if title_elem:
                title = self.clean_text(title_elem.get_text())
            
            # Try to find main content area
            main_content = None
            
            # Common selectors for main content
            content_selectors = [
                'main',
                '.main-content',
                '.content',
                '#content',
                'article',
                '.post-content',
                '.page-content',
                '[role="main"]'
            ]
            
            for selector in content_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            # Fallback: use body if no main content found
            if not main_content:
                main_content = soup.find('body')
            
            if not main_content:
                logger.warning(f"No content found on {url}")
                return None
            
            # Extract text content
            content = self.extract_text_from_element(main_content)
            
            if not content or len(content) < 100:  # Skip pages with too little content
                logger.warning(f"Page {url} has too little content ({len(content)} chars)")
                return None
            
            self.visited_urls.add(url)
            
            return {
                "title": title or url,
                "content": content,
                "url": url,
                "source": "esilv_website"
            }
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return None
    
    def find_internal_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find all internal links on a page."""
        links = []
        base_domain = urlparse(base_url).netloc
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            
            # Only include internal links
            if parsed.netloc == base_domain or not parsed.netloc:
                # Remove fragments and query params for deduplication
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if clean_url not in self.visited_urls and clean_url not in links:
                    links.append(clean_url)
        
        return links
    
    def scrape_section(self, section_path: str, max_pages: int = 10) -> List[Dict[str, any]]:
        """
        Scrape a section of the website (e.g., /formations, /admissions).
        
        Args:
            section_path: Path to scrape (e.g., "/formations", "/admissions")
            max_pages: Maximum number of pages to scrape
        
        Returns:
            List of scraped content dictionaries
        """
        results = []
        url = urljoin(self.base_url, section_path)
        
        try:
            logger.info(f"Scraping section: {url}")
            response = self.client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Scrape the main page
            page_content = self.scrape_page(url)
            if page_content:
                results.append(page_content)
            
            # Find and scrape related pages
            links = self.find_internal_links(soup, url)
            
            # Filter links that are likely relevant (contain section keywords)
            section_keywords = section_path.lower().split('/')
            relevant_links = [
                link for link in links
                if any(keyword in link.lower() for keyword in section_keywords if keyword)
                or any(keyword in link.lower() for keyword in ['formation', 'programme', 'majeure', 'specialisation', 'admission', 'cours'])
            ]
            
            # Limit to max_pages
            for link in relevant_links[:max_pages - 1]:
                if len(results) >= max_pages:
                    break
                
                page_content = self.scrape_page(link)
                if page_content:
                    results.append(page_content)
            
            logger.info(f"Scraped {len(results)} pages from section {section_path}")
            return results
            
        except Exception as e:
            logger.error(f"Error scraping section {section_path}: {str(e)}")
            return results
    
    def scrape_all_important_sections(self) -> List[Dict[str, any]]:
        """
        Scrape all important sections of the ESILV website.
        
        Returns:
            List of all scraped content
        """
        all_results = []
        
        # Important sections to scrape
        sections = [
            "/formations",  # Programs/Formations
            "/formations/majeures",  # Majors/Specializations
            "/admissions",  # Admissions
            "/ecole",  # About the school
            "/programmes",  # Programs
            "/specialisations",  # Specializations
            "/majeures",  # Majors
        ]
        
        for section in sections:
            try:
                results = self.scrape_section(section, max_pages=5)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Error scraping section {section}: {str(e)}")
                continue
        
        logger.info(f"Total pages scraped: {len(all_results)}")
        return all_results
    
    def index_scraped_content(self, content_list: List[Dict[str, any]]) -> Dict[str, int]:
        """
        Index scraped content into the vector store.
        
        Args:
            content_list: List of content dictionaries
        
        Returns:
            Dictionary with indexing statistics
        """
        if not content_list:
            return {"indexed": 0, "chunks": 0, "errors": 0}
        
        total_chunks = 0
        indexed = 0
        errors = 0
        
        for content in content_list:
            try:
                # Create document
                from langchain_core.documents import Document
                
                doc = Document(
                    page_content=content["content"],
                    metadata={
                        "source": content["url"],
                        "title": content.get("title", ""),
                        "filename": content["url"].split("/")[-1] or "esilv_page",
                        "file_type": ".html",
                        "scraped_from": "esilv_website"
                    }
                )
                
                # Process and chunk
                chunks = document_processor.text_splitter.split_documents([doc])
                
                # Add chunk index to metadata
                for i, chunk in enumerate(chunks):
                    chunk.metadata["chunk_index"] = i
                    chunk.metadata["total_chunks"] = len(chunks)
                
                # Add to vector store
                vector_store.add_documents(chunks)
                
                total_chunks += len(chunks)
                indexed += 1
                
                logger.info(f"Indexed {content.get('title', content['url'])}: {len(chunks)} chunks")
                
            except Exception as e:
                errors += 1
                logger.error(f"Error indexing content from {content.get('url', 'unknown')}: {str(e)}")
                continue
        
        return {
            "indexed": indexed,
            "chunks": total_chunks,
            "errors": errors
        }


# Global instance
esilv_scraper = ESILVScraper()


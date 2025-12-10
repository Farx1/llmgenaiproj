"""Firecrawl-based scraper for ESILV website - more efficient than manual scraping."""
import logging
from typing import List, Dict, Optional, Any
from rag.vector_store import vector_store
from rag.document_processor import document_processor
from config import settings

logger = logging.getLogger(__name__)


class FirecrawlScraper:
    """Scraper using Firecrawl API for efficient website crawling."""
    
    def __init__(self):
        """Initialize the Firecrawl scraper."""
        self.base_url = settings.esilv_base_url
        self.api_key = settings.firecrawl_api_key
        
        if not self.api_key:
            logger.warning("Firecrawl API key not set. Please set FIRECRAWL_API_KEY in .env file.")
            self.client = None
        else:
            try:
                from firecrawl import Firecrawl
                self.client = Firecrawl(api_key=self.api_key)
                logger.info("Firecrawl client initialized successfully")
            except ImportError:
                logger.error("firecrawl-py not installed. Run: pip install firecrawl-py")
                self.client = None
            except Exception as e:
                logger.error(f"Error initializing Firecrawl client: {str(e)}")
                self.client = None
    
    def scrape_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a single URL using Firecrawl.
        
        Args:
            url: URL to scrape
        
        Returns:
            Dictionary with markdown content and metadata, or None if error
        """
        if not self.client:
            return None
        
        try:
            logger.info(f"Scraping with Firecrawl: {url}")
            
            # Scrape the URL - Firecrawl returns markdown optimized for RAG
            result = self.client.scrape(
                url=url,
                formats=["markdown", "html"]
            )
            
            if not result or not hasattr(result, 'markdown'):
                logger.warning(f"No markdown content returned for {url}")
                return None
            
            markdown_content = result.markdown if hasattr(result, 'markdown') else result.get('markdown', '')
            
            if not markdown_content or len(markdown_content) < 100:
                logger.warning(f"Page {url} has too little content ({len(markdown_content)} chars)")
                return None
            
            # Extract images from result
            images = []
            metadata = result.metadata if hasattr(result, 'metadata') else {}
            
            # Check for images in various possible locations
            if isinstance(metadata, dict):
                # Check for images array
                if 'images' in metadata and isinstance(metadata['images'], list):
                    images = metadata['images']
                # Check for image field
                elif 'image' in metadata:
                    img = metadata['image']
                    if isinstance(img, str):
                        images = [img]
                    elif isinstance(img, list):
                        images = img
                # Check for og:image
                elif 'og:image' in metadata:
                    images = [metadata['og:image']]
            
            # Also try to extract images from markdown content
            if not images and markdown_content:
                import re
                # Find all markdown image links: ![alt](url)
                img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
                markdown_images = re.findall(img_pattern, markdown_content)
                if markdown_images:
                    images = [url for alt, url in markdown_images if url.startswith('http')]
            
            # Add images to metadata
            if images:
                metadata['images'] = images
                metadata['image_count'] = len(images)
                logger.info(f"Found {len(images)} image(s) for {url}")
            
            return {
                "title": metadata.get('title', url) if isinstance(metadata, dict) else url,
                "content": markdown_content,
                "url": url,
                "source": "esilv_website_firecrawl",
                "metadata": metadata,
                "images": images  # Also return images separately for easy access
            }
            
        except Exception as e:
            logger.error(f"Error scraping {url} with Firecrawl: {str(e)}")
            return None
    
    def crawl_website(
        self,
        start_url: str = None,
        limit: int = 50,
        max_depth: int = 3,
        exclude_patterns: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Crawl the ESILV website using Firecrawl.
        Firecrawl automatically discovers and crawls all accessible pages.
        
        Args:
            start_url: Starting URL (defaults to base_url)
            limit: Maximum number of pages to crawl
            max_depth: Maximum crawl depth
            exclude_patterns: List of regex patterns for URLs to exclude (e.g., [".*\\.pdf$"])
        
        Returns:
            List of scraped content dictionaries
        """
        if not self.client:
            logger.error("Firecrawl client not initialized. Check API key.")
            return []
        
        start_url = start_url or self.base_url
        
        # Default exclude patterns: exclude PDFs
        if exclude_patterns is None:
            exclude_patterns = [r".*\.pdf$"]
        
        try:
            logger.info(f"Crawling ESILV website starting from: {start_url}")
            logger.info(f"Limit: {limit} pages, Max depth: {max_depth}")
            if exclude_patterns:
                logger.info(f"Excluding patterns: {exclude_patterns}")
            
            # Use Firecrawl's crawl method - it automatically discovers pages
            # Build crawler options with exclude patterns
            crawler_options = {
                "excludes": exclude_patterns if exclude_patterns else []
            }
            
            crawl_result = self.client.crawl(
                url=start_url,
                limit=limit,
                scrape_options={
                    "formats": ["markdown", "html"]
                },
                crawler_options=crawler_options,
                # Firecrawl handles JavaScript and dynamic content automatically
            )
            
            if not crawl_result:
                logger.warning("No results from Firecrawl crawl")
                return []
            
            # Extract data from crawl result
            # Firecrawl returns a job object, we need to get the status
            results = []
            
            # Check if it's a job object that needs polling
            if hasattr(crawl_result, 'job_id'):
                # Poll for results
                import time
                job_id = crawl_result.job_id
                logger.info(f"   📋 Crawl job created: {job_id}")
                logger.info(f"   ⏳ Polling for crawl status...")
                
                max_wait = 600  # 10 minutes max (increased for large crawls)
                wait_time = 0
                poll_interval = 5
                last_pages_count = 0
                
                while wait_time < max_wait:
                    status = self.client.get_crawl_status(job_id)
                    
                    if hasattr(status, 'status'):
                        status_str = status.status if hasattr(status, 'status') else str(status)
                        logger.info(f"   📊 Status check ({wait_time}s): {status_str}")
                        
                        if status.status == 'completed':
                            logger.info(f"   ✅ Crawl job completed!")
                            # Extract data from completed crawl
                            if hasattr(status, 'data') and status.data:
                                logger.info(f"   📥 Processing {len(status.data)} pages...")
                                for idx, page in enumerate(status.data, 1):
                                    if hasattr(page, 'markdown') or 'markdown' in page:
                                        markdown = page.markdown if hasattr(page, 'markdown') else page.get('markdown', '')
                                        if markdown and len(markdown) > 100:
                                            page_url = page.url if hasattr(page, 'url') else page.get('url', '')
                                            page_title = page.metadata.get('title', page_url) if hasattr(page, 'metadata') else page.get('metadata', {}).get('title', page_url)
                                            results.append({
                                                "title": page_title,
                                                "content": markdown,
                                                "url": page_url,
                                                "source": "esilv_website_firecrawl",
                                                "metadata": page.metadata if hasattr(page, 'metadata') else page.get('metadata', {})
                                            })
                                            
                                            # Log progress every 10 pages
                                            if idx % 10 == 0 or idx == len(status.data):
                                                logger.info(f"      Processed {idx}/{len(status.data)} pages...")
                                
                                logger.info(f"   ✅ Extracted {len(results)} valid pages from crawl")
                            break
                        elif status.status == 'failed':
                            logger.error(f"   ❌ Crawl job failed: {job_id}")
                            if hasattr(status, 'error'):
                                logger.error(f"   Error details: {status.error}")
                            break
                        elif status.status in ['running', 'pending']:
                            # Try to get progress info if available
                            if hasattr(status, 'pages_crawled'):
                                pages_crawled = status.pages_crawled
                                if pages_crawled != last_pages_count:
                                    logger.info(f"   📈 Progress: {pages_crawled} pages crawled so far...")
                                    last_pages_count = pages_crawled
                    
                    time.sleep(poll_interval)
                    wait_time += poll_interval
                    
                    # Log every 30 seconds
                    if wait_time % 30 == 0:
                        logger.info(f"   ⏳ Still crawling... ({wait_time}s elapsed, max {max_wait}s)")
                
                if wait_time >= max_wait:
                    logger.warning(f"   ⚠️ Crawl timeout reached ({max_wait}s). Results may be incomplete.")
            else:
                # Direct result (synchronous mode)
                if hasattr(crawl_result, 'data') and crawl_result.data:
                    for page in crawl_result.data:
                        if hasattr(page, 'markdown') or 'markdown' in page:
                            markdown = page.markdown if hasattr(page, 'markdown') else page.get('markdown', '')
                            if markdown and len(markdown) > 100:
                                results.append({
                                    "title": page.metadata.get('title', page.url) if hasattr(page, 'metadata') else page.get('metadata', {}).get('title', page.get('url', '')),
                                    "content": markdown,
                                    "url": page.url if hasattr(page, 'url') else page.get('url', ''),
                                    "source": "esilv_website_firecrawl",
                                    "metadata": page.metadata if hasattr(page, 'metadata') else page.get('metadata', {})
                                })
            
            logger.info(f"Firecrawl crawled {len(results)} pages")
            return results
            
        except Exception as e:
            logger.error(f"Error crawling with Firecrawl: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def crawl_sections(
        self, 
        sections: List[str] = None, 
        limit_per_section: int = 10,
        exclude_patterns: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Crawl specific sections of the ESILV website.
        
        Args:
            sections: List of section paths or full URLs (e.g., ["/formations", "/admissions", "https://www.esilv.fr/page"])
                     If None, crawls the entire website
            limit_per_section: Maximum pages per section
            exclude_patterns: List of regex patterns for URLs to exclude (e.g., [".*\\.pdf$"])
        
        Returns:
            List of all scraped content
        """
        if not self.client:
            logger.error("Firecrawl client not initialized. Check API key.")
            return []
        
        # Default exclude patterns: exclude PDFs
        if exclude_patterns is None:
            exclude_patterns = [r".*\.pdf$"]
        
        all_results = []
        
        if sections:
            # Crawl specific sections
            for section in sections:
                url = f"{self.base_url}{section}" if not section.startswith('http') else section
                logger.info(f"Crawling section: {url}")
                results = self.crawl_website(
                    start_url=url, 
                    limit=limit_per_section,
                    exclude_patterns=exclude_patterns
                )
                all_results.extend(results)
        else:
            # Crawl entire website
            logger.info("Crawling entire ESILV website")
            all_results = self.crawl_website(limit=50, exclude_patterns=exclude_patterns)
        
        logger.info(f"Total pages crawled: {len(all_results)}")
        return all_results
    
    def index_scraped_content(self, content_list: List[Dict[str, Any]]) -> Dict[str, int]:
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
                from langchain_core.documents import Document
                
                doc = Document(
                    page_content=content["content"],
                    metadata={
                        "source": content["url"],
                        "title": content.get("title", ""),
                        "filename": content["url"].split("/")[-1] or "esilv_page",
                        "file_type": ".md",  # Markdown from Firecrawl
                        "scraped_from": "esilv_website_firecrawl"
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
firecrawl_scraper = FirecrawlScraper()


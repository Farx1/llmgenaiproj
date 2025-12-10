"""Crawl4AI-based scraper for ESILV website - open source, no API limits."""
import logging
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
from rag.vector_store import vector_store
from rag.document_processor import document_processor
from config import settings

logger = logging.getLogger(__name__)


class Crawl4AIScraper:
    """Scraper using Crawl4AI for efficient website scraping (open source, no API limits)."""
    
    def __init__(self):
        """Initialize the Crawl4AI scraper."""
        self.base_url = settings.esilv_base_url
        self._crawler = None
    
    async def _get_crawler(self):
        """Get or create the AsyncWebCrawler instance."""
        if self._crawler is None:
            try:
                from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
                # Configure browser (headless for performance)
                browser_config = BrowserConfig(
                    headless=True,
                    browser_type="chromium",  # or "firefox", "webkit"
                    verbose=False
                )
                self._crawler = AsyncWebCrawler(config=browser_config)
                await self._crawler.__aenter__()  # Initialize the crawler
                logger.info("Crawl4AI crawler initialized successfully")
            except ImportError:
                logger.error("crawl4ai not installed. Run: pip install crawl4ai")
                raise
            except Exception as e:
                logger.error(f"Error initializing Crawl4AI crawler: {str(e)}")
                raise
        return self._crawler
    
    async def close(self):
        """Close the crawler."""
        if self._crawler:
            try:
                await self._crawler.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing crawler: {str(e)}")
            finally:
                self._crawler = None
    
    async def _scrape_with_httpx(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fallback scraper using httpx + BeautifulSoup for static pages.
        
        Args:
            url: URL to scrape
        
        Returns:
            Dictionary with markdown content, images, and metadata, or None if error
        """
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove unwanted elements (scripts, styles, navigation, forms, cookies, etc.)
                unwanted_tags = ["script", "style", "nav", "footer", "aside", "header", 
                               "form", "noscript", "iframe", "svg", "button"]
                for tag in unwanted_tags:
                    for element in soup.find_all(tag):
                        element.decompose()
                
                # Remove cookie banners and consent popups
                for element in soup.find_all(class_=lambda x: x and any(
                    keyword in x.lower() for keyword in ['cookie', 'consent', 'gdpr', 'privacy', 'banner']
                )):
                    element.decompose()
                
                # Remove form elements
                for form in soup.find_all('form'):
                    form.decompose()
                
                # Extract title
                title = soup.find('title')
                title_text = title.get_text().strip() if title else url.split('/')[-1] or 'ESILV Page'
                
                # Extract main content (prioritize main/article over body)
                main_content = soup.find('main') or soup.find('article') or soup.find('body')
                if main_content:
                    # Remove any remaining unwanted elements from main content
                    for tag in ["script", "style", "form", "nav", "footer", "aside"]:
                        for element in main_content.find_all(tag):
                            element.decompose()
                    text = main_content.get_text(separator='\n', strip=True)
                else:
                    text = soup.get_text(separator='\n', strip=True)
                
                # Clean up text: remove excessive whitespace and empty lines
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                text = '\n'.join(lines)
                
                # Extract only relevant images (limit to 10 per page, prioritize main content)
                images = []
                if main_content:
                    for img in main_content.find_all('img', limit=10):
                        img_src = img.get('src') or img.get('data-src')
                        if img_src:
                            # Make absolute URL
                            if img_src.startswith('//'):
                                img_src = 'https:' + img_src
                            elif img_src.startswith('/'):
                                from urllib.parse import urljoin
                                img_src = urljoin(url, img_src)
                            elif not img_src.startswith('http'):
                                from urllib.parse import urljoin
                                img_src = urljoin(url, img_src)
                            
                            if img_src.startswith('http') and img_src not in images:
                                images.append({
                                    'url': img_src,
                                    'alt': img.get('alt', ''),
                                    'title': img.get('title', '')
                                })
                                if len(images) >= 10:  # Limit to 10 images per page
                                    break
                
                if not text or len(text) < 50:
                    return None
                
                # Convert to markdown-like format
                markdown_content = f"# {title_text}\n\n{text}"
                
                return {
                    "title": title_text,
                    "content": markdown_content,
                    "url": url,
                    "source": "esilv_website_httpx",
                    "metadata": {
                        "source": url,
                        "url": url,
                        "title": title_text,
                        "images": [img['url'] for img in images],
                        "image_count": len(images),
                        "image_details": images
                    },
                    "images": images
                }
        except Exception as e:
            logger.debug(f"httpx fallback failed for {url}: {str(e)[:100]}")
            return None
    
    async def scrape_url(self, url: str, exclude_patterns: List[str] = None, retries: int = 2) -> Optional[Dict[str, Any]]:
        """
        Scrape a single URL using Crawl4AI with httpx fallback.
        
        Args:
            url: URL to scrape
            exclude_patterns: List of regex patterns for URLs to exclude (e.g., [".*\\.pdf$"])
            retries: Number of retry attempts for Crawl4AI
        
        Returns:
            Dictionary with markdown content, images, and metadata, or None if error
        """
        import re
        
        # Check if URL should be excluded
        if exclude_patterns:
            for pattern in exclude_patterns:
                if re.match(pattern, url):
                    logger.debug(f"Skipping excluded URL: {url} (matches {pattern})")
                    return None
        
        # Try Crawl4AI first (better for dynamic content)
        for attempt in range(retries + 1):
            try:
                from crawl4ai import CrawlerRunConfig, CacheMode
                
                logger.debug(f"Scraping with Crawl4AI (attempt {attempt + 1}/{retries + 1}): {url}")
                
                crawler = await self._get_crawler()
                
                # Increase timeout on retries
                timeout_ms = 45000 if attempt > 0 else 60000  # 45s on retry, 60s first attempt
                
                run_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    wait_until="domcontentloaded",
                    delay_before_return_html=2.0 if attempt > 0 else 1.5,  # Longer delay on retry
                    word_count_threshold=10,
                    page_timeout=timeout_ms,
                    exclude_external_images=False,
                    screenshot=False,
                    remove_overlay_elements=False,
                    excluded_tags=['nav', 'footer', 'aside', 'header'],
                )
                
                result = await crawler.arun(url=url, config=run_config)
                
                if result.success:
                    # Extract markdown content
                    try:
                        markdown_content = result.markdown.raw_markdown if hasattr(result.markdown, 'raw_markdown') else result.markdown
                    except Exception:
                        markdown_content = str(result.markdown) if result.markdown else None
                    
                    if markdown_content and len(markdown_content) >= 50:
                        # Extract images
                        images = []
                        if result.media and 'images' in result.media:
                            for img in result.media['images']:
                                if isinstance(img, dict):
                                    img_url = img.get('src') or img.get('url')
                                    if img_url and img_url.startswith('http'):
                                        images.append({
                                            'url': img_url,
                                            'alt': img.get('alt', ''),
                                            'title': img.get('title', '')
                                        })
                                elif isinstance(img, str) and img.startswith('http'):
                                    images.append({
                                        'url': img,
                                        'alt': '',
                                        'title': ''
                                    })
                        
                        # Extract metadata
                        metadata = result.metadata if hasattr(result, 'metadata') else {}
                        if not isinstance(metadata, dict):
                            metadata = {}
                        
                        metadata['source'] = url
                        metadata['url'] = url
                        metadata['title'] = metadata.get('title', url.split('/')[-1] or 'ESILV Page')
                        
                        if images:
                            metadata['images'] = [img['url'] for img in images]
                            metadata['image_count'] = len(images)
                            metadata['image_details'] = images
                        
                        logger.debug(f"✅ Crawl4AI success: {url} ({len(markdown_content)} chars, {len(images)} images)")
                        
                        return {
                            "title": metadata.get('title', url),
                            "content": markdown_content,
                            "url": url,
                            "source": "esilv_website_crawl4ai",
                            "metadata": metadata,
                            "images": images
                        }
                    else:
                        # Content too short - try fallback on last attempt
                        if attempt == retries:
                            logger.debug(f"Crawl4AI content too short for {url}, trying httpx fallback...")
                            return await self._scrape_with_httpx(url)
                else:
                    # Crawl4AI failed (result.success == False)
                    error_msg = result.error_message or "Unknown error"
                    logger.debug(f"Crawl4AI failed for {url} (attempt {attempt + 1}): {error_msg[:100]}")
                    
                    # Try fallback on last attempt
                    if attempt == retries:
                        logger.info(f"🔄 Crawl4AI failed for {url} after {retries + 1} attempts, trying httpx fallback...")
                        return await self._scrape_with_httpx(url)
                    # Otherwise, retry with delay
                    await asyncio.sleep(1)
                    continue
                
            except Exception as scrape_error:
                error_msg = str(scrape_error).lower()
                if attempt == retries:
                    # Last attempt failed, try fallback
                    logger.debug(f"Crawl4AI exception for {url} (attempt {attempt + 1}), trying httpx fallback...")
                    return await self._scrape_with_httpx(url)
                # Otherwise, retry
                logger.debug(f"Crawl4AI error for {url} (attempt {attempt + 1}): {error_msg[:100]}")
                await asyncio.sleep(1)  # Brief delay before retry
                continue
        
        # If all Crawl4AI attempts failed, try httpx fallback
        return await self._scrape_with_httpx(url)
    
    async def scrape_urls(
        self,
        urls: List[str],
        exclude_patterns: List[str] = None,
        max_concurrent: int = 5,
        index_batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs concurrently using Crawl4AI with httpx fallback.
        Indexes content in batches and skips URLs already in RAG.
        
        Args:
            urls: List of URLs to scrape
            exclude_patterns: List of regex patterns for URLs to exclude
            max_concurrent: Maximum number of concurrent scrapes
            index_batch_size: Number of URLs to scrape before indexing (default: 10)
        
        Returns:
            List of scraped content dictionaries
        """
        if not urls:
            return []
        
        # Default exclude patterns: exclude PDFs
        if exclude_patterns is None:
            exclude_patterns = [r".*\.pdf$"]
        
        # Get existing URLs from RAG to skip them
        logger.info("Checking existing URLs in RAG...")
        existing_urls = vector_store.get_existing_urls()
        logger.info(f"Found {len(existing_urls)} existing URLs in RAG")
        
        # Filter out existing URLs
        urls_to_scrape = [url for url in urls if url not in existing_urls]
        skipped_count = len(urls) - len(urls_to_scrape)
        
        if skipped_count > 0:
            logger.info(f"⏭️  Skipping {skipped_count} URLs already in RAG")
        
        if not urls_to_scrape:
            logger.info("✅ All URLs are already in RAG!")
            return []
        
        logger.info(f"📋 Scraping {len(urls_to_scrape)} new URLs...")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        success_count = 0
        total_count = len(urls_to_scrape)
        batch_results = []
        indexed_count = 0
        
        async def scrape_with_semaphore(url, index):
            nonlocal success_count, batch_results, indexed_count
            async with semaphore:
                # Check again if URL exists (in case it was added by another process)
                if vector_store.url_exists(url):
                    logger.debug(f"⏭️  URL already in RAG (skipped): {url}")
                    return None
                
                result = await self.scrape_url(url, exclude_patterns=exclude_patterns, retries=2)
                if result:
                    success_count += 1
                    batch_results.append(result)
                    
                    # Index every index_batch_size URLs
                    if success_count % index_batch_size == 0:
                        logger.info(f"📊 Progress: {success_count}/{total_count} URLs scraped successfully")
                        logger.info(f"📥 Indexing batch of {len(batch_results)} URLs into RAG...")
                        
                        # Index the batch
                        batch_stats = self.index_scraped_content(batch_results)
                        indexed_count += batch_stats['indexed']
                        logger.info(f"✅ Indexed {batch_stats['indexed']} documents ({batch_stats['chunks']} chunks) - Total indexed: {indexed_count}")
                        
                        # Clear batch
                        batch_results = []
                
                return result
        
        # Scrape all URLs concurrently
        tasks = [scrape_with_semaphore(url, i) for i, url in enumerate(urls_to_scrape)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.debug(f"Exception during scraping {urls_to_scrape[i]}: {str(result)[:100]}")
            elif result is not None:
                valid_results.append(result)
        
        # Index remaining batch
        if batch_results:
            logger.info(f"📥 Indexing final batch of {len(batch_results)} URLs into RAG...")
            batch_stats = self.index_scraped_content(batch_results)
            indexed_count += batch_stats['indexed']
            logger.info(f"✅ Indexed {batch_stats['indexed']} documents ({batch_stats['chunks']} chunks) - Total indexed: {indexed_count}")
        
        logger.info(f"✅ Scraped {len(valid_results)}/{len(urls_to_scrape)} new URLs successfully ({len(valid_results)*100//len(urls_to_scrape) if urls_to_scrape else 0}%)")
        logger.info(f"📊 Total: {indexed_count} documents indexed in this session")
        return valid_results
    
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
        
        from langchain_core.documents import Document
        import json
        
        # Try to import filter_complex_metadata
        try:
            from langchain_community.vectorstores.utils import filter_complex_metadata
        except ImportError:
            # Fallback function if not available
            def filter_complex_metadata(docs):
                """Fallback: manually filter complex metadata."""
                for doc in docs:
                    if hasattr(doc, 'metadata') and isinstance(doc.metadata, dict):
                        # Convert lists to JSON strings
                        filtered_meta = {}
                        for key, value in doc.metadata.items():
                            if isinstance(value, (list, dict)):
                                filtered_meta[key] = json.dumps(value) if value else ""
                            elif isinstance(value, (str, int, float, bool)) or value is None:
                                filtered_meta[key] = value
                            else:
                                # Convert other types to string
                                filtered_meta[key] = str(value)
                        doc.metadata = filtered_meta
                return docs
        
        total_chunks = 0
        indexed = 0
        errors = 0
        
        for content in content_list:
            try:
                # Ensure metadata is a dictionary
                metadata = content.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                
                # Add source and URL to metadata
                metadata["source"] = content.get("url", "")
                metadata["url"] = content.get("url", "")
                metadata["title"] = content.get("title", "")
                
                # Add images to metadata - convert list to JSON string for ChromaDB compatibility
                images = content.get("images", [])
                if images:
                    # Extract image URLs
                    image_urls = [img['url'] if isinstance(img, dict) else img for img in images]
                    # Store as JSON string (ChromaDB doesn't support lists)
                    metadata["images"] = json.dumps(image_urls) if image_urls else ""
                    metadata["image_count"] = len(image_urls)
                    # Store image details as JSON string too
                    metadata["image_details"] = json.dumps(images) if images else ""
                else:
                    metadata["images"] = ""
                    metadata["image_count"] = 0
                    metadata["image_details"] = ""
                
                # Create document
                doc = Document(
                    page_content=content["content"],
                    metadata=metadata
                )
                
                # Process and chunk
                chunks = document_processor.text_splitter.split_documents([doc])
                
                # Add rich structured metadata to each chunk (as recommended in the guide)
                for i, chunk in enumerate(chunks):
                    # Basic chunk info
                    chunk.metadata["chunk_index"] = i
                    chunk.metadata["total_chunks"] = len(chunks)
                    chunk.metadata["chunk_id"] = f"{metadata.get('title', 'page').replace(' ', '_')}_chunk_{i}"
                    
                    # Content information
                    chunk.metadata["content_type"] = "web_page"
                    chunk.metadata["file_type"] = "html"
                    chunk.metadata["chunk_length"] = len(chunk.page_content)
                    chunk.metadata["scraped_from"] = content.get("source", "esilv_website_crawl4ai")
                    
                    # Don't store images in chunks - they're stored at source level only
                    # This reduces metadata bloat and improves performance
                    
                    # Ensure all important metadata is preserved
                    for key in ["source", "url", "title"]:
                        if key in metadata and key not in chunk.metadata:
                            chunk.metadata[key] = metadata[key]
                
                # Filter complex metadata before adding to ChromaDB
                chunks = filter_complex_metadata(chunks)
                
                # Add to vector store
                vector_store.add_documents(chunks)
                
                total_chunks += len(chunks)
                indexed += 1
                
                logger.info(f"Indexed {content.get('title', content.get('url', 'unknown'))}: {len(chunks)} chunks, {len(images)} images")
                
            except Exception as e:
                errors += 1
                logger.error(f"Error indexing content from {content.get('url', 'unknown')}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                continue
        
        return {
            "indexed": indexed,
            "chunks": total_chunks,
            "errors": errors
        }


# Global instance (will be initialized when needed)
crawl4ai_scraper = Crawl4AIScraper()


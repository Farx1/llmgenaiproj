"""Alternative Firecrawl integration using LangChain's FireCrawlLoader."""
import logging
from typing import List
from rag.vector_store import vector_store
from rag.document_processor import document_processor
from config import settings

logger = logging.getLogger(__name__)


def scrape_with_langchain_loader(
    url: str = None, 
    mode: str = "crawl",
    exclude_patterns: List[str] = None
) -> List:
    """
    Scrape website using LangChain's FireCrawlLoader.
    This is simpler and more integrated with LangChain.
    
    Args:
        url: URL to scrape (defaults to ESILV base URL)
        mode: "crawl" (all pages) or "scrape" (single page)
        exclude_patterns: List of regex patterns for URLs to exclude (e.g., [".*\\.pdf$"])
    
    Returns:
        List of LangChain Document objects
    """
    if not settings.firecrawl_api_key:
        logger.error("Firecrawl API key not set. Please set FIRECRAWL_API_KEY in .env file.")
        return []
    
    try:
        from langchain_community.document_loaders import FireCrawlLoader
    except ImportError:
        logger.error("FireCrawlLoader not available. Install: pip install langchain-community")
        return []
    
    url = url or settings.esilv_base_url
    
    # Default exclude patterns: exclude PDFs
    if exclude_patterns is None:
        exclude_patterns = [r".*\.pdf$"]
    
    try:
        import time
        start_time = time.time()
        
        logger.info(f"🚀 Starting FireCrawl crawl for: {url}")
        logger.info(f"   Mode: {mode}")
        if exclude_patterns:
            logger.info(f"   Excluding patterns: {exclude_patterns}")
        logger.info("   Firecrawl is discovering and crawling pages... This may take a while.")
        
        # FireCrawlLoader params for exclude patterns
        loader_params = {
            "api_key": settings.firecrawl_api_key,
            "url": url,
            "mode": mode  # "crawl" for all pages, "scrape" for single page
        }
        
        # Add exclude patterns if supported by FireCrawlLoader
        # Note: Check FireCrawlLoader documentation for exact parameter name
        # Some versions use 'params' dict, others use direct parameters
        try:
            # Try with params dict (newer versions)
            loader = FireCrawlLoader(
                **loader_params,
                params={
                    "exclude_patterns": exclude_patterns
                }
            )
            logger.info("   ✓ FireCrawlLoader initialized with exclude patterns")
        except TypeError:
            # Fallback: try without params if not supported
            loader = FireCrawlLoader(**loader_params)
            logger.info("   ✓ FireCrawlLoader initialized (exclude patterns may not be supported)")
        
        # Load documents - FireCrawlLoader returns LangChain Documents directly
        # This is a blocking call that may take several minutes
        logger.info("   ⏳ Loading document from Firecrawl API...")
        docs = loader.load()
        
        elapsed_time = time.time() - start_time
        
        # Extract images from metadata if available
        for doc in docs:
            # Firecrawl may include images in metadata
            # Try to extract images from various possible locations
            images = []
            
            # Check metadata for images
            if hasattr(doc, 'metadata') and doc.metadata:
                # Check for images array
                if 'images' in doc.metadata and isinstance(doc.metadata['images'], list):
                    images = doc.metadata['images']
                # Check for image field
                elif 'image' in doc.metadata:
                    img = doc.metadata['image']
                    if isinstance(img, str):
                        images = [img]
                    elif isinstance(img, list):
                        images = img
                # Check for og:image or other image metadata
                elif 'og:image' in doc.metadata:
                    images = [doc.metadata['og:image']]
                # Try to extract images from markdown content (images in markdown format)
                elif hasattr(doc, 'page_content'):
                    import re
                    # Find all markdown image links: ![alt](url)
                    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
                    markdown_images = re.findall(img_pattern, doc.page_content)
                    if markdown_images:
                        images = [url for alt, url in markdown_images if url.startswith('http')]
            
            # Store images in metadata
            if images:
                doc.metadata['images'] = images
                doc.metadata['image_count'] = len(images)
                logger.info(f"   📷 Found {len(images)} image(s) for {doc.metadata.get('url', url)}")
        
        if mode == "scrape":
            logger.info(f"✅ FireCrawl scrape completed!")
            logger.info(f"   Page scraped: {len(docs)} document(s)")
            logger.info(f"   Time elapsed: {elapsed_time:.2f} seconds")
            if docs:
                doc = docs[0]
                url_found = doc.metadata.get('url', doc.metadata.get('source', url))
                title = doc.metadata.get('title', 'No title')
                image_count = doc.metadata.get('image_count', 0)
                logger.info(f"   Title: {title[:60]}...")
                logger.info(f"   URL: {url_found[:80]}...")
                if image_count > 0:
                    logger.info(f"   Images: {image_count} found")
        else:
            logger.info(f"✅ FireCrawl crawl completed!")
            logger.info(f"   Pages discovered: {len(docs)}")
            logger.info(f"   Time elapsed: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
            if docs:
                # Log sample of URLs found
                sample_size = min(5, len(docs))
                logger.info(f"   Sample URLs found (first {sample_size}):")
                for i, doc in enumerate(docs[:sample_size], 1):
                    url_found = doc.metadata.get('url', doc.metadata.get('source', 'unknown'))
                    title = doc.metadata.get('title', 'No title')
                    logger.info(f"      {i}. {title[:60]}... ({url_found[:80]}...)")
                if len(docs) > sample_size:
                    logger.info(f"      ... and {len(docs) - sample_size} more pages")
        
        return docs
        
    except Exception as e:
        logger.error(f"Error loading with FireCrawlLoader: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


def index_firecrawl_documents(docs: List) -> dict:
    """
    Index FireCrawl documents into vector store.
    
    Args:
        docs: List of LangChain Document objects from FireCrawlLoader
    
    Returns:
        Dictionary with indexing statistics
    """
    if not docs:
        return {"indexed": 0, "chunks": 0, "errors": 0}
    
    import time
    start_time = time.time()
    
    total_chunks = 0
    indexed = 0
    errors = 0
    
    logger.info(f"📦 Starting indexing of {len(docs)} documents into ChromaDB...")
    
    for idx, doc in enumerate(docs, 1):
        try:
            # Add metadata for citations
            if "chunk_index" not in doc.metadata:
                doc.metadata["chunk_index"] = 0
            if "scraped_from" not in doc.metadata:
                doc.metadata["scraped_from"] = "esilv_website_firecrawl"
            
            # Get document info for logging
            doc_url = doc.metadata.get('url', doc.metadata.get('source', 'unknown'))
            doc_title = doc.metadata.get('title', 'No title')[:50]
            
            # Split into chunks
            chunks = document_processor.text_splitter.split_documents([doc])
            
            # Add chunk index to metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk_index"] = i
                chunk.metadata["total_chunks"] = len(chunks)
            
            # Add to vector store
            vector_store.add_documents(chunks)
            
            total_chunks += len(chunks)
            indexed += 1
            
            # Log progress every 10 documents or for all if less than 10
            if indexed % 10 == 0 or indexed == len(docs):
                elapsed = time.time() - start_time
                rate = indexed / elapsed if elapsed > 0 else 0
                logger.info(f"   [{indexed}/{len(docs)}] Indexed: {doc_title}... → {len(chunks)} chunks (Rate: {rate:.1f} docs/sec)")
            
        except Exception as e:
            errors += 1
            logger.error(f"   ❌ Error indexing document {idx} ({doc_url}): {str(e)}")
            continue
    
    elapsed_time = time.time() - start_time
    logger.info(f"✅ Indexing completed!")
    logger.info(f"   Documents indexed: {indexed}/{len(docs)}")
    logger.info(f"   Total chunks created: {total_chunks}")
    logger.info(f"   Errors: {errors}")
    logger.info(f"   Time elapsed: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    
    return {
        "indexed": indexed,
        "chunks": total_chunks,
        "errors": errors
    }


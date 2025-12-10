"""
Script to scrape ESILV website using Crawl4AI and index content.
Supports multiple URLs from sitemap and excludes PDFs automatically.
Crawl4AI is open source with no API limits.
"""
import logging
import sys
import os
import re
import asyncio
from typing import List, Optional
from utils.crawl4ai_scraper import crawl4ai_scraper
from config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_urls_from_file(file_path: str) -> List[str]:
    """
    Load URLs from a text file (one URL per line).
    
    Args:
        file_path: Path to the file containing URLs
    
    Returns:
        List of URLs
    """
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith('#'):  # Skip empty lines and comments
                    urls.append(url)
        logger.info(f"Loaded {len(urls)} URLs from {file_path}")
        return urls
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return []


async def scrape_multiple_urls(
    urls: List[str],
    exclude_patterns: Optional[List[str]] = None,
    max_concurrent: int = 5
):
    """
    Scrape multiple URLs using Crawl4AI (open source, no API key required).
    
    Args:
        urls: List of URLs to scrape
        exclude_patterns: List of regex patterns for URLs to exclude (default: excludes PDFs)
        max_concurrent: Maximum number of concurrent scrapes (default: 5)
    """
    # Crawl4AI doesn't require an API key - it's open source
    
    if not urls:
        print("❌ Error: No URLs provided!")
        return
    
    # Default exclude patterns: exclude PDFs
    if exclude_patterns is None:
        exclude_patterns = [r".*\.pdf$"]
    
    print("=" * 70)
    print("ESILV Website Scraper (Crawl4AI)")
    print("=" * 70)
    print(f"\nStarting URLs: {len(urls)}")
    print(f"Excluding patterns: {exclude_patterns}")
    print(f"Max concurrent scrapes: {max_concurrent}")
    print(f"Method: Crawl4AI (Open Source, No API Limits)")
    print("\nCrawl4AI will scrape each URL from your sitemap list.")
    print("This may take several minutes depending on the number of URLs.\n")
    
    import time
    overall_start = time.time()
    
    try:
        # Initialize crawler
        await crawl4ai_scraper._get_crawler()
        
        # Scrape all URLs concurrently (indexing happens automatically in batches)
        print(f"\n🚀 Starting concurrent scraping of {len(urls)} URLs...")
        print(f"   Max concurrent: {max_concurrent}")
        print(f"   Indexing in batches of 10 URLs")
        print(f"   URLs already in RAG will be skipped automatically\n")
        
        scraped_content = await crawl4ai_scraper.scrape_urls(
            urls=urls,
            exclude_patterns=exclude_patterns,
            max_concurrent=max_concurrent,
            index_batch_size=10  # Index every 10 URLs
        )
        
        scraping_elapsed = time.time() - overall_start
        
        # Close crawler
        await crawl4ai_scraper.close()
        
        total_elapsed = time.time() - overall_start
        
        # Count total images
        total_images = sum(len(content.get('images', [])) for content in scraped_content) if scraped_content else 0
        
        print("\n" + "=" * 70)
        print("🎉 Scraping and indexing completed!")
        print("=" * 70)
        print(f"📊 Statistics:")
        print(f"   Total URLs processed: {len(urls)}")
        print(f"   URLs already in RAG (skipped): {len(urls) - len(scraped_content) if scraped_content else 0}")
        print(f"   New URLs scraped: {len(scraped_content) if scraped_content else 0}")
        print(f"   Total images found: {total_images}")
        print(f"\n⏱️  Timing:")
        print(f"   Total time: {total_elapsed:.2f}s ({total_elapsed/60:.2f} min)")
        print(f"\n✅ The chatbot can now answer questions using this content!")
        print("\nCrawl4AI advantages:")
        print("  ✓ Open source - no API limits or costs")
        print("  ✓ Handles JavaScript and dynamic content (Playwright-based)")
        print("  ✓ Generates clean Markdown optimized for RAG")
        print("  ✓ Extracts images with context")
        print("  ✓ Concurrent processing for fast scraping")
        print("  ✓ Excludes PDFs and other specified patterns")
        print("  ✓ Integrated with LangChain for seamless RAG")
        
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        print(f"\n❌ Error: {str(e)}")


async def main():
    """Main async function."""
    # Check for command line arguments
    urls: List[str] = []
    priority_only = '--priority' in sys.argv or '-p' in sys.argv
    
    if len(sys.argv) > 1 and not priority_only:
        # URLs provided as command line arguments (skip --priority flag)
        urls = [url for url in sys.argv[1:] if url.startswith('http')]
    else:
        # Load priority URLs first (from sitemap XML)
        priority_file = os.path.join(os.path.dirname(__file__), 'esilv_urls_priority.txt')
        priority_urls = []
        if os.path.exists(priority_file):
            priority_urls = load_urls_from_file(priority_file)
            logger.info(f"📌 Loaded {len(priority_urls)} priority URLs from sitemap")
        
        if priority_only:
            # Only scrape priority URLs
            urls = priority_urls
            print("🎯 Scraping PRIORITY URLs only (from sitemap XML)")
        else:
            # Load regular URLs
            urls_file = os.path.join(os.path.dirname(__file__), 'esilv_urls.txt')
            regular_urls = []
            if os.path.exists(urls_file):
                regular_urls = load_urls_from_file(urls_file)
            
            # Combine: priority URLs first, then regular URLs
            # Remove duplicates (priority URLs take precedence)
            priority_set = set(priority_urls)
            regular_urls_filtered = [url for url in regular_urls if url not in priority_set]
            urls = priority_urls + regular_urls_filtered
            
            if priority_urls:
                print(f"📌 Priority URLs (from sitemap): {len(priority_urls)}")
                print(f"📄 Regular URLs: {len(regular_urls_filtered)}")
                print(f"📋 Total URLs: {len(urls)} (priority URLs will be scraped first)")
    
    # Filter out XML sitemap files and other non-HTML URLs
    filtered_urls = []
    for url in urls:
        # Skip sitemap XML files
        if url.endswith('.xml') or 'sitemap' in url.lower():
            logger.info(f"Skipping sitemap file: {url}")
            continue
        filtered_urls.append(url)
    
    if not filtered_urls:
        print("❌ No valid URLs to scrape after filtering.")
        return
    
    print(f"📋 Total URLs to scrape: {len(filtered_urls)} (filtered from {len(urls)})")
    
    # Scrape all URLs
    await scrape_multiple_urls(
        urls=filtered_urls,
        exclude_patterns=[r".*\.pdf$"],  # Exclude PDFs
        max_concurrent=5  # Process 5 URLs concurrently
    )


if __name__ == "__main__":
    asyncio.run(main())

"""Document upload and management API endpoints."""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List, Optional
import os
import aiofiles
from rag.document_processor import document_processor
from rag.vector_store import vector_store
from utils.crawl4ai_scraper import crawl4ai_scraper
import asyncio
from config import settings
from langchain_core.documents import Document
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Directory for uploaded documents
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document.
    
    Args:
        file: Uploaded file
    
    Returns:
        Upload result with document IDs
    """
    try:
        # Save file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Process document
        documents = await document_processor.process_file(file_path)
        
        # Add to vector store
        doc_ids = vector_store.add_documents(documents)
        
        return {
            "message": "Document uploaded and processed successfully",
            "filename": file.filename,
            "chunks": len(documents),
            "document_ids": doc_ids
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")


@router.post("/upload-text")
async def upload_text(text: str, metadata: dict = None):
    """
    Upload text content directly.
    
    Args:
        text: Text content
        metadata: Optional metadata
    
    Returns:
        Upload result
    """
    try:
        # Process text
        documents = document_processor.process_text(text, metadata=metadata)
        
        # Add to vector store
        doc_ids = vector_store.add_documents(documents)
        
        return {
            "message": "Text uploaded and processed successfully",
            "chunks": len(documents),
            "document_ids": doc_ids
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading text: {str(e)}")


@router.get("/search")
async def search_documents(query: str, k: int = 4):
    """
    Search documents in the vector store.
    
    Args:
        query: Search query
        k: Number of results
    
    Returns:
        Search results
    """
    try:
        results = vector_store.similarity_search_with_score(query, k=k)
        
        return {
            "query": query,
            "results": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                }
                for doc, score in results
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching documents: {str(e)}")


@router.get("/rag/stats")
async def get_rag_stats():
    """
    Get RAG statistics including collection info and document counts.
    Optimized for speed to avoid timeouts.
    
    Returns:
        RAG statistics
    """
    import time
    start_time = time.time()
    
    logger.info("=" * 70)
    logger.info("DEBUG: ========== RAG STATS REQUEST ==========")
    logger.info("=" * 70)
    
    try:
        logger.info(f"DEBUG: vector_store.collection_name = {vector_store.collection_name}")
        
        # Initialize variables
        sample_docs = []
        unique_sources = set()
        collection = None
        
        # Get collection directly - use the same method as the startup test
        # This is more reliable than get_collection_info() which may fail with NotFoundError
        try:
            logger.info("DEBUG: Getting collection from ChromaDB (same method as startup test)...")
            try:
                collection = vector_store.client.get_collection(name=vector_store.collection_name)
                logger.info(f"DEBUG: ✅ Collection retrieved")
                # Try to peek to verify it's accessible
                try:
                    collection.peek(limit=1)
                    logger.info("DEBUG: ✅ Collection is accessible")
                except KeyError as peek_error:
                    # Handle '_type' error when peeking
                    if "'_type'" in str(peek_error) or "_type" in str(peek_error):
                        logger.warning(f"DEBUG: ⚠️ Collection has '_type' error when peeking: {peek_error}")
                        logger.warning("DEBUG: Collection exists but may have structure issues - count() may still work")
                    else:
                        raise
            except (KeyError, Exception) as ke:
                # Handle '_type' error or NotFoundError - collection structure issue or not found
                error_str = str(ke)
                error_type = type(ke).__name__
                
                if "'_type'" in error_str or "_type" in error_str:
                    logger.warning(f"DEBUG: ⚠️ Collection access error (likely '_type' issue): {ke}")
                    logger.warning("DEBUG: This usually means the collection exists but may need to be re-indexed")
                    # Try to continue - count() might still work
                elif "NotFoundError" in error_type or "does not exist" in error_str:
                    logger.warning(f"DEBUG: ⚠️ Collection not found via get_collection(): {ke}")
                    logger.info("DEBUG: Trying list_collections() as fallback...")
                    # Try list_collections() to find the collection
                    try:
                        collections = vector_store.client.list_collections()
                        for col in collections:
                            if col.name == vector_store.collection_name:
                                collection = col
                                logger.info(f"DEBUG: ✅ Found collection via list_collections(): {col.name}")
                                break
                        if collection is None:
                            logger.error("DEBUG: ❌ Collection not found in list_collections() either")
                            # Collection doesn't exist - return empty
                            return {
                                "collection_info": {
                                    "name": vector_store.collection_name,
                                    "document_count": 0,
                                    "status": "empty",
                                    "error": "Collection does not exist"
                                },
                                "sample_sources": [],
                                "total_sources": 0
                            }
                    except Exception as list_error:
                        logger.error(f"DEBUG: ❌ list_collections() also failed: {list_error}")
                        # Return error
                        return {
                            "collection_info": {
                                "name": vector_store.collection_name,
                                "document_count": 0,
                                "status": "error",
                                "error": f"Error accessing collection: {str(list_error)}"
                            },
                            "sample_sources": [],
                            "total_sources": 0
                        }
                else:
                    raise
        except Exception as collection_error:
            logger.error(f"DEBUG: ❌ Error getting collection: {collection_error}")
            return {
                "collection_info": {
                    "name": vector_store.collection_name,
                    "document_count": 0,
                    "status": "error",
                    "error": f"Error accessing collection: {str(collection_error)}"
                },
                "sample_sources": [],
                "total_sources": 0
            }
        
        # If collection is None after all fallbacks, return error
        if collection is None:
            logger.error("DEBUG: ❌ Collection is None after all fallback attempts")
            return {
                "collection_info": {
                    "name": vector_store.collection_name,
                    "document_count": 0,
                    "status": "error",
                    "error": "Collection not accessible"
                },
                "sample_sources": [],
                "total_sources": 0
            }
        
        # Use collection.count() directly - same method as startup test
        doc_count = 0
        collection_info = {
            "name": vector_store.collection_name,
            "document_count": 0,
            "status": "empty"
        }
        sample_docs = []
        
        # Use collection.count() directly - same method as startup test
        if collection is not None:
            # Use EXACT same method as test_rag_on_startup.py which successfully returns 93,239
            doc_count = 0
            try:
                logger.info("DEBUG: Attempting collection.count() (EXACT same method as startup test)...")
                def get_count():
                    return collection.count()
                
                try:
                    doc_count = await asyncio.wait_for(
                        asyncio.to_thread(get_count),
                        timeout=10.0  # Same timeout as startup test
                    )
                    logger.info(f"DEBUG: ✅ count() succeeded: {doc_count}")
                except asyncio.TimeoutError:
                    logger.warning("DEBUG: count() timed out after 10s, using large sample estimation...")
                    # Fallback: use large sample for estimation
                    try:
                        larger = collection.get(limit=100000)  # Get up to 100k
                        if larger and "ids" in larger:
                            doc_count = len(larger["ids"])
                            logger.info(f"DEBUG: Estimated count from sample: {doc_count}")
                            if doc_count == 100000:
                                # Indicate it's at least 100k
                                doc_count = 100000
                        else:
                            logger.warning("DEBUG: Large sample is None or has no 'ids'")
                            doc_count = 0
                    except Exception as sample_error:
                        logger.error(f"DEBUG: ❌ Error getting large sample: {sample_error}")
                        # Try peek() as last resort
                        try:
                            peek_sample = collection.peek(limit=1000)
                            if peek_sample and "ids" in peek_sample:
                                doc_count = len(peek_sample["ids"])
                                logger.info(f"DEBUG: Estimated count from peek: {doc_count}")
                        except Exception:
                            doc_count = 0
                except (KeyError, Exception) as count_error:
                    error_str = str(count_error)
                    if "'_type'" in error_str or "_type" in error_str:
                        logger.warning(f"DEBUG: count() failed with '_type' error, using peek() estimation...")
                        # Try peek() as fallback
                        try:
                            peek_sample = collection.peek(limit=1000)
                            if peek_sample and "ids" in peek_sample:
                                doc_count = len(peek_sample["ids"])
                                logger.info(f"DEBUG: Estimated count from peek: {doc_count} (may be incomplete)")
                            else:
                                doc_count = 0
                        except Exception as peek_error:
                            logger.error(f"DEBUG: ❌ peek() also failed: {peek_error}")
                            doc_count = 0
                    else:
                        logger.error(f"DEBUG: ❌ count() failed: {count_error}")
                        # Try small sample as last resort
                        try:
                            sample = collection.get(limit=1000)
                            if sample and "ids" in sample:
                                doc_count = len(sample["ids"])
                                if doc_count == 1000:
                                    doc_count = 1000  # At least 1000
                            else:
                                doc_count = 0
                        except Exception:
                            doc_count = 0
            except Exception as e:
                logger.error(f"DEBUG: ❌ Error in count estimation: {e}")
                import traceback
                logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
                # Last resort: try to verify collection has documents using similarity_search
                try:
                    logger.info("DEBUG: Trying similarity_search as last resort to verify collection has documents...")
                    test_results = vector_store.similarity_search("ESILV", k=1)
                    if test_results:
                        logger.info("DEBUG: ✅ similarity_search works - collection has documents")
                        # Use get() with large limit to estimate count
                        try:
                            large_sample = collection.get(limit=100000)
                            if large_sample and "ids" in large_sample:
                                doc_count = len(large_sample["ids"])
                                logger.info(f"DEBUG: Estimated count from large sample: {doc_count}")
                            else:
                                # Collection has documents but can't count - indicate it's not empty
                                doc_count = 1  # At least 1 document exists
                                logger.info("DEBUG: Collection has documents but exact count unavailable")
                        except Exception:
                            doc_count = 1  # At least 1 document exists
                    else:
                        doc_count = 0
                except Exception:
                    doc_count = 0
            
            # Wrap collection access in try/except to handle errors
            try:
                collection_info = {
                    "name": vector_store.collection_name,
                    "document_count": doc_count,
                    "status": "active" if doc_count > 0 else "empty"
                }
                logger.info(f"DEBUG: ✅ Collection info: {collection_info}")
                
                # Get a sample of documents (limit to 50 for faster response)
                logger.info("DEBUG: Getting sample documents (limit=50) for sources list...")
                sample_data = collection.get(limit=50)  # Reduced from 100 for speed
                logger.info(f"DEBUG: Sample data retrieved, type: {type(sample_data)}")
                if isinstance(sample_data, dict):
                    logger.info(f"DEBUG: Sample data keys: {sample_data.keys()}")
                    if "ids" in sample_data:
                        logger.info(f"DEBUG: Sample has {len(sample_data['ids'])} IDs")
                    if "metadatas" in sample_data:
                        logger.info(f"DEBUG: Sample has {len(sample_data.get('metadatas', []))} metadatas")
                
                if sample_data and "metadatas" in sample_data and sample_data["metadatas"]:
                    logger.info(f"DEBUG: Processing {len(sample_data['metadatas'])} metadatas...")
                    sources_dict = {}
                    for idx, metadata in enumerate(sample_data["metadatas"]):
                        if metadata:
                            source = metadata.get("source") or metadata.get("url") or metadata.get("filename", "unknown")
                            if source and source not in unique_sources:
                                unique_sources.add(source)
                                sources_dict[source] = {
                                    "source": source,
                                    "title": metadata.get("title", os.path.basename(str(source))),
                                    "chunks": 1,
                                    "file_type": metadata.get("file_type", "unknown"),
                                    "scraped_from": metadata.get("scraped_from", "esilv_website")
                                }
                            elif source in sources_dict:
                                sources_dict[source]["chunks"] += 1
                    
                    sample_docs = list(sources_dict.values())[:20]  # Limit to 20 sources
                    logger.info(f"DEBUG: Created {len(sample_docs)} sample documents from {len(unique_sources)} unique sources")
                else:
                    # Fallback: use similarity search if direct get fails
                    logger.warning("DEBUG: Sample data is None or has no metadatas, using similarity search fallback")
                    try:
                        logger.info("DEBUG: Attempting similarity_search('ESILV', k=10)...")
                        sample_results = vector_store.similarity_search("ESILV", k=10)
                        logger.info(f"DEBUG: Similarity search returned {len(sample_results)} results")
                        sources = {}
                        for doc in sample_results:
                            source = doc.metadata.get("source", doc.metadata.get("filename", "unknown"))
                            if source not in sources:
                                sources[source] = {
                                    "source": source,
                                    "title": doc.metadata.get("title", os.path.basename(str(source))),
                                    "chunks": 0,
                                    "file_type": doc.metadata.get("file_type", "unknown"),
                                    "scraped_from": doc.metadata.get("scraped_from", "upload")
                                }
                            sources[source]["chunks"] += 1
                        
                        sample_docs = list(sources.values())[:20]  # Limit to 20 sources
                        logger.info(f"DEBUG: Created {len(sample_docs)} sample documents from similarity search")
                    except Exception as search_error:
                        logger.error(f"DEBUG: ❌ Similarity search also failed: {search_error}")
                        import traceback
                        logger.error(f"DEBUG: Similarity search traceback: {traceback.format_exc()}")
                        sample_docs = []
            except Exception as e:
                logger.error(f"DEBUG: ❌ Exception in collection access: {str(e)}")
                logger.error(f"DEBUG: Exception type: {type(e)}")
                import traceback
                logger.error(f"DEBUG: Full traceback: {traceback.format_exc()}")
                # Set default values
                collection_info = {
                    "name": vector_store.collection_name,
                    "document_count": 0,
                    "status": "error"
                }
                sample_docs = []
        
        # Try to get unique source count more efficiently
        total_unique_sources = len(unique_sources) if unique_sources else len(sample_docs)
        logger.info(f"DEBUG: Calculated total unique sources: {total_unique_sources}")
        
        result = {
            "collection_info": collection_info,
            "sample_sources": sample_docs,
            "total_sources": total_unique_sources
        }
        
        logger.info("=" * 70)
        logger.info(f"DEBUG: ✅ Final result: document_count={collection_info.get('document_count', 0)}, sample_sources={len(sample_docs)}, total_sources={total_unique_sources}")
        logger.info("=" * 70)
        
        return result
        
    except Exception as e:
        logger.error("=" * 70)
        logger.error(f"DEBUG: ❌❌❌ TOP-LEVEL ERROR in get_rag_stats: {str(e)}")
        logger.error(f"DEBUG: Error type: {type(e)}")
        import traceback
        logger.error(f"DEBUG: Full traceback:\n{traceback.format_exc()}")
        logger.error("=" * 70)
        raise HTTPException(status_code=500, detail=f"Error getting RAG stats: {str(e)}")


@router.get("/rag/search")
async def rag_search(query: str, k: int = 10):
    """
    Search in RAG with detailed results including images.
    
    Args:
        query: Search query
        k: Number of results
    
    Returns:
        Detailed search results with images
    """
    try:
        results = vector_store.similarity_search_with_score(query, k=k)
        
        formatted_results = []
        for doc, score in results:
            # Decode images from JSON string if needed
            images_raw = doc.metadata.get("images", [])
            images = []
            if images_raw:
                if isinstance(images_raw, str):
                    try:
                        import json
                        images = json.loads(images_raw) if images_raw else []
                    except (json.JSONDecodeError, TypeError):
                        images = []
                elif isinstance(images_raw, list):
                    images = images_raw
            
            result_item = {
                "content": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                "full_content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
                "source": doc.metadata.get("source", doc.metadata.get("filename", "unknown")),
                "title": doc.metadata.get("title", os.path.basename(str(doc.metadata.get("source", "unknown")))),
                "images": images
            }
            formatted_results.append(result_item)
        
        return {
            "query": query,
            "total_results": len(formatted_results),
            "results": formatted_results
        }
        
    except Exception as e:
        logger.error(f"Error in RAG search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching RAG: {str(e)}")


@router.get("/rag/source/{source_url:path}")
async def get_source_details(source_url: str, limit: int = 50, offset: int = 0):
    """
    Get details for a specific source including all its chunks.
    
    Args:
        source_url: URL or path of the source (URL-encoded)
        limit: Maximum number of chunks to return (default: 50)
        offset: Offset for pagination (default: 0)
    
    Returns:
        Source details with chunks
    """
    try:
        import urllib.parse
        # Decode the source URL
        decoded_source = urllib.parse.unquote(source_url)
        logger.info(f"Getting details for source: {decoded_source}")
        
        # Get the collection directly
        collection = vector_store.client.get_collection(name=vector_store.collection_name)
        
        # Get all chunks for this source
        try:
            # Try filtering by source field
            results = collection.get(
                where={"source": decoded_source},
                limit=limit + offset
            )
        except Exception:
            # Fallback: try with url field
            try:
                results = collection.get(
                    where={"url": decoded_source},
                    limit=limit + offset
                )
            except Exception:
                # Last fallback: get all and filter manually
                all_results = collection.get(limit=10000)
                filtered_ids = []
                filtered_documents = []
                filtered_metadatas = []
                
                if all_results and "ids" in all_results and "metadatas" in all_results:
                    for idx, metadata in enumerate(all_results.get("metadatas", [])):
                        if metadata and (metadata.get("source") == decoded_source or metadata.get("url") == decoded_source):
                            filtered_ids.append(all_results["ids"][idx])
                            filtered_metadatas.append(metadata)
                            if "documents" in all_results:
                                filtered_documents.append(all_results["documents"][idx])
                
                results = {
                    "ids": filtered_ids[offset:offset+limit],
                    "metadatas": filtered_metadatas[offset:offset+limit],
                    "documents": filtered_documents[offset:offset+limit] if filtered_documents else []
                }
        
        # Format the results
        chunks = []
        total_count = 0
        
        if results and "ids" in results:
            total_count = len(results["ids"])
            metadatas = results.get("metadatas", [])
            documents = results.get("documents", [])
            
            # Apply pagination
            paginated_ids = results["ids"][offset:offset+limit]
            paginated_metadatas = metadatas[offset:offset+limit] if metadatas else []
            paginated_documents = documents[offset:offset+limit] if documents else []
            
            for idx, doc_id in enumerate(paginated_ids):
                metadata = paginated_metadatas[idx] if idx < len(paginated_metadatas) else {}
                content = paginated_documents[idx] if idx < len(paginated_documents) else ""
                
                # Extract images
                images_raw = metadata.get("images", [])
                images = []
                if images_raw:
                    if isinstance(images_raw, str):
                        try:
                            import json
                            images = json.loads(images_raw) if images_raw else []
                        except (json.JSONDecodeError, TypeError):
                            images = []
                    elif isinstance(images_raw, list):
                        images = images_raw
                
                chunks.append({
                    "id": doc_id,
                    "content": content,
                    "preview": content[:300] + "..." if len(content) > 300 else content,
                    "metadata": metadata,
                    "images": images,
                    "chunk_index": metadata.get("chunk_index", idx),
                    "title": metadata.get("title", os.path.basename(str(decoded_source)))
                })
        
        # Get source metadata from first chunk
        source_metadata = {}
        if chunks:
            source_metadata = chunks[0].get("metadata", {})
        
        return {
            "source": decoded_source,
            "title": source_metadata.get("title", os.path.basename(str(decoded_source))),
            "total_chunks": total_count,
            "chunks": chunks,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count,
            "file_type": source_metadata.get("file_type", "unknown"),
            "scraped_from": source_metadata.get("scraped_from", "unknown")
        }
        
    except Exception as e:
        logger.error(f"Error getting source details: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error getting source details: {str(e)}")


@router.get("/rag/sources")
async def get_sources_list(limit: int = 20, offset: int = 0):
    """
    Get paginated list of sources.
    
    Args:
        limit: Maximum number of sources to return (default: 20)
        offset: Offset for pagination (default: 0)
    
    Returns:
        Paginated list of sources
    """
    try:
        collection = vector_store.client.get_collection(name=vector_store.collection_name)
        
        # Get a larger sample to extract unique sources
        sample_size = min(10000, (offset + limit) * 10)  # Get enough to find unique sources
        sample_data = collection.get(limit=sample_size)
        
        sources_dict = {}
        if sample_data and "metadatas" in sample_data and sample_data["metadatas"]:
            for idx, metadata in enumerate(sample_data["metadatas"]):
                if metadata:
                    source = metadata.get("source") or metadata.get("url") or metadata.get("filename", "unknown")
                    if source and source not in sources_dict:
                        sources_dict[source] = {
                            "source": source,
                            "title": metadata.get("title", os.path.basename(str(source))),
                            "chunks": 1,
                            "file_type": metadata.get("file_type", "unknown"),
                            "scraped_from": metadata.get("scraped_from", "esilv_website")
                        }
                    elif source in sources_dict:
                        sources_dict[source]["chunks"] += 1
        
        # Convert to list and apply pagination
        sources_list = list(sources_dict.values())[offset:offset+limit]
        total_sources = len(sources_dict)
        
        return {
            "sources": sources_list,
            "total": total_sources,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_sources
        }
        
    except Exception as e:
        logger.error(f"Error getting sources list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting sources list: {str(e)}")


@router.delete("/collection")
async def delete_collection():
    """Delete the entire collection."""
    try:
        vector_store.delete_collection()
        return {"message": "Collection deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting collection: {str(e)}")


@router.post("/scrape-esilv")
async def scrape_esilv_website(
    background_tasks: BackgroundTasks,
    sections: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    max_concurrent: int = 5
):
    """
    Scrape ESILV website using Crawl4AI and index content into vector store.
    Crawl4AI is open source with no API limits and handles JavaScript automatically.
    
    Args:
        background_tasks: FastAPI background tasks
        sections: Optional list of URLs to scrape (e.g., ["https://www.esilv.fr/formations", "https://www.esilv.fr/admissions"])
                  If None, uses URLs from esilv_urls.txt file
        exclude_patterns: List of regex patterns for URLs to exclude (default: excludes PDFs)
        max_concurrent: Maximum number of concurrent scrapes (default: 5)
    
    Returns:
        Scraping task started confirmation
    """
    try:
        # Default exclude patterns: exclude PDFs
        if exclude_patterns is None:
            exclude_patterns = [r".*\.pdf$"]
        
        async def scrape_and_index():
            """Background async task to scrape and index."""
            try:
                # Get URLs to scrape
                urls = sections
                if not urls:
                    # Load from file
                    urls_file = os.path.join(os.path.dirname(__file__), '..', 'esilv_urls.txt')
                    if os.path.exists(urls_file):
                        with open(urls_file, 'r', encoding='utf-8') as f:
                            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                    else:
                        urls = [settings.esilv_base_url]
                
                # Filter out XML sitemap files
                filtered_urls = [url for url in urls if not (url.endswith('.xml') or 'sitemap' in url.lower())]
                
                # Initialize crawler
                await crawl4ai_scraper._get_crawler()
                
                # Scrape URLs
                all_content = await crawl4ai_scraper.scrape_urls(
                    urls=filtered_urls,
                    exclude_patterns=exclude_patterns,
                    max_concurrent=max_concurrent
                )
                
                # Index the content
                stats = crawl4ai_scraper.index_scraped_content(all_content)
                logger.info(f"Crawl4AI scraping completed: {stats}")
                
                # Close crawler
                await crawl4ai_scraper.close()
            except Exception as e:
                logger.error(f"Error in background scraping task: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                try:
                    await crawl4ai_scraper.close()
                except:
                    pass
        
        # Run in background (FastAPI will handle the async task)
        background_tasks.add_task(lambda: asyncio.run(scrape_and_index()))
        
        return {
            "message": "Crawl4AI scraping task started in background",
            "sections": sections or "from esilv_urls.txt file",
            "exclude_patterns": exclude_patterns,
            "max_concurrent": max_concurrent,
            "note": "Crawl4AI is open source with no API limits"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting scraping task: {str(e)}")


@router.post("/scrape-esilv-sync")
async def scrape_esilv_website_sync(
    sections: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    max_concurrent: int = 5
):
    """
    Scrape ESILV website synchronously using Crawl4AI and return results.
    Use this for testing or when you want to wait for results.
    Crawl4AI is open source with no API limits and handles JavaScript automatically.
    
    Args:
        sections: Optional list of URLs to scrape
        exclude_patterns: List of regex patterns for URLs to exclude (default: excludes PDFs)
        max_concurrent: Maximum number of concurrent scrapes (default: 5)
    
    Returns:
        Scraping and indexing statistics
    """
    try:
        # Default exclude patterns: exclude PDFs
        if exclude_patterns is None:
            exclude_patterns = [r".*\.pdf$"]
        
        # Get URLs to scrape
        urls = sections
        if not urls:
            # Load from file
            urls_file = os.path.join(os.path.dirname(__file__), '..', 'esilv_urls.txt')
            if os.path.exists(urls_file):
                with open(urls_file, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            else:
                urls = [settings.esilv_base_url]
        
        # Filter out XML sitemap files
        filtered_urls = [url for url in urls if not (url.endswith('.xml') or 'sitemap' in url.lower())]
        
        logger.info(f"Using Crawl4AI to scrape {len(filtered_urls)} URLs")
        
        # Initialize crawler
        await crawl4ai_scraper._get_crawler()
        
        try:
            # Scrape URLs
            all_content = await crawl4ai_scraper.scrape_urls(
                urls=filtered_urls,
                exclude_patterns=exclude_patterns,
                max_concurrent=max_concurrent
            )
            
            # Index the content
            stats = crawl4ai_scraper.index_scraped_content(all_content)
            
            # Count total images
            total_images = sum(len(content.get('images', [])) for content in all_content)
            
            return {
                "message": "Crawl4AI scraping and indexing completed",
                "pages_scraped": len(all_content),
                "total_images": total_images,
                "indexing_stats": stats,
                "urls": filtered_urls[:10] if len(filtered_urls) > 10 else filtered_urls,  # Show first 10
                "exclude_patterns": exclude_patterns,
                "method": "crawl4ai"
            }
        finally:
            # Always close crawler
            await crawl4ai_scraper.close()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scraping ESILV website with Crawl4AI: {str(e)}")


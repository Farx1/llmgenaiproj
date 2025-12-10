"""Vector store management using ChromaDB."""
# Disable ChromaDB telemetry before importing to avoid blocking on Windows
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

import chromadb
import logging
from chromadb.config import Settings as ChromaSettings
try:
    from langchain_chroma import Chroma
except ImportError:
    # Fallback to deprecated import if langchain-chroma is not available
    from langchain_community.vectorstores import Chroma
try:
    from langchain_core.documents import Document
except ImportError:
    # Fallback for older versions
    try:
        from langchain.schema import Document
    except ImportError:
        from langchain_core.documents import Document
from typing import List, Optional
from config import settings
from utils.embeddings_factory import get_embeddings

# Initialize logger
logger = logging.getLogger(__name__)


class VectorStore:
    """Manages vector storage for RAG."""
    
    def __init__(self):
        """Initialize the vector store."""
        logger.info("=" * 70)
        logger.info("DEBUG: ========== VectorStore.__init__() ==========")
        logger.info(f"DEBUG: Initializing VectorStore...")
        logger.info(f"DEBUG: ChromaDB path: {settings.chroma_persist_directory}")
        logger.info(f"DEBUG: Collection name: {settings.chroma_collection_name}")
        
        try:
            logger.info("DEBUG: Creating ChromaDB PersistentClient...")
            self.client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            logger.info("DEBUG: ✅ ChromaDB client created")
            
            logger.info("DEBUG: Getting embeddings...")
            self.embeddings = get_embeddings()
            logger.info("DEBUG: ✅ Embeddings retrieved")
            
            self.collection_name = settings.chroma_collection_name
            self._vectorstore = None
            logger.info("DEBUG: ✅ VectorStore initialized")
            logger.info("=" * 70)
        except Exception as e:
            logger.error(f"DEBUG: ❌ Error initializing VectorStore: {e}")
            import traceback
            logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
            raise
    
    @property
    def vectorstore(self) -> Chroma:
        """Get or create the vectorstore."""
        if self._vectorstore is None:
            try:
                # Try to get existing collection
                self._vectorstore = Chroma(
                    client=self.client,
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings
                )
                # Test if collection is accessible by trying to peek
                try:
                    collection = self.client.get_collection(name=self.collection_name)
                    # Try to peek to verify collection is accessible
                    collection.peek(limit=1)
                except KeyError as ke:
                    # Handle '_type' error - collection may be corrupted
                    if "'_type'" in str(ke) or "_type" in str(ke):
                        logger.warning(f"DEBUG: Collection has '_type' error, may need re-indexing: {ke}")
                        # Continue anyway - similarity_search will handle it
                    else:
                        raise
            except Exception as e:
                logger.warning(f"DEBUG: Error accessing collection: {e}, creating new one")
                # Collection doesn't exist or has issues, create it
                self._vectorstore = Chroma.from_documents(
                    documents=[],
                    embedding=self.embeddings,
                    client=self.client,
                    collection_name=self.collection_name
                )
        return self._vectorstore
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of Document objects to add
        
        Returns:
            List of document IDs
        """
        return self.vectorstore.add_documents(documents)
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[dict] = None
    ) -> List[Document]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            k: Number of results to return
            filter: Optional metadata filter
        
        Returns:
            List of similar documents
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Don't check collection info - it may fail with '_type' error
        # Just try the search directly
        try:
            results = self.vectorstore.similarity_search(
                query=query,
                k=k,
                filter=filter
            )
            
            # Ensure all results are Document objects
            try:
                from langchain_core.documents import Document
            except ImportError:
                # Fallback for older versions
                try:
                    from langchain.schema import Document
                except ImportError:
                    from langchain_core.documents import Document
            
            normalized_results = []
            for doc in results:
                try:
                    if isinstance(doc, Document):
                        normalized_results.append(doc)
                    elif hasattr(doc, 'page_content') or hasattr(doc, 'content'):
                        # Convert to Document if it has the right attributes
                        content = getattr(doc, 'page_content', None) or getattr(doc, 'content', None)
                        metadata = getattr(doc, 'metadata', {}) if hasattr(doc, 'metadata') else {}
                        if content:
                            normalized_results.append(Document(page_content=content, metadata=metadata))
                    else:
                        # Skip invalid documents
                        logger.debug(f"Skipping document with unexpected type: {type(doc)}")
                        continue
                except Exception as doc_error:
                    # Skip this document if there's an error processing it
                    logger.warning(f"Error processing document: {str(doc_error)}")
                    continue
            
            return normalized_results
        except KeyError as e:
            # Handle '_type' or other KeyError specifically (empty collection or format issue)
            logger.error(f"KeyError in similarity_search (possibly empty collection or format issue): {str(e)}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return []
        except Exception as e:
            logger.error(f"Error in similarity_search: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return empty list instead of raising
            return []
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[dict] = None
    ) -> List[tuple]:
        """
        Search for similar documents with scores.
        
        Args:
            query: Search query
            k: Number of results to return
            filter: Optional metadata filter
        
        Returns:
            List of tuples (Document, score)
        """
        return self.vectorstore.similarity_search_with_score(
            query=query,
            k=k,
            filter=filter
        )
    
    def delete_collection(self):
        """Delete the collection."""
        try:
            self.client.delete_collection(name=self.collection_name)
            self._vectorstore = None
        except Exception as e:
            print(f"Error deleting collection: {e}")
    
    def get_collection_info(self) -> dict:
        """Get information about the collection."""
        logger.info("=" * 70)
        logger.info("DEBUG: VectorStore.get_collection_info() called")
        logger.info(f"DEBUG: collection_name = {self.collection_name}")
        logger.info(f"DEBUG: client = {self.client}")
        
        try:
            logger.info("DEBUG: Getting collection from client...")
            collection = None
            try:
                collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"DEBUG: ✅ Collection retrieved: {collection}")
                logger.info(f"DEBUG: Collection type: {type(collection)}")
            except KeyError as ke:
                # Handle '_type' error - use list_collections() as fallback
                if "'_type'" in str(ke) or "_type" in str(ke):
                    logger.warning(f"DEBUG: ⚠️ get_collection() failed with '_type' error, trying list_collections()...")
                    try:
                        collections = self.client.list_collections()
                        for col in collections:
                            if col.name == self.collection_name:
                                collection = col
                                logger.info(f"DEBUG: ✅ Found collection via list_collections(): {collection}")
                                break
                        if collection is None:
                            logger.error("DEBUG: ❌ Collection not found in list_collections()")
                            raise ke
                    except Exception as list_error:
                        logger.error(f"DEBUG: ❌ list_collections() also failed: {list_error}")
                        raise ke
                else:
                    raise
            
            # For very large collections, use count() directly with timeout
            # This is much faster than retrieving all documents
            count = 0
            try:
                logger.info("DEBUG: Attempting collection.count() (fast method)...")
                # Use count() directly - it's optimized in ChromaDB
                count = collection.count()
                logger.info(f"DEBUG: ✅ count() succeeded: {count}")
            except Exception as count_error:
                logger.warning(f"DEBUG: count() failed: {count_error}, trying sample method...")
                # Fallback: use small sample for quick estimate
                try:
                    sample = collection.get(limit=1000)  # Small sample only
                    if sample and "ids" in sample:
                        sample_count = len(sample["ids"])
                        if sample_count == 1000:
                            # Collection has at least 1000, but we don't know exact count
                            # Use a cached value or estimate
                            count = 1000  # At least 1000
                            logger.info(f"DEBUG: Sample shows at least {count} documents")
                        else:
                            count = sample_count
                            logger.info(f"DEBUG: Using sample count: {count}")
                    else:
                        count = 0
                        logger.warning("DEBUG: Sample is None or has no 'ids' key")
                except Exception as sample_error:
                    logger.error(f"DEBUG: ❌ Sample method also failed: {sample_error}")
                    count = 0
            
            result = {
                "name": self.collection_name,
                "document_count": count,
                "status": "active" if count > 0 else "empty"
            }
            logger.info(f"DEBUG: ✅ Returning collection info: {result}")
            logger.info("=" * 70)
            return result
        except Exception as e:
            logger.error("=" * 70)
            logger.error(f"DEBUG: ❌❌❌ ERROR in get_collection_info: {str(e)}")
            logger.error(f"DEBUG: Error type: {type(e)}")
            import traceback
            logger.error(f"DEBUG: Full traceback:\n{traceback.format_exc()}")
            logger.error("=" * 70)
            return {
                "name": self.collection_name,
                "document_count": 0,
                "status": "empty"
            }
    
    def url_exists(self, url: str) -> bool:
        """
        Check if a URL already exists in the collection.
        
        Args:
            url: URL to check
        
        Returns:
            True if URL exists, False otherwise
        """
        try:
            collection = self.client.get_collection(name=self.collection_name)
            # Search for documents with this URL in metadata
            # Try both "source" and "url" fields
            results_source = collection.get(
                where={"source": url},
                limit=1
            )
            if len(results_source.get("ids", [])) > 0:
                return True
            
            results_url = collection.get(
                where={"url": url},
                limit=1
            )
            return len(results_url.get("ids", [])) > 0
        except Exception:
            # If collection doesn't exist or error, URL doesn't exist
            return False
    
    def get_existing_urls(self) -> set:
            """
            Get all existing URLs from the collection.
            
            Returns:
                Set of existing URLs
            """
            existing_urls = set()
            try:
                collection = self.client.get_collection(name=self.collection_name)
                count = collection.count()
                
                if count == 0:
                    return existing_urls
                
                # Get all documents (with reasonable limit to avoid memory issues)
                # For large collections, we'll sample or use pagination
                limit = min(count, 50000)  # Limit to 50k documents
                all_docs = collection.get(limit=limit)
                
                # Extract unique URLs from metadata
                if all_docs and "metadatas" in all_docs:
                    for metadata in all_docs["metadatas"]:
                        if metadata:
                            url = metadata.get("url") or metadata.get("source")
                            if url:
                                existing_urls.add(url)
                
                logger = logging.getLogger(__name__)
                logger.debug(f"Found {len(existing_urls)} unique URLs in collection")
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.debug(f"Error getting existing URLs: {str(e)}")
            
            return existing_urls


# Global instance - lazy initialization to avoid blocking on import
_vector_store_instance = None

def get_vector_store():
    """Get or create the global vector store instance (lazy initialization)."""
    global _vector_store_instance
    if _vector_store_instance is None:
        logger.info("DEBUG: Creating global vector_store instance...")
        _vector_store_instance = VectorStore()
        logger.info("DEBUG: ✅ Global vector_store instance created")
    return _vector_store_instance

# For backward compatibility, create instance on import but log it
logger.info("DEBUG: Importing vector_store module...")
try:
    vector_store = VectorStore()
    logger.info("DEBUG: ✅ vector_store instance created on import")
except Exception as e:
    logger.error(f"DEBUG: ❌ Error creating vector_store on import: {e}")
    import traceback
    logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
    raise


"""Vector store management using ChromaDB."""
import chromadb
from chromadb.config import Settings as ChromaSettings
try:
    from langchain_chroma import Chroma
except ImportError:
    # Fallback to deprecated import if langchain-chroma is not available
    from langchain_community.vectorstores import Chroma
try:
    from langchain.schema import Document
except ImportError:
    from langchain_core.documents import Document
from typing import List, Optional
from config import settings
from utils.embeddings_factory import get_embeddings


class VectorStore:
    """Manages vector storage for RAG."""
    
    def __init__(self):
        """Initialize the vector store."""
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.embeddings = get_embeddings()
        self.collection_name = settings.chroma_collection_name
        self._vectorstore = None
    
    @property
    def vectorstore(self) -> Chroma:
        """Get or create the vectorstore."""
        if self._vectorstore is None:
            try:
                self._vectorstore = Chroma(
                    client=self.client,
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings
                )
            except Exception:
                # Collection doesn't exist, create it
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
        
        # Check if collection is empty first (prevents '_type' error)
        try:
            collection_info = self.get_collection_info()
            if collection_info.get("document_count", 0) == 0:
                logger.info("Collection is empty, returning empty list")
                return []
        except Exception as check_error:
            logger.warning(f"Could not check collection info: {str(check_error)}")
            # Continue anyway, let similarity_search handle it
        
        try:
            results = self.vectorstore.similarity_search(
                query=query,
                k=k,
                filter=filter
            )
            
            # Ensure all results are Document objects
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
        try:
            collection = self.client.get_collection(name=self.collection_name)
            count = collection.count()
            return {
                "name": self.collection_name,
                "document_count": count,
                "status": "active"
            }
        except Exception:
            return {
                "name": self.collection_name,
                "document_count": 0,
                "status": "empty"
            }


# Global instance
vector_store = VectorStore()


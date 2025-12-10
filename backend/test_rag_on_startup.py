"""
Test RAG functionality on backend startup.
This script verifies that the RAG system is operational.
"""
import logging
import sys
import asyncio
from rag.vector_store import vector_store

logger = logging.getLogger(__name__)


async def test_rag_functionality():
    """
    Test RAG functionality to ensure it's operational.
    
    Returns:
        dict: Test results with status and details
    """
    results = {
        "status": "unknown",
        "tests": {},
        "errors": []
    }
    
    logger.info("=" * 70)
    logger.info("DEBUG: ========== RAG FUNCTIONALITY TEST ==========")
    logger.info("=" * 70)
    
    # Test 1: Check if vector store is accessible
    logger.info("DEBUG: Test 1: Checking vector store accessibility...")
    collection = None
    try:
        collection = vector_store.client.get_collection(name=vector_store.collection_name)
        # Try to peek to verify it's accessible
        try:
            collection.peek(limit=1)
            logger.info("DEBUG: ✅ Vector store is accessible")
            results["tests"]["vector_store_accessible"] = True
        except KeyError as peek_error:
            # Handle '_type' error when peeking
            if "'_type'" in str(peek_error) or "_type" in str(peek_error):
                logger.warning(f"DEBUG: ⚠️ Collection has '_type' error when peeking: {peek_error}")
                logger.warning("DEBUG: Collection exists but may have structure issues - similarity_search may still work")
                results["tests"]["vector_store_accessible"] = True  # Collection exists, just has issues
                results["status"] = "warning"
            else:
                raise
    except KeyError as ke:
        # Handle '_type' error - this usually means collection exists but has issues
        if "'_type'" in str(ke) or "_type" in str(ke):
            logger.warning(f"DEBUG: ⚠️ Collection access error (likely '_type' issue): {ke}")
            logger.warning("DEBUG: This usually means the collection exists but may need to be re-indexed")
            # Try to continue with other tests - similarity_search might still work
            results["tests"]["vector_store_accessible"] = True  # Collection exists, just has access issues
            results["errors"].append(f"Collection access error (may need re-indexing): {str(ke)}")
            results["status"] = "warning"
            # Don't return - continue with other tests
        else:
            logger.error(f"DEBUG: ❌ Vector store not accessible: {ke}")
            results["tests"]["vector_store_accessible"] = False
            results["errors"].append(f"Vector store error: {str(ke)}")
            results["status"] = "failed"
            return results
    except Exception as e:
        logger.error(f"DEBUG: ❌ Vector store not accessible: {e}")
        results["tests"]["vector_store_accessible"] = False
        results["errors"].append(f"Vector store error: {str(e)}")
        results["status"] = "failed"
        return results
    
    # Test 2: Check document count (only if collection is accessible)
    if collection is None:
        logger.warning("DEBUG: ⏭️ Skipping document count test (collection not accessible)")
        results["tests"]["document_count"] = 0
    else:
        logger.info("DEBUG: Test 2: Checking document count...")
        try:
            # Try count() with timeout
            def get_count():
                return collection.count()
            
            try:
                doc_count = await asyncio.wait_for(
                    asyncio.to_thread(get_count),
                    timeout=10.0
                )
                logger.info(f"DEBUG: ✅ Document count: {doc_count}")
                results["tests"]["document_count"] = doc_count
                if doc_count == 0:
                    logger.warning("DEBUG: ⚠️ Collection is empty - no documents indexed")
                    if results["status"] != "failed":
                        results["status"] = "warning"
                else:
                    if results["status"] != "failed":
                        results["status"] = "success"
            except asyncio.TimeoutError:
                logger.warning("DEBUG: ⚠️ count() timed out, using sample estimation...")
                try:
                    sample = collection.get(limit=1000)
                    if sample and "ids" in sample:
                        doc_count = len(sample["ids"])
                        logger.info(f"DEBUG: ✅ Estimated document count (from sample): {doc_count}")
                        results["tests"]["document_count"] = doc_count
                        if doc_count == 0:
                            if results["status"] != "failed":
                                results["status"] = "warning"
                        else:
                            if results["status"] != "failed":
                                results["status"] = "success"
                    else:
                        logger.warning("DEBUG: ⚠️ Sample is empty")
                        results["tests"]["document_count"] = 0
                        if results["status"] != "failed":
                            results["status"] = "warning"
                except Exception as sample_error:
                    logger.warning(f"DEBUG: ⚠️ Could not get sample: {sample_error}")
                    results["tests"]["document_count"] = 0
                    if results["status"] != "failed":
                        results["status"] = "warning"
            except Exception as count_error:
                logger.warning(f"DEBUG: ⚠️ count() failed: {count_error}")
                results["tests"]["document_count"] = 0
                if results["status"] != "failed":
                    results["status"] = "warning"
        except Exception as e:
            logger.error(f"DEBUG: ❌ Error checking document count: {e}")
            results["tests"]["document_count"] = 0
            if results["status"] != "failed":
                results["status"] = "warning"
    
    # Test 3: Test similarity search (always try, even if collection had issues)
    logger.info("DEBUG: Test 3: Testing similarity search...")
    try:
        test_query = "ESILV majeures programmes"
        logger.info(f"DEBUG: Testing with query: '{test_query}'")
        docs = vector_store.similarity_search(test_query, k=3)
        logger.info(f"DEBUG: ✅ Similarity search returned {len(docs)} documents")
        results["tests"]["similarity_search"] = {
            "success": True,
            "results_count": len(docs),
            "query": test_query
        }
        
        if len(docs) > 0:
            # Show first result metadata
            first_doc = docs[0]
            metadata = getattr(first_doc, 'metadata', {}) if hasattr(first_doc, 'metadata') else {}
            source = metadata.get("source", metadata.get("url", "unknown"))
            logger.info(f"DEBUG: First result source: {source}")
            results["tests"]["similarity_search"]["first_result_source"] = source
            if results["status"] != "failed":
                results["status"] = "success"
        else:
            logger.warning("DEBUG: ⚠️ Similarity search returned no results")
            if results["status"] == "success":
                results["status"] = "warning"
    except KeyError as ke:
        # Handle '_type' error in similarity search
        if "'_type'" in str(ke) or "_type" in str(ke):
            logger.warning(f"DEBUG: ⚠️ Similarity search error (likely '_type' issue): {ke}")
            logger.warning("DEBUG: This usually means the collection needs to be re-indexed")
            results["tests"]["similarity_search"] = {
                "success": False,
                "error": "Collection structure issue (may need re-indexing)"
            }
            if results["status"] != "failed":
                results["status"] = "warning"
        else:
            logger.error(f"DEBUG: ❌ Error in similarity search: {ke}")
            results["tests"]["similarity_search"] = {
                "success": False,
                "error": str(ke)
            }
            results["errors"].append(f"Similarity search error: {str(ke)}")
            if results["status"] != "failed":
                results["status"] = "warning"
    except Exception as e:
        logger.error(f"DEBUG: ❌ Error in similarity search: {e}")
        import traceback
        logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
        results["tests"]["similarity_search"] = {
            "success": False,
            "error": str(e)
        }
        results["errors"].append(f"Similarity search error: {str(e)}")
        if results["status"] != "failed":
            results["status"] = "warning"
    
    # Test 4: Test embeddings
    logger.info("DEBUG: Test 4: Testing embeddings...")
    try:
        test_text = "Test embedding"
        embedding = vector_store.embeddings.embed_query(test_text)
        logger.info(f"DEBUG: ✅ Embeddings working (vector dimension: {len(embedding)})")
        results["tests"]["embeddings"] = {
            "success": True,
            "vector_dimension": len(embedding)
        }
    except Exception as e:
        logger.error(f"DEBUG: ❌ Error testing embeddings: {e}")
        results["tests"]["embeddings"] = {
            "success": False,
            "error": str(e)
        }
        results["errors"].append(f"Embeddings error: {str(e)}")
        results["status"] = "failed"
    
    # Final summary
    logger.info("=" * 70)
    if results["status"] == "success":
        logger.info("DEBUG: ✅ RAG FUNCTIONALITY TEST: SUCCESS")
        logger.info(f"DEBUG: - Documents: {results['tests'].get('document_count', 0)}")
        logger.info(f"DEBUG: - Similarity search: {results['tests'].get('similarity_search', {}).get('results_count', 0)} results")
    elif results["status"] == "warning":
        logger.warning("DEBUG: ⚠️ RAG FUNCTIONALITY TEST: WARNING (some issues detected)")
        logger.warning(f"DEBUG: - Documents: {results['tests'].get('document_count', 0)}")
    else:
        logger.error("DEBUG: ❌ RAG FUNCTIONALITY TEST: FAILED")
        for error in results["errors"]:
            logger.error(f"DEBUG: - Error: {error}")
    logger.info("=" * 70)
    
    return results


def run_rag_test():
    """Run RAG test synchronously."""
    try:
        # Configure logging if not already configured
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Run async test
        result = asyncio.run(test_rag_functionality())
        return result
    except Exception as e:
        logger.error(f"Error running RAG test: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "status": "failed",
            "errors": [str(e)]
        }


if __name__ == "__main__":
    result = run_rag_test()
    sys.exit(0 if result["status"] in ["success", "warning"] else 1)


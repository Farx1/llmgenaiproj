"""
Test script to verify that the collection fix works correctly.
This script tests the collection after running fix_chromadb_collection.py
"""
import logging
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from rag.vector_store import vector_store
from config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_collection():
    """Test that the collection is accessible and working."""
    logger.info("=" * 70)
    logger.info("TESTING COLLECTION AFTER FIX")
    logger.info("=" * 70)
    
    results = {
        "get_collection": False,
        "peek": False,
        "count": False,
        "similarity_search": False,
        "add_documents": False
    }
    
    try:
        # Test 1: get_collection
        logger.info("\n1. Testing get_collection()...")
        try:
            collection = vector_store.client.get_collection(name=vector_store.collection_name)
            logger.info("   ✅ get_collection() works")
            results["get_collection"] = True
        except Exception as e:
            logger.error(f"   ❌ get_collection() failed: {e}")
            if "'_type'" in str(e) or "_type" in str(e):
                logger.warning("   ⚠️ '_type' error still present - collection may need full reset")
        
        # Test 2: peek
        logger.info("\n2. Testing peek()...")
        try:
            if results["get_collection"]:
                sample = collection.peek(limit=1)
                logger.info(f"   ✅ peek() works - sample keys: {list(sample.keys()) if isinstance(sample, dict) else 'N/A'}")
                results["peek"] = True
            else:
                # Try via vectorstore
                vs = vector_store.vectorstore
                if hasattr(vs, '_collection'):
                    sample = vs._collection.peek(limit=1)
                    logger.info("   ✅ peek() works via vectorstore")
                    results["peek"] = True
        except Exception as e:
            logger.error(f"   ❌ peek() failed: {e}")
        
        # Test 3: count
        logger.info("\n3. Testing count()...")
        try:
            if results["get_collection"]:
                count = collection.count()
                logger.info(f"   ✅ count() works - {count} documents")
                results["count"] = True
            else:
                logger.warning("   ⏭️ Skipping count() (get_collection failed)")
        except Exception as e:
            logger.warning(f"   ⚠️ count() failed: {e} (may be OK if collection is empty)")
            # Count can fail if collection is empty, which is OK
        
        # Test 4: similarity_search
        logger.info("\n4. Testing similarity_search()...")
        try:
            results_search = vector_store.similarity_search("test", k=1)
            logger.info(f"   ✅ similarity_search() works - {len(results_search)} results")
            results["similarity_search"] = True
        except Exception as e:
            logger.error(f"   ❌ similarity_search() failed: {e}")
        
        # Test 5: add_documents (if collection is empty)
        logger.info("\n5. Testing add_documents()...")
        try:
            from langchain_core.documents import Document
            test_doc = Document(
                page_content="Test document for collection fix verification",
                metadata={"source": "test", "url": "test://test"}
            )
            doc_ids = vector_store.add_documents([test_doc])
            logger.info(f"   ✅ add_documents() works - added {len(doc_ids)} document(s)")
            results["add_documents"] = True
            
            # Clean up test document
            try:
                if results["get_collection"]:
                    collection.delete(ids=doc_ids)
                    logger.info("   ✅ Test document cleaned up")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"   ❌ add_documents() failed: {e}")
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("TEST SUMMARY")
        logger.info("=" * 70)
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"  {test_name}: {status}")
        
        all_critical = results["similarity_search"] and results["add_documents"]
        if all_critical:
            logger.info("\n✅ Collection is fully functional!")
        elif results["similarity_search"]:
            logger.info("\n⚠️ Collection is partially functional (search works, but some operations may fail)")
        else:
            logger.info("\n❌ Collection has issues - may need to run fix script again")
        
        return all_critical
        
    except Exception as e:
        logger.error(f"Error during testing: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = test_collection()
    sys.exit(0 if success else 1)


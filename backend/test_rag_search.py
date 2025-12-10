"""Test RAG similarity search directly."""
import sys
import asyncio
from rag.vector_store import vector_store

async def test():
    try:
        print("Testing similarity_search...")
        query = "majeures ESILV"
        docs = vector_store.similarity_search(query, k=4)
        print(f"✅ similarity_search returned {len(docs)} documents")
        
        if docs:
            print(f"\nFirst document preview:")
            print(f"Content (first 200 chars): {docs[0].page_content[:200]}")
            print(f"Source: {docs[0].metadata.get('source', 'unknown')}")
        else:
            print("❌ No documents found")
        
        return len(docs)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    result = asyncio.run(test())
    print(f"\n{'✅ SUCCESS' if result > 0 else '❌ FAILED'}: Found {result} documents")


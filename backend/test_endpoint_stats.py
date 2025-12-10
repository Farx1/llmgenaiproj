"""Test the RAG stats endpoint directly."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from api.documents import get_rag_stats

async def test():
    try:
        print("Testing get_rag_stats endpoint...")
        result = await get_rag_stats()
        print(f"\n✅ Result:")
        print(f"Document count: {result.get('collection_info', {}).get('document_count', 0)}")
        print(f"Status: {result.get('collection_info', {}).get('status', 'unknown')}")
        print(f"Total sources: {result.get('total_sources', 0)}")
        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test())
    if result and result.get('collection_info', {}).get('document_count', 0) > 0:
        print("\n✅ SUCCESS: Endpoint returns documents")
    else:
        print("\n❌ FAILED: Endpoint returns 0 documents")


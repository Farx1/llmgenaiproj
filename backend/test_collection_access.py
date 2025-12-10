"""Test collection access directly."""
import sys
import asyncio
from rag.vector_store import vector_store

async def test():
    try:
        print("Testing collection access...")
        collection = vector_store.client.get_collection(name=vector_store.collection_name)
        print(f"✅ Collection retrieved: {collection.name}")
        
        print("Testing count()...")
        count = await asyncio.to_thread(collection.count)
        print(f"✅ Count: {count}")
        
        return count
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test())
    if result:
        print(f"\n✅ SUCCESS: Collection has {result} documents")
    else:
        print("\n❌ FAILED: Could not access collection")


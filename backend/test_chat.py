"""Test script to debug chat endpoint errors."""
import asyncio
from agents.orchestrator import OrchestratorAgent

async def test_chat():
    """Test the orchestrator with a simple query."""
    try:
        print("Creating orchestrator...")
        orchestrator = OrchestratorAgent('ministral-3')
        print("Orchestrator created successfully")
        
        print("\nTesting query: 'Bonjour'")
        response = await orchestrator.process_query(
            query="Bonjour",
            conversation_history=[]
        )
        
        print(f"\nResponse received:")
        print(f"Answer: {response.get('answer', 'N/A')[:200]}")
        print(f"Metadata: {response.get('metadata', {})}")
        
    except Exception as e:
        import traceback
        print(f"\nERROR: {str(e)}")
        print("\nTraceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chat())


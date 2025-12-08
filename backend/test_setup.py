"""Test script to verify backend setup."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    try:
        from config import settings
        print("✓ Config imported")
        
        from utils.llm_factory import get_llm
        print("✓ LLM factory imported")
        
        from utils.embeddings_factory import get_embeddings
        print("✓ Embeddings factory imported")
        
        from rag.vector_store import vector_store
        print("✓ Vector store imported")
        
        from agents.orchestrator import OrchestratorAgent
        print("✓ Orchestrator agent imported")
        
        from agents.retrieval_agent import RetrievalAgent
        print("✓ Retrieval agent imported")
        
        from agents.web_scraper_agent import WebScraperAgent
        print("✓ Web scraper agent imported")
        
        from agents.form_agent import FormAgent
        print("✓ Form agent imported")
        
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_ollama_connection():
    """Test Ollama connection."""
    print("\nTesting Ollama connection...")
    try:
        import httpx
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5.0)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            print(f"✓ Ollama connected. Available models: {', '.join(model_names)}")
            
            # Check if default model is available
            if any(settings.ollama_default_model in name for name in model_names):
                print(f"✓ Default model '{settings.ollama_default_model}' is available")
            else:
                print(f"⚠ Default model '{settings.ollama_default_model}' not found. Available: {', '.join(model_names)}")
            return True
        else:
            print(f"✗ Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to Ollama: {e}")
        print(f"  Make sure Ollama is running at {settings.ollama_base_url}")
        return False

def test_vector_store():
    """Test vector store initialization."""
    print("\nTesting vector store...")
    try:
        info = vector_store.get_collection_info()
        print(f"✓ Vector store initialized. Collection: {info['name']}, Documents: {info['document_count']}")
        return True
    except Exception as e:
        print(f"✗ Vector store error: {e}")
        return False

def test_llm_creation():
    """Test LLM creation."""
    print("\nTesting LLM creation...")
    try:
        llm = get_llm()
        print(f"✓ LLM created successfully")
        return True
    except Exception as e:
        print(f"✗ LLM creation error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 50)
    print("ESILV Smart Assistant - Setup Test")
    print("=" * 50)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Ollama Connection", test_ollama_connection()))
    results.append(("Vector Store", test_vector_store()))
    results.append(("LLM Creation", test_llm_creation()))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ All tests passed! Your setup is ready.")
    else:
        print("\n⚠ Some tests failed. Please check the errors above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())


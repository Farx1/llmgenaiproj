# ESILV Smart Assistant - Architecture Overview

## System Architecture

The ESILV Smart Assistant is built with a **multi-agent architecture** that coordinates specialized agents to handle different types of queries.

```
┌─────────────────┐
│  Next.js Frontend │
│  (Port 3000)     │
└────────┬─────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│  FastAPI Backend │
│  (Port 8000)     │
└────────┬─────────┘
         │
         ├──► Orchestrator Agent
         │         │
         │         ├──► Retrieval Agent ──► ChromaDB (Vector Store)
         │         │
         │         ├──► Web Scraper Agent ──► ESILV Website
         │         │
         │         └──► Form Agent ──► contacts.json
         │
         └──► Ollama/GCP ──► LLM Models
```

## Components

### Frontend (Next.js)

- **Chat Interface** (`components/ChatInterface.tsx`): Main chat UI with message history
- **Document Upload** (`components/DocumentUpload.tsx`): Upload documents to enhance knowledge base
- **Model Selector** (`components/ModelSelector.tsx`): Switch between different LLM models
- **Admin Dashboard** (`app/admin/page.tsx`): View statistics and collected contacts

### Backend (FastAPI)

#### API Endpoints

- **`/api/chat/`**: Main chat endpoint for user queries
- **`/api/documents/upload`**: Upload and process documents
- **`/api/documents/search`**: Search the vector database
- **`/api/admin/stats`**: Get system statistics
- **`/api/admin/contacts`**: Get collected contacts

#### Agents

1. **Orchestrator Agent** (`agents/orchestrator.py`)
   - Coordinates all specialized agents
   - Routes queries to appropriate agents
   - Combines results from multiple agents

2. **Retrieval Agent** (`agents/retrieval_agent.py`)
   - Handles RAG queries
   - Searches vectorized documentation
   - Answers questions about programs, admissions, courses

3. **Web Scraper Agent** (`agents/web_scraper_agent.py`)
   - Scrapes ESILV website for latest news
   - Fetches real-time updates
   - Provides current information

4. **Form Agent** (`agents/form_agent.py`)
   - Collects contact information
   - Manages registration requests
   - Stores contacts in JSON file

#### RAG System

- **Vector Store** (`rag/vector_store.py`): ChromaDB integration for document storage
- **Document Processor** (`rag/document_processor.py`): Chunks and processes documents
- **Embeddings** (`utils/embeddings_factory.py`): Generates embeddings using Ollama

#### LLM Integration

- **LLM Factory** (`utils/llm_factory.py`): Creates LLM instances (Ollama or GCP)
- **Model Selection**: Supports llama3, mistral:7b, and GCP models

## Data Flow

### Chat Query Flow

1. User sends message via frontend
2. Frontend calls `/api/chat/` with message and history
3. Backend creates/uses Orchestrator Agent
4. Orchestrator analyzes query and routes to appropriate agent(s):
   - Documentation questions → Retrieval Agent → ChromaDB
   - News queries → Web Scraper Agent → ESILV Website
   - Contact collection → Form Agent → contacts.json
5. Agent processes query using LLM and tools
6. Response returned to frontend
7. Frontend displays response in chat interface

### Document Upload Flow

1. User uploads document via frontend
2. Frontend sends file to `/api/documents/upload`
3. Backend saves file temporarily
4. Document Processor chunks the document
5. Chunks are embedded using Ollama embeddings
6. Embedded chunks stored in ChromaDB
7. Document available for RAG queries

## Agent Coordination

The Orchestrator Agent uses LangChain's `create_agent` with tools from specialized agents:

```python
tools = [
    retrieval_agent.get_tool(),      # search_documentation
    web_scraper_agent.get_tool(),    # scrape_esilv_news
    form_agent.get_tool(),           # collect_contact_info
]
```

The orchestrator's system prompt guides it to:
- Analyze query intent
- Select appropriate agent(s)
- Combine results when needed
- Provide coherent responses

## Vector Database

ChromaDB stores document embeddings:
- **Collection**: `esilv_docs` (configurable)
- **Embeddings**: Generated using Ollama (llama3 by default)
- **Search**: Similarity search with configurable `k` results
- **Persistence**: Stored in `backend/chroma_db/`

## Model Support

### Ollama (Local)
- **llama3**: Default model for chat and embeddings
- **mistral:7b**: Alternative model option
- **Base URL**: `http://localhost:11434` (configurable)

### Google Cloud Platform (Optional)
- **Gemini Pro**: Available when GCP credentials configured
- **Setup**: Set `USE_GCP=true` and provide credentials

## Configuration

All configuration in `backend/config.py`:
- Ollama settings
- ChromaDB settings
- API settings
- GCP settings (optional)
- ESILV website URL

Environment variables in `backend/.env` override defaults.

## File Structure

```
.
├── backend/
│   ├── agents/          # Agent implementations
│   ├── api/             # FastAPI routes
│   ├── rag/             # RAG system
│   ├── utils/           # Utilities
│   ├── config.py        # Configuration
│   ├── main.py          # FastAPI app
│   └── requirements.txt # Python dependencies
├── frontend/
│   ├── app/             # Next.js app router
│   ├── components/      # React components
│   └── package.json     # Node dependencies
├── README.md            # Project overview
├── SETUP.md             # Setup instructions
└── ARCHITECTURE.md      # This file
```

## Extending the System

### Adding a New Agent

1. Create agent class in `backend/agents/`
2. Implement `get_tool()` method
3. Add tool to Orchestrator's tool list
4. Update orchestrator system prompt

### Adding New Document Types

1. Extend `DocumentProcessor` to handle new formats
2. Add file type handling in upload endpoint
3. Update frontend file accept types

### Customizing Prompts

Edit system prompts in agent classes:
- `OrchestratorAgent._get_system_prompt()`
- `RetrievalAgent._get_system_prompt()`
- `WebScraperAgent._get_system_prompt()`
- `FormAgent._get_system_prompt()`

## Performance Considerations

- **Vector Search**: ChromaDB is fast for similarity search
- **LLM Calls**: Ollama local models are fast but depend on hardware
- **Web Scraping**: Cached results recommended for production
- **Document Processing**: Large documents are chunked automatically

## Security Notes

- CORS configured for frontend origin
- File uploads validated by file type
- Contact information stored locally (consider database for production)
- GCP credentials should be secured

## Production Deployment

1. Use production-grade database for contacts
2. Implement authentication for admin dashboard
3. Add rate limiting for API endpoints
4. Set up monitoring and logging
5. Use environment variables for all secrets
6. Consider using a reverse proxy (nginx)
7. Implement proper error handling and logging


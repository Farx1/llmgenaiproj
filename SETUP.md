# ESILV Smart Assistant - Setup Guide

## Prerequisites

- Python 3.8+ installed
- Node.js 18+ and npm installed
- Ollama installed and running locally
- Ollama models downloaded: `llama3`, `mistral:7b`, `mistral:3`, and `mistral-large:3`

## Step 1: Install Ollama Models

If you haven't already, download the required models:

```bash
ollama pull llama3
ollama pull mistral:7b
ollama pull mistral:3
ollama pull mistral-large:3
```

**Note**: You don't need to download all models. Download only the ones you want to use. The system supports:
- `llama3` - Fast and efficient
- `mistral:7b` - Good balance of speed and quality
- `mistral:3` - Latest Mistral 3 model
- `mistral-large:3` - High-quality, larger model (requires more resources)

Verify models are available:
```bash
ollama list
```

## Step 2: Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

**Note**: If you encounter dependency conflicts with `langchain-ollama`, you can install it separately:
```bash
# First install main dependencies
pip install -r requirements.txt

# Then try installing langchain-ollama (may require compatible version)
pip install langchain-ollama

# If that fails, the code will automatically fall back to using the ollama package directly
```

4. Create environment file:
```bash
cp .env.example .env
```

5. Edit `.env` if needed (defaults should work for local development):
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=esilv_docs
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
ESILV_BASE_URL=https://www.esilv.fr
```

6. Start the backend server:
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## Step 3: Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. (Optional) Create `.env.local` to customize API URL:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Step 4: Verify Installation

1. Check backend health:
```bash
curl http://localhost:8000/health
```

2. Check available models:
```bash
curl http://localhost:8000/api/chat/models
```

3. Open `http://localhost:3000` in your browser and test the chat interface.

## Step 5: Upload Initial Documents (Optional)

1. Prepare your ESILV documentation files (TXT, PDF, MD, DOC, DOCX)
2. Use the document upload feature in the frontend
3. Or use the API directly:
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@path/to/your/document.pdf"
```

## GCP Setup (Optional)

To use Google Cloud Platform instead of Ollama:

1. Set up GCP credentials:
   - Create a service account in GCP
   - Download the JSON key file
   - Set the path in `.env`:
     ```env
     GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/key.json
     GCP_PROJECT_ID=your-project-id
     GCP_MODEL_NAME=gemini-pro
     USE_GCP=true
     ```

2. Install additional dependencies:
```bash
pip install langchain-google-genai
```

3. Restart the backend server.

## Troubleshooting

### Ollama Connection Issues
- Ensure Ollama is running: `ollama serve`
- Check if models are available: `ollama list`
- Verify the base URL in `.env` matches your Ollama instance

### ChromaDB Issues
- Delete the `chroma_db` directory and restart if you encounter persistent errors
- Ensure write permissions in the backend directory

### CORS Errors
- Verify `CORS_ORIGINS` in backend `.env` includes your frontend URL
- Check that both servers are running

### Model Not Found
- Ensure the model name matches exactly (case-sensitive)
- Check available models: `ollama list`
- Pull the model if missing: `ollama pull <model-name>`

## Development Tips

1. **Backend Logs**: Check the terminal running the backend for detailed error messages
2. **Frontend Logs**: Check the browser console (F12) for client-side errors
3. **API Testing**: Use the interactive API docs at `http://localhost:8000/docs`
4. **Vector Store**: Documents are stored in `backend/chroma_db/`
5. **Contacts**: Collected contacts are stored in `backend/contacts.json`

## Next Steps

1. Upload ESILV documentation to populate the knowledge base
2. Test different queries to see how agents coordinate
3. Customize agent prompts in `backend/agents/` for your specific needs
4. Deploy to production (see deployment guide)


# Supported Models

The ESILV Smart Assistant supports multiple Ollama models. You can switch between them using the model selector in the frontend.

## Available Models

The following models are configured by default:

1. **llama3** - Meta's Llama 3 model (default)
   - Fast and efficient
   - Good for general queries
   - Lower resource requirements

2. **mistral:7b** - Mistral 7B model
   - Good balance of speed and quality
   - Efficient for most tasks

3. **mistral:3** - Mistral 3 model
   - Latest Mistral model
   - Improved performance over previous versions

4. **mistral-large:3** - Mistral Large 3 model
   - Highest quality responses
   - Requires more computational resources
   - Best for complex queries

## Installing Models

Before using a model, make sure it's installed in Ollama:

```bash
# List installed models
ollama list

# Pull a model (if not installed)
ollama pull llama3
ollama pull mistral:7b
ollama pull mistral:3
ollama pull mistral-large:3
```

## Verifying Model Names

Model names in Ollama are case-sensitive and must match exactly. To verify the exact name of an installed model:

```bash
ollama list
```

This will show output like:
```
NAME                    ID              SIZE    MODIFIED
llama3:latest           abc123...        4.7 GB  2 hours ago
mistral:7b              def456...        4.1 GB  1 day ago
mistral-large:3         ghi789...        8.2 GB  3 days ago
```

If your model name differs (e.g., `mistral-large3` instead of `mistral-large:3`), update the model name in:
- `backend/config.py` - `ollama_available_models` list
- Or set it via environment variable

## Changing Default Model

To change the default model, edit `backend/.env`:

```env
OLLAMA_DEFAULT_MODEL=mistral-large:3
```

Or modify `backend/config.py`:

```python
ollama_default_model: str = "mistral-large:3"
```

## Model Selection in Frontend

The frontend automatically fetches available models from the backend API. The model selector dropdown will show all models configured in `backend/config.py`.

When you select a different model, all subsequent chat messages will use that model until you change it again.

## Performance Considerations

- **Smaller models** (llama3, mistral:7b): Faster responses, lower memory usage
- **Larger models** (mistral-large:3): Slower but higher quality responses, more memory required

Choose the model based on your needs:
- For quick responses: Use `llama3` or `mistral:7b`
- For best quality: Use `mistral-large:3`
- For balance: Use `mistral:3`

## Troubleshooting

### Model Not Found Error

If you get a "model not found" error:

1. Verify the model is installed:
   ```bash
   ollama list
   ```

2. Check the exact model name matches (case-sensitive)

3. Pull the model if missing:
   ```bash
   ollama pull <model-name>
   ```

4. Restart the backend server after pulling a new model

### Model Name Mismatch

If the model name in Ollama differs from what's configured:

1. Check actual model name: `ollama list`
2. Update `backend/config.py` with the correct name
3. Restart the backend server


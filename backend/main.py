"""FastAPI application entry point."""
# Configure logging FIRST, before any other imports that might use logging
import logging
import sys

# Configure logging with DEBUG level to see all logs
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG to see all logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs go to stdout
    ],
    force=True  # Force reconfiguration if already configured
)

logger = logging.getLogger(__name__)
logger.info("=" * 70)
logger.info("DEBUG: ========== LOGGING CONFIGURED ==========")
logger.info("=" * 70)

# Now import other modules (they will use the configured logging)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
logger.info("DEBUG: Importing API modules...")
from api import chat, documents, admin
logger.info("DEBUG: ✅ API modules imported")
logger.info("=" * 70)
logger.info("DEBUG: ========== APPLICATION STARTUP ==========")
logger.info(f"DEBUG: Python version: {sys.version}")
logger.info(f"DEBUG: FastAPI starting...")
logger.info("=" * 70)

logger.info("DEBUG: Creating FastAPI app...")
app = FastAPI(
    title="ESILV Smart Assistant API",
    description="Intelligent chatbot API for ESILV engineering school",
    version="1.0.0"
)
logger.info("DEBUG: ✅ FastAPI app created")

# CORS middleware
logger.info("DEBUG: Adding CORS middleware...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info(f"DEBUG: ✅ CORS middleware added (origins: {settings.cors_origins})")

# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all incoming requests."""
    import time
    start_time = time.time()
    
    # Log request
    logger.info("=" * 70)
    logger.info(f"DEBUG: 📥 INCOMING REQUEST: {request.method} {request.url.path}")
    logger.info(f"DEBUG: Client: {request.client.host if request.client else 'unknown'}")
    logger.info(f"DEBUG: Headers: {dict(request.headers)}")
    
    # Process request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"DEBUG: ✅ REQUEST COMPLETED in {process_time:.2f}s - Status: {response.status_code}")
        logger.info("=" * 70)
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"DEBUG: ❌ REQUEST FAILED after {process_time:.2f}s - Error: {str(e)}")
        logger.error("=" * 70)
        raise

# Include routers
logger.info("DEBUG: Including routers...")
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
logger.info("DEBUG: ✅ Chat router included")
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
logger.info("DEBUG: ✅ Documents router included")
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
logger.info("DEBUG: ✅ Admin router included")
logger.info("=" * 70)
logger.info("DEBUG: ✅ APPLICATION STARTUP COMPLETE")
logger.info("=" * 70)


@app.get("/")
async def root():
    """Root endpoint."""
    logger.info("DEBUG: Root endpoint called")
    return {
        "message": "ESILV Smart Assistant API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    logger.info("DEBUG: Health check endpoint called")
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    """Log startup event and run RAG test."""
    logger.info("=" * 70)
    logger.info("DEBUG: ========== FASTAPI STARTUP EVENT ==========")
    logger.info(f"DEBUG: API Host: {settings.api_host}")
    logger.info(f"DEBUG: API Port: {settings.api_port}")
    logger.info(f"DEBUG: Ollama Base URL: {settings.ollama_base_url}")
    logger.info(f"DEBUG: Default Model: {settings.ollama_default_model}")
    logger.info(f"DEBUG: ChromaDB Path: {settings.chroma_persist_directory}")
    logger.info("=" * 70)
    
    # Run RAG functionality test
    logger.info("DEBUG: Running RAG functionality test...")
    try:
        from test_rag_on_startup import test_rag_functionality
        rag_test_result = await test_rag_functionality()
        
        if rag_test_result["status"] == "success":
            logger.info("DEBUG: ✅ RAG system is operational and ready to use")
        elif rag_test_result["status"] == "warning":
            logger.warning("DEBUG: ⚠️ RAG system has warnings but may still work")
        else:
            logger.error("DEBUG: ❌ RAG system test failed - check logs above")
    except Exception as e:
        logger.error(f"DEBUG: ❌ Error running RAG test: {e}")
        import traceback
        logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown event."""
    logger.info("=" * 70)
    logger.info("DEBUG: ========== FASTAPI SHUTDOWN EVENT ==========")
    logger.info("=" * 70)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )


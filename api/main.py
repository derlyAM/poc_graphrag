"""
FastAPI main application.
REST API for RAG document query and ingestion system.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from loguru import logger

from api.routers import health, rag, documents, ingestion, integration
from api.middleware import setup_middleware
from api.utils.error_handlers import (
    validation_exception_handler,
    general_exception_handler
)
from src.config import config

# Configure logging
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=config.logging.level,
)
logger.add(
    config.logging.file,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level=config.logging.level,
    rotation="10 MB",
)

# Create FastAPI app
app = FastAPI(
    title="RAG Document Query API",
    description="""
    REST API for the RAG (Retrieval-Augmented Generation) document query system.

    ## Features

    * **Query Documents**: Natural language queries with AI-powered answers
    * **Document Management**: List, view, and delete indexed documents
    * **Document Ingestion**: Upload and process new PDF documents
    * **Health Monitoring**: System health and status endpoints

    ## Areas

    Documents are organized by knowledge areas:
    * `sgr` - Sistema General de Regalías
    * `inteligencia_artificial` - Inteligencia Artificial
    * `general` - General documents

    ## Authentication

    *Note: Authentication is not yet implemented in MVP.*

    ## Rate Limiting

    *Note: Rate limiting is not yet implemented in MVP.*
    """,
    version="1.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "RAG System",
        "url": "https://github.com/your-repo/rag-system",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# Setup middleware
setup_middleware(app)

# Register exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include routers
app.include_router(health.router)
app.include_router(rag.router)
app.include_router(documents.router)
app.include_router(ingestion.router)
app.include_router(integration.router)

logger.info("FastAPI application configured")


@app.on_event("startup")
async def startup_event():
    """
    Startup event handler.

    Runs when the FastAPI application starts.
    """
    logger.info("=" * 60)
    logger.info("RAG API STARTING")
    logger.info("=" * 60)
    logger.info(f"Version: 1.3.0")
    logger.info(f"Environment: {config.logging.level}")
    logger.info(f"Qdrant: {config.qdrant.url}")
    logger.info(f"Collection: {config.qdrant.collection_name}")
    logger.info(f"LLM Model: {config.openai.llm_model}")
    logger.info("=" * 60)

    # Validate configuration
    try:
        config.validate()
        logger.success("Configuration validated successfully")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

    # Initialize shared pipeline (will create Qdrant connection)
    try:
        from src.shared_resources import get_shared_pipeline
        pipeline = get_shared_pipeline()
        logger.success("Shared RAGPipeline initialized")

        # Log collection stats
        stats = pipeline.get_stats()
        collection = stats.get("collection", {})
        logger.info(f"Collection vectors: {collection.get('vectors_count', 0)}")

    except Exception as e:
        logger.error(f"Failed to initialize RAGPipeline: {e}")
        raise

    logger.success("API startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Shutdown event handler.

    Runs when the FastAPI application shuts down.
    """
    logger.info("=" * 60)
    logger.info("RAG API SHUTTING DOWN")
    logger.info("=" * 60)

    # Cleanup resources if needed
    # Note: Qdrant client cleanup is handled automatically

    logger.info("Shutdown complete")


@app.get("/", include_in_schema=False)
async def root():
    """
    Root endpoint redirect to documentation.
    """
    return {
        "message": "RAG Document Query API",
        "version": "1.3.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "status": "/api/v1/status"
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting API server with uvicorn...")

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )

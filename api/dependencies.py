"""
FastAPI dependencies for dependency injection.
Provides shared resources like RAGPipeline to endpoints.
"""
from typing import Generator
from loguru import logger

from src.shared_resources import get_shared_pipeline
from src.pipeline import RAGPipeline


def get_pipeline() -> Generator[RAGPipeline, None, None]:
    """
    Dependency that provides the shared RAGPipeline instance.

    Uses the singleton pattern from SharedPipelineManager to ensure
    only one Qdrant connection is active.

    Yields:
        RAGPipeline: Shared pipeline instance
    """
    try:
        pipeline = get_shared_pipeline()
        logger.debug("Pipeline dependency injected")
        yield pipeline
    except Exception as e:
        logger.error(f"Error getting pipeline: {e}")
        raise

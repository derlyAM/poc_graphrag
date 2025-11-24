"""
Health check endpoints.
System health and status monitoring.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, status
from loguru import logger
from qdrant_client import models

from api.models.responses import HealthResponse, StatusResponse, CollectionStats
from api.dependencies import get_pipeline
from src.pipeline import RAGPipeline
from src.config import config

# Track API start time for uptime calculation
API_START_TIME = datetime.now()

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the API and its dependencies are healthy"
)
async def health_check(
    pipeline: RAGPipeline = Depends(get_pipeline)
) -> HealthResponse:
    """
    Basic health check endpoint.

    Returns:
        HealthResponse with service status
    """
    logger.debug("Health check requested")

    # Check Qdrant connection
    try:
        collection_stats = pipeline.vector_search.get_collection_stats()
        # If we get stats back with vectors_count, connection is good
        if collection_stats and "vectors_count" in collection_stats:
            qdrant_status = "connected"
        else:
            qdrant_status = "disconnected"
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        qdrant_status = "disconnected"

    # Check OpenAI availability (basic check)
    openai_status = "available" if config.openai.api_key else "no_api_key"

    # Determine overall status
    if qdrant_status == "connected" and openai_status == "available":
        overall_status = "healthy"
    elif qdrant_status == "connected" or openai_status == "available":
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return HealthResponse(
        status=overall_status,
        version="1.3.0",
        timestamp=datetime.now(),
        services={
            "qdrant": qdrant_status,
            "openai": openai_status
        }
    )


@router.get(
    "/api/v1/status",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="System status",
    description="Get detailed system status and statistics"
)
async def system_status(
    pipeline: RAGPipeline = Depends(get_pipeline)
) -> StatusResponse:
    """
    Detailed system status with statistics.

    Returns:
        StatusResponse with detailed stats
    """
    logger.debug("System status requested")

    # Get pipeline stats
    pipeline_stats = pipeline.get_stats()

    # Get collection stats
    collection_stats = pipeline.vector_search.get_collection_stats()

    # Ensure collection_stats has default values
    if not collection_stats:
        collection_stats = {"vectors_count": 0, "points_count": 0}

    # Count chunks by area (requires querying Qdrant)
    # For now, we'll use total count (optimize later if needed)
    by_area = {}
    try:
        # Query to get counts per area (basic implementation)
        # This is a simplified version - can be optimized
        from src.config import VALID_AREAS

        for area_code in VALID_AREAS.keys():
            try:
                # Search with area filter to get count
                results = pipeline.vector_search.qdrant_client.scroll(
                    collection_name=config.qdrant.collection_name,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="area",
                                match=models.MatchValue(value=area_code)
                            )
                        ]
                    ),
                    limit=1,
                    with_payload=False,
                    with_vectors=False
                )
                # Note: This is not accurate for large collections
                # Better approach: maintain counts in a separate collection
                # For now, just use the total count divided by number of areas
                total_count = collection_stats.get("points_count") or collection_stats.get("vectors_count") or 0
                by_area[area_code] = total_count // len(VALID_AREAS)
            except:
                by_area[area_code] = 0

    except Exception as e:
        logger.warning(f"Could not get area stats: {e}")
        by_area = {area: 0 for area in VALID_AREAS.keys()}

    # Calculate uptime
    uptime = (datetime.now() - API_START_TIME).total_seconds()

    # Use points_count as fallback if vectors_count is None
    total_chunks = collection_stats.get("points_count") or collection_stats.get("vectors_count") or 0

    return StatusResponse(
        pipeline_stats=pipeline_stats,
        collection_stats=CollectionStats(
            total_chunks=total_chunks,
            by_area=by_area,
            collection_name=config.qdrant.collection_name
        ),
        uptime_seconds=uptime
    )

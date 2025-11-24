"""
RAG query endpoints.
Core RAG functionality for document querying.
"""
from fastapi import APIRouter, Depends, status, HTTPException
from loguru import logger

from api.models.requests import RAGQueryRequest
from api.models.responses import (
    RAGQueryResponse,
    RAGMetrics,
    SourceChunk,
    ErrorResponse
)
from api.dependencies import get_pipeline
from src.pipeline import RAGPipeline

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query documents",
    description="Query the RAG system with a question and get an answer with sources",
    responses={
        200: {"description": "Successful query"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def query_documents(
    request: RAGQueryRequest,
    pipeline: RAGPipeline = Depends(get_pipeline)
) -> RAGQueryResponse:
    """
    Query the RAG system.

    Process a natural language question and return an answer with
    supporting sources from the document collection.

    Args:
        request: RAG query request with question and configuration
        pipeline: Injected RAGPipeline instance

    Returns:
        RAGQueryResponse with answer, sources, and metrics

    Raises:
        HTTPException: If query processing fails
    """
    logger.info(f"RAG query received: '{request.question}' (area: {request.area})")

    try:
        # Prepare config from request
        config_dict = {}
        if request.config:
            config_dict = {
                "top_k_retrieval": request.config.top_k_retrieval,
                "top_k_rerank": request.config.top_k_rerank,
                "expand_context": request.config.expand_context,
                "enable_multihop": request.config.enable_multihop,
                "enable_hyde": request.config.enable_hyde,
                "enable_validation": request.config.enable_validation,
            }

        # Execute RAG pipeline query
        result = pipeline.query(
            question=request.question,
            area=request.area,
            documento_ids=request.documento_ids,
            **config_dict
        )

        # Check if query was successful
        if not result.get("success", False):
            error_msg = result.get("error", "Query failed")
            logger.error(f"Pipeline query failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": error_msg,
                    "error_code": "QUERY_FAILED"
                }
            )

        # Transform sources to response model
        sources = []
        for chunk in result.get("sources", []):
            sources.append(
                SourceChunk(
                    chunk_id=chunk.get("chunk_id", ""),
                    texto=chunk.get("texto", ""),
                    citacion_corta=chunk.get("citacion_corta", ""),
                    score=chunk.get("score"),
                    documento_id=chunk.get("documento_id", ""),
                    nivel_jerarquico=chunk.get("nivel_jerarquico", 0)
                )
            )

        # Transform metrics to response model
        metrics_data = result.get("metrics", {})
        metrics = RAGMetrics(
            total_time=metrics_data.get("total_time", 0.0),
            search_time=metrics_data.get("search_time", 0.0),
            rerank_time=metrics_data.get("rerank_time", 0.0),
            generation_time=metrics_data.get("generation_time", 0.0),
            chunks_retrieved=metrics_data.get("chunks_retrieved", 0),
            chunks_reranked=metrics_data.get("chunks_reranked", 0),
            total_cost=metrics_data.get("total_cost", 0.0),
            query_type=metrics_data.get("query_type", "unknown"),
            retrieval_strategy=metrics_data.get("retrieval_strategy", "unknown"),
            multihop_used=metrics_data.get("multihop_used", False),
            hyde_used=metrics_data.get("hyde_used", False),
            validation_retry_used=metrics_data.get("validation_retry_used", False)
        )

        # Build query metadata
        query_metadata = {
            "query_enhancement": result.get("query_enhancement", {}),
            "query_decomposition": result.get("query_decomposition"),
            "hyde_metadata": result.get("hyde_metadata", {}),
            "validation_metadata": result.get("validation_metadata", {})
        }

        # Build response
        response = RAGQueryResponse(
            success=True,
            answer=result.get("answer", ""),
            sources=sources,
            num_sources=len(sources),
            metrics=metrics,
            query_metadata=query_metadata
        )

        logger.info(
            f"RAG query completed successfully: "
            f"{len(sources)} sources, "
            f"{metrics.total_time:.2f}s, "
            f"${metrics.total_cost:.6f}"
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Unexpected error in RAG query: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": f"Internal server error: {str(e)}",
                "error_code": "INTERNAL_ERROR"
            }
        )

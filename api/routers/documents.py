"""
Document management endpoints.
List, view, and manage indexed documents.
"""
from typing import Optional
from fastapi import APIRouter, Depends, status, HTTPException, Query
from loguru import logger
from qdrant_client import models

from api.models.responses import (
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentInfo,
    HierarchySummary,
    ErrorResponse
)
from api.dependencies import get_pipeline
from src.pipeline import RAGPipeline
from src.config import config, VALID_AREAS

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.get(
    "",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List documents",
    description="Get a list of all indexed documents, optionally filtered by area",
    responses={
        200: {"description": "List of documents"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def list_documents(
    area: Optional[str] = Query(
        None,
        description="Filter by area (sgr, inteligencia_artificial, general)"
    ),
    pipeline: RAGPipeline = Depends(get_pipeline)
) -> DocumentListResponse:
    """
    List all indexed documents.

    Optionally filter by knowledge area.

    Args:
        area: Optional area filter
        pipeline: Injected RAGPipeline instance

    Returns:
        DocumentListResponse with list of documents

    Raises:
        HTTPException: If listing fails
    """
    logger.info(f"List documents requested (area filter: {area or 'none'})")

    try:
        # Validate area if provided
        if area and area not in VALID_AREAS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": f"Invalid area. Must be one of: {', '.join(VALID_AREAS.keys())}",
                    "error_code": "INVALID_AREA"
                }
            )

        # Get all documents from Qdrant
        # Strategy: Scroll through collection and group by documento_id
        qdrant_client = pipeline.vector_search.qdrant_client
        collection_name = config.qdrant.collection_name

        # Build filter
        scroll_filter = None
        if area:
            scroll_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="area",
                        match=models.MatchValue(value=area)
                    )
                ]
            )

        # Scroll through all points to get unique documents
        documents_map = {}
        offset = None

        while True:
            result = qdrant_client.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            points, next_offset = result

            if not points:
                break

            for point in points:
                payload = point.payload
                doc_id = payload.get("documento_id")

                if doc_id and doc_id not in documents_map:
                    documents_map[doc_id] = {
                        "documento_id": doc_id,
                        "documento_nombre": payload.get("documento_nombre", "Unknown"),
                        "area": payload.get("area", "general"),
                        "documento_tipo": payload.get("documento_tipo", "generic"),
                        "fecha_procesamiento": payload.get("fecha_procesamiento"),
                        "chunk_count": 0
                    }

                # Increment chunk count
                if doc_id:
                    documents_map[doc_id]["chunk_count"] += 1

            # Check if more results
            if next_offset is None:
                break

            offset = next_offset

        # Convert to list and build response
        documents = []
        for doc_data in documents_map.values():
            documents.append(
                DocumentInfo(
                    documento_id=doc_data["documento_id"],
                    documento_nombre=doc_data["documento_nombre"],
                    area=doc_data["area"],
                    documento_tipo=doc_data["documento_tipo"],
                    total_chunks=doc_data["chunk_count"],
                    fecha_procesamiento=doc_data.get("fecha_procesamiento")
                )
            )

        # Sort by documento_id
        documents.sort(key=lambda x: x.documento_id)

        # Count by area
        area_counts = {}
        for doc in documents:
            area_counts[doc.area] = area_counts.get(doc.area, 0) + 1

        logger.info(f"Found {len(documents)} documents")

        return DocumentListResponse(
            documents=documents,
            total=len(documents),
            areas=area_counts
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": f"Failed to list documents: {str(e)}",
                "error_code": "LIST_FAILED"
            }
        )


@router.get(
    "/{documento_id}",
    response_model=DocumentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document details",
    description="Get detailed information about a specific document",
    responses={
        200: {"description": "Document details"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_document_detail(
    documento_id: str,
    pipeline: RAGPipeline = Depends(get_pipeline)
) -> DocumentDetailResponse:
    """
    Get detailed information about a document.

    Args:
        documento_id: Document ID
        pipeline: Injected RAGPipeline instance

    Returns:
        DocumentDetailResponse with document details

    Raises:
        HTTPException: If document not found or retrieval fails
    """
    logger.info(f"Document detail requested: {documento_id}")

    try:
        qdrant_client = pipeline.vector_search.qdrant_client
        collection_name = config.qdrant.collection_name

        # Get all chunks for this document
        result = qdrant_client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="documento_id",
                        match=models.MatchValue(value=documento_id)
                    )
                ]
            ),
            limit=10000,  # Get all chunks
            with_payload=True,
            with_vectors=False
        )

        points, _ = result

        if not points:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": f"Document '{documento_id}' not found",
                    "error_code": "DOCUMENT_NOT_FOUND"
                }
            )

        # Extract metadata from first chunk
        first_payload = points[0].payload

        # Count hierarchy elements
        titulos = set()
        capitulos = set()
        articulos = set()
        secciones = set()

        for point in points:
            payload = point.payload

            if payload.get("titulo"):
                titulos.add(payload["titulo"])
            if payload.get("capitulo"):
                capitulos.add(payload["capitulo"])
            if payload.get("articulo"):
                articulos.add(payload["articulo"])
            if payload.get("seccion"):
                secciones.add(payload["seccion"])

        # Build metadata dict
        metadata = {
            "documento_numero": first_payload.get("documento_numero"),
            "documento_año": first_payload.get("documento_año"),
            "total_chunks": len(points),
            "documento_tipo": first_payload.get("documento_tipo", "generic")
        }

        # Build hierarchy summary
        hierarchy = HierarchySummary(
            titulos=len(titulos),
            capitulos=len(capitulos),
            articulos=len(articulos),
            secciones=len(secciones)
        )

        logger.info(f"Document found: {len(points)} chunks")

        return DocumentDetailResponse(
            documento_id=documento_id,
            documento_nombre=first_payload.get("documento_nombre", "Unknown"),
            area=first_payload.get("area", "general"),
            documento_tipo=first_payload.get("documento_tipo", "generic"),
            metadata=metadata,
            hierarchy_summary=hierarchy,
            total_chunks=len(points)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error getting document detail: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": f"Failed to get document details: {str(e)}",
                "error_code": "DETAIL_FAILED"
            }
        )


@router.delete(
    "/{documento_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete document",
    description="Delete a document and all its chunks from the collection",
    responses={
        200: {"description": "Document deleted successfully"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def delete_document(
    documento_id: str,
    pipeline: RAGPipeline = Depends(get_pipeline)
):
    """
    Delete a document from the collection.

    WARNING: This operation is irreversible!

    Args:
        documento_id: Document ID to delete
        pipeline: Injected RAGPipeline instance

    Returns:
        Success message with deletion statistics

    Raises:
        HTTPException: If document not found or deletion fails
    """
    logger.warning(f"Document deletion requested: {documento_id}")

    try:
        qdrant_client = pipeline.vector_search.qdrant_client
        collection_name = config.qdrant.collection_name

        # First, check if document exists and count chunks
        result = qdrant_client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="documento_id",
                        match=models.MatchValue(value=documento_id)
                    )
                ]
            ),
            limit=1,
            with_payload=False,
            with_vectors=False
        )

        points, _ = result

        if not points:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": f"Document '{documento_id}' not found",
                    "error_code": "DOCUMENT_NOT_FOUND"
                }
            )

        # Delete all points with this documento_id
        # Note: Qdrant doesn't return count of deleted points directly
        # We need to scroll and delete by IDs
        all_point_ids = []
        offset = None

        while True:
            result = qdrant_client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="documento_id",
                            match=models.MatchValue(value=documento_id)
                        )
                    ]
                ),
                limit=100,
                offset=offset,
                with_payload=False,
                with_vectors=False
            )

            points, next_offset = result

            if not points:
                break

            all_point_ids.extend([point.id for point in points])

            if next_offset is None:
                break

            offset = next_offset

        # Delete all points
        if all_point_ids:
            qdrant_client.delete(
                collection_name=collection_name,
                points_selector=all_point_ids
            )

        chunks_deleted = len(all_point_ids)
        logger.warning(f"Document '{documento_id}' deleted: {chunks_deleted} chunks removed")

        return {
            "success": True,
            "message": f"Document '{documento_id}' deleted successfully",
            "chunks_deleted": chunks_deleted
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": f"Failed to delete document: {str(e)}",
                "error_code": "DELETE_FAILED"
            }
        )

"""
Response models for API endpoints.
Pydantic models for structured API responses.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status (healthy, degraded, unhealthy)")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Current server timestamp")
    services: Dict[str, str] = Field(
        ...,
        description="Status of dependent services (qdrant, openai)"
    )


class CollectionStats(BaseModel):
    """Qdrant collection statistics."""

    total_chunks: int = Field(..., description="Total chunks in collection")
    by_area: Dict[str, int] = Field(
        ...,
        description="Chunks per area"
    )
    collection_name: str = Field(..., description="Qdrant collection name")


class StatusResponse(BaseModel):
    """System status response."""

    pipeline_stats: Dict[str, Any] = Field(
        ...,
        description="Pipeline statistics"
    )
    collection_stats: CollectionStats = Field(
        ...,
        description="Collection statistics"
    )
    uptime_seconds: float = Field(..., description="API uptime in seconds")


class SourceChunk(BaseModel):
    """Source chunk information."""

    chunk_id: str = Field(..., description="Unique chunk ID")
    texto: str = Field(..., description="Chunk text content")
    citacion_corta: str = Field(..., description="Short citation reference")
    score: Optional[float] = Field(default=None, description="Relevance score")
    documento_id: str = Field(..., description="Source document ID")
    nivel_jerarquico: Optional[int] = Field(default=0, description="Hierarchical level")


class RAGMetrics(BaseModel):
    """RAG query metrics."""

    total_time: float = Field(..., description="Total query time in seconds")
    search_time: float = Field(..., description="Search time in seconds")
    rerank_time: float = Field(..., description="Re-ranking time in seconds")
    generation_time: float = Field(..., description="Generation time in seconds")
    chunks_retrieved: int = Field(..., description="Number of chunks retrieved")
    chunks_reranked: int = Field(..., description="Number of chunks re-ranked")
    total_cost: float = Field(..., description="Total cost in USD")
    query_type: str = Field(..., description="Detected query type")
    retrieval_strategy: str = Field(..., description="Retrieval strategy used")
    multihop_used: bool = Field(..., description="Whether multihop was used")
    hyde_used: bool = Field(..., description="Whether HyDE was used")
    validation_retry_used: bool = Field(
        ...,
        description="Whether validation retry was triggered"
    )


class RAGQueryResponse(BaseModel):
    """Response for RAG query."""

    success: bool = Field(default=True, description="Query success status")
    answer: str = Field(..., description="Generated answer")
    sources: List[SourceChunk] = Field(..., description="Source chunks used")
    num_sources: int = Field(..., description="Number of sources")
    metrics: RAGMetrics = Field(..., description="Query metrics")
    query_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional query metadata"
    )


class DocumentInfo(BaseModel):
    """Document information."""

    documento_id: str = Field(..., description="Document ID")
    documento_nombre: str = Field(..., description="Document name")
    area: str = Field(..., description="Document area")
    documento_tipo: str = Field(..., description="Document type")
    total_chunks: int = Field(..., description="Total chunks")
    fecha_procesamiento: Optional[datetime] = Field(
        default=None,
        description="Processing date"
    )


class DocumentListResponse(BaseModel):
    """Response for document list."""

    documents: List[DocumentInfo] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    areas: Dict[str, int] = Field(
        ...,
        description="Document count per area"
    )


class HierarchySummary(BaseModel):
    """Document hierarchy summary."""

    titulos: Optional[int] = Field(default=0, description="Number of titles")
    capitulos: Optional[int] = Field(default=0, description="Number of chapters")
    articulos: Optional[int] = Field(default=0, description="Number of articles")
    secciones: Optional[int] = Field(default=0, description="Number of sections")


class DocumentDetailResponse(BaseModel):
    """Detailed document information."""

    documento_id: str = Field(..., description="Document ID")
    documento_nombre: str = Field(..., description="Document name")
    area: str = Field(..., description="Document area")
    documento_tipo: str = Field(..., description="Document type")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")
    hierarchy_summary: HierarchySummary = Field(
        ...,
        description="Hierarchy summary"
    )
    total_chunks: int = Field(..., description="Total chunks")


class IngestionTaskResponse(BaseModel):
    """Response when creating ingestion task."""

    task_id: str = Field(..., description="Unique task ID")
    status: str = Field(..., description="Task status (pending)")
    message: str = Field(..., description="Success message")
    estimated_time_seconds: int = Field(
        ...,
        description="Estimated processing time"
    )
    status_url: str = Field(..., description="URL to check task status")


class IngestionProgress(BaseModel):
    """Ingestion task progress."""

    percent: int = Field(..., ge=0, le=100, description="Progress percentage")
    current_phase: str = Field(
        ...,
        description="Current processing phase"
    )
    phases: Dict[str, str] = Field(
        ...,
        description="Status of each phase"
    )


class IngestionResults(BaseModel):
    """Ingestion task results."""

    chunks_created: int = Field(..., description="Number of chunks created")
    vectors_uploaded: int = Field(..., description="Number of vectors uploaded")
    total_cost: float = Field(..., description="Total cost in USD")
    processing_time_seconds: float = Field(
        ...,
        description="Total processing time"
    )


class IngestionStatusResponse(BaseModel):
    """Response for ingestion task status."""

    task_id: str = Field(..., description="Task ID")
    status: str = Field(
        ...,
        description="Task status (pending, processing, completed, failed)"
    )
    area: str = Field(..., description="Document area")
    documento_id: Optional[str] = Field(default=None, description="Document ID")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")

    # Progress (only for processing status)
    progress: Optional[IngestionProgress] = Field(
        default=None,
        description="Progress information"
    )

    # Results (only for completed status)
    results: Optional[IngestionResults] = Field(
        default=None,
        description="Processing results"
    )

    # Error (only for failed status)
    error: Optional[str] = Field(default=None, description="Error message")
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code"
    )

    # Timestamps
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    started_at: Optional[datetime] = Field(
        default=None,
        description="Processing start time"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Completion timestamp"
    )
    failed_at: Optional[datetime] = Field(
        default=None,
        description="Failure timestamp"
    )

    # Time estimates
    elapsed_seconds: Optional[float] = Field(
        default=None,
        description="Elapsed time"
    )
    estimated_remaining_seconds: Optional[int] = Field(
        default=None,
        description="Estimated remaining time"
    )

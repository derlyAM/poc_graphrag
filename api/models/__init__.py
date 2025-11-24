"""
API models package.
Pydantic models for request/response validation.
"""
from api.models.requests import (
    RAGQueryRequest,
    DocumentIngestionMetadata,
)
from api.models.responses import (
    HealthResponse,
    StatusResponse,
    RAGQueryResponse,
    DocumentListResponse,
    DocumentDetailResponse,
    IngestionTaskResponse,
    IngestionStatusResponse,
    ErrorResponse,
)

__all__ = [
    # Requests
    "RAGQueryRequest",
    "DocumentIngestionMetadata",
    # Responses
    "HealthResponse",
    "StatusResponse",
    "RAGQueryResponse",
    "DocumentListResponse",
    "DocumentDetailResponse",
    "IngestionTaskResponse",
    "IngestionStatusResponse",
    "ErrorResponse",
]

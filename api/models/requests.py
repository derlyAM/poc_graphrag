"""
Request models for API endpoints.
Pydantic models for validating incoming requests.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class RAGConfigRequest(BaseModel):
    """Configuration options for RAG query."""

    top_k_retrieval: Optional[int] = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of chunks to retrieve initially"
    )
    top_k_rerank: Optional[int] = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks after re-ranking"
    )
    expand_context: bool = Field(
        default=True,
        description="Whether to expand context with adjacent chunks"
    )
    enable_multihop: bool = Field(
        default=True,
        description="Enable multihop retrieval for complex queries"
    )
    enable_hyde: bool = Field(
        default=True,
        description="Enable HyDE (Hypothetical Document Embeddings)"
    )
    enable_validation: bool = Field(
        default=True,
        description="Enable response validation and auto-retry"
    )


class RAGQueryRequest(BaseModel):
    """Request model for RAG query endpoint."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="User question to query the documents"
    )
    area: str = Field(
        ...,
        description="Knowledge area to search in (sgr, inteligencia_artificial, general)"
    )
    documento_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of document IDs to filter"
    )
    config: Optional[RAGConfigRequest] = Field(
        default=None,
        description="Optional configuration for RAG pipeline"
    )

    @field_validator("area")
    @classmethod
    def validate_area_field(cls, v: str) -> str:
        """Validate area is one of the allowed values (dynamic from config)."""
        from src.config import validate_area

        try:
            # validate_area raises ValueError if invalid, otherwise returns normalized area
            return validate_area(v)
        except ValueError as e:
            # Re-raise with same message
            raise ValueError(str(e))

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate question is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()


class DocumentIngestionMetadata(BaseModel):
    """Metadata for document ingestion."""

    documento_nombre: Optional[str] = Field(
        default=None,
        description="Human-readable document name"
    )
    documento_tipo: Optional[str] = Field(
        default="generic",
        description="Document type: legal, technical, generic"
    )
    documento_año: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Document year"
    )
    documento_numero: Optional[str] = Field(
        default=None,
        description="Document number (for legal documents)"
    )
    custom_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional custom metadata"
    )

    @field_validator("documento_tipo")
    @classmethod
    def validate_tipo(cls, v: str) -> str:
        """Validate document type."""
        valid_types = ["legal", "technical", "generic"]
        if v not in valid_types:
            raise ValueError(
                f"Invalid document type. Must be one of: {', '.join(valid_types)}"
            )
        return v

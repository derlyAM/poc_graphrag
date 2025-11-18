"""
Configuration module for RAG system.
Centralizes all configuration and environment variables.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
STORAGE_DIR = BASE_DIR / "storage"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
STORAGE_DIR.mkdir(exist_ok=True)


class OpenAIConfig(BaseModel):
    """OpenAI API configuration."""
    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    embedding_model: str = Field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
    embedding_dimensions: int = Field(default_factory=lambda: int(os.getenv("EMBEDDING_DIMENSIONS", "1536")))
    llm_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    temperature: float = Field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.1")))
    max_tokens: int = Field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "800")))


class QdrantConfig(BaseModel):
    """Qdrant vector database configuration."""
    host: str = Field(default_factory=lambda: os.getenv("QDRANT_HOST", "localhost"))
    port: int = Field(default_factory=lambda: int(os.getenv("QDRANT_PORT", "6333")))
    collection_name: str = Field(default_factory=lambda: os.getenv("QDRANT_COLLECTION_NAME", "normativa_sgr"))
    use_memory: bool = Field(default_factory=lambda: os.getenv("QDRANT_USE_MEMORY", "true").lower() == "true")
    path: Optional[str] = Field(default_factory=lambda: os.getenv("QDRANT_PATH", "./storage/qdrant_local"))

    @property
    def url(self) -> str:
        """Get Qdrant URL."""
        if self.use_memory:
            return ":memory:"
        return f"http://{self.host}:{self.port}"


class RetrievalConfig(BaseModel):
    """Retrieval configuration."""
    top_k_retrieval: int = Field(default_factory=lambda: int(os.getenv("TOP_K_RETRIEVAL", "20")))
    top_k_rerank: int = Field(default_factory=lambda: int(os.getenv("TOP_K_RERANK", "5")))
    chunk_size: int = Field(default_factory=lambda: int(os.getenv("CHUNK_SIZE", "500")))
    chunk_overlap: int = Field(default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "50")))
    reranker_model: str = Field(default_factory=lambda: os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-12-v2"))


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    file: Path = Field(default_factory=lambda: LOGS_DIR / os.getenv("LOG_FILE", "app.log"))


class Config:
    """Main configuration class."""

    def __init__(self):
        self.openai = OpenAIConfig()
        self.qdrant = QdrantConfig()
        self.retrieval = RetrievalConfig()
        self.logging = LoggingConfig()

        # Paths
        self.data_dir = DATA_DIR
        self.storage_dir = STORAGE_DIR
        self.logs_dir = LOGS_DIR

    def validate(self) -> bool:
        """Validate configuration."""
        if not self.openai.api_key:
            raise ValueError("OPENAI_API_KEY is required in .env file")

        if not self.data_dir.exists():
            raise ValueError(f"Data directory does not exist: {self.data_dir}")

        return True

    def __repr__(self) -> str:
        """String representation."""
        return f"""
Config:
  OpenAI:
    - Model: {self.openai.llm_model}
    - Embedding: {self.openai.embedding_model}
    - Temperature: {self.openai.temperature}

  Qdrant:
    - URL: {self.qdrant.url}
    - Collection: {self.qdrant.collection_name}

  Retrieval:
    - Top-K Retrieval: {self.retrieval.top_k_retrieval}
    - Top-K Rerank: {self.retrieval.top_k_rerank}
    - Chunk Size: {self.retrieval.chunk_size}
    - Reranker: {self.retrieval.reranker_model}
"""


# Global config instance
config = Config()


# ============================================================================
# ÁREA DE CONOCIMIENTO - Separación de dominios
# ============================================================================

# Áreas válidas del sistema
VALID_AREAS = {
    "sgr": "Sistema General de Regalías",
    "inteligencia_artificial": "Inteligencia Artificial",
    "general": "General"
}

# Área por defecto
DEFAULT_AREA = "sgr"


def validate_area(area: str) -> str:
    """
    Valida que un área sea válida.

    Args:
        area: Código del área a validar

    Returns:
        Área validada (normalizada a lowercase)

    Raises:
        ValueError: Si el área no es válida
    """
    area_normalized = area.lower().strip()
    if area_normalized not in VALID_AREAS:
        valid_list = ", ".join(VALID_AREAS.keys())
        raise ValueError(
            f"Área '{area}' no válida. Áreas válidas: {valid_list}"
        )
    return area_normalized


def get_area_display_name(area: str) -> str:
    """
    Obtiene el nombre completo de un área.

    Args:
        area: Código del área

    Returns:
        Nombre completo del área
    """
    return VALID_AREAS.get(area.lower(), area)


def get_documents_for_area(area: str, qdrant_client=None) -> list[dict]:
    """
    Obtiene la lista de documentos disponibles en un área específica.

    PHASE 2.5 IMPROVEMENT: Allows UI to display available documents per area.

    Args:
        area: Código del área (será validado)
        qdrant_client: Optional QdrantClient instance (reuse existing connection to avoid locks)

    Returns:
        Lista de diccionarios con información de documentos:
        [
            {
                "id": "documento_id",
                "nombre": "Nombre del Documento",
                "tipo": "legal | technical | generic"
            },
            ...
        ]

    Raises:
        ValueError: Si el área no es válida

    Example:
        >>> docs = get_documents_for_area("inteligencia_artificial")
        >>> print(f"Encontrados {len(docs)} documentos")
        Encontrados 10 documentos
    """
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    from collections import defaultdict

    # Validate area
    area = validate_area(area)

    # Connect to Qdrant (reuse existing client if provided)
    if qdrant_client is None:
        qdrant_client = QdrantClient(path=config.qdrant.path)

    try:
        # Scroll through all chunks in the area
        results = qdrant_client.scroll(
            collection_name=config.qdrant.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="area", match=MatchValue(value=area))
                ]
            ),
            limit=10000,  # Get all points in area
            with_payload=True,
        )

        # Deduplicate documents by documento_id
        docs_dict = {}
        for point in results[0]:
            doc_id = point.payload.get("documento_id")
            if doc_id and doc_id not in docs_dict:
                docs_dict[doc_id] = {
                    "id": doc_id,
                    "nombre": point.payload.get("documento_nombre", doc_id),
                    "tipo": point.payload.get("tipo_documento", "generic"),
                }

        # Sort by nombre
        docs_list = sorted(docs_dict.values(), key=lambda x: x["nombre"])

        return docs_list

    except Exception as e:
        # If Qdrant is not available or collection doesn't exist
        print(f"Warning: Could not retrieve documents from Qdrant: {e}")
        return []


# Cost tracking constants
COSTS = {
    "text-embedding-3-small": {
        "input": 0.00002 / 1000  # $0.02 per 1M tokens
    },
    "text-embedding-3-large": {
        "input": 0.00013 / 1000  # $0.13 per 1M tokens
    },
    "gpt-4o-mini": {
        "input": 0.00015 / 1000,   # $0.15 per 1M tokens
        "output": 0.0006 / 1000    # $0.60 per 1M tokens
    },
    "gpt-4": {
        "input": 0.01 / 1000,      # $10 per 1M tokens
        "output": 0.03 / 1000      # $30 per 1M tokens
    }
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int = 0) -> float:
    """
    Calculate cost for API call.

    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD
    """
    if model not in COSTS:
        return 0.0

    cost = COSTS[model]["input"] * input_tokens
    if "output" in COSTS[model]:
        cost += COSTS[model]["output"] * output_tokens

    return cost

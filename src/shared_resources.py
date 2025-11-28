"""
Shared Resources - Singleton para recursos compartidos globalmente.

Este módulo mantiene UNA ÚNICA instancia de RAGPipeline y QdrantClient
compartida entre todas las páginas de Streamlit para evitar múltiples
conexiones a Qdrant (que no soporta concurrencia en modo local).

Patrón: Singleton con lazy initialization
"""
from typing import Optional
from pathlib import Path
from loguru import logger
from qdrant_client import QdrantClient


class SharedPipelineManager:
    """
    Gestor singleton de RAGPipeline y QdrantClient compartidos.

    Garantiza que solo exista UNA instancia de RAGPipeline y
    UNA instancia de QdrantClient en toda la aplicación,
    independientemente de cuántas páginas de Streamlit se abran
    o cuántos endpoints API se llamen.
    """

    _instance: Optional['SharedPipelineManager'] = None
    _pipeline: Optional['RAGPipeline'] = None
    _qdrant_client: Optional[QdrantClient] = None

    def __new__(cls):
        """Singleton pattern: siempre retorna la misma instancia."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info("SharedPipelineManager: Creating singleton instance")
        return cls._instance

    def get_qdrant_client(self) -> QdrantClient:
        """
        Obtiene la instancia única de QdrantClient.

        Lazy initialization: solo crea el cliente cuando se solicita
        por primera vez.

        Returns:
            QdrantClient: Instancia única compartida
        """
        if self._qdrant_client is None:
            logger.info("SharedPipelineManager: Initializing QdrantClient (first access)")
            from src.config import config

            if config.qdrant.use_memory:
                logger.info("Using Qdrant in-memory mode")
                self._qdrant_client = QdrantClient(":memory:")
            elif config.qdrant.path:
                # Use local persistent storage
                logger.info(f"Using Qdrant local storage at {config.qdrant.path}")
                Path(config.qdrant.path).mkdir(parents=True, exist_ok=True)
                self._qdrant_client = QdrantClient(path=config.qdrant.path)
            else:
                logger.info(f"Connecting to Qdrant server at {config.qdrant.host}:{config.qdrant.port}")
                self._qdrant_client = QdrantClient(
                    host=config.qdrant.host,
                    port=config.qdrant.port
                )

            logger.success("SharedPipelineManager: QdrantClient initialized and cached")
        else:
            logger.debug("SharedPipelineManager: Returning existing QdrantClient instance")

        return self._qdrant_client

    def get_pipeline(self) -> 'RAGPipeline':
        """
        Obtiene la instancia única de RAGPipeline.

        Lazy initialization: solo crea el pipeline cuando se solicita
        por primera vez.

        Returns:
            RAGPipeline: Instancia única compartida
        """
        if self._pipeline is None:
            logger.info("SharedPipelineManager: Initializing RAGPipeline (first access)")
            from src.pipeline import RAGPipeline
            self._pipeline = RAGPipeline()
            logger.success("SharedPipelineManager: RAGPipeline initialized and cached")
        else:
            logger.debug("SharedPipelineManager: Returning existing RAGPipeline instance")

        return self._pipeline

    def reset(self):
        """
        Resetea el pipeline y cliente Qdrant (solo para testing o debugging).

        ADVERTENCIA: Esto cerrará la conexión de Qdrant.
        """
        logger.warning("SharedPipelineManager: Resetting pipeline and Qdrant client")
        self._pipeline = None
        self._qdrant_client = None

    def __repr__(self) -> str:
        """Representación del manager."""
        status = "initialized" if self._pipeline is not None else "not initialized"
        return f"<SharedPipelineManager: {status}>"


# Funciones helper para acceso rápido
def get_shared_pipeline() -> 'RAGPipeline':
    """
    Obtiene la instancia compartida de RAGPipeline.

    Esta es la función principal que deben usar todas las páginas
    de Streamlit.

    Returns:
        RAGPipeline: Instancia única compartida

    Example:
        ```python
        from src.shared_resources import get_shared_pipeline

        pipeline = get_shared_pipeline()
        result = pipeline.query(question="...", area="...")
        ```
    """
    manager = SharedPipelineManager()
    return manager.get_pipeline()


def get_shared_qdrant_client() -> QdrantClient:
    """
    Obtiene la instancia compartida de QdrantClient.

    Esta función debe usarse para TODAS las conexiones a Qdrant
    para evitar problemas de concurrencia en modo local.

    Returns:
        QdrantClient: Instancia única compartida

    Example:
        ```python
        from src.shared_resources import get_shared_qdrant_client

        client = get_shared_qdrant_client()
        collections = client.get_collections()
        ```
    """
    manager = SharedPipelineManager()
    return manager.get_qdrant_client()

"""
Shared Resources - Singleton para recursos compartidos globalmente.

Este módulo mantiene UNA ÚNICA instancia de RAGPipeline compartida
entre todas las páginas de Streamlit para evitar múltiples conexiones
a Qdrant (que no soporta concurrencia en modo local).

Patrón: Singleton con lazy initialization
"""
from typing import Optional
from loguru import logger


class SharedPipelineManager:
    """
    Gestor singleton de RAGPipeline compartido.

    Garantiza que solo exista UNA instancia de RAGPipeline
    en toda la aplicación, independientemente de cuántas
    páginas de Streamlit se abran.
    """

    _instance: Optional['SharedPipelineManager'] = None
    _pipeline: Optional['RAGPipeline'] = None

    def __new__(cls):
        """Singleton pattern: siempre retorna la misma instancia."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info("SharedPipelineManager: Creating singleton instance")
        return cls._instance

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
        Resetea el pipeline (solo para testing o debugging).

        ADVERTENCIA: Esto cerrará la conexión de Qdrant.
        """
        logger.warning("SharedPipelineManager: Resetting pipeline")
        self._pipeline = None

    def __repr__(self) -> str:
        """Representación del manager."""
        status = "initialized" if self._pipeline is not None else "not initialized"
        return f"<SharedPipelineManager: {status}>"


# Función helper para acceso rápido
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

"""
Conversational Pipeline - Orquestador principal del chatbot de IA.

Componente de alto nivel que:
- Orquesta flujo conversacional multi-turno
- Reformula queries con contexto
- Delega retrieval/generación al Pipeline RAG (100% reuso)
- Formatea respuestas según modo (corto/largo)
- Mantiene historial de conversación

Arquitectura: COMPOSICIÓN, NO HERENCIA
- Contiene Pipeline, no lo extiende
- Zero modificaciones al código RAG existente
"""
from typing import Dict, List, Optional
from loguru import logger

from src.pipeline import RAGPipeline
from src.chatbot.conversation_manager import ConversationHistory
from src.chatbot.query_reformulator import QueryReformulator
from src.chatbot.response_formatter import ResponseFormatter
from src.chatbot.prompts import get_short_mode_config, get_long_mode_config


class ConversationalPipeline:
    """
    Pipeline conversacional para chatbot de IA.

    Wrapper sobre Pipeline RAG que agrega:
    - Gestión de historial multi-turno
    - Reformulación contextual de queries
    - Modos de respuesta (corto/largo)

    Arquitectura:
        User Query → QueryReformulator (contexto) → Pipeline.query() (RAG)
        → ResponseFormatter (modo) → Update History → Return
    """

    def __init__(
        self,
        area: str = "inteligencia_artificial",
        shared_pipeline: Optional[RAGPipeline] = None
    ):
        """
        Inicializa pipeline conversacional.

        Args:
            area: Área de documentos a consultar (por defecto IA)
            shared_pipeline: RAGPipeline existente para reutilizar (evita error de Qdrant)
                           Si None, crea uno nuevo
        """
        # ✅ COMPOSICIÓN - Contiene RAGPipeline, NO hereda
        # Reutilizar pipeline existente si se proporciona (evita múltiples conexiones Qdrant)
        if shared_pipeline is not None:
            logger.info("Reusing existing RAGPipeline (shared mode)")
            self._base_pipeline = shared_pipeline
        else:
            logger.info("Creating new RAGPipeline instance")
            self._base_pipeline = RAGPipeline()

        # Componentes conversacionales (nuevos)
        self._conversation_history = ConversationHistory(max_history=20)
        self._query_reformulator = QueryReformulator()
        self._response_formatter = ResponseFormatter()

        # Configuración
        self.area = area

        # Métricas
        self.total_queries = 0
        self.queries_reformulated = 0

        logger.info(f"ConversationalPipeline initialized (area={area})")

    def query(
        self,
        question: str,
        response_mode: str = "long",
        documento_ids: Optional[List[str]] = None,
        top_k_retrieval: Optional[int] = None,
        top_k_rerank: Optional[int] = None,
        expand_context: bool = True,
        enable_multihop: bool = True,
        enable_hyde: bool = True,
        enable_validation: bool = True
    ) -> Dict:
        """
        Procesa query conversacional.

        Flujo:
        1. Obtiene historial de conversación
        2. Reformula query si tiene referencias contextuales
        3. Llama a Pipeline.query() con query reformulada
        4. Formatea respuesta según modo (corto/largo)
        5. Actualiza historial con pregunta y respuesta
        6. Retorna resultado formateado

        Args:
            question: Pregunta del usuario
            response_mode: "short" o "long"
            documento_ids: Lista de IDs de documentos específicos (opcional)
            top_k_retrieval: Número de chunks a recuperar en retrieval inicial (default: config)
            top_k_rerank: Número de chunks después de reranking (default: config)
            expand_context: Expandir contexto con chunks adyacentes
            enable_multihop: Activar multihop retrieval
            enable_hyde: Activar HyDE
            enable_validation: Activar validación de completitud (Phase 3)

        Returns:
            {
                "answer": str,  # Respuesta formateada según modo
                "sources": List,  # Fuentes (formato según modo)
                "mode": str,  # "short" o "long"
                "original_question": str,
                "reformulated_question": str,  # Si se reformuló
                "metrics": Dict,
                "conversation_length": int
            }
        """
        self.total_queries += 1

        logger.info(f"\n{'='*60}")
        logger.info(f"CHATBOT QUERY #{self.total_queries}")
        logger.info(f"Mode: {response_mode.upper()}")
        logger.info(f"Question: '{question}'")
        logger.info(f"{'='*60}\n")

        # === PASO 1: Obtener historial ===
        conversation_context = self._conversation_history.get_last_n_messages(n=5)
        logger.debug(f"Retrieved {len(conversation_context)} previous messages")

        # === PASO 2: Reformular query con contexto ===
        reformulated_question = self._query_reformulator.reformulate_with_context(
            current_query=question,
            conversation_history=conversation_context
        )

        # Tracking
        if reformulated_question != question:
            self.queries_reformulated += 1
            logger.info(f"Query reformulated: '{question}' → '{reformulated_question}'")

        # === PASO 3: Llamar a Pipeline RAG (REUSO 100%) ===
        logger.info("[DELEGATING TO RAG PIPELINE]")

        # Preparar filtros para área de IA
        # Asumiendo que documentos de IA tienen metadata "area": "inteligencia_artificial"
        # O filtrar por documento_ids específicos si se proporcionan

        try:
            # Llamada al Pipeline RAG existente (sin modificaciones)
            rag_result = self._base_pipeline.query(
                question=reformulated_question,
                area=self.area,  # Área de IA
                documento_ids=documento_ids,  # Filtro de documentos
                top_k_retrieval=top_k_retrieval,
                top_k_rerank=top_k_rerank,
                expand_context=expand_context,
                enable_multihop=enable_multihop,
                enable_hyde=enable_hyde,
                enable_validation=enable_validation
            )

            answer = rag_result["answer"]
            retrieved_chunks = rag_result.get("sources", [])  # RAGPipeline usa "sources", no "retrieved_chunks"
            metrics = rag_result.get("metrics", {})

        except Exception as e:
            logger.error(f"Error in RAG Pipeline: {e}")
            # Fallback
            answer = f"Lo siento, ocurrió un error al procesar tu pregunta: {str(e)}"
            retrieved_chunks = []
            metrics = {"error": str(e)}

        # === PASO 4: Formatear según modo ===
        logger.info(f"[FORMATTING RESPONSE] Mode: {response_mode}")

        # Aplicar configuración de LLM según modo
        # NOTA: El Pipeline ya generó la respuesta, aquí solo formateamos
        # Para respuestas cortas/largas idealmente deberíamos pasar config ANTES
        # Pero para MVP, post-procesamos la respuesta generada

        formatted_result = self._response_formatter.format_response(
            answer=answer,
            chunks=retrieved_chunks,
            mode=response_mode
        )

        # === PASO 5: Actualizar historial ===
        self._conversation_history.add_message(role="user", content=question)
        self._conversation_history.add_message(
            role="assistant",
            content=formatted_result["formatted_answer"]
        )

        logger.debug("Conversation history updated")

        # === PASO 6: Construir respuesta final ===
        result = {
            "answer": formatted_result["formatted_answer"],
            "sources": formatted_result["sources"],
            "mode": response_mode,
            "num_sources": formatted_result["num_sources"],
            "original_question": question,
            "reformulated_question": reformulated_question,
            "was_reformulated": reformulated_question != question,
            "metrics": {
                **metrics,
                "response_mode": response_mode,
                "conversation_length": len(self._conversation_history)
            },
            "conversation_length": len(self._conversation_history)
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"CHATBOT RESPONSE READY")
        logger.info(f"Answer length: {len(result['answer'])} chars")
        logger.info(f"Sources: {result['num_sources']}")
        logger.info(f"Conversation length: {result['conversation_length']} messages")
        logger.info(f"{'='*60}\n")

        return result

    def clear_history(self) -> None:
        """
        Limpia el historial de conversación.

        Útil para empezar una nueva sesión.
        """
        logger.info("Clearing conversation history")
        self._conversation_history.clear()

    def get_conversation_summary(self) -> str:
        """
        Obtiene resumen de la conversación actual.

        Returns:
            String con resumen del historial
        """
        return self._conversation_history.get_conversation_summary()

    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas del chatbot.

        Returns:
            Dict con métricas de uso
        """
        reformulation_stats = self._query_reformulator.get_stats()

        return {
            "total_queries": self.total_queries,
            "queries_reformulated": self.queries_reformulated,
            "reformulation_rate": (
                self.queries_reformulated / self.total_queries
                if self.total_queries > 0 else 0.0
            ),
            "conversation_length": len(self._conversation_history),
            "reformulator_stats": reformulation_stats
        }

    def __repr__(self) -> str:
        """Representación string del pipeline."""
        return (
            f"<ConversationalPipeline: "
            f"queries={self.total_queries}, "
            f"conversation_length={len(self._conversation_history)}>"
        )

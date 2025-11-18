"""
Query Reformulator - Reformulación contextual de queries.

Convierte queries dependientes del contexto en queries standalone
usando el historial de conversación.

Ejemplo:
    History: [User: "¿Qué es la IA?", Bot: "..."]
    Current: "¿Cuáles son sus aplicaciones?"
    Output: "¿Cuáles son las aplicaciones de la inteligencia artificial?"
"""
from typing import List, Dict
from loguru import logger
import openai

from src.config import config
from src.chatbot.prompts import QUERY_REFORMULATION_PROMPT, format_conversation_history


class QueryReformulator:
    """
    Reformula queries usando contexto conversacional.

    Funcionalidad genuinamente nueva - NO existe en Pipeline RAG.
    Usa LLM pero con propósito diferente a HyDE (reformulación vs generación hipotética).
    """

    def __init__(self):
        """Inicializa query reformulator."""
        self.client = openai.OpenAI(api_key=config.openai.api_key)
        self.model = "gpt-4o-mini"  # Rápido y barato para reformulación

        # Métricas
        self.total_reformulations = 0
        self.reformulations_needed = 0

        logger.debug("QueryReformulator initialized")

    def reformulate_with_context(
        self,
        current_query: str,
        conversation_history: List[Dict]
    ) -> str:
        """
        Reformula query usando contexto conversacional.

        Si la query tiene referencias ("sus", "eso", "lo anterior"), las resuelve
        usando el historial. Si ya es standalone, la devuelve sin cambios.

        Args:
            current_query: Query actual del usuario
            conversation_history: Lista de mensajes previos
                [{"role": "user/assistant", "content": str}, ...]

        Returns:
            Query reformulada (standalone)
        """
        self.total_reformulations += 1

        # Si no hay historial, no hay nada que reformular
        if not conversation_history:
            logger.debug("No history - query returned as-is")
            return current_query

        # Detectar si query tiene referencias que requieren contexto
        if not self._needs_reformulation(current_query):
            logger.debug("Query appears standalone - skipping reformulation")
            return current_query

        # Reformular usando LLM
        logger.info(f"Reformulating query: '{current_query[:50]}...'")

        try:
            reformulated = self._call_llm_for_reformulation(
                current_query,
                conversation_history
            )

            self.reformulations_needed += 1

            logger.info(f"Reformulated: '{current_query}' → '{reformulated}'")
            return reformulated

        except Exception as e:
            logger.error(f"Error in reformulation: {e}")
            # Fallback: devolver query original
            return current_query

    def _needs_reformulation(self, query: str) -> bool:
        """
        Detecta si query necesita reformulación.

        Heurística rápida basada en palabras de referencia.

        Args:
            query: Query a analizar

        Returns:
            True si parece necesitar reformulación
        """
        query_lower = query.lower()

        # Palabras/frases de referencia que indican dependencia de contexto
        reference_indicators = [
            # Pronombres posesivos
            'sus', 'su', 'suyo', 'suya', 'suyos', 'suyas',
            # Pronombres demostrativos
            'eso', 'esto', 'esa', 'esta', 'esos', 'estos', 'esas', 'estas',
            'aquel', 'aquella', 'aquellos', 'aquellas',
            # Pronombres personales
            'él', 'el mismo', 'ella', 'ellos', 'ellas',
            # Adverbios de referencia
            'allí', 'ahí', 'allá',
            # Frases de referencia
            'lo anterior', 'lo mencionado', 'lo comentado',
            'como dijiste', 'como mencionaste',
            'lo mismo', 'igual'
        ]

        # Verificar si contiene algún indicador
        for indicator in reference_indicators:
            if indicator in query_lower:
                logger.debug(f"Reference detected: '{indicator}'")
                return True

        # Detectar preguntas muy cortas que probablemente dependen de contexto
        # Ej: "¿Y en Colombia?", "¿Cuáles?", "¿Por qué?"
        word_count = len(query.split())
        if word_count <= 3 and any(q in query_lower for q in ['cuál', 'cuales', 'qué', 'que', 'por qué', 'porqué']):
            logger.debug(f"Short question detected ({word_count} words)")
            return True

        return False

    def _call_llm_for_reformulation(
        self,
        current_query: str,
        conversation_history: List[Dict]
    ) -> str:
        """
        Llama a LLM para reformular query.

        Args:
            current_query: Query actual
            conversation_history: Historial de mensajes

        Returns:
            Query reformulada
        """
        # Formatear historial para el prompt
        history_text = format_conversation_history(conversation_history)

        # Construir prompt
        prompt = QUERY_REFORMULATION_PROMPT.format(
            conversation_history=history_text,
            current_query=current_query
        )

        # Llamar a LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Baja temperatura para reformulación precisa
            max_tokens=100  # Queries son cortas
        )

        reformulated = response.choices[0].message.content.strip()

        # Limpiar comillas si las agregó
        reformulated = reformulated.strip('"\'')

        # Calcular costo (opcional, para tracking)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = (input_tokens * 0.150 / 1_000_000) + (output_tokens * 0.600 / 1_000_000)

        logger.debug(f"Reformulation cost: ${cost:.6f}")

        return reformulated

    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas de reformulación.

        Returns:
            Dict con métricas
        """
        reformulation_rate = (
            self.reformulations_needed / self.total_reformulations
            if self.total_reformulations > 0 else 0.0
        )

        return {
            "total_reformulations": self.total_reformulations,
            "reformulations_needed": self.reformulations_needed,
            "reformulation_rate": reformulation_rate,
            "queries_skipped": self.total_reformulations - self.reformulations_needed
        }

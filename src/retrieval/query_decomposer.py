"""
Query Decomposer module.
Analyzes complex queries and decomposes them into simpler sub-queries for multihop retrieval.
"""
from typing import Dict, List, Optional
from loguru import logger
import openai
import json

from src.config import config


class QueryDecomposer:
    """Decomposes complex queries into sub-queries for multihop reasoning."""

    def __init__(self):
        """Initialize query decomposer."""
        self.client = openai.OpenAI(api_key=config.openai.api_key)
        self.model = config.openai.llm_model
        self.temperature = 0.1  # Low temperature for consistent decomposition

    def analyze_and_decompose(
        self,
        query: str,
        documento_id: Optional[str] = None
    ) -> Dict:
        """
        Analyze query complexity and decompose if needed.

        Args:
            query: User query
            documento_id: Optional document filter

        Returns:
            Dictionary with analysis and sub-queries
        """
        logger.info(f"Analyzing query complexity: '{query[:60]}...'")

        # Use LLM to analyze query
        analysis = self._analyze_query_with_llm(query)

        result = {
            "original_query": query,
            "query_type": analysis["query_type"],
            "complexity": analysis["complexity"],
            "requires_multihop": analysis["requires_multihop"],
            "sub_queries": analysis["sub_queries"],
            "reasoning": analysis.get("reasoning", ""),
            "search_strategy": self._determine_search_strategy(analysis),
        }

        if result["requires_multihop"]:
            logger.info(
                f"Multihop query detected. Type: {result['query_type']}, "
                f"Sub-queries: {len(result['sub_queries'])}"
            )
            for i, sq in enumerate(result['sub_queries'], 1):
                logger.info(f"  Sub-query {i}: {sq}")
        else:
            logger.info(f"Simple query detected. Type: {result['query_type']}")

        return result

    def _analyze_query_with_llm(self, query: str) -> Dict:
        """
        Use LLM to analyze query and generate sub-queries.

        Args:
            query: User query

        Returns:
            Analysis dictionary
        """
        system_prompt = """Eres un experto en análisis de consultas para sistemas RAG sobre documentos normativos.

Tu tarea es analizar consultas y determinar:
1. Tipo de consulta
2. Complejidad
3. Si requiere razonamiento multi-hop (múltiples pasos de búsqueda)
4. Sub-consultas necesarias para responder

TIPOS DE CONSULTA:
- "simple_semantic": Pregunta directa con respuesta en 1 fuente
- "structural": Solicita contenido de capítulo/artículo específico
- "comparison": Compara dos o más elementos
- "procedural": Pregunta por proceso o procedimiento con múltiples pasos
- "conditional": Pregunta con condiciones "si... entonces..."
- "aggregation": Lista o enumera múltiples elementos
- "reasoning": Requiere inferencia o razonamiento lógico

COMPLEJIDAD:
- "simple": 1 búsqueda suficiente
- "medium": 2-3 búsquedas necesarias
- "complex": 3+ búsquedas, razonamiento entre fuentes

Responde SIEMPRE en formato JSON válido."""

        user_prompt = f"""Analiza esta consulta:

"{query}"

Determina:
1. query_type: [tipo de consulta]
2. complexity: [simple | medium | complex]
3. requires_multihop: [true | false]
4. sub_queries: [lista de sub-consultas, vacía si no requiere multihop]
5. reasoning: [breve explicación de por qué requiere o no multihop]

Ejemplos:

Consulta: "¿Qué es un OCAD?"
{{
  "query_type": "simple_semantic",
  "complexity": "simple",
  "requires_multihop": false,
  "sub_queries": [],
  "reasoning": "Pregunta de definición simple, respuesta en un solo chunk"
}}

Consulta: "¿Puedo ajustar el cronograma de un proyecto de CTEI en fase II?"
{{
  "query_type": "conditional",
  "complexity": "complex",
  "requires_multihop": true,
  "sub_queries": [
    "¿Qué variables de un proyecto se pueden ajustar?",
    "¿El cronograma está incluido en las variables ajustables?",
    "¿Qué requisitos específicos hay para ajustes en fase II?"
  ],
  "reasoning": "Requiere verificar si cronograma es ajustable, luego buscar requisitos específicos de fase II"
}}

Consulta: "Lista todos los requisitos para proyectos de ciencia y tecnología"
{{
  "query_type": "aggregation",
  "complexity": "medium",
  "requires_multihop": false,
  "sub_queries": [],
  "reasoning": "Aunque requiere múltiples chunks, no necesita razonamiento secuencial. Una búsqueda exhaustiva es suficiente"
}}

Consulta: "¿Qué diferencias hay entre el Acuerdo 03/2021 y el Acuerdo 13/2025?"
{{
  "query_type": "comparison",
  "complexity": "complex",
  "requires_multihop": true,
  "sub_queries": [
    "¿Cuáles son las disposiciones principales del Acuerdo 03/2021?",
    "¿Cuáles son las disposiciones principales del Acuerdo 13/2025?",
    "¿Qué artículos fueron modificados entre ambos acuerdos?"
  ],
  "reasoning": "Requiere recuperar información de dos documentos diferentes y compararlos"
}}

Ahora analiza la consulta proporcionada y responde en formato JSON:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            analysis_text = response.choices[0].message.content
            analysis = json.loads(analysis_text)

            # Validate required fields
            required_fields = ["query_type", "complexity", "requires_multihop", "sub_queries"]
            for field in required_fields:
                if field not in analysis:
                    logger.warning(f"Missing field '{field}' in LLM response. Using defaults.")
                    analysis[field] = self._get_default_value(field)

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return self._get_fallback_analysis(query)

        except Exception as e:
            logger.error(f"Error analyzing query with LLM: {e}")
            return self._get_fallback_analysis(query)

    def _determine_search_strategy(self, analysis: Dict) -> str:
        """
        Determine search strategy based on analysis.

        Args:
            analysis: Query analysis

        Returns:
            Search strategy name
        """
        if not analysis["requires_multihop"]:
            # Single-hop strategies
            if analysis["query_type"] == "aggregation":
                return "exhaustive"  # High top-k
            elif analysis["query_type"] == "structural":
                return "metadata_filtered"
            else:
                return "standard"  # Normal semantic search
        else:
            # Multi-hop strategies
            if analysis["query_type"] == "comparison":
                return "multihop_comparison"
            elif analysis["query_type"] == "conditional":
                return "multihop_conditional"
            elif analysis["query_type"] == "procedural":
                return "multihop_procedural"
            else:
                return "multihop_sequential"

    def _get_default_value(self, field: str):
        """Get default value for missing field."""
        defaults = {
            "query_type": "simple_semantic",
            "complexity": "simple",
            "requires_multihop": False,
            "sub_queries": [],
            "reasoning": "Default analysis"
        }
        return defaults.get(field)

    def _get_fallback_analysis(self, query: str) -> Dict:
        """
        Fallback analysis using heuristics if LLM fails.

        Args:
            query: User query

        Returns:
            Fallback analysis
        """
        logger.warning("Using fallback heuristic analysis")

        query_lower = query.lower()

        # Heuristic detection
        is_comparison = any(kw in query_lower for kw in [
            "diferencia", "compara", "versus", "vs", "entre", "distinto"
        ])

        is_conditional = any(kw in query_lower for kw in [
            "si", "cuando", "en caso de", "puedo", "puede"
        ])

        is_aggregation = any(kw in query_lower for kw in [
            "lista", "enumera", "todos", "cuáles", "cuales"
        ])

        is_procedural = any(kw in query_lower for kw in [
            "proceso", "procedimiento", "cómo", "como", "pasos"
        ])

        # Determine if multihop
        requires_multihop = is_comparison or (is_conditional and len(query.split()) > 10)

        if is_comparison:
            query_type = "comparison"
            complexity = "complex"
        elif is_conditional:
            query_type = "conditional"
            complexity = "complex" if requires_multihop else "medium"
        elif is_aggregation:
            query_type = "aggregation"
            complexity = "medium"
        elif is_procedural:
            query_type = "procedural"
            complexity = "medium"
        else:
            query_type = "simple_semantic"
            complexity = "simple"

        return {
            "query_type": query_type,
            "complexity": complexity,
            "requires_multihop": requires_multihop,
            "sub_queries": [],  # Fallback doesn't generate sub-queries
            "reasoning": "Fallback heuristic analysis (LLM unavailable)"
        }


def decompose_query(query: str, documento_id: Optional[str] = None) -> Dict:
    """
    Convenience function to decompose a query.

    Args:
        query: User query
        documento_id: Optional document filter

    Returns:
        Decomposition result
    """
    decomposer = QueryDecomposer()
    return decomposer.analyze_and_decompose(query, documento_id)

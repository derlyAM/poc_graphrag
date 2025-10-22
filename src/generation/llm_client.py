"""
LLM Client module.
Handles interaction with OpenAI GPT models for answer generation.
"""
from typing import List, Dict, Optional, Tuple
from loguru import logger
import openai
import tiktoken

from src.config import config, calculate_cost


class LLMClient:
    """Client for generating answers using OpenAI LLM."""

    def __init__(self):
        """Initialize LLM client."""
        self.client = openai.OpenAI(api_key=config.openai.api_key)
        self.model = config.openai.llm_model
        self.temperature = config.openai.temperature
        self.max_tokens = config.openai.max_tokens
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.total_cost = 0.0

    def generate_answer(
        self,
        query: str,
        context_chunks: List[Dict],
        max_context_tokens: int = 2000,
        query_metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Generate answer from query and context.

        Args:
            query: User question
            context_chunks: Retrieved and re-ranked chunks
            max_context_tokens: Maximum tokens for context
            query_metadata: Optional query enhancement metadata

        Returns:
            Dictionary with answer and metadata
        """
        logger.info(f"Generating answer for: '{query[:50]}...'")

        # Build context from chunks
        context = self._build_context(context_chunks, max_context_tokens)

        # Create prompt with query metadata
        prompt = self._create_prompt(query, context, query_metadata)

        # Generate answer
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            answer = response.choices[0].message.content

            # Track cost
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = calculate_cost(self.model, input_tokens, output_tokens)
            self.total_cost += cost

            logger.info(
                f"Answer generated: {output_tokens} tokens, ${cost:.6f}"
            )

            return {
                "answer": answer,
                "query": query,
                "chunks_used": len(context_chunks),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "model": self.model,
            }

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise

    def _get_system_prompt(self) -> str:
        """
        Get system prompt for legal document QA.

        Returns:
            System prompt string
        """
        return """Eres un asistente experto en normativa colombiana, específicamente del Sistema General de Regalías (SGR).

Tu tarea es responder preguntas sobre documentos normativos usando ÚNICAMENTE el contexto proporcionado.

REGLAS ESTRICTAS:
1. TODA afirmación DEBE incluir una citación legal en formato: [Art. X, Documento]
2. Si el contexto no contiene información suficiente, indica claramente "No encontré información sobre..."
3. NUNCA inventes o asumas información que no esté en el contexto
4. Usa lenguaje claro, preciso y profesional
5. Para procedimientos, usa listas numeradas o bullets
6. Si hay múltiples fuentes relevantes, cítalas todas

FORMATO DE CITACIÓN:
- Usa corchetes: [Art. 4.5.1, Acuerdo Único 2025]
- Para múltiples fuentes: [Art. 4.5.1, Acuerdo Único 2025; Art. 2.3, Documento Técnico V2]
- Incluye la citación inmediatamente después de cada afirmación

ESTRUCTURA DE RESPUESTA:
1. Respuesta directa a la pregunta
2. Explicación con detalles relevantes y citaciones
3. Si aplica, ejemplos o procedimientos paso a paso
4. Referencias finales (opcional si son muchas)"""

    def _create_prompt(self, query: str, context: str, query_metadata: Optional[Dict] = None) -> str:
        """
        Create user prompt with query and context.

        Args:
            query: User question
            context: Built context from chunks
            query_metadata: Optional query enhancement metadata

        Returns:
            Complete prompt
        """
        # Add special instructions for structural queries
        special_instructions = ""

        if query_metadata:
            query_type = query_metadata.get('query_type', 'semantic')
            is_summary = query_metadata.get('is_summary_request', False)
            filters = query_metadata.get('filters', {})

            if query_type in ['structural', 'hybrid'] and is_summary:
                filter_desc = []
                if filters.get('capitulo'):
                    filter_desc.append(f"Capítulo {filters['capitulo']}")
                if filters.get('titulo'):
                    filter_desc.append(f"Título {filters['titulo']}")
                if filters.get('seccion'):
                    filter_desc.append(f"Sección {filters['seccion']}")

                if filter_desc:
                    special_instructions = f"""
INSTRUCCIONES ESPECIALES:
Esta es una solicitud de RESUMEN de {' y '.join(filter_desc)}.
- Proporciona un resumen completo y estructurado
- Organiza la información en secciones lógicas
- Incluye todos los puntos principales del contenido proporcionado
- Cita cada sección resumida con su artículo correspondiente
- NO te limites a respuestas cortas, desarrolla el contenido completo
"""

        prompt = f"""CONTEXTO RECUPERADO DE DOCUMENTOS NORMATIVOS:

{context}

---
{special_instructions}
---

PREGUNTA DEL USUARIO:
{query}

Por favor, responde usando el contexto anterior. Recuerda incluir citaciones para cada afirmación."""

        return prompt

    def _build_context(
        self, chunks: List[Dict], max_tokens: int = 2000
    ) -> str:
        """
        Build context string from chunks.

        Args:
            chunks: List of chunks
            max_tokens: Maximum tokens for context

        Returns:
            Context string
        """
        context_parts = []
        current_tokens = 0

        for i, chunk in enumerate(chunks):
            # Format chunk with metadata
            chunk_text = f"""[FUENTE {i + 1}]
Documento: {chunk.get('documento_nombre', 'N/A')}
Citación: {chunk.get('citacion_corta', 'N/A')}
Artículo: {chunk.get('articulo', 'N/A')}

Contenido:
{chunk.get('texto', '')}
"""

            # Count tokens
            chunk_tokens = self._count_tokens(chunk_text)

            # Check if we exceed limit
            if current_tokens + chunk_tokens > max_tokens:
                logger.warning(
                    f"Context limit reached. Using {i} of {len(chunks)} chunks"
                )
                break

            context_parts.append(chunk_text)
            current_tokens += chunk_tokens

        context = "\n---\n".join(context_parts)

        logger.info(
            f"Built context: {len(context_parts)} chunks, {current_tokens} tokens"
        )

        return context

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count

        Returns:
            Number of tokens
        """
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            # Fallback approximation
            return int(len(text.split()) * 1.3)

    def get_total_cost(self) -> float:
        """
        Get total cost of API calls in this session.

        Returns:
            Total cost in USD
        """
        return self.total_cost


def generate_answer_simple(
    query: str, context_chunks: List[Dict]
) -> Tuple[str, Dict]:
    """
    Convenience function for simple answer generation.

    Args:
        query: User question
        context_chunks: Retrieved chunks

    Returns:
        Tuple of (answer text, metadata dict)
    """
    client = LLMClient()
    result = client.generate_answer(query, context_chunks)
    return result["answer"], result

"""
Response Validator module.

PHASE 3 IMPROVEMENT: Validates response completeness and enhances incomplete answers.

Provides:
- Completeness validation using LLM
- Missing information detection
- Retry query generation
- Response enhancement with additional retrieval
"""
from typing import Dict, List, Optional, Tuple
from loguru import logger
import openai

from src.config import config


class ResponseValidator:
    """
    Validates and enhances responses for completeness.

    PHASE 3 OPTIMIZATION: Ensures responses fully address user questions.

    Features:
    - Completeness scoring (0-1 scale)
    - Missing information identification
    - Automatic retry with reformulated queries
    - Response enhancement
    """

    def __init__(self):
        """
        Initialize response validator.
        """
        self.client = openai.OpenAI(api_key=config.openai.api_key)
        self.model = "gpt-4o-mini"  # Fast and cheap for validation

        # Metrics
        self.total_validations = 0
        self.incomplete_responses = 0
        self.retry_attempts = 0
        self.enhanced_responses = 0

        logger.info("ResponseValidator initialized (PHASE 3)")

    def validate_completeness(
        self,
        question: str,
        answer: str,
        threshold: float = 0.7
    ) -> Dict:
        """
        Validate if answer completely addresses the question.

        PHASE 3: Core validation logic.

        Args:
            question: Original user question
            answer: Generated answer to validate
            threshold: Completeness threshold (0-1). Below threshold = incomplete.

        Returns:
            {
                "is_complete": bool,
                "completeness_score": float (0-1),
                "missing_aspects": List[str],
                "confidence": float
            }
        """
        self.total_validations += 1

        logger.info(f"Validating response completeness (threshold={threshold})")

        # Build validation prompt
        validation_prompt = self._build_validation_prompt(question, answer)

        try:
            # Call LLM for validation
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )

            validation_text = response.choices[0].message.content.strip()

            # Calculate cost
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = (input_tokens * 0.150 / 1_000_000) + (output_tokens * 0.600 / 1_000_000)

            # Parse validation response
            parsed = self._parse_validation_response(validation_text)

            is_complete = parsed["completeness_score"] >= threshold

            if not is_complete:
                self.incomplete_responses += 1
                logger.warning(
                    f"Response incomplete: score={parsed['completeness_score']:.2f}, "
                    f"missing={len(parsed['missing_aspects'])} aspects"
                )
            else:
                logger.info(f"Response complete: score={parsed['completeness_score']:.2f}")

            return {
                "is_complete": is_complete,
                "completeness_score": parsed["completeness_score"],
                "missing_aspects": parsed["missing_aspects"],
                "confidence": parsed.get("confidence", 0.8),
                "validation_cost": cost
            }

        except Exception as e:
            logger.error(f"Validation error: {e}")
            # Fallback: assume complete if validation fails
            return {
                "is_complete": True,
                "completeness_score": 1.0,
                "missing_aspects": [],
                "confidence": 0.5,
                "validation_cost": 0.0,
                "error": str(e)
            }

    def _build_validation_prompt(self, question: str, answer: str) -> str:
        """Build prompt for completeness validation."""
        return f"""Evalúa si la siguiente respuesta responde COMPLETAMENTE a la pregunta del usuario.

**Pregunta del usuario:**
{question}

**Respuesta generada:**
{answer}

**Tu tarea:**
1. Identifica TODOS los aspectos/sub-preguntas en la pregunta original
2. Verifica si cada aspecto fue respondido en la respuesta
3. Asigna un puntaje de completitud (0.0 a 1.0)
4. Lista los aspectos NO respondidos (si existen)

**Formato de respuesta (JSON):**
{{
  "completeness_score": 0.85,
  "missing_aspects": ["aspecto 1 no respondido", "aspecto 2 no respondido"],
  "confidence": 0.9
}}

**Criterios de puntaje:**
- 1.0 = Respuesta completamente satisfactoria
- 0.7-0.9 = Respuesta mayormente completa, falta información menor
- 0.4-0.6 = Respuesta parcial, falta información significativa
- 0.0-0.3 = Respuesta muy incompleta o no responde la pregunta

**Nota:** Si la respuesta dice "No encontré información" pero realmente NO HAY información disponible, puntuar 1.0 (es una respuesta honesta y completa).

Responde SOLO con el JSON, sin explicaciones adicionales."""

    def _parse_validation_response(self, validation_text: str) -> Dict:
        """
        Parse LLM validation response.

        Args:
            validation_text: Raw LLM response

        Returns:
            Parsed validation data
        """
        import json
        import re

        # Try to extract JSON
        json_match = re.search(r'\{[^}]+\}', validation_text, re.DOTALL)

        if json_match:
            try:
                parsed = json.loads(json_match.group())

                return {
                    "completeness_score": float(parsed.get("completeness_score", 0.5)),
                    "missing_aspects": parsed.get("missing_aspects", []),
                    "confidence": float(parsed.get("confidence", 0.8))
                }
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse validation JSON: {e}")

        # Fallback parsing
        score_match = re.search(r'"?completeness_score"?\s*:\s*([0-9.]+)', validation_text)

        if score_match:
            score = float(score_match.group(1))
        else:
            # Heuristic fallback
            if "no encontré" in validation_text.lower() or "no hay información" in validation_text.lower():
                score = 1.0  # Honest answer is complete
            else:
                score = 0.7  # Assume mostly complete

        return {
            "completeness_score": score,
            "missing_aspects": [],
            "confidence": 0.6
        }

    def generate_retry_queries(
        self,
        original_question: str,
        missing_aspects: List[str],
        max_retries: int = 3
    ) -> List[str]:
        """
        Generate targeted retry queries for missing information.

        PHASE 3: Automatic query reformulation.

        Args:
            original_question: Original user question
            missing_aspects: List of missing information aspects
            max_retries: Maximum number of retry queries

        Returns:
            List of reformulated queries to retrieve missing information
        """
        if not missing_aspects:
            return []

        logger.info(f"Generating retry queries for {len(missing_aspects)} missing aspects")

        # Limit to max_retries
        aspects_to_address = missing_aspects[:max_retries]

        retry_queries = []

        for aspect in aspects_to_address:
            # Simple reformulation: convert aspect to direct question
            if "?" in aspect:
                retry_query = aspect
            else:
                retry_query = f"¿{aspect}?"

            retry_queries.append(retry_query)
            logger.debug(f"Retry query: {retry_query}")

        self.retry_attempts += len(retry_queries)

        return retry_queries

    def enhance_incomplete_response(
        self,
        original_question: str,
        original_answer: str,
        missing_aspects: List[str],
        retry_chunks: List[Dict],
        area: str
    ) -> Dict:
        """
        Enhance incomplete response with additional retrieved information.

        PHASE 3: Response enhancement with retry context.

        Args:
            original_question: Original user question
            original_answer: Initial incomplete answer
            missing_aspects: List of missing information aspects
            retry_chunks: Additional chunks retrieved from retry queries
            area: Knowledge area

        Returns:
            {
                "enhanced_answer": str,
                "enhancement_cost": float,
                "chunks_added": int
            }
        """
        if not retry_chunks:
            return {
                "enhanced_answer": original_answer,
                "enhancement_cost": 0.0,
                "chunks_added": 0
            }

        logger.info(f"Enhancing response with {len(retry_chunks)} additional chunks")

        # Build enhancement prompt
        enhancement_prompt = self._build_enhancement_prompt(
            original_question=original_question,
            original_answer=original_answer,
            missing_aspects=missing_aspects,
            retry_chunks=retry_chunks
        )

        try:
            # Generate enhanced answer
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": enhancement_prompt}
                ],
                temperature=0.2,
                max_tokens=800
            )

            enhanced_answer = response.choices[0].message.content.strip()

            # Calculate cost
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = (input_tokens * 0.150 / 1_000_000) + (output_tokens * 0.600 / 1_000_000)

            self.enhanced_responses += 1

            logger.info("Response successfully enhanced")

            return {
                "enhanced_answer": enhanced_answer,
                "enhancement_cost": cost,
                "chunks_added": len(retry_chunks)
            }

        except Exception as e:
            logger.error(f"Enhancement error: {e}")
            return {
                "enhanced_answer": original_answer,
                "enhancement_cost": 0.0,
                "chunks_added": 0,
                "error": str(e)
            }

    def _build_enhancement_prompt(
        self,
        original_question: str,
        original_answer: str,
        missing_aspects: List[str],
        retry_chunks: List[Dict]
    ) -> str:
        """Build prompt for response enhancement."""

        # Format retry chunks
        retry_context = "\n\n".join([
            f"**Fragmento {i+1}:**\n{chunk.get('texto', '')}"
            for i, chunk in enumerate(retry_chunks[:5])  # Limit to 5 chunks
        ])

        missing_list = "\n".join([f"- {aspect}" for aspect in missing_aspects])

        return f"""Mejora la siguiente respuesta incompleta agregando la información faltante.

**Pregunta original:**
{original_question}

**Respuesta inicial (incompleta):**
{original_answer}

**Información faltante identificada:**
{missing_list}

**Contexto adicional recuperado:**
{retry_context}

**Tu tarea:**
1. Conserva TODA la información de la respuesta inicial
2. Agrega la información faltante usando el contexto adicional
3. Integra ambas partes de forma coherente
4. Si el contexto adicional no tiene la información faltante, indica "No se encontró información sobre [aspecto]"

**Formato de respuesta:**
Proporciona una respuesta mejorada y completa que combine la información inicial con el contexto adicional.

Responde de forma clara, concisa y estructurada."""

    def get_stats(self) -> Dict:
        """Get validator statistics."""
        return {
            "total_validations": self.total_validations,
            "incomplete_responses": self.incomplete_responses,
            "incomplete_rate": (
                self.incomplete_responses / self.total_validations
                if self.total_validations > 0 else 0.0
            ),
            "retry_attempts": self.retry_attempts,
            "enhanced_responses": self.enhanced_responses
        }

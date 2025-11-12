"""
HyDE (Hypothetical Document Embeddings) Retriever.

Implements HyDE technique for improved retrieval:
1. Generates hypothetical document that would answer the query
2. Uses doc-to-doc similarity instead of query-to-doc
3. Hybrid search: combines HyDE + original query
4. Fallback: retries with HyDE if initial scores are low

References:
- Paper: "Precise Zero-Shot Dense Retrieval without Relevance Labels" (2022)
- https://arxiv.org/abs/2212.10496
"""
from typing import Dict, List, Optional, Tuple
from loguru import logger
import openai
from src.config import config


class HyDERetriever:
    """
    HyDE-based retrieval with selective activation and fallback.

    Features:
    - Document-type specific prompts (legal, technical, generic)
    - Selective activation based on query type
    - Hybrid search (HyDE + original query with RRF fusion)
    - Automatic fallback for low-score results
    - Extensible to new document types
    """

    def __init__(self):
        """Initialize HyDE retriever."""
        self.client = openai.OpenAI(api_key=config.openai.api_key)
        self.model = "gpt-4o-mini"  # Fast and cheap for doc generation

        # Counters for statistics
        self.total_queries = 0
        self.hyde_used_count = 0
        self.fallback_count = 0
        self.improvement_count = 0

        logger.info("HyDE Retriever initialized")

    # ============================================================
    # PROMPTS BY DOCUMENT TYPE (Extensible)
    # ============================================================

    def _get_prompt_for_document_type(self, documento_tipo: str) -> str:
        """
        Get HyDE prompt template for specific document type.

        Args:
            documento_tipo: Document type (legal, technical, generic)

        Returns:
            Prompt template with {question} placeholder
        """
        prompts = {
            "legal": """Eres un experto en normativa legal colombiana, especialmente en el Sistema General de Regalías (SGR).

Tu tarea: Genera un fragmento de documento legal formal que RESPONDERÍA la siguiente pregunta. NO respondas la pregunta directamente, sino genera el texto tal como aparecería en un documento legal oficial.

Características del texto:
- Estilo formal y técnico legal colombiano
- Usa terminología correcta del SGR (OCAD, viabilización, radicación, etc.)
- 2-3 oraciones concisas
- Declarativo, no interrogativo
- Sin citas ficticias a artículos

Pregunta: {question}

Fragmento de documento legal hipotético:""",

            "technical": """Eres un experto en documentos técnicos de proyectos de inversión en Colombia.

Tu tarea: Genera un fragmento de documento técnico que RESPONDERÍA la siguiente pregunta. NO respondas la pregunta directamente, sino genera el texto tal como aparecería en un documento técnico de proyecto.

Características del texto:
- Estilo técnico formal
- Usa terminología de proyectos (productos esperados, fuentes de financiación, metodología, resultados e impactos)
- 2-3 oraciones concisas
- Declarativo, orientado a descripción de proyecto
- Puede incluir valores/cifras si es relevante

Pregunta: {question}

Fragmento de documento técnico hipotético:""",

            "generic": """Genera un fragmento de documento formal que respondería la siguiente pregunta.

Características:
- Estilo formal y profesional
- 2-3 oraciones concisas
- Declarativo, no interrogativo

Pregunta: {question}

Fragmento de documento hipotético:"""
        }

        return prompts.get(documento_tipo, prompts["generic"])

    def _infer_document_type_from_id(self, documento_id: Optional[str]) -> str:
        """
        Infer document type from documento_id.

        This mapping should be updated when new documents are added.

        Args:
            documento_id: Document ID or None

        Returns:
            Document type: legal, technical, or generic
        """
        if not documento_id:
            return "generic"

        # Current documents mapping
        document_type_map = {
            "acuerdo_unico_comision_rectora_2025_07_15": "legal",
            "acuerdo_03_2021": "legal",
            "documentotecnico_v2": "technical",
        }

        # Check exact match
        if documento_id in document_type_map:
            return document_type_map[documento_id]

        # Fuzzy matching for future documents
        documento_lower = documento_id.lower()
        if any(kw in documento_lower for kw in ["acuerdo", "decreto", "resolucion", "ley"]):
            return "legal"
        if any(kw in documento_lower for kw in ["tecnico", "proyecto", "plan"]):
            return "technical"

        return "generic"

    # ============================================================
    # HYPOTHETICAL DOCUMENT GENERATION
    # ============================================================

    def generate_hypothetical_document(
        self,
        question: str,
        documento_id: Optional[str] = None,
        max_tokens: int = 150
    ) -> Tuple[str, float]:
        """
        Generate hypothetical document that would answer the query.

        Args:
            question: User question
            documento_id: Optional document ID to determine style
            max_tokens: Max tokens for generation

        Returns:
            Tuple of (hypothetical_doc, cost)
        """
        # Infer document type
        doc_type = self._infer_document_type_from_id(documento_id)
        logger.info(f"Generating HyDE document (type: {doc_type})")

        # Get prompt template
        prompt_template = self._get_prompt_for_document_type(doc_type)
        prompt = prompt_template.format(question=question)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3,  # Lower temperature for more focused generation
            )

            hyde_doc = response.choices[0].message.content.strip()

            # Calculate cost
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = (input_tokens * 0.150 / 1_000_000) + (output_tokens * 0.600 / 1_000_000)

            logger.info(f"HyDE doc generated: {hyde_doc[:100]}...")
            logger.info(f"Cost: ${cost:.6f}")

            return hyde_doc, cost

        except Exception as e:
            logger.error(f"Error generating HyDE document: {e}")
            # Fallback: return original question
            return question, 0.0

    # ============================================================
    # DECISION LOGIC: WHEN TO USE HYDE
    # ============================================================

    def should_use_hyde(
        self,
        enhancement: Dict,
        decomposition: Optional[Dict] = None
    ) -> bool:
        """
        Decide whether to use HyDE based on query characteristics.

        HyDE is beneficial for:
        - Simple semantic queries (definitions, explanations)
        - Queries without structural filters
        - Queries with potential terminology mismatch

        HyDE is NOT beneficial for:
        - Structural queries (with capitulo, articulo, etc.)
        - Multihop queries (already decomposed)
        - Queries with specific IDs/numbers

        Args:
            enhancement: Query enhancement metadata
            decomposition: Query decomposition metadata (if multihop)

        Returns:
            True if HyDE should be used
        """
        query_lower = enhancement['original_query'].lower()

        # Rule 1: NO HyDE if structural filters present
        if enhancement.get('filters'):
            logger.debug("HyDE: NO - structural filters detected")
            return False

        # Rule 2: NO HyDE if structural query type
        if enhancement['query_type'] == 'structural':
            logger.debug("HyDE: NO - structural query type")
            return False

        # Rule 3: NO HyDE if multihop query
        if decomposition and decomposition.get('requires_multihop'):
            logger.debug("HyDE: NO - multihop query")
            return False

        # Rule 4: NO HyDE if query contains specific article/section numbers
        if any(pattern in query_lower for pattern in ['artículo', 'articulo', 'art.', 'sección', 'seccion']):
            # Exception: if it's asking ABOUT a section (not filtering)
            if any(kw in query_lower for kw in ['qué dice', 'que dice', 'contenido de', 'explica']):
                pass  # Continue to next rules
            else:
                logger.debug("HyDE: NO - specific article/section reference")
                return False

        # Rule 5: YES HyDE for definition queries
        definition_keywords = ['qué es', 'que es', 'define', 'definición', 'significado', 'concepto']
        if any(kw in query_lower for kw in definition_keywords):
            logger.info("HyDE: YES - definition query")
            return True

        # Rule 6: YES HyDE for procedural queries (how-to)
        procedural_keywords = ['cómo', 'como', 'proceso', 'procedimiento', 'pasos', 'solicitar']
        if any(kw in query_lower for kw in procedural_keywords):
            logger.info("HyDE: YES - procedural query")
            return True

        # Rule 7: YES HyDE for explanation queries
        explanation_keywords = ['explica', 'explicar', 'describe', 'cuáles son', 'cuales son', 'enumera']
        if any(kw in query_lower for kw in explanation_keywords):
            logger.info("HyDE: YES - explanation query")
            return True

        # Rule 8: YES HyDE for simple semantic queries
        if enhancement['query_type'] == 'simple_semantic':
            logger.info("HyDE: YES - simple semantic query")
            return True

        # Default: NO
        logger.debug("HyDE: NO - no matching criteria")
        return False

    # ============================================================
    # HYBRID SEARCH WITH RRF FUSION
    # ============================================================

    def _fuse_results_rrf(
        self,
        results_hyde: List[Dict],
        results_original: List[Dict],
        k: int = 60
    ) -> List[Dict]:
        """
        Fuse results using Reciprocal Rank Fusion (RRF).

        RRF formula: score(d) = sum(1 / (k + rank(d)))

        Args:
            results_hyde: Results from HyDE search
            results_original: Results from original query search
            k: RRF constant (default 60)

        Returns:
            Fused and sorted results
        """
        # Build ranking maps
        hyde_ranks = {chunk['chunk_id']: rank for rank, chunk in enumerate(results_hyde, 1)}
        orig_ranks = {chunk['chunk_id']: rank for rank, chunk in enumerate(results_original, 1)}

        # Get all unique chunks
        all_chunk_ids = set(hyde_ranks.keys()) | set(orig_ranks.keys())

        # Calculate RRF scores
        fused_chunks = {}
        for chunk_id in all_chunk_ids:
            rrf_score = 0.0

            if chunk_id in hyde_ranks:
                rrf_score += 1.0 / (k + hyde_ranks[chunk_id])

            if chunk_id in orig_ranks:
                rrf_score += 1.0 / (k + orig_ranks[chunk_id])

            # Get chunk data (prefer from hyde results, fallback to original)
            chunk = next((c for c in results_hyde if c['chunk_id'] == chunk_id), None)
            if not chunk:
                chunk = next((c for c in results_original if c['chunk_id'] == chunk_id), None)

            if chunk:
                chunk_copy = chunk.copy()
                chunk_copy['rrf_score'] = rrf_score
                chunk_copy['original_score'] = chunk.get('score', 0.0)
                chunk_copy['score'] = rrf_score  # Use RRF as primary score
                chunk_copy['found_by_hyde'] = chunk_id in hyde_ranks
                chunk_copy['found_by_original'] = chunk_id in orig_ranks
                fused_chunks[chunk_id] = chunk_copy

        # Sort by RRF score
        sorted_chunks = sorted(fused_chunks.values(), key=lambda x: x['rrf_score'], reverse=True)

        logger.info(f"Fused {len(sorted_chunks)} unique chunks using RRF")
        return sorted_chunks

    def retrieve_with_hyde_hybrid(
        self,
        vector_search,
        question: str,
        hyde_doc: str,
        enhancement: Dict,
        top_k: int = 30,
        hyde_weight: float = 0.7
    ) -> List[Dict]:
        """
        Perform hybrid retrieval: HyDE search + original query search.

        Args:
            vector_search: VectorSearch instance
            question: Original user question
            hyde_doc: Generated hypothetical document
            enhancement: Query enhancement metadata
            top_k: Total number of chunks to retrieve
            hyde_weight: Weight for HyDE results (0.7 means 70% HyDE, 30% original)

        Returns:
            Fused results
        """
        # Calculate top_k for each search
        hyde_k = int(top_k * hyde_weight)
        orig_k = int(top_k * (1 - hyde_weight))

        # Ensure at least some results from each
        hyde_k = max(hyde_k, 10)
        orig_k = max(orig_k, 5)

        logger.info(f"Hybrid search: HyDE (top_{hyde_k}) + Original (top_{orig_k})")

        # Search with HyDE document
        results_hyde = vector_search.search_with_context(
            query=hyde_doc,
            top_k=hyde_k,
            expand_context=False,  # Don't expand yet
            documento_id=enhancement.get('documento_id'),
        )

        # Search with original query
        results_original = vector_search.search_with_context(
            query=question,
            top_k=orig_k,
            expand_context=False,  # Don't expand yet
            documento_id=enhancement.get('documento_id'),
        )

        # Fuse results with RRF
        fused = self._fuse_results_rrf(results_hyde, results_original)

        # Take top_k
        fused = fused[:top_k]

        logger.info(f"Hybrid retrieval complete: {len(fused)} chunks")
        return fused

    # ============================================================
    # MAIN RETRIEVAL WITH FALLBACK
    # ============================================================

    def retrieve(
        self,
        vector_search,
        question: str,
        enhancement: Dict,
        decomposition: Optional[Dict] = None,
        documento_id: Optional[str] = None,
        top_k: int = 30,
        enable_fallback: bool = True,
        fallback_threshold: float = 0.30
    ) -> Dict:
        """
        Main retrieval method with HyDE selective activation and fallback.

        Strategy:
        1. Decide if HyDE should be used
        2. If YES: Perform hybrid HyDE + original search
        3. If NO: Perform standard search
        4. If results have low scores: Retry with HyDE (fallback)

        Args:
            vector_search: VectorSearch instance
            question: User question
            enhancement: Query enhancement metadata
            decomposition: Optional decomposition (for multihop detection)
            documento_id: Optional document filter
            top_k: Number of chunks to retrieve
            enable_fallback: Whether to enable HyDE fallback for low scores
            fallback_threshold: Avg score threshold for fallback

        Returns:
            Dictionary with chunks, metadata, and costs
        """
        self.total_queries += 1

        # Store documento_id in enhancement for later use
        enhancement['documento_id'] = documento_id

        # STEP 1: Decide if HyDE should be used
        use_hyde = self.should_use_hyde(enhancement, decomposition)

        hyde_doc = None
        hyde_cost = 0.0
        hyde_used = False
        fallback_used = False

        if use_hyde:
            # STEP 2A: Generate hypothetical document
            hyde_doc, hyde_cost = self.generate_hypothetical_document(
                question, documento_id
            )

            # STEP 2B: Hybrid search
            chunks = self.retrieve_with_hyde_hybrid(
                vector_search=vector_search,
                question=question,
                hyde_doc=hyde_doc,
                enhancement=enhancement,
                top_k=top_k
            )

            hyde_used = True
            self.hyde_used_count += 1

        else:
            # STEP 3: Standard search
            logger.info("Standard retrieval (no HyDE)")
            chunks = vector_search.search_with_context(
                query=question,
                top_k=top_k,
                expand_context=False,
                documento_id=documento_id,
                # Apply detected filters
                capitulo=enhancement['filters'].get('capitulo'),
                titulo=enhancement['filters'].get('titulo'),
                articulo=enhancement['filters'].get('articulo'),
                seccion=enhancement['filters'].get('seccion'),
                subseccion=enhancement['filters'].get('subseccion'),
                anexo_numero=enhancement['filters'].get('anexo_numero'),
            )

        # STEP 4: Fallback if scores are low
        if enable_fallback and not hyde_used and chunks:
            avg_score = sum(c.get('score', 0) for c in chunks) / len(chunks)

            if avg_score < fallback_threshold:
                logger.warning(f"Low avg score detected: {avg_score:.3f} < {fallback_threshold}")
                logger.info("Activating HyDE fallback...")

                # Generate HyDE doc
                hyde_doc, hyde_cost = self.generate_hypothetical_document(
                    question, documento_id
                )

                # Retry with HyDE
                chunks_hyde = self.retrieve_with_hyde_hybrid(
                    vector_search=vector_search,
                    question=question,
                    hyde_doc=hyde_doc,
                    enhancement=enhancement,
                    top_k=top_k
                )

                # Compare scores
                avg_score_hyde = sum(c.get('score', 0) for c in chunks_hyde) / len(chunks_hyde)

                improvement = (avg_score_hyde - avg_score) / avg_score if avg_score > 0 else 0

                if avg_score_hyde > avg_score * 1.2:  # 20% improvement threshold
                    logger.info(f"HyDE fallback improved scores: {avg_score:.3f} → {avg_score_hyde:.3f} (+{improvement:.1%})")
                    chunks = chunks_hyde
                    hyde_used = True
                    fallback_used = True
                    self.fallback_count += 1
                    self.improvement_count += 1
                else:
                    logger.info(f"HyDE fallback did not improve: {avg_score:.3f} vs {avg_score_hyde:.3f}")

        return {
            'chunks': chunks,
            'hyde_used': hyde_used,
            'fallback_used': fallback_used,
            'hyde_doc': hyde_doc,
            'hyde_cost': hyde_cost,
            'avg_score': sum(c.get('score', 0) for c in chunks) / len(chunks) if chunks else 0.0,
        }

    def get_stats(self) -> Dict:
        """
        Get HyDE usage statistics.

        Returns:
            Statistics dictionary
        """
        if self.total_queries == 0:
            return {
                'total_queries': 0,
                'hyde_usage_rate': 0.0,
                'fallback_rate': 0.0,
                'improvement_rate': 0.0,
            }

        return {
            'total_queries': self.total_queries,
            'hyde_used': self.hyde_used_count,
            'hyde_usage_rate': self.hyde_used_count / self.total_queries,
            'fallback_triggered': self.fallback_count,
            'fallback_rate': self.fallback_count / self.total_queries,
            'fallback_improved': self.improvement_count,
            'improvement_rate': self.improvement_count / self.fallback_count if self.fallback_count > 0 else 0.0,
        }

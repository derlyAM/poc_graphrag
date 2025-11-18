"""
RAG Pipeline module.
Orchestrates the complete RAG flow: retrieval → re-ranking → generation → citation.
"""
import time
from typing import Dict, Optional, List
from loguru import logger

from src.retrieval.vector_search import VectorSearch
from src.retrieval.reranker import Reranker
from src.retrieval.query_enhancer import QueryEnhancer
from src.retrieval.query_decomposer import QueryDecomposer
from src.retrieval.multihop_retriever import MultihopRetriever
from src.retrieval.hyde_retriever import HyDERetriever
from src.retrieval.response_validator import ResponseValidator
from src.generation.llm_client import LLMClient
from src.generation.citation_manager import CitationManager
from src.config import config, validate_area, get_area_display_name


class RAGPipeline:
    """Complete RAG pipeline for document Q&A."""

    def __init__(self):
        """Initialize pipeline components."""
        logger.info("Initializing RAG Pipeline")

        self.vector_search = VectorSearch()
        self.reranker = Reranker()
        self.query_enhancer = QueryEnhancer()
        self.query_decomposer = QueryDecomposer()
        self.multihop_retriever = MultihopRetriever(
            vector_search=self.vector_search,
            query_enhancer=self.query_enhancer
        )
        self.hyde_retriever = HyDERetriever()
        self.llm_client = LLMClient()
        self.citation_manager = CitationManager()
        self.response_validator = ResponseValidator()

        logger.info("Pipeline initialized successfully (with PHASE 3 post-processing)")

    def query(
        self,
        question: str,
        area: str,
        documento_ids: Optional[List[str]] = None,
        documento_id: Optional[str] = None,
        top_k_retrieval: Optional[int] = None,
        top_k_rerank: Optional[int] = None,
        expand_context: bool = True,
        enable_multihop: bool = True,
        enable_hyde: bool = True,
        enable_validation: bool = True,
    ) -> Dict:
        """
        Process a query through the complete RAG pipeline.

        Args:
            question: User question
            area: Knowledge area to search in (REQUIRED) - 'sgr', 'inteligencia_artificial', 'general'
            documento_ids: Optional list of document IDs to filter (None = all documents in area)
            documento_id: [DEPRECATED] Optional filter by single document
            top_k_retrieval: Number of chunks to retrieve (default from config)
            top_k_rerank: Number of chunks after re-ranking (default from config)
            expand_context: Whether to expand context with adjacent chunks
            enable_multihop: Whether to enable multihop retrieval for complex queries
            enable_hyde: Whether to enable HyDE (Hypothetical Document Embeddings)
            enable_validation: Whether to enable response validation and auto-retry (PHASE 3)

        Returns:
            Complete results dictionary
        """
        start_time = time.time()

        # Validate area (raises ValueError if invalid)
        area = validate_area(area)
        area_display = get_area_display_name(area)

        logger.info(f"\n{'='*60}")
        logger.info(f"ÁREA: {area_display} ({area})")
        logger.info(f"QUERY: {question}")
        logger.info(f"{'='*60}")

        # Use config defaults if not specified
        if top_k_retrieval is None:
            top_k_retrieval = config.retrieval.top_k_retrieval
        if top_k_rerank is None:
            top_k_rerank = config.retrieval.top_k_rerank

        try:
            # STEP 0A: Query Decomposition (if multihop enabled)
            decomposition = None
            if enable_multihop:
                logger.info("\n[STEP 0A/7] Query Decomposition & Complexity Analysis")
                decomposition = self.query_decomposer.analyze_and_decompose(
                    question, documento_id
                )
                logger.info(f"Complexity: {decomposition['complexity']}")
                logger.info(f"Requires multihop: {decomposition['requires_multihop']}")
                logger.info(f"Query type: {decomposition['query_type']}")

            # STEP 0B: Query Enhancement
            logger.info("\n[STEP 0B/7] Query Enhancement")
            enhancement = self.query_enhancer.enhance_query(question, documento_id)

            logger.info(f"Query type: {enhancement['query_type']}")
            if enhancement['filters']:
                logger.info(f"Detected filters: {enhancement['filters']}")

            # Get optimized retrieval config
            # PHASE 2.5: Pass documento_ids and area for adaptive top-k
            retrieval_config = self.query_enhancer.get_retrieval_config(
                enhancement,
                default_top_k=top_k_retrieval,
                documento_ids=documento_ids,
                area=area
            )

            # Use enhanced query for semantic search (if hybrid/semantic)
            search_query = enhancement.get('enhanced_query', question)

            # STEP 1: Retrieval (Vector Search or Multihop)
            search_start = time.time()
            multihop_used = False
            multihop_stats = None
            hyde_result = None  # Initialize hyde_result for all paths

            # EXCEPTION: Numerical/financing queries should use HyDE instead of multihop
            # HyDE Mejorado with numerical templates is more effective for these queries
            numerical_keywords = ['cuánto', 'cuanto', 'costo', 'monto', 'valor', 'precio',
                                 'plazo', 'presupuesto', 'financiación', 'financiacion',
                                 'inversión', 'inversion', 'recurso']
            is_numerical_query = any(kw in question.lower() for kw in numerical_keywords)

            if is_numerical_query and decomposition and decomposition['requires_multihop']:
                logger.info("[OVERRIDE] Numerical query detected - using HyDE instead of multihop for better precision")

            if enable_multihop and decomposition and decomposition['requires_multihop'] and not is_numerical_query:
                # MULTIHOP RETRIEVAL
                logger.info(f"\n[STEP 1/7] Multihop Retrieval (strategy: {decomposition['search_strategy']})")
                logger.info(f"Executing {len(decomposition['sub_queries'])} sub-queries")

                # Choose specialized retrieval method based on strategy
                if decomposition['search_strategy'] == 'multihop_comparison':
                    retrieval_result = self.multihop_retriever.retrieve_comparison(
                        original_query=question,
                        sub_queries=decomposition['sub_queries'],
                        area=area,
                        documento_ids=documento_ids,
                        documento_id=documento_id,
                        top_k_per_side=15,
                    )
                elif decomposition['search_strategy'] == 'multihop_conditional':
                    retrieval_result = self.multihop_retriever.retrieve_conditional(
                        original_query=question,
                        sub_queries=decomposition['sub_queries'],
                        area=area,
                        documento_ids=documento_ids,
                        documento_id=documento_id,
                    )
                else:
                    # Standard multihop
                    retrieval_result = self.multihop_retriever.retrieve_multihop(
                        original_query=question,
                        sub_queries=decomposition['sub_queries'],
                        search_strategy=decomposition['search_strategy'],
                        area=area,
                        documento_ids=documento_ids,
                        documento_id=documento_id,
                        top_k_per_query=15,
                        max_total_chunks=50,
                    )

                chunks = retrieval_result['chunks']
                multihop_used = True
                multihop_stats = self.multihop_retriever.get_retrieval_stats(retrieval_result)

                logger.info(f"Multihop retrieval complete: {len(chunks)} unique chunks")
                logger.info(f"Stats: {multihop_stats}")

            else:
                # STANDARD SINGLE-HOP RETRIEVAL (with optional HyDE)
                if enable_hyde:
                    # STEP 1: HyDE-enhanced Retrieval
                    logger.info(f"\n[STEP 1/7] HyDE-Enhanced Retrieval (strategy: {enhancement['retrieval_strategy']})")

                    hyde_result = self.hyde_retriever.retrieve(
                        vector_search=self.vector_search,
                        question=question,
                        area=area,
                        enhancement=enhancement,
                        decomposition=decomposition,
                        documento_ids=documento_ids,
                        documento_id=documento_id,
                        top_k=retrieval_config['top_k'],
                        enable_fallback=True,
                        fallback_threshold=0.30,
                    )

                    chunks = hyde_result['chunks']
                    logger.info(f"Retrieved {len(chunks)} chunks (HyDE used: {hyde_result['hyde_used']})")
                    if hyde_result['fallback_used']:
                        logger.info("HyDE fallback was activated")

                else:
                    # Standard vector search without HyDE
                    logger.info(f"\n[STEP 1/7] Vector Search (strategy: {enhancement['retrieval_strategy']})")

                    chunks = self.vector_search.search_with_context(
                        query=search_query,
                        area=area,
                        top_k=retrieval_config['top_k'],
                        expand_context=retrieval_config['expand_context'],
                        context_window=retrieval_config.get('context_window', 1),  # PHASE 2
                        documento_ids=documento_ids,
                        documento_id=documento_id,
                        capitulo=enhancement['filters'].get('capitulo'),
                        titulo=enhancement['filters'].get('titulo'),
                        articulo=enhancement['filters'].get('articulo'),
                        seccion=enhancement['filters'].get('seccion'),
                        subseccion=enhancement['filters'].get('subseccion'),
                        anexo_numero=enhancement['filters'].get('anexo_numero'),
                    )

                    logger.info(f"Retrieved {len(chunks)} chunks")

            search_time = time.time() - search_start
            logger.info(f"Retrieval completed in {search_time:.2f}s")

            if not chunks:
                return self._create_no_results_response(question, start_time, enhancement)

            # STEP 2: Re-ranking
            logger.info("\n[STEP 2/7] Re-ranking")
            rerank_start = time.time()

            # For structural queries, use more chunks in final result
            final_top_k = top_k_rerank
            if enhancement['retrieval_strategy'] == 'exhaustive':
                final_top_k = min(15, len(chunks))  # Use up to 15 chunks for summaries
                logger.info(f"Using expanded top_k={final_top_k} for structural query")

            reranked_chunks = self.reranker.rerank(
                query=question, chunks=chunks, top_k=final_top_k
            )

            rerank_time = time.time() - rerank_start
            logger.info(
                f"Re-ranked to {len(reranked_chunks)} chunks in {rerank_time:.2f}s"
            )

            # STEP 3: Generate Answer
            logger.info("\n[STEP 3/7] Generating Answer")
            generation_start = time.time()

            # Pass enhancement and decomposition info to LLM for better context
            # Merge both metadata dictionaries
            query_metadata = {**enhancement}
            if decomposition:
                query_metadata.update(decomposition)

            llm_result = self.llm_client.generate_answer(
                query=question,
                context_chunks=reranked_chunks,
                query_metadata=query_metadata,
            )

            generation_time = time.time() - generation_start
            logger.info(f"Answer generated in {generation_time:.2f}s")

            # STEP 4: Validate Citations
            logger.info("\n[STEP 4/7] Validating Citations")
            validation = self.citation_manager.validate_answer(
                llm_result["answer"], reranked_chunks
            )

            # STEP 5: Enhance Answer
            logger.info("\n[STEP 5/7] Enhancing Answer")
            enhanced_answer = self.citation_manager.enhance_answer(
                llm_result["answer"], reranked_chunks, add_references=True
            )

            # PHASE 3: STEP 6 - Response Validation and Auto-Retry
            validation_metadata = {}
            retry_used = False
            validation_cost = 0.0

            if enable_validation:
                logger.info("\n[STEP 6/8] PHASE 3: Validating Response Completeness")

                # Validate initial response
                validation_result = self.response_validator.validate_completeness(
                    question=question,
                    answer=enhanced_answer,
                    threshold=0.7  # Configurable threshold
                )

                validation_metadata = {
                    "is_complete": validation_result["is_complete"],
                    "completeness_score": validation_result["completeness_score"],
                    "missing_aspects": validation_result["missing_aspects"],
                    "confidence": validation_result["confidence"]
                }
                validation_cost += validation_result.get("validation_cost", 0.0)

                logger.info(
                    f"Completeness: {validation_result['completeness_score']:.2f} "
                    f"({'Complete' if validation_result['is_complete'] else 'Incomplete'})"
                )

                # If incomplete, attempt retry with additional retrieval
                if not validation_result["is_complete"] and validation_result["missing_aspects"]:
                    logger.warning(
                        f"Response incomplete. Missing {len(validation_result['missing_aspects'])} aspects. "
                        f"Attempting auto-retry..."
                    )

                    retry_used = True

                    # Generate retry queries
                    retry_queries = self.response_validator.generate_retry_queries(
                        original_question=question,
                        missing_aspects=validation_result["missing_aspects"],
                        max_retries=2  # Limit retries to avoid excessive cost
                    )

                    logger.info(f"Generated {len(retry_queries)} retry queries")

                    # Retrieve additional chunks for missing information
                    retry_chunks = []
                    for retry_query in retry_queries:
                        logger.debug(f"Retry query: {retry_query}")

                        try:
                            retry_results = self.vector_search.search_with_context(
                                query=retry_query,
                                area=area,
                                top_k=5,  # Small number for targeted retrieval
                                expand_context=True,
                                documento_ids=documento_ids,
                                documento_id=documento_id,
                            )
                            retry_chunks.extend(retry_results)
                        except Exception as e:
                            logger.error(f"Retry query failed: {e}")

                    # Deduplicate retry chunks (by chunk_id)
                    seen_ids = {chunk["chunk_id"] for chunk in reranked_chunks}
                    unique_retry_chunks = [
                        chunk for chunk in retry_chunks
                        if chunk["chunk_id"] not in seen_ids
                    ]

                    logger.info(f"Retrieved {len(unique_retry_chunks)} new chunks from retry")

                    if unique_retry_chunks:
                        # Enhance response with additional information
                        enhancement_result = self.response_validator.enhance_incomplete_response(
                            original_question=question,
                            original_answer=enhanced_answer,
                            missing_aspects=validation_result["missing_aspects"],
                            retry_chunks=unique_retry_chunks,
                            area=area
                        )

                        # Update enhanced answer
                        enhanced_answer = enhancement_result["enhanced_answer"]
                        validation_cost += enhancement_result.get("enhancement_cost", 0.0)

                        logger.info(
                            f"Response enhanced with {enhancement_result['chunks_added']} additional chunks"
                        )

                        validation_metadata["retry_used"] = True
                        validation_metadata["retry_chunks_added"] = len(unique_retry_chunks)
                    else:
                        logger.warning("No new chunks retrieved from retry. Using original response.")
                        validation_metadata["retry_used"] = False
            else:
                logger.info("\n[STEP 6/8] Response Validation: Skipped (disabled)")

            # Build complete result
            total_time = time.time() - start_time

            # Extract HyDE metadata (if used)
            hyde_metadata = {}
            total_cost = llm_result["cost"]

            if enable_hyde and hyde_result:
                hyde_metadata = {
                    "hyde_used": hyde_result.get("hyde_used", False),
                    "hyde_fallback_used": hyde_result.get("fallback_used", False),
                    "hyde_doc": hyde_result.get("hyde_doc"),  # For debugging
                    "hyde_avg_score": hyde_result.get("avg_score", 0.0),
                }
                total_cost += hyde_result.get("hyde_cost", 0.0)

            # Add validation cost (PHASE 3)
            total_cost += validation_cost

            result = {
                # Answer
                "answer": enhanced_answer,
                "original_answer": llm_result["answer"],
                # Query
                "query": question,
                "documento_filter": documento_id,  # DEPRECATED
                "documento_ids_filter": documento_ids,  # PHASE 2.5: New filter
                "query_enhancement": enhancement,
                "query_decomposition": decomposition,  # NEW: include decomposition info
                "multihop_used": multihop_used,  # NEW: flag if multihop was used
                "hyde_metadata": hyde_metadata,  # NEW: HyDE information
                "validation_metadata": validation_metadata,  # PHASE 3: Response validation
                # Sources
                "sources": reranked_chunks,
                "num_sources": len(reranked_chunks),
                # Citation validation
                "citation_validation": validation,
                "citation_report": self.citation_manager.generate_citation_report(
                    llm_result["answer"], validation
                ),
                # Metrics
                "metrics": {
                    "total_time": total_time,
                    "search_time": search_time,
                    "rerank_time": rerank_time,
                    "generation_time": generation_time,
                    "chunks_retrieved": len(chunks),
                    "chunks_reranked": len(reranked_chunks),
                    "input_tokens": llm_result["input_tokens"],
                    "output_tokens": llm_result["output_tokens"],
                    "llm_cost": llm_result["cost"],
                    "hyde_cost": hyde_result.get("hyde_cost", 0.0) if hyde_result else 0.0,
                    "validation_cost": validation_cost,  # PHASE 3: Validation cost
                    "total_cost": total_cost,  # NEW: total cost including HyDE + validation
                    "query_type": enhancement["query_type"],
                    "retrieval_strategy": enhancement["retrieval_strategy"],
                    "multihop_enabled": enable_multihop,  # NEW
                    "multihop_used": multihop_used,  # NEW
                    "multihop_stats": multihop_stats,  # NEW: multihop statistics
                    "hyde_enabled": enable_hyde,  # NEW
                    "hyde_used": hyde_metadata.get("hyde_used", False),  # NEW
                    "validation_enabled": enable_validation,  # PHASE 3
                    "validation_retry_used": retry_used,  # PHASE 3
                },
                # Success
                "success": True,
            }

            logger.info(f"\n{'='*60}")
            logger.info(f"PIPELINE COMPLETED in {total_time:.2f}s")
            logger.info(f"Cost: ${total_cost:.6f} (LLM: ${llm_result['cost']:.6f}, HyDE: ${hyde_result.get('hyde_cost', 0.0) if hyde_result else 0.0:.6f})")
            logger.info(f"{'='*60}\n")

            return result

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            logger.exception("Full traceback:")

            return {
                "answer": f"Error procesando la consulta: {str(e)}",
                "query": question,
                "success": False,
                "error": str(e),
                "metrics": {"total_time": time.time() - start_time},
            }

    def _create_no_results_response(
        self, question: str, start_time: float, enhancement: Dict = None
    ) -> Dict:
        """
        Create response when no results are found.

        Args:
            question: User question
            start_time: Query start time
            enhancement: Query enhancement metadata

        Returns:
            Response dictionary
        """
        logger.warning("No results found for query")

        # Customize message based on query type
        if enhancement and enhancement.get('filters'):
            filters_str = ", ".join([f"{k}={v}" for k, v in enhancement['filters'].items()])
            answer = (
                f"No encontré información relevante para '{question}' "
                f"con los filtros detectados ({filters_str}). "
                "Por favor, verifica que el capítulo/título existe en el documento "
                "o intenta reformular tu consulta."
            )
        else:
            answer = (
                "No encontré información relevante en los documentos "
                "para responder tu pregunta. Por favor, intenta reformular "
                "tu consulta o verifica que los documentos apropiados "
                "estén indexados."
            )

        return {
            "answer": answer,
            "query": question,
            "query_enhancement": enhancement,
            "sources": [],
            "num_sources": 0,
            "success": True,
            "metrics": {"total_time": time.time() - start_time},
        }

    def get_stats(self) -> Dict:
        """
        Get pipeline statistics.

        Returns:
            Statistics dictionary
        """
        collection_stats = self.vector_search.get_collection_stats()
        hyde_stats = self.hyde_retriever.get_stats()

        return {
            "collection": collection_stats,
            "llm_total_cost": self.llm_client.get_total_cost(),
            "model": self.llm_client.model,
            "reranker_model": config.retrieval.reranker_model,
            "hyde_stats": hyde_stats,  # NEW: HyDE usage statistics
        }


def query_documents(question: str, documento_id: Optional[str] = None) -> Dict:
    """
    Convenience function for querying documents.

    Args:
        question: User question
        documento_id: Optional document filter

    Returns:
        Query results
    """
    pipeline = RAGPipeline()
    return pipeline.query(question, documento_id=documento_id)

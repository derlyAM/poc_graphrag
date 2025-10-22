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
from src.generation.llm_client import LLMClient
from src.generation.citation_manager import CitationManager
from src.config import config


class RAGPipeline:
    """Complete RAG pipeline for document Q&A."""

    def __init__(self):
        """Initialize pipeline components."""
        logger.info("Initializing RAG Pipeline")

        self.vector_search = VectorSearch()
        self.reranker = Reranker()
        self.query_enhancer = QueryEnhancer()
        self.llm_client = LLMClient()
        self.citation_manager = CitationManager()

        logger.info("Pipeline initialized successfully")

    def query(
        self,
        question: str,
        documento_id: Optional[str] = None,
        top_k_retrieval: Optional[int] = None,
        top_k_rerank: Optional[int] = None,
        expand_context: bool = True,
    ) -> Dict:
        """
        Process a query through the complete RAG pipeline.

        Args:
            question: User question
            documento_id: Optional filter by document
            top_k_retrieval: Number of chunks to retrieve (default from config)
            top_k_rerank: Number of chunks after re-ranking (default from config)
            expand_context: Whether to expand context with adjacent chunks

        Returns:
            Complete results dictionary
        """
        start_time = time.time()

        logger.info(f"\n{'='*60}")
        logger.info(f"QUERY: {question}")
        logger.info(f"{'='*60}")

        # Use config defaults if not specified
        if top_k_retrieval is None:
            top_k_retrieval = config.retrieval.top_k_retrieval
        if top_k_rerank is None:
            top_k_rerank = config.retrieval.top_k_rerank

        try:
            # STEP 0: Query Enhancement
            logger.info("\n[STEP 0/6] Query Enhancement")
            enhancement = self.query_enhancer.enhance_query(question, documento_id)

            logger.info(f"Query type: {enhancement['query_type']}")
            if enhancement['filters']:
                logger.info(f"Detected filters: {enhancement['filters']}")

            # Get optimized retrieval config
            retrieval_config = self.query_enhancer.get_retrieval_config(
                enhancement, default_top_k=top_k_retrieval
            )

            # Use enhanced query for semantic search (if hybrid/semantic)
            search_query = enhancement.get('enhanced_query', question)

            # STEP 1: Vector Search
            logger.info(f"\n[STEP 1/6] Vector Search (strategy: {enhancement['retrieval_strategy']})")
            search_start = time.time()

            chunks = self.vector_search.search_with_context(
                query=search_query,
                top_k=retrieval_config['top_k'],
                expand_context=retrieval_config['expand_context'],
                documento_id=documento_id,
                capitulo=enhancement['filters'].get('capitulo'),
                titulo=enhancement['filters'].get('titulo'),
                articulo=enhancement['filters'].get('articulo'),
                seccion=enhancement['filters'].get('seccion'),
                subseccion=enhancement['filters'].get('subseccion'),
                anexo_numero=enhancement['filters'].get('anexo_numero'),  # NEW
            )

            search_time = time.time() - search_start
            logger.info(f"Retrieved {len(chunks)} chunks in {search_time:.2f}s")

            if not chunks:
                return self._create_no_results_response(question, start_time, enhancement)

            # STEP 2: Re-ranking
            logger.info("\n[STEP 2/6] Re-ranking")
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
            logger.info("\n[STEP 3/6] Generating Answer")
            generation_start = time.time()

            # Pass enhancement info to LLM for better context
            llm_result = self.llm_client.generate_answer(
                query=question,
                context_chunks=reranked_chunks,
                query_metadata=enhancement,  # NEW: pass enhancement metadata
            )

            generation_time = time.time() - generation_start
            logger.info(f"Answer generated in {generation_time:.2f}s")

            # STEP 4: Validate Citations
            logger.info("\n[STEP 4/6] Validating Citations")
            validation = self.citation_manager.validate_answer(
                llm_result["answer"], reranked_chunks
            )

            # STEP 5: Enhance Answer
            logger.info("\n[STEP 5/6] Enhancing Answer")
            enhanced_answer = self.citation_manager.enhance_answer(
                llm_result["answer"], reranked_chunks, add_references=True
            )

            # Build complete result
            total_time = time.time() - start_time

            result = {
                # Answer
                "answer": enhanced_answer,
                "original_answer": llm_result["answer"],
                # Query
                "query": question,
                "documento_filter": documento_id,
                "query_enhancement": enhancement,  # NEW: include enhancement info
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
                    "query_type": enhancement["query_type"],  # NEW
                    "retrieval_strategy": enhancement["retrieval_strategy"],  # NEW
                },
                # Success
                "success": True,
            }

            logger.info(f"\n{'='*60}")
            logger.info(f"PIPELINE COMPLETED in {total_time:.2f}s")
            logger.info(f"Cost: ${llm_result['cost']:.6f}")
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

        return {
            "collection": collection_stats,
            "llm_total_cost": self.llm_client.get_total_cost(),
            "model": self.llm_client.model,
            "reranker_model": config.retrieval.reranker_model,
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

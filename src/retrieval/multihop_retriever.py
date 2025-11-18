"""
Multihop Retriever module.
Executes iterative retrieval for complex queries requiring multiple search rounds.
"""
from typing import Dict, List, Optional, Set
from loguru import logger
from collections import defaultdict

from src.retrieval.vector_search import VectorSearch
from src.retrieval.query_enhancer import QueryEnhancer


class MultihopRetriever:
    """
    Handles multihop retrieval with iterative searches.

    Executes multiple search rounds based on sub-queries,
    deduplicates results, and tracks provenance.
    """

    def __init__(
        self,
        vector_search: Optional[VectorSearch] = None,
        query_enhancer: Optional[QueryEnhancer] = None
    ):
        """
        Initialize multihop retriever.

        Args:
            vector_search: Optional VectorSearch instance
            query_enhancer: Optional QueryEnhancer instance
        """
        self.vector_search = vector_search or VectorSearch()
        self.query_enhancer = query_enhancer or QueryEnhancer()

    def retrieve_multihop(
        self,
        original_query: str,
        sub_queries: List[str],
        search_strategy: str,
        area: str,
        documento_ids: Optional[List[str]] = None,
        documento_id: Optional[str] = None,
        top_k_per_query: int = 15,
        max_total_chunks: int = 50,
    ) -> Dict:
        """
        Execute multihop retrieval with multiple search rounds.

        Args:
            original_query: Original user query
            sub_queries: List of sub-queries to execute
            search_strategy: Search strategy name
            area: Knowledge area to search in (REQUIRED)
            documento_ids: Optional list of document IDs to filter (PHASE 2.5)
            documento_id: [DEPRECATED] Optional single document filter
            top_k_per_query: Chunks to retrieve per sub-query
            max_total_chunks: Maximum total chunks to return

        Returns:
            Dictionary with retrieved chunks and metadata
        """
        logger.info(f"Starting multihop retrieval with {len(sub_queries)} sub-queries")
        logger.info(f"Strategy: {search_strategy}, top-k per query: {top_k_per_query}")

        all_chunks = []
        chunk_provenance = {}  # Maps chunk_id → list of sub-queries that found it
        seen_chunk_ids: Set[str] = set()

        # Execute each sub-query
        for i, sub_query in enumerate(sub_queries, 1):
            logger.info(f"\n[Round {i}/{len(sub_queries)}] Sub-query: '{sub_query}'")

            # Enhance sub-query
            enhancement = self.query_enhancer.enhance_query(sub_query, documento_id)

            # Get retrieval config
            retrieval_config = self.query_enhancer.get_retrieval_config(
                enhancement, default_top_k=top_k_per_query
            )

            # Execute search
            try:
                chunks = self.vector_search.search_with_context(
                    query=sub_query,
                    area=area,
                    top_k=retrieval_config['top_k'],
                    expand_context=retrieval_config['expand_context'],
                    documento_ids=documento_ids,  # PHASE 2.5
                    documento_id=documento_id,
                    capitulo=enhancement['filters'].get('capitulo'),
                    titulo=enhancement['filters'].get('titulo'),
                    articulo=enhancement['filters'].get('articulo'),
                    seccion=enhancement['filters'].get('seccion'),
                    subseccion=enhancement['filters'].get('subseccion'),
                    anexo_numero=enhancement['filters'].get('anexo_numero'),
                )

                logger.info(f"Retrieved {len(chunks)} chunks for sub-query {i}")

                # Track provenance and deduplicate
                new_chunks = 0
                for chunk in chunks:
                    chunk_id = chunk.get('chunk_id')

                    if chunk_id not in seen_chunk_ids:
                        # New chunk
                        seen_chunk_ids.add(chunk_id)
                        chunk['sub_query_source'] = [sub_query]
                        chunk['retrieval_round'] = i
                        all_chunks.append(chunk)
                        chunk_provenance[chunk_id] = [sub_query]
                        new_chunks += 1
                    else:
                        # Duplicate - track that it was found by multiple sub-queries
                        chunk_provenance[chunk_id].append(sub_query)
                        # Update the chunk in all_chunks to increase its importance score
                        for existing_chunk in all_chunks:
                            if existing_chunk.get('chunk_id') == chunk_id:
                                # Boost score for chunks found by multiple sub-queries
                                existing_chunk['score'] = max(
                                    existing_chunk.get('score', 0),
                                    chunk.get('score', 0)
                                )
                                # Track all sub-queries that found this chunk
                                if 'sub_query_source' not in existing_chunk:
                                    existing_chunk['sub_query_source'] = []
                                existing_chunk['sub_query_source'].append(sub_query)
                                break

                logger.info(f"  → {new_chunks} new chunks, {len(chunks) - new_chunks} duplicates")

            except Exception as e:
                logger.error(f"Error retrieving for sub-query {i}: {e}")
                continue

        # Apply fusion scoring
        logger.info("\nApplying fusion scoring...")
        all_chunks = self._apply_fusion_scoring(all_chunks, chunk_provenance, len(sub_queries))

        # Sort by fused score
        all_chunks.sort(key=lambda x: x.get('fused_score', x.get('score', 0)), reverse=True)

        # Limit total chunks
        if len(all_chunks) > max_total_chunks:
            logger.info(f"Limiting from {len(all_chunks)} to {max_total_chunks} chunks")
            all_chunks = all_chunks[:max_total_chunks]

        logger.info(f"\nMultihop retrieval complete: {len(all_chunks)} unique chunks")

        return {
            "chunks": all_chunks,
            "num_chunks": len(all_chunks),
            "num_sub_queries": len(sub_queries),
            "chunk_provenance": chunk_provenance,
            "search_strategy": search_strategy,
        }

    def _apply_fusion_scoring(
        self,
        chunks: List[Dict],
        provenance: Dict[str, List[str]],
        total_sub_queries: int
    ) -> List[Dict]:
        """
        Apply fusion scoring to boost chunks found by multiple sub-queries.

        Uses a variant of Reciprocal Rank Fusion (RRF) to combine scores.

        Args:
            chunks: List of chunks
            provenance: Chunk provenance mapping
            total_sub_queries: Total number of sub-queries

        Returns:
            Chunks with fused scores
        """
        for chunk in chunks:
            chunk_id = chunk.get('chunk_id')
            original_score = chunk.get('score', 0.0)

            # Count how many sub-queries found this chunk
            num_sources = len(provenance.get(chunk_id, []))

            # Boost factor: chunks found by multiple sub-queries are more relevant
            # 1 source: 1.0x, 2 sources: 1.3x, 3+ sources: 1.5x
            if num_sources == 1:
                boost_factor = 1.0
            elif num_sources == 2:
                boost_factor = 1.3
            else:  # 3+
                boost_factor = 1.5

            # Apply boost
            fused_score = original_score * boost_factor

            chunk['fused_score'] = fused_score
            chunk['num_sub_query_sources'] = num_sources
            chunk['boost_factor'] = boost_factor

        return chunks

    def retrieve_comparison(
        self,
        original_query: str,
        sub_queries: List[str],
        area: str,
        documento_ids: Optional[List[str]] = None,
        documento_id: Optional[str] = None,
        top_k_per_side: int = 10,
    ) -> Dict:
        """
        Specialized retrieval for comparison queries.

        Ensures balanced retrieval from both sides of comparison.

        Args:
            original_query: Original user query
            sub_queries: Sub-queries (should be 2+ for comparison)
            area: Knowledge area to search in (REQUIRED)
            documento_ids: Optional list of document IDs to filter (PHASE 2.5)
            documento_id: [DEPRECATED] Optional single document filter
            top_k_per_side: Chunks to retrieve per comparison side

        Returns:
            Retrieval results
        """
        logger.info("Using specialized comparison retrieval")

        if len(sub_queries) < 2:
            logger.warning("Comparison query has less than 2 sub-queries. Falling back to standard multihop.")
            return self.retrieve_multihop(
                original_query, sub_queries, "multihop_comparison",
                area=area, documento_ids=documento_ids, documento_id=documento_id, top_k_per_query=top_k_per_side
            )

        # For comparisons, we want balanced results from each side
        # Use higher max_total_chunks to preserve both sides
        max_total = top_k_per_side * len(sub_queries)

        return self.retrieve_multihop(
            original_query=original_query,
            sub_queries=sub_queries,
            search_strategy="multihop_comparison",
            area=area,
            documento_ids=documento_ids,  # PHASE 2.5
            documento_id=documento_id,
            top_k_per_query=top_k_per_side,
            max_total_chunks=max_total,
        )

    def retrieve_conditional(
        self,
        original_query: str,
        sub_queries: List[str],
        area: str,
        documento_ids: Optional[List[str]] = None,
        documento_id: Optional[str] = None,
    ) -> Dict:
        """
        Specialized retrieval for conditional queries (if-then).

        Args:
            original_query: Original user query
            sub_queries: Sub-queries for condition and consequence
            area: Knowledge area to search in (REQUIRED)
            documento_ids: Optional list of document IDs to filter (PHASE 2.5)
            documento_id: [DEPRECATED] Optional single document filter

        Returns:
            Retrieval results
        """
        logger.info("Using specialized conditional retrieval")

        # For conditional queries, first sub-queries are more important
        # (they establish the condition)
        return self.retrieve_multihop(
            original_query=original_query,
            sub_queries=sub_queries,
            search_strategy="multihop_conditional",
            area=area,
            documento_ids=documento_ids,  # PHASE 2.5
            documento_id=documento_id,
            top_k_per_query=15,
            max_total_chunks=40,
        )

    def get_retrieval_stats(self, result: Dict) -> Dict:
        """
        Get statistics about multihop retrieval.

        Args:
            result: Retrieval result from retrieve_multihop

        Returns:
            Statistics dictionary
        """
        chunks = result.get('chunks', [])
        provenance = result.get('chunk_provenance', {})

        # Count chunks by number of sources
        source_distribution = defaultdict(int)
        for chunk_id, sources in provenance.items():
            source_distribution[len(sources)] += 1

        # Count chunks by retrieval round
        round_distribution = defaultdict(int)
        for chunk in chunks:
            round_num = chunk.get('retrieval_round', 0)
            round_distribution[round_num] += 1

        return {
            "total_chunks": len(chunks),
            "chunks_by_num_sources": dict(source_distribution),
            "chunks_by_round": dict(round_distribution),
            "avg_score": sum(c.get('fused_score', 0) for c in chunks) / len(chunks) if chunks else 0,
            "top_score": max((c.get('fused_score', 0) for c in chunks), default=0),
        }


def retrieve_multihop_simple(
    query: str,
    sub_queries: List[str],
    documento_id: Optional[str] = None
) -> Dict:
    """
    Convenience function for multihop retrieval.

    Args:
        query: Original query
        sub_queries: Sub-queries to execute
        documento_id: Optional document filter

    Returns:
        Retrieval results
    """
    retriever = MultihopRetriever()
    return retriever.retrieve_multihop(
        original_query=query,
        sub_queries=sub_queries,
        search_strategy="multihop_sequential",
        documento_id=documento_id
    )

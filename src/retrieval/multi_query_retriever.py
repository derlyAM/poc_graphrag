"""
Multi-Query Retrieval module.

PHASE 2 IMPROVEMENT: Generate multiple query variations to improve recall.

Generates multiple reformulations of a query, searches with each one,
and fuses results using Reciprocal Rank Fusion (RRF).
"""
from typing import List, Dict, Optional
from loguru import logger
import re

from src.retrieval.vector_search import VectorSearch
from src.retrieval.reranker import Reranker
from src.generation.llm_client import LLMClient


class MultiQueryRetriever:
    """
    Retrieves documents using multiple query variations for better recall.

    PHASE 2 IMPROVEMENT: Helps find relevant chunks even when the original
    query doesn't match well semantically.

    Example:
        Original: "¿Cuál es el objetivo número 1?"
        Variations:
        - "primer objetivo de la política"
        - "objetivo prioritario establecido"
        - "meta principal número uno"
    """

    def __init__(
        self,
        vector_search: VectorSearch,
        reranker: Reranker,
        llm_client: LLMClient
    ):
        """
        Initialize multi-query retriever.

        Args:
            vector_search: Vector search instance
            reranker: Re-ranker instance
            llm_client: LLM client for generating variations
        """
        self.vector_search = vector_search
        self.reranker = reranker
        self.llm_client = llm_client

    def generate_query_variations(
        self,
        query: str,
        num_variations: int = 3
    ) -> List[str]:
        """
        Generate multiple variations of a query.

        PHASE 2: Uses LLM to reformulate the question in different ways.

        Args:
            query: Original query
            num_variations: Number of variations to generate (default 3)

        Returns:
            List of query variations (including original)
        """
        variations = [query]  # Always include original

        # Generate reformulations using LLM
        prompt = f"""Genera {num_variations} reformulaciones de esta pregunta manteniendo el mismo significado pero usando diferentes palabras y estructuras.

Pregunta original: {query}

Instrucciones:
- Mantén el significado exacto
- Usa sinónimos y estructuras diferentes
- Si hay números, mantenlos (ej: "número 1" → "primer", "1º", "primero")
- Si pregunta por listas, usa variantes ("cuáles son" → "enumera", "lista")
- Responde solo con las reformulaciones, una por línea
- NO incluyas numeración ni viñetas

Reformulaciones:"""

        try:
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Higher temp for more variety
                max_tokens=200,
            )

            reformulations_text = response.choices[0].message.content.strip()

            # Parse reformulations (one per line)
            for line in reformulations_text.split('\n'):
                line = line.strip()
                # Remove numbering if present
                line = re.sub(r'^\d+[\.\)]\s*', '', line)
                line = re.sub(r'^[-•]\s*', '', line)

                if line and line not in variations:
                    variations.append(line)

                if len(variations) >= num_variations + 1:  # +1 for original
                    break

            logger.info(
                f"Generated {len(variations)-1} query variations for: "
                f"'{query[:50]}...'"
            )
            for i, var in enumerate(variations[1:], 1):
                logger.debug(f"  Variation {i}: {var[:60]}...")

        except Exception as e:
            logger.warning(f"Could not generate query variations: {e}")
            logger.info("Falling back to keyword extraction")

            # Fallback: Simple keyword variation
            keywords = self._extract_keywords(query)
            if keywords:
                variations.append(" ".join(keywords))

        return variations[:num_variations + 1]

    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract keywords from query (fallback method).

        Args:
            query: Query text

        Returns:
            List of keywords
        """
        # Remove question words
        stopwords = {
            '¿', '?', 'qué', 'que', 'cuál', 'cual', 'cuáles', 'cuales',
            'cómo', 'como', 'cuándo', 'cuando', 'dónde', 'donde',
            'por qué', 'porque', 'es', 'son', 'está', 'esta',
            'la', 'el', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'de', 'del', 'a', 'al', 'en', 'para', 'por', 'con'
        }

        words = query.lower().split()
        keywords = [w for w in words if w not in stopwords and len(w) > 3]

        return keywords[:5]  # Top 5 keywords

    def retrieve_multi_query(
        self,
        query: str,
        area: str,
        top_k_per_query: int = 10,
        num_variations: int = 3,
        final_top_k: int = None,
        **search_kwargs
    ) -> List[Dict]:
        """
        Retrieve using multiple query variations and fuse results.

        PHASE 2 IMPROVEMENT: Searches with multiple reformulations
        to improve recall, then fuses and re-ranks.

        Args:
            query: Original query
            area: Knowledge area
            top_k_per_query: Number of results per query variation
            num_variations: Number of variations to generate
            final_top_k: Final number of results to return (default: top_k_per_query)
            **search_kwargs: Additional search parameters

        Returns:
            Deduplicated and re-ranked chunks
        """
        if final_top_k is None:
            final_top_k = top_k_per_query

        logger.info(
            f"Multi-query retrieval: {num_variations} variations, "
            f"{top_k_per_query} chunks each → {final_top_k} final"
        )

        # Generate query variations
        variations = self.generate_query_variations(query, num_variations)

        # Search with each variation
        all_chunks = []
        for i, variant_query in enumerate(variations):
            logger.debug(f"Searching with variant {i+1}/{len(variations)}: {variant_query[:50]}...")

            try:
                chunks = self.vector_search.search(
                    query=variant_query,
                    area=area,
                    top_k=top_k_per_query,
                    **search_kwargs
                )

                # Tag chunks with query variant info
                for chunk in chunks:
                    chunk["query_variant"] = i
                    chunk["query_variant_text"] = variant_query
                    all_chunks.append(chunk)

                logger.debug(f"  → Found {len(chunks)} chunks")

            except Exception as e:
                logger.warning(f"Search failed for variant {i+1}: {e}")
                continue

        if not all_chunks:
            logger.warning("No chunks found with any query variation")
            return []

        logger.info(f"Total chunks from all variations: {len(all_chunks)}")

        # Deduplicate and fuse scores
        unique_chunks = self._deduplicate_and_fuse(all_chunks)

        logger.info(f"Unique chunks after deduplication: {len(unique_chunks)}")

        # Re-rank using the ORIGINAL query
        if len(unique_chunks) > final_top_k:
            logger.info(f"Re-ranking {len(unique_chunks)} chunks to top-{final_top_k}")
            reranked = self.reranker.rerank(
                query=query,  # Use original query for re-ranking
                chunks=unique_chunks,
                top_k=final_top_k
            )
            return reranked
        else:
            # Sort by fused score
            unique_chunks.sort(key=lambda x: x.get("score", 0), reverse=True)
            return unique_chunks

    def _deduplicate_and_fuse(self, chunks: List[Dict]) -> List[Dict]:
        """
        Deduplicate chunks and fuse scores from multiple queries.

        PHASE 2: Chunks appearing in multiple query results get
        boosted scores.

        Args:
            chunks: All chunks from all query variations

        Returns:
            Deduplicated chunks with fused scores
        """
        chunk_map = {}  # chunk_id → chunk data

        for chunk in chunks:
            chunk_id = chunk["chunk_id"]

            if chunk_id not in chunk_map:
                # First time seeing this chunk
                chunk_map[chunk_id] = chunk.copy()
                chunk_map[chunk_id]["appearances"] = 1
                chunk_map[chunk_id]["source_scores"] = [chunk["score"]]
                chunk_map[chunk_id]["source_variants"] = [chunk.get("query_variant", 0)]
            else:
                # Chunk seen before - boost score
                chunk_map[chunk_id]["appearances"] += 1
                chunk_map[chunk_id]["source_scores"].append(chunk["score"])
                chunk_map[chunk_id]["source_variants"].append(chunk.get("query_variant", 0))

        # Fuse scores: average score * sqrt(appearances)
        # This boosts chunks that appear in multiple query results
        for chunk_id, chunk in chunk_map.items():
            avg_score = sum(chunk["source_scores"]) / len(chunk["source_scores"])
            boost = chunk["appearances"] ** 0.5  # Square root for diminishing returns
            chunk["score"] = avg_score * boost
            chunk["fusion_boost"] = boost

        return list(chunk_map.values())


def create_multi_query_retriever(
    vector_search: VectorSearch,
    reranker: Reranker,
    llm_client: LLMClient
) -> MultiQueryRetriever:
    """
    Factory function to create a MultiQueryRetriever.

    Args:
        vector_search: Vector search instance
        reranker: Re-ranker instance
        llm_client: LLM client instance

    Returns:
        MultiQueryRetriever instance
    """
    return MultiQueryRetriever(vector_search, reranker, llm_client)

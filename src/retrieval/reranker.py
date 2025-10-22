"""
Re-ranker module.
Re-ranks search results using cross-encoder for improved precision.
"""
from typing import List, Dict
from loguru import logger
from sentence_transformers import CrossEncoder

from src.config import config


class Reranker:
    """Re-ranks search results using cross-encoder model."""

    def __init__(self, model_name: str = None):
        """
        Initialize re-ranker.

        Args:
            model_name: Cross-encoder model name
        """
        if model_name is None:
            model_name = config.retrieval.reranker_model

        logger.info(f"Loading re-ranker model: {model_name}")

        try:
            self.model = CrossEncoder(model_name)
            logger.info("Re-ranker model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading re-ranker model: {e}")
            raise

    def rerank(
        self, query: str, chunks: List[Dict], top_k: int = None
    ) -> List[Dict]:
        """
        Re-rank chunks based on relevance to query.

        Args:
            query: Search query
            chunks: List of chunks from vector search
            top_k: Number of top results to return

        Returns:
            Re-ranked chunks with updated scores
        """
        if not chunks:
            return []

        if top_k is None:
            top_k = config.retrieval.top_k_rerank

        logger.info(f"Re-ranking {len(chunks)} chunks (top-{top_k})")

        # Prepare pairs for cross-encoder
        pairs = [(query, chunk["texto"]) for chunk in chunks]

        # Get scores from cross-encoder
        try:
            scores = self.model.predict(pairs)

            # Add rerank scores to chunks
            for i, chunk in enumerate(chunks):
                chunk["rerank_score"] = float(scores[i])
                chunk["original_score"] = chunk.get("score", 0)

            # Sort by rerank score
            chunks.sort(key=lambda x: x["rerank_score"], reverse=True)

            # Return top-k
            result = chunks[:top_k]

            logger.info(
                f"Re-ranking complete. Top score: {result[0]['rerank_score']:.4f}"
            )

            return result

        except Exception as e:
            logger.error(f"Error during re-ranking: {e}")
            # Fallback: return original chunks
            logger.warning("Returning original results without re-ranking")
            return chunks[:top_k]

    def get_relevance_scores(self, query: str, chunks: List[Dict]) -> List[float]:
        """
        Get relevance scores without modifying chunks.

        Args:
            query: Search query
            chunks: List of chunks

        Returns:
            List of relevance scores
        """
        pairs = [(query, chunk["texto"]) for chunk in chunks]

        try:
            scores = self.model.predict(pairs)
            return [float(score) for score in scores]
        except Exception as e:
            logger.error(f"Error getting relevance scores: {e}")
            return [0.0] * len(chunks)


def rerank_results(
    query: str, chunks: List[Dict], top_k: int = None, model_name: str = None
) -> List[Dict]:
    """
    Convenience function for re-ranking.

    Args:
        query: Search query
        chunks: Chunks to re-rank
        top_k: Number of results to return
        model_name: Optional model name

    Returns:
        Re-ranked chunks
    """
    reranker = Reranker(model_name=model_name)
    return reranker.rerank(query, chunks, top_k=top_k)

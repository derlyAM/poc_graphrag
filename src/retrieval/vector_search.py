"""
Vector Search module.
Implements semantic search in Qdrant with context expansion.
Supports hybrid search (dense + sparse vectors) with RRF fusion.
"""
from typing import List, Dict, Optional, Tuple
from loguru import logger
import openai
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from pathlib import Path

from src.config import config
from src.ingest.bm25_encoder import BM25Encoder


class VectorSearch:
    """Semantic search using Qdrant vector database."""

    def __init__(
        self,
        qdrant_client: Optional[QdrantClient] = None,
        use_hybrid_search: bool = True
    ):
        """
        Initialize vector search.

        Args:
            qdrant_client: Optional pre-initialized Qdrant client
            use_hybrid_search: Whether to use hybrid search (dense + sparse)
        """
        self.openai_client = openai.OpenAI(api_key=config.openai.api_key)
        self.embedding_model = config.openai.embedding_model
        self.use_hybrid_search = use_hybrid_search

        # Load BM25 encoder if hybrid search is enabled
        self.bm25_encoder = None
        if use_hybrid_search:
            vocab_path = Path(config.qdrant.path) / "bm25_vocabulary.json"
            if vocab_path.exists():
                self.bm25_encoder = BM25Encoder()
                self.bm25_encoder.load_vocabulary(str(vocab_path))
                logger.info("BM25 encoder loaded for hybrid search")
            else:
                logger.warning(
                    f"BM25 vocabulary not found at {vocab_path}. "
                    "Hybrid search disabled. Run ingestion first."
                )
                self.use_hybrid_search = False

        # Use provided client or create new one
        if qdrant_client:
            self.qdrant_client = qdrant_client
        else:
            if config.qdrant.use_memory:
                logger.warning("Creating new in-memory Qdrant client - previous data will be lost")
                self.qdrant_client = QdrantClient(":memory:")
            elif config.qdrant.path:
                logger.info(f"Connecting to local Qdrant at {config.qdrant.path}")
                self.qdrant_client = QdrantClient(path=config.qdrant.path)
            else:
                self.qdrant_client = QdrantClient(
                    host=config.qdrant.host, port=config.qdrant.port
                )

        self.collection_name = config.qdrant.collection_name

    def search(
        self,
        query: str,
        top_k: int = None,
        documento_id: Optional[str] = None,
        articulo: Optional[str] = None,
        capitulo: Optional[str] = None,
        titulo: Optional[str] = None,
        seccion: Optional[str] = None,
        subseccion: Optional[str] = None,
        anexo_numero: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search for relevant chunks.

        Args:
            query: Search query
            top_k: Number of results to return
            documento_id: Filter by document ID
            articulo: Filter by article number
            capitulo: Filter by chapter number
            titulo: Filter by title number
            seccion: Filter by section number (technical docs)
            subseccion: Filter by subsection number
            anexo_numero: Filter by anexo number (NEW)

        Returns:
            List of chunks with scores
        """
        if top_k is None:
            top_k = config.retrieval.top_k_retrieval

        logger.info(f"Searching for: '{query[:50]}...' (top-{top_k})")

        # Build filters
        search_filter = self._build_filter(
            documento_id=documento_id,
            articulo=articulo,
            capitulo=capitulo,
            titulo=titulo,
            seccion=seccion,
            subseccion=subseccion,
            anexo_numero=anexo_numero,
        )

        # Decide search strategy
        if self.use_hybrid_search and self.bm25_encoder:
            # Hybrid search: combine dense + sparse with RRF
            logger.debug("Using HYBRID search (dense + sparse with RRF)")
            chunks = self._hybrid_search(query, top_k, search_filter)
        else:
            # Dense-only search
            logger.debug("Using DENSE-only search")
            chunks = self._dense_search(query, top_k, search_filter)

        logger.info(f"Found {len(chunks)} results")
        return chunks

    def search_with_context(
        self,
        query: str,
        top_k: int = None,
        expand_context: bool = True,
        documento_id: Optional[str] = None,
        capitulo: Optional[str] = None,
        titulo: Optional[str] = None,
        articulo: Optional[str] = None,
        seccion: Optional[str] = None,
        subseccion: Optional[str] = None,
        anexo_numero: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search with context expansion (adjacent chunks).

        Args:
            query: Search query
            top_k: Number of initial results
            expand_context: Whether to add adjacent chunks
            documento_id: Filter by document ID
            capitulo: Filter by chapter number
            titulo: Filter by title number
            articulo: Filter by article number
            seccion: Filter by section number
            subseccion: Filter by subsection number
            anexo_numero: Filter by anexo number (NEW)

        Returns:
            List of chunks with expanded context
        """
        # Initial search
        chunks = self.search(
            query,
            top_k=top_k,
            documento_id=documento_id,
            capitulo=capitulo,
            titulo=titulo,
            articulo=articulo,
            seccion=seccion,
            subseccion=subseccion,
            anexo_numero=anexo_numero,
        )

        if not expand_context or not chunks:
            return chunks

        # Expand context
        logger.info("Expanding context with adjacent chunks")
        expanded_chunks = self._expand_context(chunks)

        return expanded_chunks

    def _embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for query.

        Args:
            query: Query text

        Returns:
            Embedding vector
        """
        try:
            # Clean query
            clean_query = query.replace('\x00', '').strip()
            if not clean_query:
                clean_query = "[Empty query]"

            response = self.openai_client.embeddings.create(
                model=self.embedding_model, input=[clean_query]
            )

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise

    def _build_filter(
        self,
        documento_id: Optional[str] = None,
        articulo: Optional[str] = None,
        capitulo: Optional[str] = None,
        titulo: Optional[str] = None,
        seccion: Optional[str] = None,
        subseccion: Optional[str] = None,
        anexo_numero: Optional[str] = None,
    ) -> Optional[Filter]:
        """
        Build Qdrant filter.

        Args:
            documento_id: Filter by document ID
            articulo: Filter by article number
            capitulo: Filter by chapter number
            titulo: Filter by title number
            seccion: Filter by section number
            subseccion: Filter by subsection number
            anexo_numero: Filter by anexo number (NEW)

        Returns:
            Qdrant filter or None
        """
        # Build conditions for regular chunks (articles, chapters, etc.)
        regular_conditions = []

        if articulo:
            regular_conditions.append(
                FieldCondition(key="articulo", match=MatchValue(value=articulo))
            )

        if capitulo:
            regular_conditions.append(
                FieldCondition(key="capitulo", match=MatchValue(value=capitulo))
            )

        if titulo:
            regular_conditions.append(
                FieldCondition(key="titulo", match=MatchValue(value=titulo))
            )

        if seccion:
            regular_conditions.append(
                FieldCondition(key="seccion", match=MatchValue(value=seccion))
            )

        if subseccion:
            regular_conditions.append(
                FieldCondition(key="subseccion", match=MatchValue(value=subseccion))
            )

        # Build condition for anexos
        anexo_condition = None
        if anexo_numero:
            anexo_condition = FieldCondition(
                key="anexo_numero", match=MatchValue(value=anexo_numero)
            )

        # Combine filters intelligently
        must_conditions = []
        should_conditions = []

        # Always filter by document if specified
        if documento_id:
            must_conditions.append(
                FieldCondition(
                    key="documento_id", match=MatchValue(value=documento_id)
                )
            )

        # If we have both regular filters AND anexo filter, use OR (should)
        if regular_conditions and anexo_condition:
            # Case: "¿Qué diferencias hay entre el anexo 6 y el capítulo 3?"
            # Need: (anexo=6) OR (capitulo=3)
            should_conditions.append(Filter(must=regular_conditions))
            should_conditions.append(Filter(must=[anexo_condition]))
            logger.info("Using OR filter for regular chunks + anexos")

        # If only regular filters, use AND (must)
        elif regular_conditions:
            must_conditions.extend(regular_conditions)

        # If only anexo filter, use it
        elif anexo_condition:
            must_conditions.append(anexo_condition)

        # Build final filter
        if should_conditions:
            # Use OR for mutually exclusive filters
            # NOTE: Qdrant's should clause works as OR without min_should_match
            if must_conditions:
                return Filter(must=must_conditions, should=should_conditions)
            else:
                return Filter(should=should_conditions)
        elif must_conditions:
            return Filter(must=must_conditions)

        return None

    def _expand_context(self, chunks: List[Dict]) -> List[Dict]:
        """
        Expand context by retrieving adjacent chunks.

        Args:
            chunks: Initial chunks

        Returns:
            Chunks with adjacent context
        """
        expanded = {}  # Use dict to deduplicate by chunk_id

        for chunk in chunks:
            # Add the chunk itself
            expanded[chunk["chunk_id"]] = chunk

            # Try to get previous chunk
            prev_id = chunk.get("chunk_anterior_id")
            if prev_id and prev_id not in expanded:
                prev_chunk = self._get_chunk_by_id(prev_id)
                if prev_chunk:
                    prev_chunk["score"] = chunk["score"] * 0.8  # Lower score
                    prev_chunk["context_type"] = "anterior"
                    expanded[prev_id] = prev_chunk

            # Try to get next chunk
            next_id = chunk.get("chunk_siguiente_id")
            if next_id and next_id not in expanded:
                next_chunk = self._get_chunk_by_id(next_id)
                if next_chunk:
                    next_chunk["score"] = chunk["score"] * 0.8  # Lower score
                    next_chunk["context_type"] = "siguiente"
                    expanded[next_id] = next_chunk

        result = list(expanded.values())

        # Sort by score
        result.sort(key=lambda x: x.get("score", 0), reverse=True)

        logger.info(f"Expanded from {len(chunks)} to {len(result)} chunks")

        return result

    def _get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """
        Retrieve chunk by chunk_id from Qdrant.

        Args:
            chunk_id: Chunk ID to retrieve

        Returns:
            Chunk dictionary or None
        """
        try:
            # Search by chunk_id in payload
            results = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="chunk_id", match=MatchValue(value=chunk_id)
                        )
                    ]
                ),
                limit=1,
            )

            if results[0]:  # results is tuple (points, next_offset)
                point = results[0][0]
                chunk = dict(point.payload)
                chunk["id"] = point.id
                return chunk

            return None

        except Exception as e:
            logger.warning(f"Could not retrieve chunk {chunk_id}: {e}")
            return None

    def _dense_search(
        self,
        query: str,
        top_k: int,
        search_filter: Optional[Filter]
    ) -> List[Dict]:
        """
        Perform dense-only vector search.

        Args:
            query: Search query
            top_k: Number of results
            search_filter: Qdrant filter

        Returns:
            List of chunks with scores
        """
        query_embedding = self._embed_query(query)

        try:
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=search_filter,
            )

            chunks = []
            for result in results:
                chunk = dict(result.payload)
                chunk["score"] = result.score
                chunk["id"] = result.id
                chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.error(f"Dense search error: {e}")
            raise

    def _hybrid_search(
        self,
        query: str,
        top_k: int,
        search_filter: Optional[Filter]
    ) -> List[Dict]:
        """
        Perform hybrid search (dense + sparse) with RRF fusion.

        Args:
            query: Search query
            top_k: Number of results
            search_filter: Qdrant filter

        Returns:
            List of chunks with RRF-fused scores
        """
        # Get dense results (2x top_k for better fusion)
        dense_query_embedding = self._embed_query(query)

        try:
            dense_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=dense_query_embedding,
                limit=top_k * 2,
                query_filter=search_filter,
            )
        except Exception as e:
            logger.error(f"Dense search failed: {e}")
            dense_results = []

        # Get sparse results (2x top_k for better fusion)
        sparse_query_vector = self.bm25_encoder.encode_query(query)

        try:
            from qdrant_client.models import SparseVector
            sparse_results = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=SparseVector(**sparse_query_vector),
                using="text",
                limit=top_k * 2,
                query_filter=search_filter,
            )
        except Exception as e:
            logger.error(f"Sparse search failed: {e}")
            sparse_results = []

        # Convert results to lists with (id, score)
        dense_list = [(r.id, r.score) for r in dense_results]
        sparse_list = [(r.id, r.score) for r in (sparse_results.points if hasattr(sparse_results, 'points') else [])]

        # Apply RRF fusion
        fused_scores = self._reciprocal_rank_fusion(
            dense_list,
            sparse_list,
            k=60  # RRF constant
        )

        # Get top-k by fused score
        top_ids = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Retrieve full chunks
        chunks = []
        for chunk_id, fused_score in top_ids:
            chunk = self._get_chunk_by_id_numeric(chunk_id)
            if chunk:
                chunk["score"] = fused_score
                chunk["id"] = chunk_id
                chunks.append(chunk)

        logger.debug(f"Hybrid search: {len(dense_list)} dense + {len(sparse_list)} sparse → {len(chunks)} fused")

        return chunks

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Tuple[int, float]],
        sparse_results: List[Tuple[int, float]],
        k: int = 60
    ) -> Dict[int, float]:
        """
        Fuse dense and sparse results using Reciprocal Rank Fusion.

        RRF(d) = Σ 1 / (k + rank(d))

        Args:
            dense_results: List of (id, score) from dense search
            sparse_results: List of (id, score) from sparse search
            k: RRF constant (default 60)

        Returns:
            Dictionary mapping chunk_id → fused_score
        """
        fused_scores = {}

        # Add dense scores
        for rank, (chunk_id, _) in enumerate(dense_results, start=1):
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + 1 / (k + rank)

        # Add sparse scores
        for rank, (chunk_id, _) in enumerate(sparse_results, start=1):
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + 1 / (k + rank)

        return fused_scores

    def _get_chunk_by_id_numeric(self, chunk_id: int) -> Optional[Dict]:
        """
        Retrieve a chunk by its numeric ID.

        Args:
            chunk_id: Numeric chunk ID

        Returns:
            Chunk dictionary or None
        """
        try:
            results = self.qdrant_client.retrieve(
                collection_name=self.collection_name,
                ids=[chunk_id],
            )

            if results:
                return dict(results[0].payload)

            return None

        except Exception as e:
            logger.warning(f"Could not retrieve chunk {chunk_id}: {e}")
            return None

    def get_collection_stats(self) -> Dict:
        """
        Get statistics about the collection.

        Returns:
            Dictionary with stats
        """
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)

            return {
                "name": self.collection_name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}


def search_documents(
    query: str,
    top_k: int = None,
    expand_context: bool = True,
    documento_id: Optional[str] = None,
    qdrant_client: Optional[QdrantClient] = None,
) -> List[Dict]:
    """
    Convenience function for searching documents.

    Args:
        query: Search query
        top_k: Number of results
        expand_context: Whether to expand context
        documento_id: Filter by document
        qdrant_client: Optional Qdrant client

    Returns:
        List of relevant chunks
    """
    searcher = VectorSearch(qdrant_client=qdrant_client)
    return searcher.search_with_context(
        query=query,
        top_k=top_k,
        expand_context=expand_context,
        documento_id=documento_id,
    )

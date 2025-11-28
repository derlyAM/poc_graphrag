"""
Vector Search module.
Implements semantic search in Qdrant with context expansion.
Supports hybrid search (dense + sparse vectors) with RRF fusion.
"""
from typing import List, Dict, Optional, Tuple
from loguru import logger
import openai
import re
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from pathlib import Path

from src.config import config, validate_area
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
            # Use storage_dir if qdrant.path is None (Docker mode)
            if config.qdrant.path:
                vocab_path = Path(config.qdrant.path) / "bm25_vocabulary.json"
            else:
                vocab_path = config.storage_dir / "bm25_vocabulary.json"

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
        area: str,
        top_k: int = None,
        documento_ids: Optional[List[str]] = None,
        documento_id: Optional[str] = None,
        articulo: Optional[str] = None,
        capitulo: Optional[str] = None,
        titulo: Optional[str] = None,
        seccion: Optional[str] = None,
        subseccion: Optional[str] = None,
        anexo_numero: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search for relevant chunks in a specific knowledge area.

        Args:
            query: Search query
            area: Knowledge area to search in (REQUIRED) - 'sgr', 'inteligencia_artificial', 'general'
            top_k: Number of results to return
            documento_ids: Filter by list of document IDs (None = all documents in area)
            documento_id: [DEPRECATED] Filter by single document ID (use documento_ids instead)
            articulo: Filter by article number
            capitulo: Filter by chapter number
            titulo: Filter by title number
            seccion: Filter by section number (technical docs)
            subseccion: Filter by subsection number
            anexo_numero: Filter by anexo number

        Returns:
            List of chunks with scores

        Raises:
            ValueError: If area is invalid
        """
        # Validate area (raises ValueError if invalid)
        area = validate_area(area)

        if top_k is None:
            top_k = config.retrieval.top_k_retrieval

        logger.info(f"[ÁREA:{area}] Searching for: '{query[:50]}...' (top-{top_k})")

        # Build filters (including mandatory area filter)
        search_filter = self._build_filter(
            area=area,
            documento_ids=documento_ids,
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
        area: str,
        top_k: int = None,
        expand_context: bool = True,
        context_window: int = 1,
        documento_ids: Optional[List[str]] = None,
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
            area: Knowledge area to search in (REQUIRED)
            top_k: Number of initial results
            expand_context: Whether to add adjacent chunks
            context_window: Number of chunks to expand before/after each result (PHASE 2 improvement)
                           1 = ±1 chunk (default), 2 = ±2 chunks, etc.
            documento_ids: Filter by list of document IDs (None = all documents)
            documento_id: [DEPRECATED] Filter by single document ID
            capitulo: Filter by chapter number
            titulo: Filter by title number
            articulo: Filter by article number
            seccion: Filter by section number
            subseccion: Filter by subsection number
            anexo_numero: Filter by anexo number

        Returns:
            List of chunks with expanded context
        """
        # Initial search
        chunks = self.search(
            query,
            area=area,
            top_k=top_k,
            documento_ids=documento_ids,
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

        # PHASE 2 IMPROVEMENT: Expand context with configurable window
        # PHASE 2.5 IMPROVEMENT: Respect document boundaries during expansion
        logger.info(f"Expanding context with adjacent chunks (window={context_window})")
        expanded_chunks = self._expand_context(
            chunks,
            context_window=context_window,
            documento_ids=documento_ids
        )

        return expanded_chunks

    def search_with_hierarchy(
        self,
        query: str,
        area: str,
        top_k: int = None,
        include_parent: bool = True,
        include_siblings: bool = False,
        max_siblings: int = 3,
        documento_ids: Optional[List[str]] = None,
        documento_id: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        Search with hierarchical context (parent and sibling chunks).

        PHASE 2 IMPROVEMENT: Include chunks related by document hierarchy.
        PHASE 2.5 IMPROVEMENT: Respect document boundaries for parents/siblings.

        Args:
            query: Search query
            area: Knowledge area (REQUIRED)
            top_k: Number of initial results
            include_parent: Whether to include parent chunks (higher hierarchy level)
            include_siblings: Whether to include sibling chunks (same hierarchy level)
            max_siblings: Maximum number of siblings per chunk (default 3)
            documento_ids: Filter by list of document IDs (None = all documents)
            documento_id: [DEPRECATED] Filter by single document ID
            **kwargs: Additional filters (capitulo, titulo, etc.)

        Returns:
            List of chunks with hierarchical context

        Example:
            # For a question about a specific article, also retrieve:
            # - Parent: The chapter/title containing the article
            # - Siblings: Other articles in the same chapter
        """
        # Initial search
        base_chunks = self.search(
            query=query,
            area=area,
            top_k=top_k,
            documento_ids=documento_ids,
            documento_id=documento_id,
            **kwargs
        )

        if not base_chunks:
            return []

        if not (include_parent or include_siblings):
            return base_chunks

        # Expand with hierarchical context
        logger.info(
            f"Expanding with hierarchy: parent={include_parent}, "
            f"siblings={include_siblings}"
        )

        enriched = {}  # Use dict to deduplicate by chunk_id

        for chunk in base_chunks:
            chunk_id = chunk["chunk_id"]
            chunk_doc_id = chunk.get("documento_id")

            # Add base chunk
            enriched[chunk_id] = chunk

            # Include parent chunk (higher level context)
            # PHASE 2.5: Verify parent is from same document
            if include_parent:
                parent_id = chunk.get("parent_id")
                if parent_id and parent_id not in enriched:
                    parent = self._get_chunk_by_id(parent_id)
                    if parent:
                        # PHASE 2.5: Boundary check - same document
                        parent_doc_id = parent.get("documento_id")
                        if parent_doc_id != chunk_doc_id:
                            logger.debug(
                                f"Skipping parent from different document: "
                                f"{chunk_doc_id} → {parent_doc_id}"
                            )
                            continue

                        # PHASE 2.5: Verify parent is in allowed documents
                        if documento_ids and parent_doc_id not in documento_ids:
                            logger.debug(
                                f"Skipping parent from excluded document: {parent_doc_id}"
                            )
                            continue

                        parent["score"] = chunk["score"] * 0.7  # Lower score
                        parent["hierarchy_relation"] = "parent"
                        parent["related_to"] = chunk_id
                        enriched[parent_id] = parent

            # Include sibling chunks (same hierarchy level)
            # PHASE 2.5: Siblings already filtered by same parent, inherently same document
            if include_siblings:
                parent_id = chunk.get("parent_id")
                if parent_id:
                    siblings = self._get_sibling_chunks(
                        chunk,
                        max_siblings=max_siblings
                    )
                    for i, sibling in enumerate(siblings):
                        sibling_id = sibling["chunk_id"]
                        if sibling_id not in enriched:
                            # Decay score based on position
                            sibling["score"] = chunk["score"] * (0.6 - i * 0.1)
                            sibling["hierarchy_relation"] = "sibling"
                            sibling["related_to"] = chunk_id
                            enriched[sibling_id] = sibling

        result = list(enriched.values())

        # Sort by score
        result.sort(key=lambda x: x.get("score", 0), reverse=True)

        logger.info(f"Hierarchy expansion: {len(base_chunks)} → {len(result)} chunks")

        return result

    def _get_sibling_chunks(
        self,
        chunk: Dict,
        max_siblings: int = 3
    ) -> List[Dict]:
        """
        Get sibling chunks (chunks with the same parent).

        PHASE 2 IMPROVEMENT: Retrieve related chunks at the same hierarchy level.

        Args:
            chunk: Reference chunk
            max_siblings: Maximum number of siblings to return

        Returns:
            List of sibling chunks
        """
        parent_id = chunk.get("parent_id")
        if not parent_id:
            return []

        chunk_id = chunk["chunk_id"]

        try:
            # Search for chunks with the same parent
            results = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="parent_id",
                            match=MatchValue(value=parent_id)
                        )
                    ]
                ),
                limit=max_siblings + 5,  # Get extra to filter out self
            )

            siblings = []
            for point in results[0]:  # results is tuple (points, next_offset)
                sibling = dict(point.payload)
                sibling_id = sibling.get("chunk_id")

                # Skip the chunk itself
                if sibling_id == chunk_id:
                    continue

                sibling["id"] = point.id
                siblings.append(sibling)

                if len(siblings) >= max_siblings:
                    break

            return siblings

        except Exception as e:
            logger.warning(f"Could not retrieve siblings for chunk {chunk_id}: {e}")
            return []

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
        area: str,
        documento_ids: Optional[List[str]] = None,
        documento_id: Optional[str] = None,
        articulo: Optional[str] = None,
        capitulo: Optional[str] = None,
        titulo: Optional[str] = None,
        seccion: Optional[str] = None,
        subseccion: Optional[str] = None,
        anexo_numero: Optional[str] = None,
    ) -> Optional[Filter]:
        """
        Build Qdrant filter with mandatory area filtering.

        PHASE 2.5 IMPROVEMENT: Support filtering by multiple documents with MatchAny.

        Args:
            area: Knowledge area (REQUIRED) - ensures separation between domains
            documento_ids: Filter by list of document IDs (None = all documents in area)
            documento_id: [DEPRECATED] Filter by single document ID
            articulo: Filter by article number
            capitulo: Filter by chapter number
            titulo: Filter by title number
            seccion: Filter by section number
            subseccion: Filter by subsection number
            anexo_numero: Filter by anexo number

        Returns:
            Qdrant filter (always non-None due to mandatory area filter)
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

        # ALWAYS filter by area (MANDATORY for domain separation)
        must_conditions.append(
            FieldCondition(key="area", match=MatchValue(value=area))
        )

        # PHASE 2.5: Filter by documents (list or single)
        if documento_ids:
            # Multiple documents - use MatchAny
            if len(documento_ids) == 1:
                must_conditions.append(
                    FieldCondition(
                        key="documento_id", match=MatchValue(value=documento_ids[0])
                    )
                )
                logger.debug(f"Filtering by single document: {documento_ids[0]}")
            else:
                from qdrant_client.models import MatchAny
                must_conditions.append(
                    FieldCondition(
                        key="documento_id", match=MatchAny(any=documento_ids)
                    )
                )
                logger.debug(f"Filtering by {len(documento_ids)} documents: {documento_ids}")
        elif documento_id:
            # DEPRECATED: Single document (backward compatibility)
            logger.warning(
                "Parameter 'documento_id' is deprecated. Use 'documento_ids' (list) instead."
            )
            must_conditions.append(
                FieldCondition(
                    key="documento_id", match=MatchValue(value=documento_id)
                )
            )
        # If neither specified → search ALL documents in the area

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

    def _expand_context(
        self,
        chunks: List[Dict],
        context_window: int = 1,
        documento_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Expand context by retrieving adjacent chunks.

        PHASE 2 IMPROVEMENT: Supports configurable expansion window.
        PHASE 2.5 IMPROVEMENT: Respect document boundaries - do NOT cross documents.

        Args:
            chunks: Initial chunks
            context_window: Number of chunks to expand before/after (default 1)
                          1 = ±1 chunk, 2 = ±2 chunks, etc.
            documento_ids: List of allowed document IDs (for boundary checking)

        Returns:
            Chunks with adjacent context
        """
        expanded = {}  # Use dict to deduplicate by chunk_id

        for chunk in chunks:
            chunk_doc_id = chunk.get("documento_id")

            # Add the chunk itself
            expanded[chunk["chunk_id"]] = chunk

            # PHASE 2: Expand with configurable window
            # PHASE 2.5: CRITICAL - Stop expansion at document boundaries

            # Expand BEFORE (previous chunks)
            current_id = chunk.get("chunk_anterior_id")
            for i in range(1, context_window + 1):
                if not current_id or current_id in expanded:
                    break

                prev_chunk = self._get_chunk_by_id(current_id)
                if prev_chunk:
                    prev_doc_id = prev_chunk.get("documento_id")

                    # PHASE 2.5: BOUNDARY CHECK - Same document
                    if prev_doc_id != chunk_doc_id:
                        logger.debug(
                            f"Context expansion stopped: crossed document boundary "
                            f"({chunk_doc_id} → {prev_doc_id})"
                        )
                        break  # Stop expansion at document boundary

                    # PHASE 2.5: BOUNDARY CHECK - Allowed documents
                    if documento_ids and prev_doc_id not in documento_ids:
                        logger.debug(
                            f"Context expansion stopped: chunk from excluded document "
                            f"({prev_doc_id})"
                        )
                        break

                    # Safe to add - same document
                    score_decay = 0.8 ** i  # 0.8, 0.64, 0.512, ...
                    prev_chunk["score"] = chunk["score"] * score_decay
                    prev_chunk["context_type"] = f"anterior_{i}"
                    prev_chunk["expansion_distance"] = -i
                    expanded[current_id] = prev_chunk

                    # Move to next previous chunk
                    current_id = prev_chunk.get("chunk_anterior_id")
                else:
                    break

            # Expand AFTER (next chunks)
            current_id = chunk.get("chunk_siguiente_id")
            for i in range(1, context_window + 1):
                if not current_id or current_id in expanded:
                    break

                next_chunk = self._get_chunk_by_id(current_id)
                if next_chunk:
                    next_doc_id = next_chunk.get("documento_id")

                    # PHASE 2.5: BOUNDARY CHECK - Same document
                    if next_doc_id != chunk_doc_id:
                        logger.debug(
                            f"Context expansion stopped: crossed document boundary "
                            f"({chunk_doc_id} → {next_doc_id})"
                        )
                        break  # Stop expansion at document boundary

                    # PHASE 2.5: BOUNDARY CHECK - Allowed documents
                    if documento_ids and next_doc_id not in documento_ids:
                        logger.debug(
                            f"Context expansion stopped: chunk from excluded document "
                            f"({next_doc_id})"
                        )
                        break

                    # Safe to add - same document
                    score_decay = 0.8 ** i  # 0.8, 0.64, 0.512, ...
                    next_chunk["score"] = chunk["score"] * score_decay
                    next_chunk["context_type"] = f"siguiente_{i}"
                    next_chunk["expansion_distance"] = i
                    expanded[current_id] = next_chunk

                    # Move to next following chunk
                    current_id = next_chunk.get("chunk_siguiente_id")
                else:
                    break

        result = list(expanded.values())

        # Sort by score
        result.sort(key=lambda x: x.get("score", 0), reverse=True)

        logger.info(f"Expanded from {len(chunks)} to {len(result)} chunks (window={context_window})")

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
        Dynamically adjusts BM25 vs vector weights based on query characteristics.

        Args:
            query: Search query
            top_k: Number of results
            search_filter: Qdrant filter

        Returns:
            List of chunks with RRF-fused scores
        """
        # PHASE 1 IMPROVEMENT: Detect specific terms to adjust weights
        has_numbers = bool(re.search(r'\d+', query))
        has_quotes = '"' in query
        has_specific_terms = any(term in query.lower() for term in [
            'número', 'artículo', 'sección', 'costo', 'sanción', 'objetivo',
            'artículo', 'capitulo', 'título', 'parágrafo', 'anexo'
        ])

        # Adjust weights based on query type
        if has_numbers or has_quotes or has_specific_terms:
            # Give more weight to BM25 (exact match) for specific queries
            vector_weight = 0.4
            bm25_weight = 0.6
            logger.debug(
                f"Specific query detected (numbers={has_numbers}, quotes={has_quotes}, "
                f"specific_terms={has_specific_terms}). Using BM25 weight={bm25_weight}"
            )
        else:
            # Equal weights for semantic queries
            vector_weight = 0.5
            bm25_weight = 0.5
            logger.debug("Semantic query. Using balanced weights (0.5/0.5)")

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

        # Apply RRF fusion with variable weights
        fused_scores = self._reciprocal_rank_fusion(
            dense_list,
            sparse_list,
            k=60,  # RRF constant
            weights=(vector_weight, bm25_weight)  # PHASE 1: Variable weights
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

        logger.debug(
            f"Hybrid search: {len(dense_list)} dense + {len(sparse_list)} sparse "
            f"→ {len(chunks)} fused (weights: {vector_weight:.1f}/{bm25_weight:.1f})"
        )

        return chunks

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Tuple[int, float]],
        sparse_results: List[Tuple[int, float]],
        k: int = 60,
        weights: Tuple[float, float] = (0.5, 0.5)
    ) -> Dict[int, float]:
        """
        Fuse dense and sparse results using Reciprocal Rank Fusion with variable weights.

        RRF(d) = w_dense * 1/(k + rank_dense(d)) + w_sparse * 1/(k + rank_sparse(d))

        Args:
            dense_results: List of (id, score) from dense search
            sparse_results: List of (id, score) from sparse search
            k: RRF constant (default 60)
            weights: Tuple of (dense_weight, sparse_weight). Default (0.5, 0.5) for equal weights

        Returns:
            Dictionary mapping chunk_id → fused_score
        """
        dense_weight, sparse_weight = weights
        fused_scores = {}

        # Add weighted dense scores
        for rank, (chunk_id, _) in enumerate(dense_results, start=1):
            score = dense_weight * (1 / (k + rank))
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + score

        # Add weighted sparse scores
        for rank, (chunk_id, _) in enumerate(sparse_results, start=1):
            score = sparse_weight * (1 / (k + rank))
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + score

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

            # In Qdrant 1.15.1, vectors_count doesn't exist, use points_count instead
            # points_count represents the number of vectors in the collection
            vectors_count = getattr(collection_info, 'vectors_count', None)
            if vectors_count is None:
                vectors_count = collection_info.points_count

            return {
                "name": self.collection_name,
                "vectors_count": vectors_count,
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

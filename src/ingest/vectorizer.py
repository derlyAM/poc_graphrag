"""
Vectorizer module.
Generates embeddings and loads chunks into Qdrant.
Supports hybrid search with dense (OpenAI) + sparse (BM25) vectors.
"""
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger
import openai
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    SparseVectorParams, SparseIndexParams
)
import time
import tiktoken

from src.config import config, calculate_cost
from src.ingest.bm25_encoder import BM25Encoder


class Vectorizer:
    """Generates embeddings and manages Qdrant collection."""

    def __init__(self, use_hybrid_search: bool = True):
        """
        Initialize vectorizer with OpenAI and Qdrant clients.

        Args:
            use_hybrid_search: If True, enable hybrid search with BM25 sparse vectors
        """
        self.openai_client = openai.OpenAI(api_key=config.openai.api_key)
        self.embedding_model = config.openai.embedding_model
        self.embedding_dim = config.openai.embedding_dimensions
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # For token counting

        # Hybrid search configuration
        self.use_hybrid_search = use_hybrid_search
        self.bm25_encoder = BM25Encoder() if use_hybrid_search else None
        logger.info(f"Hybrid search (BM25): {'ENABLED' if use_hybrid_search else 'DISABLED'}")

        # Initialize Qdrant client
        if config.qdrant.use_memory:
            logger.info("Using Qdrant in-memory mode")
            self.qdrant_client = QdrantClient(":memory:")
        elif config.qdrant.path:
            # Use local persistent storage
            logger.info(f"Using Qdrant local storage at {config.qdrant.path}")
            Path(config.qdrant.path).mkdir(parents=True, exist_ok=True)
            self.qdrant_client = QdrantClient(path=config.qdrant.path)
        else:
            logger.info(f"Connecting to Qdrant at {config.qdrant.url}")
            self.qdrant_client = QdrantClient(
                host=config.qdrant.host, port=config.qdrant.port
            )

        self.collection_name = config.qdrant.collection_name
        self.total_cost = 0.0

    def create_collection(self, recreate: bool = False) -> None:
        """
        Create Qdrant collection with hybrid search support.

        Args:
            recreate: If True, delete existing collection first
        """
        # Check if collection exists
        collections = self.qdrant_client.get_collections().collections
        collection_exists = any(
            col.name == self.collection_name for col in collections
        )

        if collection_exists and recreate:
            logger.warning(f"Deleting existing collection: {self.collection_name}")
            self.qdrant_client.delete_collection(self.collection_name)
            collection_exists = False

        if not collection_exists:
            logger.info(f"Creating collection: {self.collection_name}")

            # Prepare vectors config
            vectors_config = VectorParams(
                size=self.embedding_dim, distance=Distance.COSINE
            )

            # If hybrid search is enabled, add sparse vectors config
            if self.use_hybrid_search:
                logger.info("Configuring hybrid search (dense + sparse vectors)")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=vectors_config,
                    sparse_vectors_config={
                        "text": SparseVectorParams(
                            index=SparseIndexParams()
                        )
                    }
                )
                logger.info("Collection created with HYBRID search (dense + BM25 sparse)")
            else:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=vectors_config,
                )
                logger.info("Collection created with dense vectors only")
        else:
            logger.info(f"Collection {self.collection_name} already exists")

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using OpenAI.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        logger.info(f"Generating embeddings for {len(texts)} texts")

        embeddings = []
        batch_size = 100  # OpenAI limit
        max_tokens = 8191  # text-embedding-3-small limit (leave 1 token buffer)

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            # Clean and validate texts
            clean_batch = []
            for j, text in enumerate(batch):
                # Remove null characters and excessive whitespace
                clean_text = text.replace('\x00', '').strip()
                # Ensure text is not empty
                if not clean_text:
                    clean_text = "[Empty chunk]"

                # Count actual tokens and truncate if necessary
                try:
                    tokens = self.tokenizer.encode(clean_text)
                    if len(tokens) > max_tokens:
                        logger.warning(
                            f"Chunk {i+j}: Truncating from {len(tokens)} to {max_tokens} tokens"
                        )
                        # Decode back to get truncated text
                        truncated_tokens = tokens[:max_tokens]
                        clean_text = self.tokenizer.decode(truncated_tokens)
                except Exception as e:
                    logger.warning(f"Error tokenizing text, using char-based truncation: {e}")
                    # Fallback: character-based truncation
                    max_chars = max_tokens * 3  # Conservative estimate
                    if len(clean_text) > max_chars:
                        clean_text = clean_text[:max_chars]

                clean_batch.append(clean_text)

            try:
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model, input=clean_batch
                )

                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)

                # Track cost
                tokens_used = response.usage.total_tokens
                cost = calculate_cost(self.embedding_model, tokens_used)
                self.total_cost += cost

                logger.debug(
                    f"Batch {i // batch_size + 1}: {tokens_used} tokens, ${cost:.6f}"
                )

                # Rate limiting
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error generating embeddings for batch {i}: {e}")
                raise

        logger.info(
            f"Generated {len(embeddings)} embeddings. Total cost: ${self.total_cost:.6f}"
        )

        return embeddings

    def upload_to_qdrant(
        self,
        chunks: List[Dict],
        embeddings: List[List[float]],
        sparse_vectors: Optional[List[Dict]] = None
    ) -> None:
        """
        Upload chunks with embeddings to Qdrant.

        Args:
            chunks: List of chunk dictionaries
            embeddings: List of dense embedding vectors
            sparse_vectors: Optional list of sparse vectors (BM25)
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings"
            )

        if sparse_vectors and len(chunks) != len(sparse_vectors):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks but {len(sparse_vectors)} sparse vectors"
            )

        logger.info(f"Uploading {len(chunks)} chunks to Qdrant")
        if sparse_vectors:
            logger.info("  Mode: HYBRID (dense + sparse vectors)")
        else:
            logger.info("  Mode: Dense vectors only")

        points = []

        iterator = zip(chunks, embeddings, sparse_vectors) if sparse_vectors else zip(chunks, embeddings)

        for i, data in enumerate(iterator):
            if sparse_vectors:
                chunk, embedding, sparse_vector = data
            else:
                chunk, embedding = data
                sparse_vector = None
            # Create payload with all metadata (including new graph fields)
            payload = {
                "chunk_id": chunk["chunk_id"],
                "documento_id": chunk["documento_id"],
                "documento_nombre": chunk["documento_nombre"],
                # Legal hierarchy
                "articulo": chunk.get("articulo"),
                "paragrafo": chunk.get("paragrafo"),
                "titulo": chunk.get("titulo"),
                "capitulo": chunk.get("capitulo"),
                "titulo_nombre": chunk.get("titulo_nombre"),
                "capitulo_nombre": chunk.get("capitulo_nombre"),
                # Technical hierarchy
                "seccion": chunk.get("seccion"),
                "subseccion": chunk.get("subseccion"),
                # Anexos
                "anexo_numero": chunk.get("anexo_numero"),
                "es_anexo": chunk.get("es_anexo", False),
                # Document type
                "tipo_documento": chunk.get("tipo_documento"),
                # GRAPH FIELDS (FASE 1) - NEW
                "nivel_jerarquico": chunk.get("nivel_jerarquico"),  # 0=doc, 1=titulo, 2=cap, 3=art, 4=para, 5=anexo
                "parent_id": chunk.get("parent_id"),  # UUID del chunk padre
                "children_ids": chunk.get("children_ids", []),  # Array de UUIDs de hijos
                "hierarchy_path": chunk.get("hierarchy_path"),  # Path completo en el grafo (ej: "Acuerdo > Título 4 > Capítulo 3 > Artículo 4.3.1")
                # Content
                "texto": chunk["texto"],
                "longitud_tokens": chunk["longitud_tokens"],
                # Navigation (sequential)
                "chunk_anterior_id": chunk.get("chunk_anterior_id"),
                "chunk_siguiente_id": chunk.get("chunk_siguiente_id"),
                # Citation
                "citacion_corta": chunk["citacion_corta"],
                "fecha_procesamiento": chunk["fecha_procesamiento"],
                "tipo_contenido": chunk["tipo_contenido"],
            }

            # Create point with dense vector (and sparse if hybrid mode)
            if sparse_vector:
                # Hybrid mode: vector is a dict with named vectors
                from qdrant_client.models import SparseVector
                point = PointStruct(
                    id=i,
                    vector={
                        "": embedding,  # Default dense vector (unnamed)
                        "text": SparseVector(**sparse_vector)  # Named sparse vector
                    },
                    payload=payload
                )
            else:
                # Dense-only mode
                point = PointStruct(id=i, vector=embedding, payload=payload)

            points.append(point)

        # Upload in batches
        batch_size = 100

        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]

            try:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name, points=batch
                )

                logger.debug(f"Uploaded batch {i // batch_size + 1}")

            except Exception as e:
                logger.error(f"Error uploading batch {i}: {e}")
                raise

        logger.info("Upload completed successfully")

    def get_collection_info(self) -> Dict:
        """
        Get information about the collection.

        Returns:
            Dictionary with collection stats
        """
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)

            return {
                "name": self.collection_name,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}

    def process_chunks(
        self, chunks: List[Dict], recreate_collection: bool = False
    ) -> None:
        """
        Full pipeline: create collection, generate embeddings, upload.

        Args:
            chunks: List of chunks to process
            recreate_collection: Whether to recreate collection
        """
        logger.info(f"Processing {len(chunks)} chunks")

        # Step 1: Create collection
        self.create_collection(recreate=recreate_collection)

        # Step 2: Generate dense embeddings (OpenAI)
        texts = [chunk["texto"] for chunk in chunks]
        embeddings = self.generate_embeddings(texts)

        # Step 3: Generate sparse embeddings (BM25) if enabled
        sparse_vectors = None
        if self.use_hybrid_search:
            logger.info("Training BM25 encoder on corpus")
            self.bm25_encoder.fit(texts)

            logger.info("Generating BM25 sparse vectors")
            sparse_vectors = self.bm25_encoder.encode_documents(texts)

            # Save BM25 vocabulary for later use
            vocab_path = Path(config.qdrant.path) / "bm25_vocabulary.json"
            self.bm25_encoder.save_vocabulary(str(vocab_path))

        # Step 4: Upload to Qdrant
        self.upload_to_qdrant(chunks, embeddings, sparse_vectors)

        # Step 5: Show stats
        info = self.get_collection_info()
        logger.info(f"Collection stats: {info}")
        logger.info(f"Total embedding cost: ${self.total_cost:.6f}")


def vectorize_chunks(
    chunks: List[Dict],
    recreate_collection: bool = False,
    use_hybrid_search: bool = True
) -> Vectorizer:
    """
    Convenience function to vectorize chunks.

    Args:
        chunks: List of chunks
        recreate_collection: Whether to recreate collection
        use_hybrid_search: Whether to use hybrid search (dense + BM25 sparse)

    Returns:
        Vectorizer instance with stats
    """
    vectorizer = Vectorizer(use_hybrid_search=use_hybrid_search)
    vectorizer.process_chunks(chunks, recreate_collection=recreate_collection)
    return vectorizer

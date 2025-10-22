"""
Test Retrieval Script.
Tests vector search and re-ranking with sample queries.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.config import config
from src.retrieval.vector_search import VectorSearch
from src.retrieval.reranker import Reranker
from qdrant_client import QdrantClient


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )


def print_chunk(chunk: Dict, index: int = None):
    """Pretty print a chunk."""
    prefix = f"[{index + 1}]" if index is not None else "[-]"

    print(f"\n{prefix} Score: {chunk.get('rerank_score', chunk.get('score', 0)):.4f}")
    print(f"    Documento: {chunk.get('documento_nombre', 'N/A')}")
    print(f"    Citación: {chunk.get('citacion_corta', 'N/A')}")
    print(f"    Tipo: {chunk.get('tipo_contenido', 'N/A')}")
    print(f"    Tokens: {chunk.get('longitud_tokens', 0)}")

    # Preview text
    text = chunk.get('texto', '')
    preview = text[:200] + "..." if len(text) > 200 else text
    print(f"    Texto: {preview}")


def test_query(searcher: VectorSearch, reranker: Reranker, query: str):
    """Test a single query with full pipeline."""
    print("\n" + "=" * 80)
    print(f"QUERY: {query}")
    print("=" * 80)

    # Step 1: Vector search
    print("\n[STEP 1] Vector Search (top-20)")
    chunks = searcher.search_with_context(query, top_k=20, expand_context=True)

    if not chunks:
        print("  ❌ No results found")
        return

    print(f"  ✓ Found {len(chunks)} chunks (with context expansion)")

    # Step 2: Re-ranking
    print("\n[STEP 2] Re-ranking (top-5)")
    reranked = reranker.rerank(query, chunks, top_k=5)

    print(f"  ✓ Re-ranked to top {len(reranked)} chunks")

    # Show results
    print("\n[RESULTS] Top 5 chunks:")
    for i, chunk in enumerate(reranked):
        print_chunk(chunk, i)


def main():
    """Main test function."""
    setup_logging()

    print("=" * 80)
    print("RETRIEVAL SYSTEM TEST")
    print("=" * 80)

    # Initialize Qdrant client (in-memory mode)
    logger.info("Initializing Qdrant client...")

    # Note: For in-memory mode, we need to re-ingest data
    # For now, we'll assume data was just ingested in the same session
    # In production, you'd use persistent storage or Docker

    # Create searcher (will use config settings for Qdrant)
    searcher = VectorSearch()

    # Check collection
    stats = searcher.get_collection_stats()
    print(f"\n📊 Collection Stats:")
    print(f"    Name: {stats.get('name')}")
    print(f"    Points: {stats.get('points_count', 0)}")
    print(f"    Status: {stats.get('status')}")

    if stats.get('points_count', 0) == 0:
        print("\n❌ Collection is empty! Please run scripts/01_ingest_pdfs.py first")
        return

    # Initialize re-ranker
    logger.info("Loading re-ranker model...")
    reranker = Reranker()

    # Test queries
    test_queries = [
        "¿Qué es un OCAD?",
        "¿Cuáles son los requisitos para viabilizar un proyecto?",
        "Explica el proceso de ajuste de proyectos aprobados",
        "¿Qué es el Sistema General de Regalías?",
    ]

    for query in test_queries:
        test_query(searcher, reranker, query)
        input("\nPress ENTER for next query...")

    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    from typing import Dict
    main()

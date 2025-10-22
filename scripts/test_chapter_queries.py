"""
Test script for chapter/title-specific queries.
Tests the new query enhancement functionality.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.pipeline import RAGPipeline
from src.retrieval.query_enhancer import QueryEnhancer


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )


def print_separator(title: str = ""):
    """Print a visual separator."""
    print("\n" + "=" * 80)
    if title:
        print(f"  {title}")
        print("=" * 80)
    print()


def test_query_enhancement():
    """Test the query enhancement module."""
    print_separator("TESTING QUERY ENHANCEMENT MODULE")

    enhancer = QueryEnhancer()

    test_queries = [
        "Resume el capítulo 2 del acuerdo único",
        "¿Qué dice el título 4?",
        "Dame un resumen del Capítulo III",
        "Explica el artículo 5.2.1",
        "¿Qué es un OCAD?",  # Regular semantic query
        "Resume la sección 2.1 del documento técnico",
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        enhancement = enhancer.enhance_query(query)

        print(f"  → Type: {enhancement['query_type']}")
        print(f"  → Summary request: {enhancement['is_summary_request']}")
        print(f"  → Retrieval strategy: {enhancement['retrieval_strategy']}")

        if enhancement['filters']:
            print(f"  → Filters detected: {enhancement['filters']}")

        if enhancement['enhanced_query'] != query:
            print(f"  → Enhanced query: '{enhancement['enhanced_query']}'")

        print()


def test_pipeline_with_chapters():
    """Test the full pipeline with chapter queries."""
    print_separator("TESTING FULL PIPELINE WITH CHAPTER QUERIES")

    pipeline = RAGPipeline()

    # Test queries specifically for chapters
    test_queries = [
        {
            "query": "Resume el capítulo 2 del acuerdo único",
            "doc_id": "acuerdo_unico_comision_rectora_2025_07_15",
            "description": "Should retrieve all chunks from chapter 2"
        },
        {
            "query": "Dame un resumen del Título 4",
            "doc_id": None,
            "description": "Should retrieve all chunks from title 4"
        },
        {
            "query": "¿Qué dice el Capítulo III sobre proyectos?",
            "doc_id": None,
            "description": "Hybrid query: chapter filter + semantic 'proyectos'"
        },
    ]

    for i, test_case in enumerate(test_queries, 1):
        print(f"\n[TEST {i}/{len(test_queries)}]")
        print(f"Query: '{test_case['query']}'")
        print(f"Document filter: {test_case['doc_id']}")
        print(f"Expected: {test_case['description']}")
        print()

        try:
            result = pipeline.query(
                question=test_case['query'],
                documento_id=test_case['doc_id']
            )

            if result['success']:
                # Print enhancement info
                enhancement = result.get('query_enhancement', {})
                print(f"✓ Query Type: {enhancement.get('query_type', 'N/A')}")
                print(f"✓ Retrieval Strategy: {enhancement.get('retrieval_strategy', 'N/A')}")

                if enhancement.get('filters'):
                    print(f"✓ Filters Applied: {enhancement['filters']}")

                # Print metrics
                metrics = result['metrics']
                print(f"\n📊 Metrics:")
                print(f"  - Chunks retrieved: {metrics['chunks_retrieved']}")
                print(f"  - Chunks reranked: {metrics['chunks_reranked']}")
                print(f"  - Total time: {metrics['total_time']:.2f}s")
                print(f"  - Cost: ${metrics['llm_cost']:.6f}")

                # Print answer preview
                answer = result['answer']
                print(f"\n💬 Answer Preview (first 300 chars):")
                print(f"  {answer[:300]}...")

                # Print sources
                print(f"\n📚 Sources ({result['num_sources']} chunks):")
                for j, source in enumerate(result['sources'][:3], 1):  # Show first 3
                    print(f"  [{j}] {source.get('citacion_corta', 'N/A')}")
                    print(f"      Capítulo: {source.get('capitulo', 'N/A')}, Título: {source.get('titulo', 'N/A')}")

                if result['num_sources'] > 3:
                    print(f"  ... and {result['num_sources'] - 3} more")

            else:
                print(f"❌ Query failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"❌ Exception: {e}")
            logger.exception("Full traceback:")

        print("\n" + "-" * 80)
        input("\nPress ENTER to continue to next test...")


def main():
    """Main test function."""
    setup_logging()

    print_separator("CHAPTER/TITLE QUERY TESTING")
    print("This script tests the new query enhancement functionality")
    print("that enables chapter and title-specific queries.")

    # Test 1: Query Enhancement
    test_query_enhancement()

    input("\nPress ENTER to test full pipeline...")

    # Test 2: Full Pipeline
    test_pipeline_with_chapters()

    print_separator("TESTING COMPLETED")
    print("✓ All tests completed successfully!")
    print("\nNext steps:")
    print("1. Try these queries in the Streamlit UI: streamlit run app/streamlit_app.py")
    print("2. Example queries:")
    print("   - 'Resume el capítulo 2 del acuerdo único'")
    print("   - 'Dame un resumen del Título 4'")
    print("   - '¿Qué dice el Capítulo III sobre proyectos?'")
    print()


if __name__ == "__main__":
    main()

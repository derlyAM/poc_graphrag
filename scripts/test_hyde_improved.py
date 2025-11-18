"""
Test script for HyDE Mejorado (Improved HyDE with specialized templates).

Tests different query types and verifies that specialized templates are used.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.retrieval.hyde_retriever import HyDERetriever
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_query_type_detection():
    """Test query type detection for different queries."""
    print("\n" + "="*80)
    print("TEST 1: Query Type Detection")
    print("="*80)

    hyde = HyDERetriever()

    test_queries = [
        ("Enumera los requisitos para proyectos de infraestructura", "list"),
        ("¿Cuáles son los objetivos del SGR?", "objectives"),
        ("¿Cuánto cuesta la viabilización de un proyecto?", "numerical"),
        ("¿Cómo se solicita la radicación de un proyecto?", "procedural"),
        ("Diferencias entre Acuerdo 03/2021 y Acuerdo 13/2025", "comparison"),
        ("¿Qué es un OCAD?", "definition"),
        ("Resume el Título 4", "generic"),
    ]

    passed = 0
    failed = 0

    for query, expected_type in test_queries:
        detected = hyde._detect_query_type(query)
        status = "✓" if detected == expected_type else "✗"

        if detected == expected_type:
            passed += 1
        else:
            failed += 1

        print(f"{status} Query: '{query[:60]}...'")
        print(f"   Expected: {expected_type}, Detected: {detected}")

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_hypothetical_document_generation():
    """Test HyDE document generation with specialized templates."""
    print("\n" + "="*80)
    print("TEST 2: Hypothetical Document Generation")
    print("="*80)

    hyde = HyDERetriever()

    test_queries = [
        ("Enumera los requisitos para proyectos de ciencia y tecnología", "list"),
        ("¿Cuáles son los objetivos del Sistema General de Regalías?", "objectives"),
        ("¿Cuánto es el plazo máximo para viabilización?", "numerical"),
        ("¿Cómo se realiza el proceso de ajuste de proyectos?", "procedural"),
    ]

    print("\nGenerating hypothetical documents...\n")

    for query, query_type in test_queries:
        print(f"\n{'─'*80}")
        print(f"Query Type: {query_type}")
        print(f"Query: {query}")
        print(f"{'─'*80}")

        hyde_doc, cost = hyde.generate_hypothetical_document(
            question=query,
            documento_id="acuerdo_03_2021"
        )

        print(f"\nGenerated HyDE Document:")
        print(f"{hyde_doc}")
        print(f"\nCost: ${cost:.6f}")

    print("\n✓ All hypothetical documents generated successfully")
    return True


def test_hyde_improved_integration():
    """Test full integration of HyDE Mejorado with retrieval."""
    print("\n" + "="*80)
    print("TEST 3: Full Integration Test")
    print("="*80)

    from src.retrieval.vector_search import VectorSearch
    from src.retrieval.query_enhancer import QueryEnhancer

    hyde = HyDERetriever()
    vector_search = VectorSearch()
    query_enhancer = QueryEnhancer()

    # Test query
    query = "Enumera los documentos necesarios para viabilizar un proyecto"
    area = "sgr"  # Correct area name

    print(f"\nTest Query: {query}")
    print(f"Area: {area}\n")

    # Enhance query
    enhancement = query_enhancer.enhance_query(query)
    print(f"Query enhancement: {enhancement['query_type']}")

    # Check if HyDE should be used
    should_use = hyde.should_use_hyde(enhancement)
    print(f"Should use HyDE: {should_use}")

    # Retrieve with HyDE
    result = hyde.retrieve(
        vector_search=vector_search,
        question=query,
        area=area,
        enhancement=enhancement,
        top_k=10
    )

    print(f"\nRetrieval Results:")
    print(f"  - Chunks retrieved: {len(result['chunks'])}")
    print(f"  - HyDE used: {result['hyde_used']}")
    print(f"  - Query type detected: {result['query_type']}")
    print(f"  - Average score: {result['avg_score']:.4f}")
    print(f"  - HyDE cost: ${result['hyde_cost']:.6f}")

    if result['hyde_doc']:
        print(f"\nGenerated HyDE doc (first 200 chars):")
        print(f"{result['hyde_doc'][:200]}...")

    print("\n✓ Integration test completed successfully")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("HyDE MEJORADO - TEST SUITE")
    print("="*80)

    tests = [
        ("Query Type Detection", test_query_type_detection),
        ("Hypothetical Document Generation", test_hypothetical_document_generation),
        ("Full Integration", test_hyde_improved_integration),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"Test '{test_name}' failed with error: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, success in results if success)
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n🎉 All tests passed! HyDE Mejorado is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")


if __name__ == "__main__":
    main()

"""
Test script for multihop queries.
Tests the new multihop retrieval system with complex queries.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.pipeline import RAGPipeline
import json


# Test queries of different complexity levels
TEST_QUERIES = [
    {
        "name": "Simple Semantic (baseline)",
        "query": "¿Qué es un OCAD?",
        "expected_type": "simple_semantic",
        "expected_multihop": False,
        "description": "Simple definition query - should NOT trigger multihop"
    },
    {
        "name": "Conditional Multihop",
        "query": "¿Puedo ajustar el cronograma de un proyecto de CTEI en fase II?",
        "expected_type": "conditional",
        "expected_multihop": True,
        "description": "Requires checking if 'cronograma' is adjustable, then phase II requirements"
    },
    {
        "name": "Comparison Multihop",
        "query": "¿Qué diferencias hay entre los requisitos de proyectos de infraestructura y proyectos de ciencia y tecnología?",
        "expected_type": "comparison",
        "expected_multihop": True,
        "description": "Requires retrieving requirements from two different project types"
    },
    {
        "name": "Procedural Multihop",
        "query": "¿Cuál es el proceso completo desde la radicación de un proyecto hasta el primer desembolso?",
        "expected_type": "procedural",
        "expected_multihop": True,
        "description": "Requires retrieving multiple steps of a procedure"
    },
    {
        "name": "Aggregation (single-hop but exhaustive)",
        "query": "Lista todos los documentos necesarios para la viabilización de proyectos",
        "expected_type": "aggregation",
        "expected_multihop": False,
        "description": "Requires many chunks but doesn't need multihop reasoning"
    },
    {
        "name": "Complex Conditional with Multiple Conditions",
        "query": "Si mi proyecto es de salud, está en fase III y el monto es mayor a 5.000 millones, ¿qué OCAD debe evaluarlo?",
        "expected_type": "conditional",
        "expected_multihop": True,
        "description": "Requires checking multiple conditions and routing logic"
    }
]


def test_query(pipeline: RAGPipeline, test_case: dict, test_num: int):
    """
    Test a single query.

    Args:
        pipeline: RAG pipeline
        test_case: Test case dictionary
        test_num: Test number
    """
    print("\n" + "="*80)
    print(f"TEST {test_num}: {test_case['name']}")
    print("="*80)
    print(f"\nQuery: {test_case['query']}")
    print(f"Description: {test_case['description']}")
    print(f"Expected type: {test_case['expected_type']}")
    print(f"Expected multihop: {test_case['expected_multihop']}")

    print("\n" + "-"*80)
    print("EXECUTING QUERY...")
    print("-"*80)

    try:
        # Execute query with multihop enabled
        result = pipeline.query(
            question=test_case['query'],
            enable_multihop=True
        )

        # Extract key information
        decomposition = result.get('query_decomposition')
        multihop_used = result.get('multihop_used', False)
        metrics = result.get('metrics', {})
        answer = result.get('answer', '')

        print("\n" + "-"*80)
        print("RESULTS:")
        print("-"*80)

        # Decomposition analysis
        if decomposition:
            print(f"\n✓ Query Analysis:")
            print(f"  - Type: {decomposition['query_type']}")
            print(f"  - Complexity: {decomposition['complexity']}")
            print(f"  - Requires multihop: {decomposition['requires_multihop']}")
            print(f"  - Strategy: {decomposition['search_strategy']}")

            if decomposition['sub_queries']:
                print(f"\n✓ Sub-queries generated ({len(decomposition['sub_queries'])}):")
                for i, sq in enumerate(decomposition['sub_queries'], 1):
                    print(f"  {i}. {sq}")

        # Multihop execution
        print(f"\n✓ Multihop used: {multihop_used}")

        if multihop_used and metrics.get('multihop_stats'):
            stats = metrics['multihop_stats']
            print(f"\n✓ Multihop Statistics:")
            print(f"  - Total chunks: {stats['total_chunks']}")
            print(f"  - Top score: {stats['top_score']:.4f}")
            print(f"  - Avg score: {stats['avg_score']:.4f}")

            if 'chunks_by_num_sources' in stats:
                print(f"  - Chunks by source count:")
                for num_sources, count in sorted(stats['chunks_by_num_sources'].items()):
                    print(f"    • {num_sources} sources: {count} chunks")

        # Performance metrics
        print(f"\n✓ Performance:")
        print(f"  - Total time: {metrics.get('total_time', 0):.2f}s")
        print(f"  - Search time: {metrics.get('search_time', 0):.2f}s")
        print(f"  - Generation time: {metrics.get('generation_time', 0):.2f}s")
        print(f"  - Cost: ${metrics.get('llm_cost', 0):.6f}")

        # Answer preview
        print(f"\n✓ Answer (first 300 chars):")
        print(f"  {answer[:300]}...")

        # Validation
        print(f"\n✓ Validation:")
        type_match = decomposition['query_type'] == test_case['expected_type'] if decomposition else False
        multihop_match = multihop_used == test_case['expected_multihop']

        print(f"  - Type match: {'✓' if type_match else '✗'} (expected {test_case['expected_type']}, got {decomposition['query_type'] if decomposition else 'N/A'})")
        print(f"  - Multihop match: {'✓' if multihop_match else '✗'} (expected {test_case['expected_multihop']}, got {multihop_used})")

        # Success indicator
        success = result.get('success', False)
        if success and multihop_match:
            print(f"\n{'🎉 TEST PASSED!' if type_match else '⚠️ TEST PASSED (with type mismatch)'}")
        else:
            print(f"\n❌ TEST FAILED!")

        return result

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.exception("Full traceback:")
        return None


def run_all_tests(documento_id: str = None):
    """
    Run all test queries.

    Args:
        documento_id: Optional document filter
    """
    print("\n" + "="*80)
    print("MULTIHOP RETRIEVAL TEST SUITE")
    print("="*80)
    print(f"\nTotal tests: {len(TEST_QUERIES)}")
    if documento_id:
        print(f"Document filter: {documento_id}")

    # Initialize pipeline
    print("\nInitializing RAG Pipeline...")
    pipeline = RAGPipeline()

    # Run tests
    results = []
    passed = 0
    failed = 0

    for i, test_case in enumerate(TEST_QUERIES, 1):
        result = test_query(pipeline, test_case, i)
        results.append({
            "test_case": test_case,
            "result": result,
            "passed": result is not None and result.get('success', False)
        })

        if results[-1]['passed']:
            passed += 1
        else:
            failed += 1

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"\nTotal tests: {len(TEST_QUERIES)}")
    print(f"Passed: {passed} ✓")
    print(f"Failed: {failed} ✗")
    print(f"Success rate: {passed/len(TEST_QUERIES)*100:.1f}%")

    # Detailed results
    print("\nDetailed Results:")
    for i, result_data in enumerate(results, 1):
        test_name = result_data['test_case']['name']
        status = "✓ PASS" if result_data['passed'] else "✗ FAIL"
        print(f"  {i}. {test_name}: {status}")

    # Save results to JSON
    output_file = Path(__file__).parent.parent / "test_results_multihop.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        # Serialize results (excluding non-serializable objects)
        serializable_results = []
        for r in results:
            serializable_results.append({
                "test_name": r['test_case']['name'],
                "query": r['test_case']['query'],
                "expected_type": r['test_case']['expected_type'],
                "expected_multihop": r['test_case']['expected_multihop'],
                "passed": r['passed'],
                "result": {
                    "multihop_used": r['result'].get('multihop_used') if r['result'] else None,
                    "query_type": r['result'].get('query_decomposition', {}).get('query_type') if r['result'] else None,
                    "metrics": r['result'].get('metrics') if r['result'] else None,
                } if r['result'] else None
            })

        json.dump(serializable_results, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {output_file}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test multihop retrieval system")
    parser.add_argument(
        "--documento",
        type=str,
        help="Filter by document ID (e.g., 'acuerdo_03_2021')"
    )
    parser.add_argument(
        "--test",
        type=int,
        help="Run single test by number (1-6)"
    )

    args = parser.parse_args()

    # Configure logger
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    if args.test:
        # Run single test
        if 1 <= args.test <= len(TEST_QUERIES):
            pipeline = RAGPipeline()
            test_query(pipeline, TEST_QUERIES[args.test - 1], args.test)
        else:
            print(f"Error: Test number must be between 1 and {len(TEST_QUERIES)}")
    else:
        # Run all tests
        run_all_tests(documento_id=args.documento)

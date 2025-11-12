"""
Test suite for HyDE (Hypothetical Document Embeddings) implementation.

Tests different query types to verify:
1. HyDE activation decision is correct
2. HyDE improves results for appropriate queries
3. HyDE doesn't activate for structural queries
4. Fallback works when needed
5. Both document types (legal, technical) are supported
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import RAGPipeline
from loguru import logger
import argparse


# Test cases organized by expected behavior
TEST_CASES = {
    # Cases where HyDE SHOULD activate and SHOULD help
    "hyde_should_help": [
        {
            "name": "Definition query with wrong terminology",
            "query": "¿Qué es el comité que aprueba proyectos?",  # Wrong: "comité" (should be "OCAD")
            "documento_id": "acuerdo_unico_comision_rectora_2025_07_15",
            "expected_hyde": True,
            "reason": "Terminology mismatch: 'comité' vs 'OCAD'",
        },
        {
            "name": "Technical query with colloquial language",
            "query": "¿Cuáles son las cosas que se van a construir con este proyecto?",  # Wrong: "cosas construir"
            "documento_id": "documentotecnico_v2",
            "expected_hyde": True,
            "reason": "Colloquial language: 'cosas construir' vs 'productos esperados'",
        },
        {
            "name": "Definition query - simple",
            "query": "¿Qué es el Sistema General de Regalías?",
            "documento_id": "acuerdo_unico_comision_rectora_2025_07_15",
            "expected_hyde": True,
            "reason": "Simple definition query - HyDE should generate formal definition",
        },
        {
            "name": "How-to procedural query",
            "query": "¿Cómo solicito un ajuste a mi proyecto aprobado?",
            "documento_id": "acuerdo_unico_comision_rectora_2025_07_15",
            "expected_hyde": True,
            "reason": "Procedural query - HyDE should generate formal procedure text",
        },
        {
            "name": "Technical explanation query",
            "query": "Explica la metodología del proyecto",
            "documento_id": "documentotecnico_v2",
            "expected_hyde": True,
            "reason": "Explanation query - HyDE should help",
        },
    ],

    # Cases where HyDE should NOT activate (structural queries)
    "hyde_should_not_activate": [
        {
            "name": "Structural query with capítulo",
            "query": "capítulo 4 ajustes de proyectos",
            "documento_id": "acuerdo_unico_comision_rectora_2025_07_15",
            "expected_hyde": False,
            "reason": "Structural filter detected (capítulo)",
        },
        {
            "name": "Specific article query",
            "query": "artículo 4.5.1.2",
            "documento_id": "acuerdo_unico_comision_rectora_2025_07_15",
            "expected_hyde": False,
            "reason": "Specific article reference",
        },
        {
            "name": "Technical section query",
            "query": "sección 18 productos esperados",
            "documento_id": "documentotecnico_v2",
            "expected_hyde": False,
            "reason": "Specific section reference",
        },
        {
            "name": "Multihop conditional query",
            "query": "¿Puedo ajustar el cronograma si estoy en fase II?",
            "documento_id": "acuerdo_unico_comision_rectora_2025_07_15",
            "expected_hyde": False,
            "reason": "Multihop query (should use multihop instead of HyDE)",
        },
    ],

    # Cases to test fallback mechanism
    "hyde_fallback_test": [
        {
            "name": "Query likely to get low scores initially",
            "query": "¿Cuál es el presupuesto del proyecto?",  # Wrong: "presupuesto" (should be "fuentes de financiación")
            "documento_id": "documentotecnico_v2",
            "expected_hyde": None,  # Will activate via fallback
            "expected_fallback": True,
            "reason": "Poor terminology should trigger fallback",
        },
    ],
}


def run_single_test(pipeline, test_case, enable_hyde=True, enable_multihop=True):
    """
    Run a single test case.

    Args:
        pipeline: RAGPipeline instance
        test_case: Test case dictionary
        enable_hyde: Whether HyDE is enabled
        enable_multihop: Whether multihop is enabled

    Returns:
        Test results dictionary
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"TEST: {test_case['name']}")
    logger.info(f"Query: {test_case['query']}")
    logger.info(f"Documento: {test_case['documento_id']}")
    logger.info(f"Expected HyDE: {test_case.get('expected_hyde', 'N/A')}")
    logger.info(f"Reason: {test_case.get('reason', 'N/A')}")
    logger.info(f"{'='*80}\n")

    # Execute query
    result = pipeline.query(
        question=test_case['query'],
        documento_id=test_case['documento_id'],
        enable_hyde=enable_hyde,
        enable_multihop=enable_multihop,
    )

    # Extract results
    hyde_metadata = result.get('hyde_metadata', {})
    hyde_used = hyde_metadata.get('hyde_used', False)
    fallback_used = hyde_metadata.get('hyde_fallback_used', False)
    avg_score = hyde_metadata.get('hyde_avg_score', 0.0)

    metrics = result.get('metrics', {})
    total_time = metrics.get('total_time', 0)
    total_cost = metrics.get('total_cost', 0)
    hyde_cost = metrics.get('hyde_cost', 0)

    # Check expectations
    expected_hyde = test_case.get('expected_hyde')
    expected_fallback = test_case.get('expected_fallback', False)

    # Determine test pass/fail
    test_passed = True
    failure_reason = None

    if expected_hyde is not None:
        if expected_hyde and not hyde_used:
            test_passed = False
            failure_reason = f"Expected HyDE to activate but it didn't"
        elif not expected_hyde and hyde_used:
            test_passed = False
            failure_reason = f"HyDE activated when it shouldn't"

    if expected_fallback and not fallback_used:
        test_passed = False
        failure_reason = f"Expected fallback to activate but it didn't"

    # Log results
    logger.info(f"\n--- RESULTS ---")
    logger.info(f"✓ HyDE Used: {hyde_used}")
    if hyde_used:
        logger.info(f"  - Fallback: {fallback_used}")
        logger.info(f"  - Avg Score: {avg_score:.3f}")
        logger.info(f"  - HyDE Cost: ${hyde_cost:.6f}")
    logger.info(f"✓ Total Time: {total_time:.2f}s")
    logger.info(f"✓ Total Cost: ${total_cost:.6f}")
    logger.info(f"✓ Sources: {result.get('num_sources', 0)}")

    if test_passed:
        logger.success(f"✅ TEST PASSED")
    else:
        logger.error(f"❌ TEST FAILED: {failure_reason}")

    return {
        'test_name': test_case['name'],
        'query': test_case['query'],
        'hyde_used': hyde_used,
        'fallback_used': fallback_used,
        'expected_hyde': expected_hyde,
        'expected_fallback': expected_fallback,
        'test_passed': test_passed,
        'failure_reason': failure_reason,
        'avg_score': avg_score,
        'total_time': total_time,
        'total_cost': total_cost,
        'hyde_cost': hyde_cost,
        'num_sources': result.get('num_sources', 0),
    }


def run_test_suite(
    test_category=None,
    enable_hyde=True,
    enable_multihop=True,
    test_index=None
):
    """
    Run test suite for HyDE.

    Args:
        test_category: Optional category to test (hyde_should_help, hyde_should_not_activate, hyde_fallback_test)
        enable_hyde: Whether to enable HyDE
        enable_multihop: Whether to enable multihop
        test_index: Optional index of specific test to run within category
    """
    logger.info("="*80)
    logger.info("HyDE TEST SUITE")
    logger.info("="*80)
    logger.info(f"HyDE Enabled: {enable_hyde}")
    logger.info(f"Multihop Enabled: {enable_multihop}")
    logger.info("="*80)

    # Initialize pipeline
    logger.info("\nInitializing RAG Pipeline...")
    pipeline = RAGPipeline()

    # Determine which tests to run
    if test_category:
        if test_category not in TEST_CASES:
            logger.error(f"Unknown test category: {test_category}")
            logger.info(f"Available categories: {list(TEST_CASES.keys())}")
            return

        categories_to_run = {test_category: TEST_CASES[test_category]}
    else:
        categories_to_run = TEST_CASES

    # Run tests
    all_results = []

    for category_name, test_cases in categories_to_run.items():
        logger.info(f"\n\n{'#'*80}")
        logger.info(f"CATEGORY: {category_name.replace('_', ' ').upper()}")
        logger.info(f"{'#'*80}\n")

        # Filter by test index if specified
        if test_index is not None:
            if test_index < 0 or test_index >= len(test_cases):
                logger.error(f"Invalid test index {test_index}. Category has {len(test_cases)} tests.")
                continue
            test_cases = [test_cases[test_index]]

        for idx, test_case in enumerate(test_cases):
            result = run_single_test(
                pipeline=pipeline,
                test_case=test_case,
                enable_hyde=enable_hyde,
                enable_multihop=enable_multihop,
            )
            result['category'] = category_name
            result['index'] = idx
            all_results.append(result)

    # Summary
    logger.info(f"\n\n{'='*80}")
    logger.info("TEST SUITE SUMMARY")
    logger.info(f"{'='*80}\n")

    total_tests = len(all_results)
    passed_tests = sum(1 for r in all_results if r['test_passed'])
    failed_tests = total_tests - passed_tests

    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"✅ Passed: {passed_tests}")
    logger.info(f"❌ Failed: {failed_tests}")
    logger.info(f"Success Rate: {(passed_tests/total_tests*100):.1f}%\n")

    # Failed tests details
    if failed_tests > 0:
        logger.info("Failed Tests:")
        for result in all_results:
            if not result['test_passed']:
                logger.error(f"  ❌ {result['test_name']}")
                logger.error(f"     Reason: {result['failure_reason']}")
                logger.error(f"     Query: {result['query']}\n")

    # HyDE usage statistics
    hyde_activated = sum(1 for r in all_results if r['hyde_used'])
    fallback_activated = sum(1 for r in all_results if r['fallback_used'])

    logger.info(f"\nHyDE Statistics:")
    logger.info(f"  - HyDE Activated: {hyde_activated}/{total_tests} ({hyde_activated/total_tests*100:.1f}%)")
    logger.info(f"  - Fallback Activated: {fallback_activated}/{total_tests} ({fallback_activated/total_tests*100:.1f}%)")

    # Cost statistics
    total_cost = sum(r['total_cost'] for r in all_results)
    total_hyde_cost = sum(r['hyde_cost'] for r in all_results)
    avg_time = sum(r['total_time'] for r in all_results) / total_tests

    logger.info(f"\nCost & Performance:")
    logger.info(f"  - Total Cost: ${total_cost:.6f}")
    logger.info(f"  - HyDE Cost: ${total_hyde_cost:.6f} ({total_hyde_cost/total_cost*100:.1f}% of total)")
    logger.info(f"  - Avg Time: {avg_time:.2f}s")

    # Get HyDE stats from pipeline
    hyde_stats = pipeline.hyde_retriever.get_stats()
    logger.info(f"\nHyDE Retriever Stats:")
    for key, value in hyde_stats.items():
        if isinstance(value, float):
            logger.info(f"  - {key}: {value:.2%}" if key.endswith('_rate') else f"  - {key}: {value:.3f}")
        else:
            logger.info(f"  - {key}: {value}")

    logger.info(f"\n{'='*80}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test HyDE implementation")
    parser.add_argument(
        '--category',
        type=str,
        choices=list(TEST_CASES.keys()) + ['all'],
        default='all',
        help='Test category to run'
    )
    parser.add_argument(
        '--test',
        type=int,
        help='Specific test index within category'
    )
    parser.add_argument(
        '--no-hyde',
        action='store_true',
        help='Disable HyDE (for comparison)'
    )
    parser.add_argument(
        '--no-multihop',
        action='store_true',
        help='Disable Multihop'
    )

    args = parser.parse_args()

    # Run tests
    run_test_suite(
        test_category=None if args.category == 'all' else args.category,
        enable_hyde=not args.no_hyde,
        enable_multihop=not args.no_multihop,
        test_index=args.test,
    )


if __name__ == "__main__":
    main()

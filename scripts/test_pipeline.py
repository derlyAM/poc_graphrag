"""
End-to-End Pipeline Test.
Tests the complete RAG pipeline with real queries.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.pipeline import RAGPipeline

# Configure logging
logger.remove()
logger.add(sys.stdout, level="INFO")


def print_result(result: dict):
    """Pretty print pipeline result."""
    print("\n" + "=" * 80)
    print("RESULTADO")
    print("=" * 80)

    # Answer
    print("\n📝 RESPUESTA:")
    print("-" * 80)
    print(result["answer"])
    print()

    # Citation Report
    if result.get("citation_report"):
        print("\n" + result["citation_report"])

    # Metrics
    metrics = result.get("metrics", {})
    print("\n⏱️ MÉTRICAS:")
    print(f"  - Tiempo total: {metrics.get('total_time', 0):.2f}s")
    print(f"  - Búsqueda: {metrics.get('search_time', 0):.2f}s")
    print(f"  - Re-ranking: {metrics.get('rerank_time', 0):.2f}s")
    print(f"  - Generación: {metrics.get('generation_time', 0):.2f}s")
    print(f"  - Chunks recuperados: {metrics.get('chunks_retrieved', 0)}")
    print(f"  - Chunks finales: {metrics.get('chunks_reranked', 0)}")
    print(f"  - Tokens de entrada: {metrics.get('input_tokens', 0)}")
    print(f"  - Tokens de salida: {metrics.get('output_tokens', 0)}")
    print(f"  - Costo: ${metrics.get('llm_cost', 0):.6f}")

    print("\n" + "=" * 80)


def main():
    """Main test function."""
    print("=" * 80)
    print("PRUEBA END-TO-END DEL PIPELINE RAG")
    print("=" * 80)

    # Initialize pipeline
    print("\n🔧 Inicializando pipeline...")
    pipeline = RAGPipeline()

    # Get stats
    stats = pipeline.get_stats()
    print(f"\n📊 Estadísticas:")
    print(f"  - Colección: {stats['collection'].get('name')}")
    print(f"  - Documentos indexados: {stats['collection'].get('points_count')}")
    print(f"  - Modelo LLM: {stats['model']}")
    print(f"  - Modelo Re-ranker: {stats['reranker_model']}")

    # Test queries
    test_queries = [
        "¿Qué es un OCAD?",
        "¿Cuáles son los requisitos para viabilizar un proyecto?",
        "Explica el proceso de ajuste de proyectos aprobados",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n\n{'#' * 80}")
        print(f"PRUEBA {i}/{len(test_queries)}")
        print(f"{'#' * 80}")
        print(f"\n❓ PREGUNTA: {query}")

        # Execute query
        result = pipeline.query(query)

        # Print result
        print_result(result)

        if i < len(test_queries):
            input("\n👉 Presiona ENTER para la siguiente prueba...")

    # Final stats
    print("\n\n" + "=" * 80)
    print("RESUMEN FINAL")
    print("=" * 80)
    print(f"Costo total acumulado: ${pipeline.llm_client.get_total_cost():.6f}")
    print("=" * 80)


if __name__ == "__main__":
    main()

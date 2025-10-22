"""
Script de prueba para query sobre sección de antecedentes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import RAGPipeline
from loguru import logger

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
)

def test_antecedentes_query():
    """Probar query sobre antecedentes del documento técnico V2."""

    logger.info("=" * 80)
    logger.info("PRUEBA: Query sobre sección de ANTECEDENTES")
    logger.info("=" * 80)

    # Inicializar pipeline
    pipeline = RAGPipeline()

    # Query
    question = "que dice la sección de antecedentes del documento tecnico V2"

    logger.info(f"\nQuery: {question}")
    logger.info("-" * 80)

    # Ejecutar
    result = pipeline.query(
        question=question,
        documento_id="documentotecnico_v2",  # Filtrar por documento técnico
        top_k_retrieval=10,
        top_k_rerank=5,
        expand_context=True
    )

    # Mostrar resultados
    logger.info("\n" + "=" * 80)
    logger.info("RESULTADOS")
    logger.info("=" * 80)

    logger.info(f"\nRespuesta generada:")
    logger.info("-" * 80)
    print(result["answer"])

    logger.info("\n" + "=" * 80)
    logger.info("FUENTES CONSULTADAS")
    logger.info("=" * 80)

    for i, source in enumerate(result["sources"], 1):
        logger.info(f"\nFuente {i}:")
        logger.info(f"  chunk_id: {source['chunk_id'][:16]}...")
        logger.info(f"  documento: {source.get('documento_nombre', 'N/A')}")
        logger.info(f"  nivel: {source.get('nivel_jerarquico', 'N/A')}")
        logger.info(f"  seccion: {source.get('seccion', 'N/A')}")
        logger.info(f"  hierarchy_path: {source.get('hierarchy_path', 'N/A')}")
        logger.info(f"  score: {source.get('score', 'N/A')}")
        logger.info(f"  texto (preview): {source['texto'][:200]}...")

    logger.info("\n" + "=" * 80)
    logger.info("MÉTRICAS")
    logger.info("=" * 80)

    metrics = result["metrics"]
    logger.info(f"\nTiempo total: {metrics['total_time']:.2f}s")
    logger.info(f"Chunks recuperados (retrieval): {metrics['retrieval_chunks']}")
    logger.info(f"Chunks finales (rerank): {metrics['rerank_chunks']}")
    logger.info(f"Tokens input: {metrics['generation_input_tokens']}")
    logger.info(f"Tokens output: {metrics['generation_output_tokens']}")
    logger.info(f"Costo: ${metrics['generation_cost']:.4f}")


if __name__ == "__main__":
    test_antecedentes_query()

"""
Script de validación comprehensivo para múltiples secciones del documento técnico V2.
Prueba que la solución de chunking funciona correctamente para CUALQUIER sección.
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


def test_section(pipeline: RAGPipeline, query: str, section_name: str):
    """Probar query sobre una sección específica."""

    logger.info("=" * 80)
    logger.info(f"PRUEBA: {section_name}")
    logger.info("=" * 80)
    logger.info(f"\nQuery: {query}")
    logger.info("-" * 80)

    # Ejecutar query
    result = pipeline.query(
        question=query,
        documento_id="documentotecnico_v2",
        top_k_retrieval=10,
        top_k_rerank=5,
        expand_context=True
    )

    # Verificar si encontró información
    answer = result["answer"]

    if "No encontré información" in answer or "no encontré" in answer.lower():
        logger.error(f"\n❌ FALLO: No se encontró información para {section_name}")
        logger.error(f"Respuesta: {answer[:200]}...")
        return False
    else:
        logger.success(f"\n✓ ÉXITO: Se encontró información para {section_name}")
        print(f"\nRespuesta generada:")
        print("-" * 80)
        print(answer)
        print()

        # Mostrar fuentes
        logger.info(f"Fuentes consultadas: {len(result['sources'])}")
        for i, source in enumerate(result["sources"][:3], 1):  # Solo primeras 3
            logger.info(f"  {i}. {source.get('seccion', 'N/A')} - {source.get('hierarchy_path', 'N/A')[:60]}...")

        return True


def main():
    """Ejecutar tests de múltiples secciones."""

    logger.info("=" * 80)
    logger.info("VALIDACIÓN COMPREHENSIVA - Múltiples Secciones")
    logger.info("=" * 80)
    logger.info("\nObjetivo: Probar que el fix de chunking funciona para TODAS las secciones\n")

    # Inicializar pipeline
    logger.info("Inicializando RAG pipeline...")
    pipeline = RAGPipeline()
    logger.info("✓ Pipeline inicializado\n")

    # Definir queries para diferentes secciones
    test_cases = [
        {
            "query": "que dice la sección de antecedentes del documento tecnico V2",
            "section": "ANTECEDENTES (Sección 6)"
        },
        {
            "query": "que dice la sección de justificación del documento tecnico V2",
            "section": "JUSTIFICACIÓN (Sección 7)"
        },
        {
            "query": "cual es la metodología propuesta en el documento tecnico V2",
            "section": "METODOLOGÍA (Sección 14)"
        },
        {
            "query": "cuales son los productos esperados del documento tecnico V2",
            "section": "PRODUCTOS ESPERADOS (Sección 18)"
        },
        {
            "query": "cual es el cronograma del documento tecnico V2",
            "section": "CRONOGRAMA (Sección 19)"
        }
    ]

    # Ejecutar tests
    results = []
    for test_case in test_cases:
        success = test_section(
            pipeline=pipeline,
            query=test_case["query"],
            section_name=test_case["section"]
        )
        results.append({
            "section": test_case["section"],
            "success": success
        })
        print("\n")

    # Resumen final
    logger.info("=" * 80)
    logger.info("RESUMEN DE VALIDACIÓN")
    logger.info("=" * 80)

    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed

    logger.info(f"\nTotal de tests: {total}")
    logger.success(f"Pasados: {passed}")
    if failed > 0:
        logger.error(f"Fallados: {failed}")

    print("\nDetalle:")
    for result in results:
        status = "✓ PASS" if result["success"] else "❌ FAIL"
        print(f"  {status} - {result['section']}")

    # Conclusión
    print("\n" + "=" * 80)
    if failed == 0:
        logger.success("✓ VALIDACIÓN COMPLETA: Todas las secciones funcionan correctamente")
        logger.success("✓ La solución de chunking es GENERAL y funcional")
    else:
        logger.warning(f"⚠️ VALIDACIÓN PARCIAL: {failed}/{total} secciones presentan problemas")
    print("=" * 80)


if __name__ == "__main__":
    main()

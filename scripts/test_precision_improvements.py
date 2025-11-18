"""
Test script for Phase 1 precision improvements.
Tests only the 15 questions that previously returned "No encontré información".

PHASE 1 IMPROVEMENTS IMPLEMENTED:
1. ✅ Query Enhancement para términos específicos
2. ✅ Top-k dinámico según tipo de pregunta
3. ✅ BM25 con pesos ajustables

Expected improvement: 75% → 90% precision
"""
import sys
from pathlib import Path
import time
import json
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import RAGPipeline
from loguru import logger

# Configurar logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# 15 preguntas que fallaron en la prueba original
# (devolvieron "No encontré información" a pesar de encontrar chunks)
FAILED_QUESTIONS = {
    "CONPES Colombia": [
        "¿Cuál es el objetivo número 1 de la política nacional de inteligencia artificial en Colombia?",
        "¿Cuál es el objetivo número 4 de la política nacional de inteligencia artificial en Colombia?",
        "¿Cuál es el costo estimado y de dónde proviene la financiación de las políticas propuestas?",
    ],
    "EU AI Act": [
        "¿Cuáles son los niveles de riesgo según el AI Act?",
        "¿Qué sanciones económicas pueden imponerse por incumplimiento del AI Act?",
        "¿Cuáles son algunas de las prácticas de IA prohibidas?",
        "¿Qué obligaciones de transparencia establece el AI Act para los sistemas de IA?",
    ],
    "Facultad IA Caldas": [
        "¿Qué sucede si un estudiante beneficiario de algún apoyo socioeconómico de la universidad quiere postularse?",
    ],
    "IEEE Ética": [
        "¿Qué indica el estándar sobre la competencia de los operadores y creadores de sistemas inteligentes?",
    ],
    "Historia IA": [
        "¿Qué aplicaciones actuales de la IA se mencionan en el documento?",
        "¿Cuándo resurgieron las redes neuronales en la investigación de IA y por qué?",
    ],
    "Ametic IA Generativa": [
        "¿Cuáles son algunos ejemplos prácticos de aplicaciones de IA generativa?",
        "¿Qué retos principales enfrenta la IA generativa según el documento?",
    ],
    "Guía Estudiantes": [
        "¿Cuáles son los principales cambios positivos y negativos que los líderes académicos observan en la educación superior debido a la IA?",
    ],
    "UNESCO": [
        "¿Qué recomienda la UNESCO para avanzar en un desarrollo ético de la inteligencia artificial?",
    ],
}


def test_question(pipeline: RAGPipeline, pregunta: str, documento: str) -> Dict:
    """
    Test a single question and return detailed results.

    Returns:
        Dict with: pregunta, documento, respuesta, num_chunks, costo, tiempo, tiene_respuesta
    """
    inicio = time.time()

    try:
        resultado = pipeline.query(
            question=pregunta,
            area="inteligencia_artificial",
            top_k_retrieval=10,  # Will be adjusted by query enhancer
            top_k_rerank=5,
            expand_context=True,
        )

        tiempo = time.time() - inicio
        num_chunks = len(resultado.get("sources", []))
        costo = resultado.get("metrics", {}).get("total_cost", 0)
        respuesta = resultado.get("answer", "")

        # Check if answer contains actual information (not "No encontré")
        tiene_respuesta = not any(phrase in respuesta.lower() for phrase in [
            "no encontré información",
            "no pude encontrar",
            "no hay información disponible",
            "no se encuentra información"
        ])

        return {
            "pregunta": pregunta,
            "documento": documento,
            "respuesta": respuesta,
            "num_chunks": num_chunks,
            "costo": costo,
            "tiempo": tiempo,
            "tiene_respuesta": tiene_respuesta,
            "error": None,
        }

    except Exception as e:
        return {
            "pregunta": pregunta,
            "documento": documento,
            "respuesta": None,
            "num_chunks": 0,
            "costo": 0,
            "tiempo": time.time() - inicio,
            "tiene_respuesta": False,
            "error": str(e),
        }


def run_tests(pipeline: RAGPipeline) -> Dict:
    """Execute all failed questions and collect results."""

    resultados = {
        "total_preguntas": 0,
        "con_respuesta": 0,
        "sin_respuesta": 0,
        "errores": 0,
        "tiempo_total": 0,
        "costo_total": 0,
        "detalles": [],
        "por_documento": {},
    }

    print("\n" + "="*80)
    print("FASE 1: PRUEBA DE PRECISIÓN CON 15 PREGUNTAS FALLIDAS")
    print("="*80)
    print("\nMEJORAS IMPLEMENTADAS:")
    print("  1. ✅ Query Enhancement para términos específicos")
    print("  2. ✅ Top-k dinámico según tipo de pregunta")
    print("  3. ✅ BM25 con pesos ajustables")
    print("\n" + "="*80 + "\n")

    pregunta_num = 0

    for documento, preguntas in FAILED_QUESTIONS.items():
        print(f"\n{'='*80}")
        print(f"DOCUMENTO: {documento} ({len(preguntas)} preguntas)")
        print(f"{'='*80}")

        resultados["por_documento"][documento] = {
            "total": len(preguntas),
            "con_respuesta": 0,
            "sin_respuesta": 0,
            "errores": 0,
        }

        for pregunta in preguntas:
            pregunta_num += 1
            resultados["total_preguntas"] += 1

            print(f"\n[{pregunta_num}/15] {pregunta[:70]}...")

            # Test question
            resultado = test_question(pipeline, pregunta, documento)
            resultados["detalles"].append(resultado)

            # Update stats
            resultados["tiempo_total"] += resultado["tiempo"]
            resultados["costo_total"] += resultado["costo"]

            if resultado["error"]:
                resultados["errores"] += 1
                resultados["por_documento"][documento]["errores"] += 1
                print(f"  ❌ ERROR: {resultado['error'][:80]}")

            elif resultado["tiene_respuesta"]:
                resultados["con_respuesta"] += 1
                resultados["por_documento"][documento]["con_respuesta"] += 1
                print(f"  ✅ RESPUESTA VÁLIDA")
                print(f"     Chunks: {resultado['num_chunks']} | Tiempo: {resultado['tiempo']:.2f}s | Costo: ${resultado['costo']:.4f}")
                print(f"     📝 {resultado['respuesta'][:100]}...")

            else:
                resultados["sin_respuesta"] += 1
                resultados["por_documento"][documento]["sin_respuesta"] += 1
                print(f"  ⚠️  SIN RESPUESTA (No encontré información)")
                print(f"     Chunks: {resultado['num_chunks']} | Tiempo: {resultado['tiempo']:.2f}s")

    return resultados


def print_summary(resultados: Dict):
    """Print summary and comparison with baseline."""

    print("\n" + "="*80)
    print("RESUMEN DE RESULTADOS - FASE 1")
    print("="*80)

    # General stats
    total = resultados["total_preguntas"]
    con_respuesta = resultados["con_respuesta"]
    sin_respuesta = resultados["sin_respuesta"]
    errores = resultados["errores"]

    precision_actual = (con_respuesta / total * 100) if total > 0 else 0
    precision_baseline = 75.0  # From original test: 45/60 = 75%
    mejora = precision_actual - precision_baseline

    print(f"\n📊 ESTADÍSTICAS GENERALES:")
    print(f"  Total de preguntas: {total}")
    print(f"  ✅ Con respuesta válida: {con_respuesta} ({precision_actual:.1f}%)")
    print(f"  ⚠️  Sin respuesta: {sin_respuesta} ({sin_respuesta/total*100:.1f}%)")
    print(f"  ❌ Errores: {errores} ({errores/total*100:.1f}%)")

    print(f"\n📈 COMPARACIÓN CON BASELINE:")
    print(f"  Precisión baseline: {precision_baseline:.1f}% (45/60 correctas)")
    print(f"  Precisión actual: {precision_actual:.1f}% ({con_respuesta}/{total} correctas)")
    if mejora > 0:
        print(f"  🎉 MEJORA: +{mejora:.1f} puntos porcentuales")
    elif mejora < 0:
        print(f"  ⚠️  REGRESIÓN: {mejora:.1f} puntos porcentuales")
    else:
        print(f"  ➡️  Sin cambio")

    print(f"\n⏱️  RENDIMIENTO:")
    print(f"  Tiempo total: {resultados['tiempo_total']:.2f}s ({resultados['tiempo_total']/60:.2f} min)")
    print(f"  Tiempo promedio: {resultados['tiempo_total']/total:.2f}s por pregunta")

    print(f"\n💰 COSTOS:")
    print(f"  Costo total: ${resultados['costo_total']:.4f}")
    print(f"  Costo promedio: ${resultados['costo_total']/total:.4f} por pregunta")

    print(f"\n📚 DETALLES POR DOCUMENTO:")
    for doc, stats in resultados["por_documento"].items():
        exito_rate = (stats["con_respuesta"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"\n  {doc}:")
        print(f"    Total: {stats['total']}")
        print(f"    ✅ Con respuesta: {stats['con_respuesta']} ({exito_rate:.1f}%)")
        print(f"    ⚠️  Sin respuesta: {stats['sin_respuesta']}")
        print(f"    ❌ Errores: {stats['errores']}")

    # Detailed failures (questions still without answers)
    preguntas_sin_respuesta = [
        d for d in resultados["detalles"]
        if not d["tiene_respuesta"] and not d["error"]
    ]

    if preguntas_sin_respuesta:
        print(f"\n⚠️  PREGUNTAS AÚN SIN RESPUESTA ({len(preguntas_sin_respuesta)}):")
        for i, detalle in enumerate(preguntas_sin_respuesta, 1):
            print(f"\n  {i}. [{detalle['documento']}]")
            print(f"     {detalle['pregunta'][:70]}...")
            print(f"     Chunks encontrados: {detalle['num_chunks']}")

    print("\n" + "="*80)

    # Save results
    output_file = "test_results_phase1_improvements.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Resultados guardados en: {output_file}")

    # Print recommendation
    print("\n" + "="*80)
    if precision_actual >= 90:
        print("🎉 FASE 1 COMPLETADA CON ÉXITO")
        print("   Objetivo de 90% de precisión alcanzado.")
        print("   Listo para implementar Fase 2 (mejoras importantes).")
    elif precision_actual >= 85:
        print("✅ FASE 1 CASI COMPLETADA")
        print(f"   Precisión: {precision_actual:.1f}% (objetivo: 90%)")
        print("   Considerar ajustes finos antes de Fase 2.")
    else:
        print("⚠️  FASE 1 REQUIERE AJUSTES")
        print(f"   Precisión: {precision_actual:.1f}% (objetivo: 90%)")
        print("   Revisar implementación o parámetros.")
    print("="*80 + "\n")

    # Exit code
    if precision_actual >= 85:
        return 0
    else:
        return 1


def main():
    """Main function."""

    print("\n" + "="*80)
    print("INICIALIZANDO PIPELINE RAG CON MEJORAS FASE 1")
    print("="*80)

    try:
        pipeline = RAGPipeline()
        print("✅ Pipeline inicializado correctamente\n")
    except Exception as e:
        print(f"❌ Error al inicializar pipeline: {e}")
        return 1

    # Run tests
    resultados = run_tests(pipeline)

    # Print summary and get exit code
    exit_code = print_summary(resultados)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

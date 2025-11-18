"""
Script de prueba completo con las 60 preguntas del archivo Preguntas.pdf.
Ejecuta todas las preguntas contra el área de Inteligencia Artificial.
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

# Configurar logging solo para errores críticos
logger.remove()
logger.add(sys.stderr, level="ERROR")

# 60 preguntas organizadas por documento
PREGUNTAS = {
    "CONPES Colombia": [
        "¿Cuál es el objetivo general de la política nacional de inteligencia artificial en Colombia?",
        "¿Cuál es el objetivo número 1 de la política nacional de inteligencia artificial en Colombia?",
        "¿Cuál es el objetivo número 4 de la política nacional de inteligencia artificial en Colombia?",
        "¿Qué ejes estratégicos estructuran la política nacional de IA y cuáles son sus acciones principales?",
        "¿Qué barreras tecnológicas impiden a la oferta educativa que habilite capacidades para el diseño, desarrollo y adopción de sistemas de IA?",
        "¿Cuál es el costo estimado y de dónde proviene la financiación de las políticas propuestas?",
    ],
    "EU AI Act": [
        "¿Cuáles son los niveles de riesgo según el AI Act?",
        "¿Qué sanciones económicas pueden imponerse por incumplimiento del AI Act?",
        "¿Cuáles son algunas de las prácticas de IA prohibidas?",
        "¿Qué obligaciones de transparencia establece el AI Act para los sistemas de IA?",
        "¿Quién tiene derecho a una explicación sobre decisiones tomadas por sistemas de IA de alto riesgo?",
        "¿Qué obligaciones de documentación existen para los proveedores de modelos de IA de propósito general?",
    ],
    "Facultad IA Caldas": [
        "¿Cuál es el nombre oficial de la facultad según el documento?",
        "¿Qué tipo de proceso regula la Resolución No. 024 del 16 de agosto de 2024 citada en el documento?",
        "¿Cuáles son algunos de los programas o áreas en las que se abren monitorías académicas en la facultad?",
        "¿Cuáles son dos de los requisitos para ser monitor académico en esta facultad?",
        "¿Qué criterio principal se utiliza para la selección entre aspirantes a monitor académico?",
        "¿Qué sucede si un estudiante beneficiario de algún apoyo socioeconómico de la universidad quiere postularse?",
    ],
    "IEEE Ética": [
        "¿Cómo define el estándar global IEEE la importancia de los derechos humanos en el desarrollo de sistemas autónomos e inteligentes?",
        "¿Cuál debe ser el principal criterio de éxito para el desarrollo de sistemas autónomos e inteligentes según el documento?",
        "¿Qué establece el estándar sobre el control de datos personales por parte de los individuos?",
        "¿Qué demanda el estándar respecto a la transparencia en los sistemas autónomos e inteligentes?",
        "¿Qué se exige acerca de la responsabilidad sobre las decisiones tomadas por estos sistemas?",
        "¿Qué indica el estándar sobre la competencia de los operadores y creadores de sistemas inteligentes?",
    ],
    "Historia IA": [
        "¿Quiénes sentaron las bases para la disciplina de la inteligencia artificial?",
        "¿Qué modelo propusieron Warren McCulloch y Walter Pitts en 1943?",
        "¿Quién acuñó el término 'Inteligencia Artificial' y qué aportó además?",
        "¿Qué aplicaciones actuales de la IA se mencionan en el documento?",
        "¿Cuándo resurgieron las redes neuronales en la investigación de IA y por qué?",
        "¿Qué empresa y fundador proponen un nuevo modelo basado en el neocórtex humano?",
    ],
    "Nuria Oliver": [
        "¿Qué motiva la escritura de este libro sobre Inteligencia Artificial?",
        "¿Cuál identifica la autora como el mayor riesgo social ante el avance de la IA?",
        "¿Cuáles son algunos de los retos éticos que plantea la IA en la actualidad?",
        "¿Cuál es una limitación técnica importante de los modelos de IA según la autora?",
        "¿Qué ventajas sociales se proponen si se desarrolla una IA centrada en las personas?",
        "¿Qué principios se mencionan para el desarrollo responsable de la IA?",
    ],
    "Ametic IA Generativa": [
        "¿Cómo define el documento la Inteligencia Artificial Generativa?",
        "¿Cuáles son algunos ejemplos prácticos de aplicaciones de IA generativa?",
        "¿Qué retos principales enfrenta la IA generativa según el documento?",
        "¿Nombra ejemplos de empresas que ya usan Gen IAI en la industria?",
        "¿Cuáles son los principales riesgos éticos y legales identificados?",
        "¿Qué impacto tiene la IA generativa en la educación, según el texto?",
    ],
    "IA Sector Público": [
        "¿Cómo define la OCDE los sistemas de inteligencia artificial (IA)?",
        "¿Cuál es uno de los beneficios inmediatos de la IA para el sector público en el contexto gubernamental?",
        "¿Qué desafíos éticos y de transparencia se identifican como relevantes para el uso de IA en el sector público?",
        "¿Cuáles son algunas áreas clave de aplicación de la IA identificadas para la transformación del sector público a nivel mundial?",
        "¿Qué recomienda la OCDE como uno de los pilares para una IA confiable en políticas nacionales e internacionales?",
        "¿Qué elementos debe incluir una estrategia de IA gubernamental eficaz?",
    ],
    "Guía Estudiantes": [
        "¿Por qué es esencial comprender la IA hoy en día para los estudiantes universitarios?",
        "¿Cuál es la principal advertencia ética que el documento da sobre el uso de IA en la escritura académica?",
        "¿Qué riesgos éticos señala la guía respecto a la privacidad y la seguridad al usar sistemas de IA?",
        "¿Cuáles son los principales cambios positivos y negativos que los líderes académicos observan en la educación superior debido a la IA?",
        "Según la guía, ¿cómo deben los estudiantes combinar el desarrollo de capacidades humanas y habilidades en IA para prepararse profesionalmente?",
        "¿Qué recomienda el documento para evitar sesgos y resultados erróneos al usar contenido generado por IA?",
    ],
    "UNESCO": [
        "¿Cómo define el documento la inteligencia artificial?",
        "¿Cuál es uno de los principales riesgos éticos que señala la UNESCO respecto al uso de IA?",
        "¿Qué recomienda la UNESCO para avanzar en un desarrollo ético de la inteligencia artificial?",
        "¿La IA puede reemplazar a la escuela o a los docentes según el documento?",
        "¿Qué habilidades debe potenciar la educación ante los desafíos de la IA?",
        "¿Qué rol fundamental le asigna la UNESCO a la alfabetización digital en la era de la IA?",
    ],
}


def run_all_tests(pipeline: RAGPipeline) -> Dict:
    """Ejecuta todas las preguntas y recopila resultados."""

    resultados = {
        "total_preguntas": 0,
        "exitosas": 0,
        "con_chunks": 0,
        "sin_chunks": 0,
        "errores": 0,
        "tiempo_total": 0,
        "costo_total": 0,
        "detalles_por_documento": {},
        "preguntas_fallidas": [],
    }

    print("\n" + "="*80)
    print("EJECUTANDO PRUEBAS CON 60 PREGUNTAS DE INTELIGENCIA ARTIFICIAL")
    print("="*80 + "\n")

    pregunta_num = 0

    for documento, preguntas in PREGUNTAS.items():
        print(f"\n{'='*80}")
        print(f"DOCUMENTO: {documento} ({len(preguntas)} preguntas)")
        print(f"{'='*80}")

        resultados["detalles_por_documento"][documento] = {
            "total": len(preguntas),
            "exitosas": 0,
            "con_chunks": 0,
            "sin_chunks": 0,
            "errores": 0,
        }

        for pregunta in preguntas:
            pregunta_num += 1
            resultados["total_preguntas"] += 1

            print(f"\n[{pregunta_num}/60] {pregunta[:70]}...")

            try:
                inicio = time.time()

                # Ejecutar consulta
                resultado = pipeline.query(
                    question=pregunta,
                    area="inteligencia_artificial",
                    top_k_retrieval=10,
                    top_k_rerank=5,
                    expand_context=True,
                )

                tiempo = time.time() - inicio

                # Extraer métricas
                num_chunks = len(resultado.get("sources", []))
                costo = resultado.get("metrics", {}).get("total_cost", 0)
                respuesta = resultado.get("answer", "")

                # Actualizar estadísticas
                resultados["tiempo_total"] += tiempo
                resultados["costo_total"] += costo
                resultados["exitosas"] += 1
                resultados["detalles_por_documento"][documento]["exitosas"] += 1

                if num_chunks > 0:
                    resultados["con_chunks"] += 1
                    resultados["detalles_por_documento"][documento]["con_chunks"] += 1
                    status = "✅"
                else:
                    resultados["sin_chunks"] += 1
                    resultados["detalles_por_documento"][documento]["sin_chunks"] += 1
                    status = "⚠️"

                print(f"  {status} Chunks: {num_chunks} | Tiempo: {tiempo:.2f}s | Costo: ${costo:.4f}")
                print(f"  📝 {respuesta[:100]}...")

                if num_chunks == 0:
                    resultados["preguntas_fallidas"].append({
                        "documento": documento,
                        "pregunta": pregunta,
                        "razon": "Sin chunks encontrados",
                    })

            except Exception as e:
                print(f"  ❌ ERROR: {str(e)[:100]}")
                resultados["errores"] += 1
                resultados["detalles_por_documento"][documento]["errores"] += 1
                resultados["preguntas_fallidas"].append({
                    "documento": documento,
                    "pregunta": pregunta,
                    "razon": str(e),
                })

    return resultados


def print_summary(resultados: Dict):
    """Imprime resumen de resultados."""

    print("\n" + "="*80)
    print("RESUMEN DE RESULTADOS")
    print("="*80)

    print(f"\n📊 ESTADÍSTICAS GENERALES:")
    print(f"  Total de preguntas: {resultados['total_preguntas']}")
    print(f"  ✅ Exitosas: {resultados['exitosas']} ({resultados['exitosas']/resultados['total_preguntas']*100:.1f}%)")
    print(f"  ✅ Con chunks: {resultados['con_chunks']} ({resultados['con_chunks']/resultados['total_preguntas']*100:.1f}%)")
    print(f"  ⚠️  Sin chunks: {resultados['sin_chunks']} ({resultados['sin_chunks']/resultados['total_preguntas']*100:.1f}%)")
    print(f"  ❌ Errores: {resultados['errores']} ({resultados['errores']/resultados['total_preguntas']*100:.1f}%)")

    print(f"\n⏱️  RENDIMIENTO:")
    print(f"  Tiempo total: {resultados['tiempo_total']:.2f}s ({resultados['tiempo_total']/60:.2f} min)")
    print(f"  Tiempo promedio por pregunta: {resultados['tiempo_total']/resultados['total_preguntas']:.2f}s")

    print(f"\n💰 COSTOS:")
    print(f"  Costo total: ${resultados['costo_total']:.4f}")
    print(f"  Costo promedio por pregunta: ${resultados['costo_total']/resultados['total_preguntas']:.4f}")

    print(f"\n📚 DETALLES POR DOCUMENTO:")
    for doc, stats in resultados["detalles_por_documento"].items():
        exito_rate = (stats["con_chunks"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"\n  {doc}:")
        print(f"    Total: {stats['total']} | Con chunks: {stats['con_chunks']} ({exito_rate:.1f}%) | Sin chunks: {stats['sin_chunks']} | Errores: {stats['errores']}")

    if resultados["preguntas_fallidas"]:
        print(f"\n⚠️  PREGUNTAS FALLIDAS ({len(resultados['preguntas_fallidas'])}):")
        for i, falla in enumerate(resultados["preguntas_fallidas"][:10], 1):  # Mostrar solo las primeras 10
            print(f"\n  {i}. [{falla['documento']}]")
            print(f"     {falla['pregunta'][:70]}...")
            print(f"     Razón: {falla['razon'][:80]}")

        if len(resultados["preguntas_fallidas"]) > 10:
            print(f"\n  ... y {len(resultados['preguntas_fallidas']) - 10} más")

    print("\n" + "="*80)

    # Guardar resultados en JSON
    output_file = "test_results_ia_questions.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Resultados guardados en: {output_file}")
    print("="*80 + "\n")


def main():
    """Función principal."""

    print("\n" + "="*80)
    print("INICIALIZANDO PIPELINE RAG")
    print("="*80)

    try:
        pipeline = RAGPipeline()
        print("✅ Pipeline inicializado correctamente\n")
    except Exception as e:
        print(f"❌ Error al inicializar pipeline: {e}")
        return 1

    # Ejecutar pruebas
    resultados = run_all_tests(pipeline)

    # Imprimir resumen
    print_summary(resultados)

    # Determinar código de salida
    if resultados["errores"] > 0:
        return 1
    elif resultados["sin_chunks"] > resultados["total_preguntas"] * 0.2:  # Más del 20% sin chunks
        print("⚠️  ADVERTENCIA: Más del 20% de las preguntas no encontraron chunks relevantes")
        return 1
    else:
        print("✅ TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
        return 0


if __name__ == "__main__":
    sys.exit(main())

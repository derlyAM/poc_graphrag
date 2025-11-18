"""
Script de diagnóstico para verificar documentos de IA en Qdrant.
Verifica si los documentos están procesados y prueba consultas de ejemplo.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from src.config import config
from src.pipeline import RAGPipeline
from loguru import logger

def check_documents_in_qdrant():
    """Verifica qué documentos están en Qdrant y cuenta chunks por área."""
    print("\n" + "="*60)
    print("VERIFICACIÓN DE DOCUMENTOS EN QDRANT")
    print("="*60)

    try:
        # Connect to Qdrant
        client = QdrantClient(path=config.qdrant.path)

        collection_name = config.qdrant.collection_name

        # Check if collection exists
        collections = client.get_collections().collections
        collection_exists = any(c.name == collection_name for c in collections)

        if not collection_exists:
            print(f"❌ Colección '{collection_name}' NO existe")
            print("\nSOLUCIÓN: Ejecutar ingestión:")
            print(f"  python scripts/01_ingest_pdfs.py --area inteligencia_artificial --data-dir data_topic_IA")
            return False

        print(f"✅ Colección '{collection_name}' existe\n")

        # Count chunks by area
        print("Chunks por área:")
        areas = ["sgr", "inteligencia_artificial", "general"]

        area_counts = {}
        for area in areas:
            result = client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="area", match=MatchValue(value=area))]
                ),
                limit=1,
                with_payload=False
            )
            # Get total count
            count_result = client.count(
                collection_name=collection_name,
                count_filter=Filter(
                    must=[FieldCondition(key="area", match=MatchValue(value=area))]
                )
            )
            count = count_result.count
            area_counts[area] = count

            status = "✅" if count > 0 else "❌"
            print(f"  {status} {area}: {count} chunks")

        # If no IA documents
        if area_counts["inteligencia_artificial"] == 0:
            print("\n⚠️  NO hay documentos de Inteligencia Artificial procesados")
            print("\nSOLUCIÓN: Ejecutar ingestión:")
            print(f"  python scripts/01_ingest_pdfs.py --area inteligencia_artificial --data-dir data_topic_IA")
            return False

        # Show IA documents
        print(f"\n📄 Documentos de IA procesados:")
        result = client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="area", match=MatchValue(value="inteligencia_artificial"))]
            ),
            limit=100,
            with_payload=True
        )

        doc_ids = set()
        for point in result[0]:
            doc_id = point.payload.get("documento_id")
            if doc_id:
                doc_ids.add(doc_id)

        for doc_id in sorted(doc_ids):
            # Count chunks for this document
            count_result = client.count(
                collection_name=collection_name,
                count_filter=Filter(
                    must=[
                        FieldCondition(key="area", match=MatchValue(value="inteligencia_artificial")),
                        FieldCondition(key="documento_id", match=MatchValue(value=doc_id))
                    ]
                )
            )
            print(f"  - {doc_id}: {count_result.count} chunks")

        return True

    except Exception as e:
        print(f"❌ Error al conectar con Qdrant: {e}")
        return False


def test_sample_queries():
    """Prueba consultas de ejemplo del archivo Preguntas.pdf."""
    print("\n" + "="*60)
    print("PRUEBA DE CONSULTAS DE EJEMPLO")
    print("="*60)

    # Sample queries from Preguntas.pdf
    test_queries = [
        "¿Cuál es el objetivo general de la política nacional de inteligencia artificial en Colombia?",
        "¿Qué características debe tener un sistema de IA de alto riesgo según el EU AI Act?",
        "¿Cuáles son los principios éticos fundamentales para el desarrollo de IA según IEEE?",
    ]

    try:
        pipeline = RAGPipeline()

        for i, query in enumerate(test_queries, 1):
            print(f"\n[Query {i}/3] {query[:80]}...")

            try:
                result = pipeline.query(
                    question=query,
                    area="inteligencia_artificial",
                    top_k_retrieval=10,
                    expand_context=True
                )

                num_chunks = len(result.get("sources", []))
                answer = result.get("answer", "")

                print(f"  ✅ Chunks encontrados: {num_chunks}")
                print(f"  📝 Respuesta (primeros 200 chars): {answer[:200]}...")

                if num_chunks == 0:
                    print(f"  ⚠️  NO se encontraron chunks relevantes")

            except Exception as e:
                print(f"  ❌ Error en consulta: {e}")

        print("\n" + "="*60)
        print("RESULTADO:")
        print("Si todas las consultas retornan chunks > 0, el sistema funciona correctamente")
        print("Si retorna 0 chunks, revisar:")
        print("  1. Que los documentos de IA estén procesados (verificar arriba)")
        print("  2. Que el contenido de los PDFs sea extraíble (no imágenes)")
        print("  3. Que los embeddings se hayan generado correctamente")
        print("="*60)

    except Exception as e:
        print(f"❌ Error al inicializar pipeline: {e}")


def main():
    """Ejecuta diagnóstico completo."""
    print("\n" + "="*60)
    print("SCRIPT DE DIAGNÓSTICO - DOCUMENTOS IA")
    print("="*60)

    # Step 1: Check documents in Qdrant
    docs_ok = check_documents_in_qdrant()

    if not docs_ok:
        print("\n⚠️  DETENIENDO: Primero procesar documentos de IA")
        sys.exit(1)

    # Step 2: Test sample queries
    test_sample_queries()

    print("\n✅ Diagnóstico completado")


if __name__ == "__main__":
    main()

"""
Script para inspeccionar cómo se procesó DocumentoTecnico_V2.
Analiza chunks, niveles jerárquicos y detección de estructura.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from src.config import config
from loguru import logger
from collections import Counter


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )


def inspect_tecnico_v2():
    """Inspect DocumentoTecnico_V2 processing."""
    setup_logging()

    logger.info("=" * 80)
    logger.info("INSPECCIÓN: DocumentoTecnico_V2")
    logger.info("=" * 80)

    # Connect to Qdrant
    if config.qdrant.path:
        logger.info(f"Connecting to local Qdrant at {config.qdrant.path}")
        client = QdrantClient(path=config.qdrant.path)
    else:
        logger.info(f"Connecting to Qdrant at {config.qdrant.host}:{config.qdrant.port}")
        client = QdrantClient(host=config.qdrant.host, port=config.qdrant.port)

    collection_name = config.qdrant.collection_name

    # Get all chunks from DocumentoTecnico_V2
    logger.info("\n" + "=" * 80)
    logger.info("BUSCANDO CHUNKS DEL DocumentoTecnico_V2")
    logger.info("=" * 80)

    # Try different possible document IDs
    possible_ids = [
        "documentotecnico_v2",
        "documento_tecnico_v2",
        "tecnico_v2",
    ]

    all_chunks = []
    found_id = None

    for doc_id in possible_ids:
        result = client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="documento_id", match=MatchValue(value=doc_id))]
            ),
            limit=10000,
            with_payload=True,
        )

        if result[0]:
            found_id = doc_id
            all_chunks = result[0]
            break

    if not all_chunks:
        # Try fuzzy search
        logger.warning("No encontrado con IDs exactos, buscando con búsqueda amplia...")
        result = client.scroll(
            collection_name=collection_name,
            limit=10000,
            with_payload=True,
        )

        for point in result[0]:
            doc_nombre = point.payload.get('documento_nombre', '').lower()
            doc_id = point.payload.get('documento_id', '').lower()
            if 'tecnico' in doc_nombre or 'tecnico' in doc_id:
                all_chunks.append(point)

        if all_chunks:
            logger.info(f"Encontrados {len(all_chunks)} chunks con búsqueda amplia")
            found_id = all_chunks[0].payload.get('documento_id')

    if not all_chunks:
        logger.error("❌ NO SE ENCONTRARON CHUNKS DEL DocumentoTecnico_V2")
        logger.error("Posibles razones:")
        logger.error("  1. El documento no fue procesado")
        logger.error("  2. El documento_id es diferente")
        logger.error("  3. La colección está vacía")

        # Show available document IDs
        logger.info("\nDocumentos disponibles en la colección:")
        all_docs = client.scroll(
            collection_name=collection_name,
            limit=1000,
            with_payload=True,
        )

        doc_ids = set()
        for point in all_docs[0]:
            doc_ids.add(point.payload.get('documento_id', 'N/A'))

        for doc_id in sorted(doc_ids):
            logger.info(f"  - {doc_id}")

        return

    logger.success(f"✓ Encontrados {len(all_chunks)} chunks")
    logger.info(f"  Documento ID: {found_id}")

    # ANÁLISIS 1: Tipo de documento detectado
    logger.info("\n" + "=" * 80)
    logger.info("ANÁLISIS 1: TIPO DE DOCUMENTO DETECTADO")
    logger.info("=" * 80)

    doc_types = Counter()
    for chunk in all_chunks:
        doc_type = chunk.payload.get('tipo_documento', 'unknown')
        doc_types[doc_type] += 1

    for doc_type, count in doc_types.items():
        logger.info(f"  {doc_type}: {count} chunks ({count/len(all_chunks)*100:.1f}%)")

    # ANÁLISIS 2: Niveles jerárquicos
    logger.info("\n" + "=" * 80)
    logger.info("ANÁLISIS 2: DISTRIBUCIÓN DE NIVELES JERÁRQUICOS")
    logger.info("=" * 80)

    level_counts = Counter()
    level_names = {
        0: "Documento (Root)",
        1: "Título",
        2: "Capítulo",
        3: "Artículo/Sección",
        4: "Parágrafo",
        5: "Anexo"
    }

    for chunk in all_chunks:
        level = chunk.payload.get('nivel_jerarquico')
        if level is not None:
            level_counts[level] += 1

    logger.info("Distribución por nivel:")
    for level in sorted(level_counts.keys()):
        name = level_names.get(level, f"Nivel {level}")
        count = level_counts[level]
        logger.info(f"  Nivel {level} ({name}): {count} chunks")

    if not level_counts:
        logger.warning("⚠️ NO SE ENCONTRARON CAMPOS nivel_jerarquico")
        logger.warning("  El documento NO fue procesado con estructura jerárquica")

    # ANÁLISIS 3: Estructura técnica (secciones)
    logger.info("\n" + "=" * 80)
    logger.info("ANÁLISIS 3: ESTRUCTURA TÉCNICA (Secciones)")
    logger.info("=" * 80)

    secciones = set()
    subsecciones = set()

    for chunk in all_chunks:
        sec = chunk.payload.get('seccion')
        subsec = chunk.payload.get('subseccion')

        if sec:
            secciones.add(sec)
        if subsec:
            subsecciones.add(subsec)

    logger.info(f"  Secciones principales detectadas: {len(secciones)}")
    if secciones:
        logger.info(f"    Ejemplos: {sorted(list(secciones))[:10]}")

    logger.info(f"  Subsecciones detectadas: {len(subsecciones)}")
    if subsecciones:
        logger.info(f"    Ejemplos: {sorted(list(subsecciones))[:10]}")

    if not secciones and not subsecciones:
        logger.warning("⚠️ NO SE DETECTARON SECCIONES TÉCNICAS")
        logger.warning("  Verificar patrones de detección en pdf_extractor.py")

    # ANÁLISIS 4: Campos de grafo (parent/children)
    logger.info("\n" + "=" * 80)
    logger.info("ANÁLISIS 4: CAMPOS DE GRAFO (parent_id, children_ids)")
    logger.info("=" * 80)

    chunks_with_parent = 0
    chunks_with_children = 0
    chunks_with_path = 0

    for chunk in all_chunks:
        if chunk.payload.get('parent_id'):
            chunks_with_parent += 1
        if chunk.payload.get('children_ids') and len(chunk.payload['children_ids']) > 0:
            chunks_with_children += 1
        if chunk.payload.get('hierarchy_path'):
            chunks_with_path += 1

    logger.info(f"  Chunks con parent_id: {chunks_with_parent}/{len(all_chunks)} ({chunks_with_parent/len(all_chunks)*100:.1f}%)")
    logger.info(f"  Chunks con children_ids: {chunks_with_children}/{len(all_chunks)} ({chunks_with_children/len(all_chunks)*100:.1f}%)")
    logger.info(f"  Chunks con hierarchy_path: {chunks_with_path}/{len(all_chunks)} ({chunks_with_path/len(all_chunks)*100:.1f}%)")

    # ANÁLISIS 5: Ejemplos de chunks
    logger.info("\n" + "=" * 80)
    logger.info("ANÁLISIS 5: EJEMPLOS DE CHUNKS")
    logger.info("=" * 80)

    # Mostrar 3 ejemplos variados
    example_chunks = all_chunks[:3] if len(all_chunks) >= 3 else all_chunks

    for i, chunk in enumerate(example_chunks, 1):
        payload = chunk.payload
        logger.info(f"\nEjemplo {i}:")
        logger.info(f"  chunk_id: {payload.get('chunk_id', 'N/A')[:16]}...")
        logger.info(f"  tipo_documento: {payload.get('tipo_documento', 'N/A')}")
        logger.info(f"  nivel_jerarquico: {payload.get('nivel_jerarquico', 'N/A')}")
        logger.info(f"  seccion: {payload.get('seccion', 'N/A')}")
        logger.info(f"  subseccion: {payload.get('subseccion', 'N/A')}")
        logger.info(f"  parent_id: {payload.get('parent_id', 'N/A')[:16] if payload.get('parent_id') else 'None'}...")
        logger.info(f"  children_ids: {len(payload.get('children_ids', []))} hijos")
        logger.info(f"  hierarchy_path: {payload.get('hierarchy_path', 'N/A')}")
        logger.info(f"  longitud_tokens: {payload.get('longitud_tokens', 'N/A')}")
        logger.info(f"  texto (preview): {payload.get('texto', '')[:150]}...")

    # ANÁLISIS 6: Problemas detectados
    logger.info("\n" + "=" * 80)
    logger.info("ANÁLISIS 6: PROBLEMAS DETECTADOS")
    logger.info("=" * 80)

    problems = []

    if not level_counts:
        problems.append("❌ CRÍTICO: No se detectaron niveles jerárquicos (nivel_jerarquico)")

    if not secciones and not subsecciones:
        problems.append("❌ CRÍTICO: No se detectaron secciones técnicas (seccion, subseccion)")

    if chunks_with_parent == 0:
        problems.append("⚠️ ALTO: Ningún chunk tiene parent_id asignado")

    if chunks_with_children == 0:
        problems.append("⚠️ ALTO: Ningún chunk tiene children_ids asignados")

    if chunks_with_path == 0:
        problems.append("⚠️ MEDIO: Ningún chunk tiene hierarchy_path")

    # Check if all chunks are flat (level 3 only)
    if len(level_counts) == 1 and 3 in level_counts:
        problems.append("⚠️ ALTO: Todos los chunks son nivel 3 (no hay jerarquía multinivel)")

    if problems:
        for problem in problems:
            logger.warning(problem)
    else:
        logger.success("✓ No se detectaron problemas críticos")

    # RESUMEN FINAL
    logger.info("\n" + "=" * 80)
    logger.info("RESUMEN FINAL")
    logger.info("=" * 80)
    logger.info(f"Total de chunks procesados: {len(all_chunks)}")
    logger.info(f"Tipo de documento detectado: {list(doc_types.keys())[0] if doc_types else 'unknown'}")
    logger.info(f"Niveles jerárquicos: {len(level_counts)} niveles detectados")
    logger.info(f"Secciones técnicas: {len(secciones)} secciones, {len(subsecciones)} subsecciones")
    logger.info(f"Completitud del grafo: {(chunks_with_parent + chunks_with_children + chunks_with_path) / (len(all_chunks) * 3) * 100:.1f}%")

    if problems:
        logger.warning(f"\n⚠️ Se detectaron {len(problems)} problemas que requieren atención")
    else:
        logger.success("\n✓ Documento procesado correctamente")


if __name__ == "__main__":
    inspect_tecnico_v2()

"""
Test script to validate hierarchical graph structure.
Queries Qdrant to inspect the hierarchy of chunks.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from src.config import config
from loguru import logger


def setup_logging():
    """Configure logging."""
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )


def test_hierarchy():
    """Test hierarchical structure in Qdrant."""
    setup_logging()

    logger.info("=" * 80)
    logger.info("HIERARCHICAL GRAPH STRUCTURE - VALIDATION TEST")
    logger.info("=" * 80)

    # Connect to Qdrant
    if config.qdrant.path:
        logger.info(f"Connecting to local Qdrant at {config.qdrant.path}")
        client = QdrantClient(path=config.qdrant.path)
    else:
        logger.info(f"Connecting to Qdrant at {config.qdrant.host}:{config.qdrant.port}")
        client = QdrantClient(host=config.qdrant.host, port=config.qdrant.port)

    collection_name = config.qdrant.collection_name

    # Test 1: Count chunks by hierarchy level
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: COUNT CHUNKS BY HIERARCHY LEVEL")
    logger.info("=" * 80)

    levels = {
        0: "Document",
        1: "Título",
        2: "Capítulo",
        3: "Artículo",
        4: "Parágrafo",
        5: "Anexo"
    }

    for level, name in levels.items():
        result = client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="nivel_jerarquico", match=MatchValue(value=level))]
            ),
            limit=1000,
            with_payload=True,
        )

        count = len(result[0])
        logger.info(f"Level {level} ({name}): {count} chunks")

    # Test 2: Inspect document root
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: INSPECT DOCUMENT ROOT (Level 0)")
    logger.info("=" * 80)

    doc_chunks = client.scroll(
        collection_name=collection_name,
        scroll_filter=Filter(
            must=[FieldCondition(key="nivel_jerarquico", match=MatchValue(value=0))]
        ),
        limit=10,
        with_payload=True,
    )

    for chunk in doc_chunks[0]:
        payload = chunk.payload
        logger.info(f"\nDocument Node:")
        logger.info(f"  ID: {payload.get('chunk_id')}")
        logger.info(f"  Nombre: {payload.get('documento_nombre')}")
        logger.info(f"  Parent: {payload.get('parent_id')}")
        logger.info(f"  Children: {len(payload.get('children_ids', []))} hijos")
        logger.info(f"  Hierarchy Path: {payload.get('hierarchy_path')}")
        logger.info(f"  Text Preview: {payload.get('texto', '')[:100]}...")

    # Test 3: Inspect títulos (Level 1)
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: INSPECT TÍTULOS (Level 1)")
    logger.info("=" * 80)

    titulo_chunks = client.scroll(
        collection_name=collection_name,
        scroll_filter=Filter(
            must=[FieldCondition(key="nivel_jerarquico", match=MatchValue(value=1))]
        ),
        limit=5,
        with_payload=True,
    )

    for chunk in titulo_chunks[0]:
        payload = chunk.payload
        logger.info(f"\nTítulo Node:")
        logger.info(f"  ID: {payload.get('chunk_id')[:8]}...")
        logger.info(f"  Título: {payload.get('titulo')} - {payload.get('titulo_nombre')}")
        logger.info(f"  Parent: {payload.get('parent_id')[:8] if payload.get('parent_id') else 'None'}...")
        logger.info(f"  Children: {len(payload.get('children_ids', []))} hijos")
        logger.info(f"  Hierarchy Path: {payload.get('hierarchy_path')}")

    # Test 4: Inspect capítulos (Level 2)
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: INSPECT CAPÍTULOS (Level 2)")
    logger.info("=" * 80)

    cap_chunks = client.scroll(
        collection_name=collection_name,
        scroll_filter=Filter(
            must=[FieldCondition(key="nivel_jerarquico", match=MatchValue(value=2))]
        ),
        limit=5,
        with_payload=True,
    )

    for chunk in cap_chunks[0]:
        payload = chunk.payload
        logger.info(f"\nCapítulo Node:")
        logger.info(f"  ID: {payload.get('chunk_id')[:8]}...")
        logger.info(f"  Capítulo: {payload.get('capitulo')} - {payload.get('capitulo_nombre')}")
        logger.info(f"  Parent: {payload.get('parent_id')[:8] if payload.get('parent_id') else 'None'}...")
        logger.info(f"  Children: {len(payload.get('children_ids', []))} hijos")
        logger.info(f"  Hierarchy Path: {payload.get('hierarchy_path')}")

    # Test 5: Inspect artículos (Level 3)
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: INSPECT ARTÍCULOS (Level 3)")
    logger.info("=" * 80)

    art_chunks = client.scroll(
        collection_name=collection_name,
        scroll_filter=Filter(
            must=[FieldCondition(key="nivel_jerarquico", match=MatchValue(value=3))]
        ),
        limit=5,
        with_payload=True,
    )

    for chunk in art_chunks[0]:
        payload = chunk.payload
        logger.info(f"\nArtículo Node:")
        logger.info(f"  ID: {payload.get('chunk_id')[:8]}...")
        logger.info(f"  Artículo: {payload.get('articulo')}")
        logger.info(f"  Capítulo: {payload.get('capitulo')} - {payload.get('capitulo_nombre', 'N/A')}")
        logger.info(f"  Título: {payload.get('titulo')} - {payload.get('titulo_nombre', 'N/A')}")
        logger.info(f"  Parent: {payload.get('parent_id')[:8] if payload.get('parent_id') else 'None'}...")
        logger.info(f"  Children: {len(payload.get('children_ids', []))} hijos")
        logger.info(f"  Hierarchy Path: {payload.get('hierarchy_path')}")
        logger.info(f"  Text Preview: {payload.get('texto', '')[:80]}...")

    # Test 6: Inspect anexos (Level 5)
    logger.info("\n" + "=" * 80)
    logger.info("TEST 6: INSPECT ANEXOS (Level 5)")
    logger.info("=" * 80)

    anexo_chunks = client.scroll(
        collection_name=collection_name,
        scroll_filter=Filter(
            must=[FieldCondition(key="nivel_jerarquico", match=MatchValue(value=5))]
        ),
        limit=5,
        with_payload=True,
    )

    for chunk in anexo_chunks[0]:
        payload = chunk.payload
        logger.info(f"\nAnexo Node:")
        logger.info(f"  ID: {payload.get('chunk_id')[:8]}...")
        logger.info(f"  Anexo: {payload.get('anexo_numero')}")
        logger.info(f"  Parent: {payload.get('parent_id')[:8] if payload.get('parent_id') else 'None'}...")
        logger.info(f"  Children: {len(payload.get('children_ids', []))} hijos")
        logger.info(f"  Hierarchy Path: {payload.get('hierarchy_path')}")
        logger.info(f"  Text Preview: {payload.get('texto', '')[:80]}...")

    # Test 7: Validate parent-child relationships
    logger.info("\n" + "=" * 80)
    logger.info("TEST 7: VALIDATE PARENT-CHILD RELATIONSHIPS")
    logger.info("=" * 80)

    # Get a random título node
    titulo_node = titulo_chunks[0][0].payload if titulo_chunks[0] else None

    if titulo_node:
        titulo_id = titulo_node.get('chunk_id')
        children_ids = titulo_node.get('children_ids', [])

        logger.info(f"\nValidating Título: {titulo_node.get('titulo')} - {titulo_node.get('titulo_nombre')}")
        logger.info(f"  Reported children count: {len(children_ids)}")

        # Count actual children
        actual_children = client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="parent_id", match=MatchValue(value=titulo_id))]
            ),
            limit=1000,
            with_payload=False,
        )

        actual_count = len(actual_children[0])
        logger.info(f"  Actual children in DB: {actual_count}")

        if len(children_ids) == actual_count:
            logger.success("✓ Parent-child relationship is CONSISTENT")
        else:
            logger.warning(f"✗ MISMATCH: Expected {len(children_ids)}, found {actual_count}")

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("HIERARCHY VALIDATION COMPLETE")
    logger.info("=" * 80)
    logger.info("✓ All tests completed successfully")


if __name__ == "__main__":
    test_hierarchy()

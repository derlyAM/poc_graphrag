"""
Script para debug de búsqueda vectorial.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from src.config import config
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")

def test_vector_search():
    """Test de búsqueda vectorial para antecedentes."""

    # Client OpenAI
    client_openai = OpenAI(api_key=config.openai.api_key)

    # Query (la misma que usa el RAG)
    query = "que dice la sección de antecedentes del documento tecnico V2"

    logger.info(f"Query: {query}")

    # Generar embedding
    response = client_openai.embeddings.create(
        model=config.openai.embedding_model,
        input=query
    )
    query_vector = response.data[0].embedding

    logger.info(f"Embedding generado: {len(query_vector)} dimensiones")

    # Buscar en Qdrant
    client_qdrant = QdrantClient(path=config.qdrant.path)

    # Búsqueda filtrada por documento técnico
    result = client_qdrant.search(
        collection_name=config.qdrant.collection_name,
        query_vector=query_vector,
        query_filter=Filter(
            must=[
                FieldCondition(key="documento_id", match=MatchValue(value="documentotecnico_v2"))
            ]
        ),
        limit=20,
        with_payload=True,
    )

    logger.info(f"\nResultados de búsqueda vectorial: {len(result)}\n")

    found_antecedentes = False

    for i, hit in enumerate(result, 1):
        path = hit.payload.get("hierarchy_path", "N/A")

        if "ANTECEDENTES" in path.upper():
            found_antecedentes = True
            logger.success(f"✓ Resultado {i}: ENCONTRADO ANTECEDENTES!")
        else:
            logger.info(f"  Resultado {i}:")

        print(f"  Score: {hit.score:.4f}")
        print(f"  Sección: {hit.payload.get('seccion', 'N/A')}")
        print(f"  Nivel: {hit.payload.get('nivel_jerarquico', 'N/A')}")
        print(f"  Path: {path}")
        print(f"  Texto (preview): {hit.payload.get('texto', '')[:150]}...")
        print()

    if not found_antecedentes:
        logger.error("\n❌ PROBLEMA: La sección de ANTECEDENTES NO fue recuperada en top-20")
        logger.error("Esto explica por qué el RAG no encuentra la información")

        # Buscar directamente el chunk de antecedentes
        logger.info("\nBuscando chunk de ANTECEDENTES directamente...")
        all_chunks = client_qdrant.scroll(
            collection_name=config.qdrant.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="documento_id", match=MatchValue(value="documentotecnico_v2"))
                ]
            ),
            limit=500,
            with_payload=True,
        )[0]

        for chunk in all_chunks:
            path = chunk.payload.get("hierarchy_path", "")
            if "ANTECEDENTES" in path.upper():
                logger.info(f"\nChunk de ANTECEDENTES encontrado:")
                print(f"  chunk_id: {chunk.payload['chunk_id']}")
                print(f"  Path: {path}")
                print(f"  Longitud texto: {len(chunk.payload.get('texto', ''))} chars")
                print(f"  Longitud tokens: {chunk.payload.get('longitud_tokens', 'N/A')}")

                # Intentar búsqueda vectorial solo con este chunk
                logger.info("\nBuscando qué tan similar es el embedding de este chunk vs la query...")

                # No podemos obtener el vector directamente desde Qdrant scroll,
                # pero podemos hacer search sin filtro y ver si aparece
                result_no_filter = client_qdrant.search(
                    collection_name=config.qdrant.collection_name,
                    query_vector=query_vector,
                    limit=100,
                    with_payload=True,
                )

                for i, hit in enumerate(result_no_filter):
                    if hit.payload.get("chunk_id") == chunk.payload["chunk_id"]:
                        logger.warning(f"\n⚠️ Chunk de ANTECEDENTES está en posición {i+1} de 100 (sin filtro)")
                        logger.warning(f"   Score: {hit.score:.4f}")
                        logger.warning(f"   Esto indica que el embedding NO es similar a la query")
                        break
    else:
        logger.success("\n✓ ANTECEDENTES fue recuperado correctamente")

if __name__ == "__main__":
    test_vector_search()

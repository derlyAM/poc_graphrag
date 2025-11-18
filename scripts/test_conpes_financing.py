"""
Test script to search for financing information in CONPES document.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.retrieval.vector_search import VectorSearch
from src.retrieval.query_enhancer import QueryEnhancer
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")


def search_financing_info():
    """Search for financing information in CONPES document."""
    print("\n" + "="*80)
    print("BÚSQUEDA DE INFORMACIÓN DE FINANCIACIÓN EN CONPES")
    print("="*80)

    vector_search = VectorSearch()
    query_enhancer = QueryEnhancer()

    # Document ID for CONPES
    documento_id = "conpes_colombia___política_nacional_de_inteligencia_artificial"

    # Test queries
    queries = [
        "¿Cuál es el costo estimado y de dónde proviene la financiación de las políticas propuestas?",
        "presupuesto financiación recursos económicos",
        "costo inversión",
        "fuentes de financiación"
    ]

    for query in queries:
        print(f"\n{'─'*80}")
        print(f"Query: {query}")
        print(f"{'─'*80}")

        # Search in inteligencia_artificial area with CONPES filter
        chunks = vector_search.search_with_context(
            query=query,
            area="inteligencia_artificial",  # CORRECT AREA!
            documento_id=documento_id,
            top_k=10,
            expand_context=False
        )

        print(f"\nChunks encontrados: {len(chunks)}")

        if chunks:
            print("\nTop 3 resultados:")
            for i, chunk in enumerate(chunks[:3], 1):
                print(f"\n[{i}] Score: {chunk.get('score', 0):.4f}")
                print(f"Citación: {chunk.get('citacion_corta', 'N/A')}")
                print(f"Texto (primeros 200 chars):")
                texto = chunk.get('texto', '')
                print(f"{texto[:200]}...")
        else:
            print("❌ No se encontraron chunks")

    # Now search in ALL documents in IA area (without filter)
    print(f"\n{'='*80}")
    print("BÚSQUEDA SIN FILTRO DE DOCUMENTO (toda el área IA)")
    print(f"{'='*80}")

    query = "¿Cuál es el costo estimado y de dónde proviene la financiación de las políticas propuestas?"
    chunks = vector_search.search_with_context(
        query=query,
        area="inteligencia_artificial",
        top_k=15,
        expand_context=False
    )

    print(f"\nChunks encontrados: {len(chunks)}")

    if chunks:
        # Group by document
        by_doc = {}
        for chunk in chunks:
            doc_id = chunk.get('documento_id', 'unknown')
            if doc_id not in by_doc:
                by_doc[doc_id] = []
            by_doc[doc_id].append(chunk)

        print(f"\nDocumentos con resultados:")
        for doc_id, doc_chunks in by_doc.items():
            doc_name = doc_chunks[0].get('documento_nombre', 'N/A')
            avg_score = sum(c.get('score', 0) for c in doc_chunks) / len(doc_chunks)
            print(f"  - {doc_name}: {len(doc_chunks)} chunks, avg_score={avg_score:.4f}")

        # Show top result
        print(f"\nMejor resultado:")
        top_chunk = chunks[0]
        print(f"Documento: {top_chunk.get('documento_nombre', 'N/A')}")
        print(f"Citación: {top_chunk.get('citacion_corta', 'N/A')}")
        print(f"Score: {top_chunk.get('score', 0):.4f}")
        print(f"Texto:")
        print(top_chunk.get('texto', '')[:500])


if __name__ == "__main__":
    search_financing_info()

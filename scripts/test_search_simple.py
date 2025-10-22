"""
Simple search test - just vector search without re-ranking.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.vector_search import VectorSearch
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")

# Create searcher
print("Initializing search...")
searcher = VectorSearch()

# Check collection
stats = searcher.get_collection_stats()
print(f"\nCollection: {stats.get('name')}")
print(f"Points: {stats.get('points_count')}")
print(f"Status: {stats.get('status')}")

if stats.get('points_count', 0) == 0:
    print("\n❌ Collection is empty!")
    sys.exit(1)

# Test query
query = "¿Qué es un OCAD?"
print(f"\n🔍 Searching: {query}")

results = searcher.search(query, top_k=5)

print(f"\n✅ Found {len(results)} results:\n")

for i, chunk in enumerate(results, 1):
    print(f"[{i}] Score: {chunk['score']:.4f}")
    print(f"    Doc: {chunk['documento_nombre']}")
    print(f"    Citación: {chunk['citacion_corta']}")
    preview = chunk['texto'][:150] + "..."
    print(f"    Texto: {preview}\n")

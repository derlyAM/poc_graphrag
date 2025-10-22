"""Quick pipeline test with one query."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import RAGPipeline

print("Inicializando pipeline...")
pipeline = RAGPipeline()

query = "¿Qué es un OCAD?"
print(f"\nPregunta: {query}\n")

result = pipeline.query(query)

print("\n" + "="*80)
print("RESPUESTA:")
print("="*80)
print(result["answer"])

print("\n" + "="*80)
print("MÉTRICAS:")
print("="*80)
metrics = result["metrics"]
print(f"Tiempo: {metrics['total_time']:.2f}s")
print(f"Chunks: {metrics['chunks_reranked']}")
print(f"Costo: ${metrics['llm_cost']:.6f}")

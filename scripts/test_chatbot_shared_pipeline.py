"""
Test script para verificar que el chatbot funciona con pipeline compartido.

Verifica que:
1. Se puede crear un RAGPipeline
2. Se puede reutilizar en ConversationalPipeline
3. No hay errores de Qdrant por múltiples conexiones
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import RAGPipeline
from src.chatbot import ConversationalPipeline
from loguru import logger

logger.info("\n" + "="*60)
logger.info("TEST: Chatbot con Pipeline Compartido")
logger.info("="*60 + "\n")

# 1. Crear RAGPipeline
logger.info("1. Creando RAGPipeline...")
rag_pipeline = RAGPipeline()
logger.success("✅ RAGPipeline creado exitosamente")

# 2. Crear ConversationalPipeline reutilizando el RAGPipeline
logger.info("\n2. Creando ConversationalPipeline con pipeline compartido...")
chatbot = ConversationalPipeline(
    area="inteligencia_artificial",
    shared_pipeline=rag_pipeline
)
logger.success("✅ ConversationalPipeline creado exitosamente (modo compartido)")

# 3. Test de query simple (modo corto)
logger.info("\n3. Test de query en modo CORTO...")
result = chatbot.query(
    question="¿Qué es la inteligencia artificial?",
    response_mode="short",
    enable_multihop=False,  # Desactivar para test rápido
    enable_hyde=False,
    top_k_retrieval=5
)

logger.info(f"\n{'='*60}")
logger.info("RESULTADO MODO CORTO:")
logger.info(f"{'='*60}")
logger.info(f"Pregunta: {result['original_question']}")
logger.info(f"Respuesta: {result['answer'][:200]}...")
logger.info(f"Fuentes: {result['num_sources']}")
logger.info(f"Modo: {result['mode']}")

# 4. Test de query con contexto (modo largo)
logger.info("\n4. Test de query con CONTEXTO (modo largo)...")
result2 = chatbot.query(
    question="¿Cuáles son sus aplicaciones?",  # "sus" debería reformularse
    response_mode="long",
    enable_multihop=False,
    enable_hyde=False,
    top_k_retrieval=5
)

logger.info(f"\n{'='*60}")
logger.info("RESULTADO MODO LARGO CON CONTEXTO:")
logger.info(f"{'='*60}")
logger.info(f"Pregunta original: {result2['original_question']}")
logger.info(f"Pregunta reformulada: {result2['reformulated_question']}")
logger.info(f"¿Fue reformulada?: {result2['was_reformulated']}")
logger.info(f"Respuesta: {result2['answer'][:200]}...")
logger.info(f"Fuentes: {result2['num_sources']}")
logger.info(f"Modo: {result2['mode']}")

# 5. Verificar estadísticas
logger.info("\n5. Estadísticas del chatbot...")
stats = chatbot.get_stats()
logger.info(f"Total queries: {stats['total_queries']}")
logger.info(f"Queries reformuladas: {stats['queries_reformulated']}")
logger.info(f"Tasa de reformulación: {stats['reformulation_rate']:.1%}")
logger.info(f"Longitud conversación: {stats['conversation_length']}")

logger.success("\n✅ TODOS LOS TESTS PASARON EXITOSAMENTE")
logger.info("El chatbot funciona correctamente con pipeline compartido")
logger.info("No hay errores de Qdrant por múltiples conexiones\n")

"""
Test script para verificar que el singleton de RAGPipeline funciona correctamente.

Simula el comportamiento de múltiples páginas accediendo al pipeline.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared_resources import get_shared_pipeline, SharedPipelineManager
from loguru import logger

logger.info("\n" + "="*60)
logger.info("TEST: Singleton RAGPipeline")
logger.info("="*60 + "\n")

# Simular múltiples accesos como lo harían diferentes páginas de Streamlit
logger.info("1. Primera página accede al pipeline...")
pipeline1 = get_shared_pipeline()
id1 = id(pipeline1)
logger.success(f"✅ Pipeline obtenido (ID: {id1})")

logger.info("\n2. Segunda página accede al pipeline...")
pipeline2 = get_shared_pipeline()
id2 = id(pipeline2)
logger.success(f"✅ Pipeline obtenido (ID: {id2})")

logger.info("\n3. Tercera página accede al pipeline...")
pipeline3 = get_shared_pipeline()
id3 = id(pipeline3)
logger.success(f"✅ Pipeline obtenido (ID: {id3})")

# Verificar que todas son la misma instancia
logger.info("\n" + "="*60)
logger.info("VERIFICACIÓN DE SINGLETON")
logger.info("="*60)

if id1 == id2 == id3:
    logger.success("✅ SINGLETON CORRECTO: Todas las instancias son la misma")
    logger.info(f"   ID compartido: {id1}")
else:
    logger.error("❌ ERROR: Se crearon múltiples instancias")
    logger.error(f"   ID1: {id1}")
    logger.error(f"   ID2: {id2}")
    logger.error(f"   ID3: {id3}")
    sys.exit(1)

# Verificar que el manager también es singleton
logger.info("\n4. Verificar que el manager también es singleton...")
manager1 = SharedPipelineManager()
manager2 = SharedPipelineManager()
manager3 = SharedPipelineManager()

if id(manager1) == id(manager2) == id(manager3):
    logger.success("✅ Manager también es singleton")
else:
    logger.error("❌ ERROR: Manager no es singleton")
    sys.exit(1)

# Test de funcionalidad básica
logger.info("\n5. Test de funcionalidad del pipeline...")
try:
    result = pipeline1.query(
        question="¿Qué es la inteligencia artificial?",
        area="inteligencia_artificial",
        top_k_retrieval=3,
        enable_multihop=False,
        enable_hyde=False,
        enable_validation=False
    )

    if result and "answer" in result:
        logger.success("✅ Pipeline funciona correctamente")
        logger.info(f"   Respuesta: {result['answer'][:100]}...")
        logger.info(f"   Fuentes: {result.get('num_sources', 0)}")
    else:
        logger.error("❌ Pipeline no retornó resultado válido")
        sys.exit(1)

except Exception as e:
    logger.error(f"❌ Error al ejecutar query: {e}")
    sys.exit(1)

logger.info("\n" + "="*60)
logger.success("✅ TODOS LOS TESTS PASARON")
logger.info("="*60)
logger.info("\nEl singleton funciona correctamente:")
logger.info("- Solo se crea UNA instancia de RAGPipeline")
logger.info("- Múltiples accesos retornan la misma instancia")
logger.info("- No hay error de Qdrant por múltiples conexiones")
logger.info("- El pipeline funciona correctamente\n")

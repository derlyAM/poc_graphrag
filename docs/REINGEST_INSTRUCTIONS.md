# 🔄 Instrucciones para Re-Ingestar Documentos

## ⚠️ Problema Actual

Los chunks en Qdrant fueron creados con la versión anterior del código que **NO guardaba** los campos `capitulo` y `titulo`. Por eso las búsquedas filtradas por capítulo no funcionan.

## ✅ Solución: Re-Ingestar los Documentos

Necesitas volver a procesar los PDFs para que los chunks incluyan toda la metadata necesaria.

### Paso 1: Detener Streamlit

Si tienes Streamlit corriendo, deténlo (`Ctrl+C`) para liberar la base de datos Qdrant.

### Paso 2: Re-Ingestar Documentos

```bash
# Activar entorno virtual (si no está activo)
source venv/bin/activate  # En Mac/Linux
# o
venv\Scripts\activate  # En Windows

# Re-ingestar PDFs (esto recreará la colección)
python scripts/01_ingest_pdfs.py
```

**IMPORTANTE**: El script debe usar `recreate_collection=True` para borrar la colección anterior y crear una nueva.

### Paso 3: Verificar el Script de Ingestión

Asegúrate de que tu script `scripts/01_ingest_pdfs.py` esté configurado correctamente.

Si el script no existe o necesita actualización, aquí está la versión correcta:

```python
"""
Script to ingest PDF documents into Qdrant.
Extracts PDFs, chunks them, generates embeddings, and loads into Qdrant.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.ingest.pdf_extractor import extract_all_pdfs
from src.ingest.chunker import chunk_documents
from src.ingest.vectorizer import vectorize_chunks

def main():
    """Main ingestion function."""
    logger.info("=" * 80)
    logger.info("STARTING DOCUMENT INGESTION")
    logger.info("=" * 80)

    # Define paths
    data_dir = Path(__file__).parent.parent / "data"

    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return

    # Step 1: Extract PDFs
    logger.info("\n[STEP 1] Extracting PDFs")
    documents = extract_all_pdfs(data_dir)

    if not documents:
        logger.error("No documents were extracted!")
        return

    logger.info(f"Extracted {len(documents)} documents")

    # Step 2: Chunk documents
    logger.info("\n[STEP 2] Chunking documents")
    chunks = chunk_documents(documents)

    logger.info(f"Created {len(chunks)} chunks")

    # Step 3: Vectorize and upload
    logger.info("\n[STEP 3] Generating embeddings and uploading to Qdrant")
    vectorizer = vectorize_chunks(
        chunks,
        recreate_collection=True  # IMPORTANTE: Recrear colección
    )

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("INGESTION COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)
    logger.info(f"Documents processed: {len(documents)}")
    logger.info(f"Total chunks: {len(chunks)}")
    logger.info(f"Total cost: ${vectorizer.total_cost:.6f}")

if __name__ == "__main__":
    main()
```

### Paso 4: Verificar que Funcionó

Después de la re-ingestión, verifica que los chunks tienen los campos correctos:

```bash
python scripts/test_chapter_queries.py
```

O prueba directamente en Streamlit:

```bash
streamlit run app/streamlit_app.py
```

Y prueba una query como:
- "Resume el capítulo 2 del acuerdo único"
- "Dame un resumen del título 4"

### Paso 5: Verificar los Logs

Durante la ingestión, deberías ver:

```
[STEP 1] Extracting PDFs
Legal structure: X títulos, Y capítulos, Z artículos, ...

[STEP 2] Chunking documents
Created ABC chunks for legal document

[STEP 3] Generating embeddings and uploading to Qdrant
```

## 🔍 Troubleshooting

### Error: "Storage folder is already accessed"

**Causa**: Streamlit u otro proceso está usando Qdrant.

**Solución**:
1. Detén todos los procesos que usen Qdrant (Streamlit, scripts, etc.)
2. Vuelve a intentar

### Error: "No documents were extracted"

**Causa**: No hay PDFs en la carpeta `data/`

**Solución**:
1. Verifica que tienes PDFs en `data/`
2. Verifica que los archivos terminan en `.pdf`

### Los chunks no tienen capítulo/título

**Causa**: El PDF no fue detectado como documento "legal"

**Solución**:
1. Verifica los logs: debe decir "Document type detected: legal"
2. Si dice "generic" o "technical", el PDF no tiene suficientes patrones legales (TÍTULO, CAPÍTULO, ARTÍCULO)
3. Revisa el PDF y asegúrate de que tiene la estructura adecuada

### Aún no funciona después de re-ingestar

**Debugging**:

1. Verifica que la colección fue recreada:
```python
from src.retrieval.vector_search import VectorSearch
searcher = VectorSearch()
stats = searcher.get_collection_stats()
print(stats)
```

2. Inspecciona un chunk manualmente para ver su estructura

3. Revisa los logs del pipeline para ver qué filtros se están aplicando

## 📊 Datos de Ejemplo

Después de la re-ingestión correcta, un chunk debería verse así:

```json
{
  "chunk_id": "uuid-...",
  "documento_id": "acuerdo_unico_...",
  "documento_nombre": "Acuerdo Único...",
  "articulo": "4.5.1",
  "capitulo": "2",        // ← ESTO DEBE EXISTIR
  "titulo": "4",          // ← ESTO DEBE EXISTIR
  "seccion": null,
  "subseccion": null,
  "texto": "...",
  "citacion_corta": "Art. 4.5.1, Acuerdo...",
  ...
}
```

## ✅ Checklist

- [ ] Streamlit detenido
- [ ] Script de ingestión actualizado con `recreate_collection=True`
- [ ] PDFs están en carpeta `data/`
- [ ] Re-ingestión completada sin errores
- [ ] Logs muestran "Document type detected: legal"
- [ ] Test de queries funcionando
- [ ] Streamlit muestra resultados para queries de capítulos

## 🎯 Próximos Pasos

Una vez que la re-ingestión esté completa:

1. Prueba queries estructurales en Streamlit
2. Verifica que se detectan los filtros correctamente en los logs
3. Confirma que se recuperan múltiples chunks del mismo capítulo
4. Valida que los resúmenes son completos y estructurados

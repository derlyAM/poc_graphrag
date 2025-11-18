# Guía: Separación por Áreas de Conocimiento (v1.3.0)

**Fecha:** 2025-11-12
**Versión:** 1.3.0
**Implementación:** Opción A (Una colección + Filtros de metadata)

---

## ✅ IMPLEMENTACIÓN COMPLETADA

El sistema ahora soporta **separación total por áreas de conocimiento**, garantizando que las consultas SOLO busquen en el área seleccionada.

### Áreas Disponibles

```python
VALID_AREAS = {
    "sgr": "Sistema General de Regalías",
    "inteligencia_artificial": "Inteligencia Artificial",
    "general": "General"
}
```

---

## 📋 CAMBIOS IMPLEMENTADOS

### 1. Configuración (src/config.py)
- ✅ Constantes `VALID_AREAS` y `DEFAULT_AREA`
- ✅ Función `validate_area(area: str)` - Validación obligatoria
- ✅ Función `get_area_display_name(area: str)` - Nombres completos

### 2. Metadata de Chunks (src/ingest/document_hierarchy_processor.py)
- ✅ Campo `area` agregado a TODOS los chunks
- ✅ Se propaga desde metadata del documento

### 3. Vector Search (src/retrieval/vector_search.py)
- ✅ Parámetro `area: str` **OBLIGATORIO** en `search()`
- ✅ Parámetro `area: str` **OBLIGATORIO** en `search_with_context()`
- ✅ Filtro automático por área en `_build_filter()`
- ✅ Validación con `validate_area()` en cada búsqueda
- ✅ Logging: `[ÁREA:sgr] Searching for...`

### 4. Multihop Retriever (src/retrieval/multihop_retriever.py)
- ✅ Parámetro `area: str` en `retrieve_multihop()`
- ✅ Parámetro `area: str` en `retrieve_comparison()`
- ✅ Parámetro `area: str` en `retrieve_conditional()`
- ✅ Propagación automática en búsquedas iterativas

### 5. HyDE Retriever (src/retrieval/hyde_retriever.py)
- ✅ Parámetro `area: str` en `retrieve()`
- ✅ Parámetro `area: str` en `retrieve_with_hyde_hybrid()`
- ✅ Propagación a todas las búsquedas (HyDE + original + fallback)

### 6. RAG Pipeline (src/pipeline.py)
- ✅ Parámetro `area: str` **OBLIGATORIO** en `query()`
- ✅ Validación automática con `validate_area()`
- ✅ Propagación a todos los métodos de retrieval
- ✅ Logging mejorado con área en cada query

### 7. UI Streamlit (app/streamlit_app.py)
- ✅ **Selector de área obligatorio** en sidebar (primer control)
- ✅ Dropdown con nombres legibles
- ✅ Info box mostrando área seleccionada
- ✅ Parámetro `area` en llamada a `pipeline.query()`

### 8. Script de Ingestión (scripts/01_ingest_pdfs.py)
- ✅ Argumento obligatorio `--area` en línea de comandos
- ✅ Argumento opcional `--data-dir` para especificar carpeta
- ✅ Validación automática del área
- ✅ Metadata `area` agregada a TODOS los documentos procesados

---

## 🚀 USO DEL SISTEMA

### 1. Ingestar Documentos por Área

#### Procesar documentos de SGR (área existente)

```bash
python scripts/01_ingest_pdfs.py --area sgr
```

#### Procesar documentos de Inteligencia Artificial (área nueva)

```bash
python scripts/01_ingest_pdfs.py --area inteligencia_artificial --data-dir data_topic_IA
python scripts/01_ingest_pdfs.py --area sgr --data-dir data
```

#### Ver opciones disponibles

```bash
python scripts/01_ingest_pdfs.py --help
```

**Salida esperada:**
```
usage: 01_ingest_pdfs.py [-h] --area {sgr,inteligencia_artificial,general}
                         [--data-dir DATA_DIR]

Ingestar PDFs en el sistema RAG con separación por área

optional arguments:
  -h, --help            show this help message and exit
  --area {sgr,inteligencia_artificial,general}
                        Área de conocimiento para los documentos. Opciones:
                        sgr, inteligencia_artificial, general
  --data-dir DATA_DIR   Directorio de datos (opcional, sobrescribe config)
```

---

### 2. Usar la UI de Streamlit

#### Iniciar la aplicación

```bash
streamlit run app/streamlit_app.py
```

#### Seleccionar área

1. **En el sidebar**, aparece como PRIMER control: **"🎯 Área de Consulta"**
2. Opciones disponibles:
   - Sistema General de Regalías
   - Inteligencia Artificial
   - General
3. **IMPORTANTE:** Solo se buscarán documentos del área seleccionada

#### Ejemplo de consulta

```
Área seleccionada: Inteligencia Artificial

Query: ¿Qué es el EU AI Act?

✅ Resultado: Solo chunks del área "inteligencia_artificial"
❌ NO retorna: Chunks de "sgr" ni "general"
```

---

### 3. Usar el Pipeline Programáticamente

```python
from src.pipeline import RAGPipeline

# Inicializar pipeline
pipeline = RAGPipeline()

# Query en área SGR
result_sgr = pipeline.query(
    question="¿Qué es un OCAD?",
    area="sgr"  # OBLIGATORIO
)

# Query en área IA
result_ia = pipeline.query(
    question="¿Qué sistemas de IA son de alto riesgo?",
    area="inteligencia_artificial"  # OBLIGATORIO
)

# ❌ ERROR: Sin área (lanza ValueError)
result = pipeline.query(question="Test")  # ValueError: área requerida
```

---

## 🔒 GARANTÍAS DE SEPARACIÓN

### Nivel 1: Validación Obligatoria

```python
# En TODOS los puntos de entrada:
area = validate_area(area)  # Lanza ValueError si inválida

# Áreas válidas:
✅ "sgr" → Válido
✅ "inteligencia_artificial" → Válido
✅ "general" → Válido
❌ "ia" → ValueError
❌ "SGR" → Normalizado a "sgr" (válido)
❌ "" → ValueError
❌ None → ValueError
```

### Nivel 2: Filtro Automático en Qdrant

```python
# En _build_filter() (vector_search.py):
must_conditions.append(
    FieldCondition(key="area", match=MatchValue(value=area))
)

# SIEMPRE se agrega, sin excepciones
```

### Nivel 3: Logging Exhaustivo

```python
# Cada búsqueda registra:
logger.info(f"[ÁREA:{area}] Searching for: '{query}'")
logger.info(f"[ÁREA:{area}] Chunks encontrados: {len(chunks)}")

# Ejemplo en logs:
[ÁREA:sgr] Searching for: '¿Qué es un OCAD?'
[ÁREA:sgr] Chunks encontrados: 15
```

---

## 📊 VERIFICACIÓN DEL SISTEMA

### Verificar chunks por área en Qdrant

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(path="./storage/qdrant_local")
collection = "normativa_sgr"

# Contar chunks por área
for area in ["sgr", "inteligencia_artificial", "general"]:
    result = client.scroll(
        collection_name=collection,
        scroll_filter=Filter(
            must=[FieldCondition(key="area", match=MatchValue(value=area))]
        ),
        limit=1,
        with_payload=False
    )
    count = len(result[0])
    print(f"Área '{area}': {count} chunks")
```

**Salida esperada (ejemplo):**
```
Área 'sgr': 487 chunks
Área 'inteligencia_artificial': 0 chunks (antes de procesar)
Área 'general': 0 chunks
```

### Probar separación en UI

```python
# Test 1: Query en SGR
Área: Sistema General de Regalías
Query: "OCAD"
✅ Esperado: Solo chunks con area="sgr"

# Test 2: Query en IA
Área: Inteligencia Artificial
Query: "EU AI Act"
✅ Esperado: Solo chunks con area="inteligencia_artificial"

# Test 3: Cambiar área y re-buscar
Área: SGR → Resultados de SGR
Cambiar a IA → Resultados de IA
✅ Esperado: Resultados COMPLETAMENTE diferentes
```

---

## 🔄 FLUJO DE DATOS COMPLETO

```
┌─────────────────────────────────────────────────────────────┐
│  1. INGESTIÓN (Offline)                                     │
│                                                             │
│  python scripts/01_ingest_pdfs.py \                         │
│    --area inteligencia_artificial \                         │
│    --data-dir data_topic_IA                                 │
│                                                             │
│  ↓                                                          │
│  PDF → Extracción → Chunks → metadata["area"] = "ia"       │
│  ↓                                                          │
│  Vectorización → Carga en Qdrant                            │
│    {vector, payload: {area: "ia", texto: "...", ...}}       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  2. CONSULTA (Online - Streamlit)                           │
│                                                             │
│  Usuario selecciona área en UI: "Inteligencia Artificial"   │
│  ↓                                                          │
│  area = "inteligencia_artificial"                           │
│  ↓                                                          │
│  pipeline.query(question="...", area="inteligencia_art...") │
│  ↓                                                          │
│  validate_area(area)  # ✅ Válido                           │
│  ↓                                                          │
│  vector_search.search(query="...", area="ia")               │
│  ↓                                                          │
│  _build_filter(area="ia")                                   │
│    → Filter(must=[FieldCondition(key="area", value="ia")])  │
│  ↓                                                          │
│  Qdrant.search(filter=...)                                  │
│    → Solo retorna chunks con area="ia"                      │
│  ↓                                                          │
│  Re-ranking → Generation → Respuesta                        │
│    (todos basados en chunks de IA únicamente)               │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚠️ PUNTOS IMPORTANTES

### 1. Área es SIEMPRE obligatoria

```python
# ❌ ESTO NO COMPILA:
pipeline.query(question="Test")

# ✅ ESTO SÍ:
pipeline.query(question="Test", area="sgr")
```

### 2. No existe "buscar en todas las áreas"

Por diseño, para garantizar separación total.

Si necesitas buscar en múltiples áreas:
```python
# Opción 1: Búsquedas separadas y merge manual
results_sgr = pipeline.query(question="...", area="sgr")
results_ia = pipeline.query(question="...", area="inteligencia_artificial")

# Opción 2: Cambiar el área en UI y buscar de nuevo
```

### 3. Documentos antiguos sin campo 'area'

Si tienes chunks antiguos SIN el campo 'area':
- ⚠️ NO aparecerán en ninguna búsqueda
- ✅ Solución: Re-procesar con `--area general` o el área correspondiente

```bash
# Re-procesar documentos existentes
python scripts/01_ingest_pdfs.py --area sgr
```

### 4. Nombres normalizados

```python
# Internamente, todas las áreas se normalizan a lowercase:
"SGR" → "sgr"
"Inteligencia_Artificial" → "inteligencia_artificial"
" sgr " → "sgr"
```

---

## 🎯 CASOS DE USO RECOMENDADOS

### Caso 1: Usuario consulta SOLO sobre SGR

```
UI: Área = "Sistema General de Regalías"
Queries: Documentos normativos, OCAD, viabilidad, etc.
✅ Solo busca en chunks de SGR
```

### Caso 2: Usuario consulta SOLO sobre IA

```
UI: Área = "Inteligencia Artificial"
Queries: EU AI Act, ética IA, regulación, etc.
✅ Solo busca en chunks de IA
```

### Caso 3: Usuario necesita ambos (futuro)

```
Opción A: Cambiar área en UI y buscar dos veces
Opción B: Usar colecciones separadas (Opción B del análisis)
```

---

## 📚 DOCUMENTOS DE REFERENCIA

- **Análisis Completo:** `docs/ANALISIS_DOCUMENTOS_IA.md`
- **Arquitectura Técnica:** Ver sección 11 del análisis
- **Comparación Opción A vs B:** `docs/ANALISIS_DOCUMENTOS_IA.md#11-arquitecturas-de-separacion`

---

## 🔧 TROUBLESHOOTING

### Problema: "ValueError: Área 'X' no válida"

**Causa:** Área no reconocida

**Solución:**
```python
# Ver áreas válidas:
from src.config import VALID_AREAS
print(VALID_AREAS.keys())  # dict_keys(['sgr', 'inteligencia_artificial', 'general'])

# Usar una de las áreas válidas
```

### Problema: No encuentra chunks después de ingestión

**Causa:** Chunks no tienen metadata 'area' o usan área diferente

**Solución:**
```python
# Verificar área de chunks en Qdrant:
from qdrant_client import QdrantClient

client = QdrantClient(path="./storage/qdrant_local")
chunks = client.scroll(collection_name="normativa_sgr", limit=5)

for chunk in chunks[0]:
    print(f"Chunk {chunk.id}: area='{chunk.payload.get('area')}'")

# Si área es None o diferente, re-procesar:
python scripts/01_ingest_pdfs.py --area <area_correcta>
```

### Problema: Mezcla resultados de diferentes áreas

**Causa:** Bug en filtro (muy improbable con implementación actual)

**Solución:**
```python
# Verificar logs:
# Buscar líneas con [ÁREA:X]
# Si aparece [ÁREA:sgr] pero retorna chunks de IA, reportar bug

# Workaround temporal:
# Validar chunks manualmente:
for chunk in result["chunks"]:
    assert chunk["area"] == "sgr", f"Chunk área incorrecta: {chunk['area']}"
```

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Para Nuevas Áreas

Si quieres agregar un área nueva (ej: "finanzas"):

1. ✅ **Agregar a `src/config.py`:**
   ```python
   VALID_AREAS = {
       "sgr": "Sistema General de Regalías",
       "inteligencia_artificial": "Inteligencia Artificial",
       "finanzas": "Finanzas Públicas",  # NUEVO
       "general": "General"
   }
   ```

2. ✅ **Procesar documentos:**
   ```bash
   python scripts/01_ingest_pdfs.py --area finanzas --data-dir data/finanzas
   ```

3. ✅ **Usar en UI:**
   - Selector automáticamente mostrará "Finanzas Públicas"
   - Seleccionar y consultar normalmente

---

**Fecha de creación:** 2025-11-12
**Autor:** Claude Code
**Versión del sistema:** v1.3.0

# 📖 Flujo Implementado: Sistema RAG Explicado Paso a Paso

> **Para personas sin conocimientos técnicos previos**
>
> Este documento explica cómo funciona el sistema RAG (Retrieval-Augmented Generation) implementado,
> desde que haces una pregunta hasta que obtienes la respuesta.

**Versión del Sistema**: v1.1.1 (2025-10-21)
**Última Actualización**: 2025-10-21

---

## 📚 Índice

1. [¿Qué es un Sistema RAG?](#qué-es-un-sistema-rag)
2. [Arquitectura General](#arquitectura-general)
3. [Fase 1: Preparación (Ingestión de Documentos)](#fase-1-preparación-ingestión-de-documentos)
4. [Fase 2: Consulta (Cuando Haces una Pregunta)](#fase-2-consulta-cuando-haces-una-pregunta)
5. [Componentes Técnicos Detallados](#componentes-técnicos-detallados)
6. [Versiones de Software Utilizadas](#versiones-de-software-utilizadas)
7. [Ejemplos Paso a Paso](#ejemplos-paso-a-paso)

---

## ¿Qué es un Sistema RAG?

### Analogía Simple

Imagina que tienes una biblioteca enorme con miles de documentos legales. Cuando alguien te hace una pregunta:

1. **Sin RAG**: Tendrías que leer TODOS los documentos completos para encontrar la respuesta → ❌ Lento e imposible
2. **Con RAG**: El sistema busca inteligentemente SOLO las partes relevantes y luego genera una respuesta precisa → ✅ Rápido y efectivo

### Los 3 Componentes de RAG

```
┌─────────────────────────────────────────────────────────┐
│  RAG = Retrieval + Augmented + Generation               │
│        (Búsqueda) (Mejorada)   (Generación)             │
└─────────────────────────────────────────────────────────┘

  R: Retrieval      → Buscar fragmentos relevantes en la base de datos
  A: Augmented      → Mejorar la búsqueda con contexto adicional
  G: Generation     → Generar respuesta natural usando IA
```

---

## Arquitectura General

### Vista de Alto Nivel

```
┌─────────────────────────────────────────────────────────────┐
│                   USUARIO (Streamlit)                        │
│                                                              │
│  "¿Qué dice el artículo 4.5.1 sobre ajustes?"              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              SISTEMA RAG (src/pipeline.py)                   │
│                                                              │
│  [Paso 0] Query Enhancement      ← Mejora la pregunta       │
│  [Paso 1] Vector Search          ← Busca chunks relevantes  │
│  [Paso 2] Re-ranking             ← Ordena por relevancia    │
│  [Paso 3] Generate Answer        ← IA genera respuesta      │
│  [Paso 4] Validate Citations     ← Valida referencias       │
│  [Paso 5] Enhance Answer         ← Agrega fuentes           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  RESPUESTA AL USUARIO                        │
│                                                              │
│  "El artículo 4.5.1 establece que los ajustes..."          │
│  Fuente: Art. 4.5.1, Acuerdo 03/2021                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Fase 1: Preparación (Ingestión de Documentos)

> **Cuándo ocurre**: UNA SOLA VEZ cuando cargas los PDFs al sistema
>
> **Comando**: `python scripts/01_ingest_pdfs.py`

### Paso 1.1: Extracción del PDF

**¿Qué hace?**
Convierte el PDF en texto preservando su estructura jerárquica.

```
PDF Original                     →    Texto Estructurado
├─ TÍTULO 4                           {
│  ├─ CAPÍTULO 5                        "titulos": [{"numero": "4", ...}],
│  │  └─ Artículo 4.5.1                 "capitulos": [{"numero": "5", ...}],
│  │     Texto del artículo...          "articulos": [{"numero": "4.5.1", ...}]
│  │                                   }
```

**Herramienta usada**: `pymupdf4llm` (versión 0.0.27)

**Código**: `src/ingest/pdf_extractor.py`

### Paso 1.2: Chunking Jerárquico

**¿Qué es un "chunk"?**
Un fragmento pequeño del documento (aproximadamente 500 palabras o tokens).

**¿Por qué chunks pequeños?**
- ✅ Más precisos para buscar
- ✅ Caben en la memoria del modelo de IA
- ✅ Se pueden combinar si necesitas más contexto

```
Documento Completo (200 páginas)
        ↓
División Inteligente
        ↓
┌──────────────────────────────────────────────┐
│ Chunk 1: Título 4 > Capítulo 5 > Art. 4.5.1 │
│ Texto: "Los ajustes procederán cuando..."   │
│ Tokens: 245                                  │
│ Parent: Capítulo 5 (UUID)                   │
│ Children: [] (no tiene hijos)               │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ Chunk 2: Título 4 > Capítulo 5 > Art. 4.5.2 │
│ Texto: "Las liberaciones de recursos..."    │
│ Tokens: 312                                  │
│ Parent: Capítulo 5 (UUID)                   │
│ Children: [] (no tiene hijos)               │
└──────────────────────────────────────────────┘
```

**Procesador**: `DocumentHierarchyProcessor` (src/ingest/document_hierarchy_processor.py)

**Configuración**:
- Tamaño máximo por chunk: **500 tokens** (~400 palabras)
- Solapamiento entre chunks: **50 tokens** (para no perder contexto)

### Paso 1.3: Vectorización (Embeddings)

**¿Qué es vectorización?**
Convertir texto en números que representan su **significado semántico**.

```
Texto Original:
"Los ajustes a los proyectos de inversión aprobados procederán..."

        ↓ OpenAI text-embedding-3-small

Vector (1536 números):
[0.023, -0.145, 0.891, ..., -0.234]
      ↑
Representa el "significado" del texto en espacio matemático
```

**¿Por qué es útil?**
Dos textos con significado similar tendrán vectores cercanos, aunque usen palabras diferentes.

**Ejemplo**:
```
"¿Qué es un OCAD?"     →  Vector A: [0.1, 0.8, ...]
"Define OCAD"          →  Vector B: [0.12, 0.79, ...]  ← Similar!
"Receta de pizza"      →  Vector C: [-0.5, 0.2, ...]  ← Muy diferente
```

**Modelo usado**: `text-embedding-3-small` (OpenAI)
- Dimensiones: 1536
- Costo: $0.02 por 1M tokens

### Paso 1.4: Almacenamiento en Qdrant

**¿Qué es Qdrant?**
Una base de datos especializada en guardar y buscar vectores rápidamente.

```
┌─────────────────── Qdrant Database ────────────────────┐
│                                                         │
│  Collection: normativa_sgr                             │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │ Point ID: uuid-abc-123                      │       │
│  │ Vector: [0.023, -0.145, 0.891, ...]         │       │
│  │ Payload (Metadata):                         │       │
│  │   - chunk_id: "uuid-abc-123"                │       │
│  │   - documento_id: "acuerdo_03_2021"         │       │
│  │   - texto: "Los ajustes procederán..."      │       │
│  │   - nivel_jerarquico: 3 (artículo)          │       │
│  │   - titulo: "4"                             │       │
│  │   - capitulo: "5"                           │       │
│  │   - articulo: "4.5.1"                       │       │
│  │   - parent_id: "uuid-capitulo-5"            │       │
│  │   - hierarchy_path: "Doc > T4 > C5 > A4.5.1"│       │
│  │   - citacion_corta: "Art. 4.5.1, Ac. 03..."│       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  Total chunks almacenados: ~615                        │
└─────────────────────────────────────────────────────────┘
```

**Almacenamiento**: `./storage/qdrant_local/`

---

## Fase 2: Consulta (Cuando Haces una Pregunta)

> **Cuándo ocurre**: CADA VEZ que haces una pregunta en Streamlit
>
> **Tiempo total**: 3-8 segundos

### 📊 Vista General del Flujo

```
Tu Pregunta
    ↓
[0] Query Enhancement (0.1s)      "Mejoro tu pregunta"
    ↓
[1] Vector Search (1-2s)          "Busco 20 fragmentos relevantes"
    ↓
[2] Re-ranking (0.5-1s)           "Ordeno por relevancia REAL"
    ↓
[3] Generate Answer (2-4s)        "IA lee y genera respuesta"
    ↓
[4] Validate Citations (0.1s)     "Verifico que las citas sean correctas"
    ↓
[5] Enhance Answer (0.1s)         "Agrego referencias y formato"
    ↓
Respuesta Final
```

---

### [Paso 0] Query Enhancement

**Archivo**: `src/retrieval/query_enhancer.py`

**¿Qué hace?**
Mejora tu pregunta detectando filtros automáticamente.

#### Ejemplo 1: Detección de Filtros

```
ENTRADA:
"¿Qué dice el capítulo 3 sobre proyectos?"

PROCESAMIENTO:
1. Detecta patrón "capítulo 3" → filtro: capitulo="3"
2. Tipo de query: "structural" (busca sección específica)
3. Estrategia: "exhaustive" (necesita más chunks)

SALIDA:
{
  "original_query": "¿Qué dice el capítulo 3 sobre proyectos?",
  "enhanced_query": "proyectos inversión financiación",
  "filters": {
    "capitulo": "3"
  },
  "query_type": "structural",
  "retrieval_strategy": "exhaustive",
  "top_k_recommendation": 30  # Usa más chunks
}
```

#### Ejemplo 2: Query Semántica

```
ENTRADA:
"¿Qué requisitos necesito para un proyecto de ciencia?"

PROCESAMIENTO:
1. No detecta patrones estructurales
2. Tipo de query: "semantic" (busca por significado)
3. Estrategia: "standard" (búsqueda normal)

SALIDA:
{
  "original_query": "¿Qué requisitos necesito para un proyecto de ciencia?",
  "enhanced_query": "requisitos proyecto ciencia tecnología innovación",
  "filters": {},
  "query_type": "semantic",
  "retrieval_strategy": "standard",
  "top_k_recommendation": 20
}
```

#### Patrones Detectados

| Patrón | Ejemplo | Filtro Generado |
|--------|---------|-----------------|
| `capítulo N` | "capítulo 5" | `capitulo="5"` |
| `título N` | "título IV" | `titulo="4"` (convierte romano→número) |
| `artículo X.Y.Z` | "artículo 4.5.1.2" | `articulo="4.5.1.2"` |
| `sección N` | "sección 6" | `seccion="6"` |
| `anexo N` | "anexo 8" | `anexo_numero="8"` |

**Configuración**:
```python
# En config.py
top_k_retrieval: 20  # Chunks a recuperar (default)
```

---

### [Paso 1] Vector Search

**Archivo**: `src/retrieval/vector_search.py`

**¿Qué hace?**
Busca los chunks más relevantes usando similitud de vectores.

#### Proceso Detallado

```
1. VECTORIZAR PREGUNTA
   "¿Qué dice el capítulo 5?"
        ↓ OpenAI Embedding
   Vector Query: [0.15, -0.23, 0.87, ...]

2. BUSCAR EN QDRANT
   Qdrant compara:
   - Vector Query vs TODOS los vectores almacenados
   - Calcula distancia coseno (0 = lejano, 1 = idéntico)

   Resultados ordenados por score:
   ┌──────────────────────────────────────┐
   │ Chunk 1: Score 0.92 (muy similar)   │
   │ Chunk 2: Score 0.89                 │
   │ Chunk 3: Score 0.85                 │
   │ ...                                  │
   │ Chunk 20: Score 0.71                │
   └──────────────────────────────────────┘

3. APLICAR FILTROS (si existen)
   Si query enhancement detectó capitulo="5":
   - Qdrant filtra: SOLO chunks con capitulo="5"
   - Esto reduce falsos positivos

4. EXPANDIR CONTEXTO (opcional)
   Para cada chunk encontrado, agrega:
   - Parent chunk (capítulo completo)
   - Adjacent chunks (artículos vecinos)

   Esto da más contexto al LLM.
```

#### Ejemplo Real

```python
# Input
query = "¿Qué dice el capítulo 5 sobre ajustes?"
filters = {"capitulo": "5"}
top_k = 20

# Proceso
1. Vector query → [0.15, -0.23, ...]
2. Qdrant search con filtros
3. Expande contexto

# Output (20 chunks)
[
  {
    "chunk_id": "uuid-1",
    "texto": "Los ajustes procederán cuando...",
    "score": 0.92,  # Score vectorial
    "articulo": "4.5.1",
    "capitulo": "5",
    "hierarchy_path": "Acuerdo > Título 4 > Capítulo 5 > Artículo 4.5.1",
    "citacion_corta": "Art. 4.5.1, Acuerdo 03/2021"
  },
  {
    "chunk_id": "uuid-2",
    "texto": "Las variables susceptibles de ajuste son...",
    "score": 0.89,
    "articulo": "4.5.1.2",
    "capitulo": "5",
    ...
  },
  ...
]
```

**Tiempo**: 1-2 segundos
**Modelo**: `text-embedding-3-small` (OpenAI)

---

### [Paso 2] Re-ranking

**Archivo**: `src/retrieval/reranker.py`

**¿Qué hace?**
Re-ordena los chunks usando un modelo más sofisticado que lee **pregunta + texto completo**.

#### ¿Por qué Re-ranking?

**Búsqueda vectorial** (Paso 1):
- ✅ Rápida (milisegundos)
- ❌ Aproximada (solo compara vectores)
- ❌ No lee el texto realmente

**Re-ranking** (Paso 2):
- ✅ Precisa (lee pregunta + texto completo)
- ✅ Detecta relevancia REAL
- ❌ Más lenta (pero tolerable)

#### Proceso Detallado

```
ENTRADA: 20 chunks del paso anterior

PROCESAMIENTO:

1. CREAR PARES (query, chunk_text)
   [
     ("¿Qué dice el capítulo 5?", "Los ajustes procederán cuando..."),
     ("¿Qué dice el capítulo 5?", "Las variables susceptibles..."),
     ...
   ]

2. CROSS-ENCODER PREDICE RELEVANCIA

   Model: ms-marco-MiniLM-L-12-v2

   Para cada par → Score de relevancia (0-1)

   ┌───────────────────────────────────────────────┐
   │ Chunk 1: Vector Score 0.92 → Rerank 0.95 ✅  │
   │ Chunk 5: Vector Score 0.81 → Rerank 0.94 ⬆️  │ Subió!
   │ Chunk 2: Vector Score 0.89 → Rerank 0.88 ⬇️  │ Bajó
   │ Chunk 3: Vector Score 0.85 → Rerank 0.82     │
   │ ...                                           │
   └───────────────────────────────────────────────┘

3. RE-ORDENAR POR RERANK_SCORE

4. SELECCIONAR TOP-K (default: 5)
```

#### Ejemplo Real

```python
# Input
query = "¿Qué dice el capítulo 5 sobre ajustes?"
chunks = [20 chunks del vector search]
top_k = 5

# Modelo
model = "cross-encoder/ms-marco-MiniLM-L-12-v2"

# Output (5 mejores chunks)
[
  {
    "chunk_id": "uuid-1",
    "texto": "Los ajustes procederán cuando...",
    "original_score": 0.92,  # Score vectorial (Paso 1)
    "rerank_score": 0.95,    # Score cross-encoder (Paso 2) ⬆️
    ...
  },
  {
    "chunk_id": "uuid-5",
    "texto": "Variables susceptibles de ajuste...",
    "original_score": 0.81,
    "rerank_score": 0.94,  # ⬆️ Subió gracias al re-ranking!
    ...
  },
  ...
]
```

**Tiempo**: 0.5-1 segundo
**Modelo**: `cross-encoder/ms-marco-MiniLM-L-12-v2`
**Framework**: `sentence-transformers` (versión 5.1.0)

#### Versión del Modelo de Re-ranking

**Nombre completo**: `cross-encoder/ms-marco-MiniLM-L-12-v2`

**Características**:
- **Tipo**: Cross-Encoder (lee query + documento juntos)
- **Tamaño**: 12 capas, ~33M parámetros (MiniLM = versión compacta)
- **Entrenamiento**: MS MARCO dataset (Microsoft)
- **Uso**: CPU (no requiere GPU)
- **Velocidad**: ~50-100 pares/segundo en CPU estándar
- **Precisión**: +15-20% mejora vs búsqueda vectorial pura

**¿Por qué este modelo?**
- ✅ Rápido en CPU (no necesitas GPU)
- ✅ Buen balance precisión/velocidad
- ✅ Entrenado específicamente para re-ranking
- ✅ Open source (no cuesta dinero por uso)

**Alternativas evaluadas** (NO usadas):
- `ms-marco-MiniLM-L-6-v2`: Más rápido pero menos preciso
- `ms-marco-TinyBERT-L-6`: Aún más rápido pero demasiado impreciso
- `ms-marco-electra-base`: Más preciso pero más lento

---

### [Paso 3] Generate Answer

**Archivo**: `src/generation/llm_client.py`

**¿Qué hace?**
El modelo de lenguaje (GPT-4o-mini) lee los chunks y genera una respuesta natural.

#### Proceso

```
ENTRADA:
- Pregunta: "¿Qué dice el capítulo 5 sobre ajustes?"
- Contexto: 5 chunks mejor rankeados

PROMPT AL LLM:
┌─────────────────────────────────────────────────────┐
│ Eres un experto en normativa del SGR.              │
│                                                     │
│ CONTEXTO:                                          │
│ [Chunk 1]                                          │
│ Art. 4.5.1 (Acuerdo 03/2021)                      │
│ Los ajustes a los proyectos de inversión...       │
│                                                     │
│ [Chunk 2]                                          │
│ Art. 4.5.1.2 (Acuerdo 03/2021)                    │
│ Las variables susceptibles de ajuste son...        │
│ ...                                                 │
│                                                     │
│ PREGUNTA:                                          │
│ ¿Qué dice el capítulo 5 sobre ajustes?           │
│                                                     │
│ INSTRUCCIONES:                                     │
│ - Responde basándote SOLO en el contexto          │
│ - Cita los artículos específicos                  │
│ - Sé preciso y conciso                            │
└─────────────────────────────────────────────────────┘

GPT-4o-mini procesa y genera:

RESPUESTA:
"El Capítulo 5 del Acuerdo 03 de 2021 regula los ajustes
a proyectos de inversión aprobados.

Según el Artículo 4.5.1, los ajustes procederán cuando:
1. Existan modificaciones en el alcance del proyecto
2. Se requiera actualización de precios
3. Cambios en la normativa aplicable

Las variables susceptibles de ajuste, según el Artículo
4.5.1.2, incluyen:
- Cronograma de ejecución
- Presupuesto y costos
- Productos y metas

Fuentes: Art. 4.5.1 y 4.5.1.2 del Acuerdo 03/2021"
```

**Modelo usado**: `gpt-4o-mini`
- Contexto máximo: 128k tokens
- Temperatura: 0.1 (respuestas más determinísticas)
- Max tokens output: 800

**Tiempo**: 2-4 segundos
**Costo**: ~$0.0002-0.0005 por consulta

---

### [Paso 4] Validate Citations

**Archivo**: `src/generation/citation_manager.py`

**¿Qué hace?**
Verifica que las citas mencionadas en la respuesta realmente existen en los chunks.

```
ENTRADA:
- Answer: "Según el Artículo 4.5.1..."
- Chunks: [5 chunks usados como contexto]

VALIDACIÓN:
1. Extrae menciones en la respuesta:
   - "Artículo 4.5.1"
   - "Artículo 4.5.1.2"

2. Busca en chunks:
   ✅ Artículo 4.5.1 → Encontrado en Chunk 1
   ✅ Artículo 4.5.1.2 → Encontrado en Chunk 2

3. Genera reporte:
   {
     "valid_citations": 2,
     "invalid_citations": 0,
     "missing_citations": 0,
     "accuracy": 100%
   }
```

**Tiempo**: 0.1 segundos

---

### [Paso 5] Enhance Answer

**Archivo**: `src/generation/citation_manager.py`

**¿Qué hace?**
Formatea la respuesta final agregando:
- Referencias bibliográficas completas
- Enlaces a fuentes
- Metadata adicional

```
ENTRADA:
"Según el Artículo 4.5.1, los ajustes procederán..."

SALIDA:
"Según el Artículo 4.5.1, los ajustes procederán...

📚 FUENTES CONSULTADAS:
1. Artículo 4.5.1 - Acuerdo Único del SGR (Acuerdo 03/2021)
   Ubicación: Título 4 > Capítulo 5 > Artículo 4.5.1

2. Artículo 4.5.1.2 - Variables susceptibles de ajuste
   Ubicación: Título 4 > Capítulo 5 > Artículo 4.5.1.2

📊 CONFIANZA: 95%
⏱️ TIEMPO DE RESPUESTA: 5.2 segundos"
```

**Tiempo**: 0.1 segundos

---

## Componentes Técnicos Detallados

### 1. Query Enhancer

**Propósito**: Mejora la consulta del usuario

**Algoritmo**:
```python
def enhance_query(query, documento_id=None):
    # 1. Normalizar query (lowercase, quitar tildes)
    normalized = normalize_text(query)

    # 2. Detectar patrones estructurales
    filters = {}
    if "capítulo" in normalized:
        filters["capitulo"] = extract_number(query)
    if "artículo" in normalized:
        filters["articulo"] = extract_article_number(query)
    # ... más patrones

    # 3. Determinar tipo de query
    if filters:
        query_type = "structural"
        strategy = "exhaustive"  # Necesita más chunks
    else:
        query_type = "semantic"
        strategy = "standard"

    # 4. Expandir query con sinónimos (opcional)
    enhanced_query = expand_with_synonyms(query)

    return {
        "original_query": query,
        "enhanced_query": enhanced_query,
        "filters": filters,
        "query_type": query_type,
        "retrieval_strategy": strategy
    }
```

### 2. Vector Search

**Propósito**: Búsqueda semántica rápida

**Algoritmo**:
```python
def search_with_context(query, top_k=20, filters=None):
    # 1. Generar embedding de la query
    query_vector = openai_embed(query)  # [0.15, -0.23, ...]

    # 2. Buscar en Qdrant con filtros
    results = qdrant.search(
        collection="normativa_sgr",
        query_vector=query_vector,
        limit=top_k,
        filter=build_qdrant_filter(filters)  # capitulo="5", etc.
    )

    # 3. Expandir contexto (opcional)
    if expand_context:
        for chunk in results:
            # Agregar chunks adyacentes
            parent = get_parent_chunk(chunk.parent_id)
            adjacent = get_adjacent_chunks(chunk.chunk_id)
            chunk.context = [parent] + adjacent

    return results
```

**Complejidad**:
- Búsqueda vectorial: O(log N) gracias a HNSW index
- N = número total de chunks (~615)

### 3. Re-ranker

**Propósito**: Re-ordenar por relevancia real

**Algoritmo**:
```python
def rerank(query, chunks, top_k=5):
    # 1. Crear pares (query, texto)
    pairs = [(query, chunk.texto) for chunk in chunks]

    # 2. Predecir scores con cross-encoder
    # El modelo lee QUERY + TEXTO completo
    model = CrossEncoder("ms-marco-MiniLM-L-12-v2")
    scores = model.predict(pairs)

    # 3. Agregar scores a chunks
    for i, chunk in enumerate(chunks):
        chunk.rerank_score = scores[i]

    # 4. Ordenar por rerank_score
    chunks.sort(key=lambda x: x.rerank_score, reverse=True)

    # 5. Retornar top-k
    return chunks[:top_k]
```

**Cross-Encoder vs Bi-Encoder**:

```
BI-ENCODER (Vector Search):
Query → Encoder → Vector A
Text  → Encoder → Vector B
            ↓
    Cosine Similarity(A, B)

✅ Rápido (vectores pre-computados)
❌ Menos preciso (no ve interacción)

CROSS-ENCODER (Re-ranker):
Query + Text → Encoder → Relevance Score
                  ↑
        Ve la interacción completa

✅ Muy preciso
❌ Más lento (debe procesar cada par)
```

### 4. LLM Client

**Propósito**: Generar respuesta natural

**Prompt Engineering**:
```python
system_prompt = """
Eres un experto en normativa del Sistema General de Regalías (SGR) de Colombia.

REGLAS:
1. Responde SOLO con información del CONTEXTO proporcionado
2. Cita SIEMPRE los artículos específicos
3. Si la información no está en el contexto, di "No encontré información"
4. Usa lenguaje claro y profesional
5. Estructura la respuesta con viñetas si hay múltiples puntos
"""

user_prompt = f"""
CONTEXTO:
{format_chunks_as_context(chunks)}

PREGUNTA:
{query}

RESPUESTA:
"""
```

**Modelo**: GPT-4o-mini
- Input tokens: ~2000-3000 (contexto + prompt)
- Output tokens: ~200-500 (respuesta)
- Costo por query: ~$0.0003

### 5. Citation Manager

**Propósito**: Validar y mejorar citas

**Algoritmo de Validación**:
```python
def validate_answer(answer, chunks):
    # 1. Extraer menciones de artículos en la respuesta
    pattern = r"Art(?:ículo|\.)\s+([\d.]+)"
    mentions = re.findall(pattern, answer)

    # 2. Construir índice de artículos disponibles en chunks
    available = {chunk.articulo for chunk in chunks}

    # 3. Validar cada mención
    valid = [m for m in mentions if m in available]
    invalid = [m for m in mentions if m not in available]

    return {
        "valid_citations": len(valid),
        "invalid_citations": len(invalid),
        "accuracy": len(valid) / len(mentions) if mentions else 1.0
    }
```

---

## Versiones de Software Utilizadas

### Dependencias Core

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| **Python** | 3.11+ | Lenguaje base |
| **openai** | ≥1.10.0 | Embeddings y LLM |
| **qdrant-client** | ≥1.7.0 | Base de datos vectorial |
| **sentence-transformers** | 5.1.0 | Re-ranking (cross-encoder) |
| **pymupdf4llm** | 0.0.27 | Extracción de PDFs |
| **streamlit** | ≥1.30.0 | Interfaz de usuario |
| **tiktoken** | ≥0.5.2 | Conteo de tokens OpenAI |
| **loguru** | ≥0.7.2 | Logging |
| **pydantic** | ≥2.5.0 | Validación de config |

### Modelos de IA

| Modelo | Versión/ID | Uso | Costo |
|--------|-----------|-----|-------|
| **OpenAI Embeddings** | `text-embedding-3-small` | Vectorización | $0.02 / 1M tokens |
| **OpenAI LLM** | `gpt-4o-mini` | Generación | $0.15 input + $0.60 output / 1M tokens |
| **Cross-Encoder** | `ms-marco-MiniLM-L-12-v2` | Re-ranking | Gratis (local) |

### Configuración por Defecto

```python
# Retrieval
TOP_K_RETRIEVAL = 20    # Chunks recuperados
TOP_K_RERANK = 5        # Chunks después del re-ranking
CHUNK_SIZE = 500        # Tokens por chunk
CHUNK_OVERLAP = 50      # Tokens de solapamiento

# LLM
LLM_MODEL = "gpt-4o-mini"
TEMPERATURE = 0.1       # Respuestas más determinísticas
MAX_TOKENS = 800        # Máximo tokens en respuesta

# Embeddings
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# Re-ranking
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-12-v2"
```

---

## Ejemplos Paso a Paso

### Ejemplo 1: Query Estructural

**Input**: "Resume el capítulo 5 del acuerdo único"

#### Paso 0: Query Enhancement
```
Detectado: capitulo="5"
Tipo: structural
Estrategia: exhaustive
Top-K recomendado: 30 (más chunks para resumen completo)
```

#### Paso 1: Vector Search
```
Búsqueda con filtros: capitulo="5"
Chunks recuperados: 30
Tiempo: 1.2s

Top 3 scores:
1. Art. 4.5.1 - Ajustes a proyectos (score: 0.89)
2. Art. 4.5.2 - Liberación de recursos (score: 0.87)
3. Art. 4.5.3 - Modificaciones (score: 0.85)
```

#### Paso 2: Re-ranking
```
Re-ordenando 30 chunks...
Top-K final: 15 (extendido para resumen)
Tiempo: 0.8s

Nuevo orden:
1. Art. 4.5.1 (rerank: 0.92) ✅
2. Art. 4.5.2 (rerank: 0.90) ✅
3. Art. 4.5.3 (rerank: 0.88) ✅
```

#### Paso 3: Generate Answer
```
Prompt enviado con 15 chunks de contexto
Tokens input: 4500
Tokens output: 350

Respuesta generada:
"El Capítulo 5 del Título 4 regula los ajustes y liberaciones
de recursos en proyectos de inversión aprobados.

**Principales disposiciones:**

**Ajustes (Art. 4.5.1):**
- Los ajustes procederán cuando existan modificaciones...
- Variables ajustables: cronograma, presupuesto, productos...

**Liberaciones (Art. 4.5.2):**
- Los recursos se liberarán cuando...
..."
```

#### Paso 4-5: Validación y Mejora
```
Citas validadas: 15/15 ✅
Accuracy: 100%

Respuesta mejorada con fuentes:
[Respuesta] +

📚 FUENTES:
1. Art. 4.5.1 - Acuerdo 03/2021
2. Art. 4.5.2 - Acuerdo 03/2021
...
```

**Tiempo total**: 6.8 segundos
**Costo**: $0.0004

---

### Ejemplo 2: Query Semántica

**Input**: "¿Qué es un OCAD y cuáles son sus funciones?"

#### Paso 0: Query Enhancement
```
No se detectan patrones estructurales
Tipo: semantic
Estrategia: standard
Top-K recomendado: 20
```

#### Paso 1: Vector Search
```
Búsqueda semántica sin filtros
Chunks recuperados: 20
Tiempo: 1.0s

Top 3 scores:
1. Definición de OCAD (score: 0.94)
2. Funciones del OCAD (score: 0.91)
3. Composición del OCAD (score: 0.88)
```

#### Paso 2: Re-ranking
```
Re-ordenando 20 chunks...
Top-K final: 5
Tiempo: 0.5s

Orden mejorado:
1. Definición (rerank: 0.96) ✅ Subió
2. Funciones (rerank: 0.94) ✅
3. Composición (rerank: 0.89) ✅
```

#### Paso 3: Generate Answer
```
Tokens input: 2200
Tokens output: 280

Respuesta:
"El OCAD (Órgano Colegiado de Administración y Decisión)
es la instancia responsable de definir los proyectos de
inversión financiados con recursos del SGR.

**Funciones principales:**
1. Aprobar proyectos de inversión
2. Realizar seguimiento a la ejecución
3. Viabilizar modificaciones
..."
```

**Tiempo total**: 4.2 segundos
**Costo**: $0.0002

---

### Ejemplo 3: Query con Filtro Múltiple

**Input**: "Artículo 4.5.1.2 del título 4"

#### Paso 0: Query Enhancement
```
Detectado: titulo="4", articulo="4.5.1.2"
Tipo: specific
Estrategia: precise
Top-K recomendado: 5 (búsqueda muy específica)
```

#### Paso 1: Vector Search
```
Búsqueda con filtros: titulo="4" AND articulo="4.5.1.2"
Chunks recuperados: 2 (muy específico)
Tiempo: 0.8s
```

#### Paso 2: Re-ranking
```
Solo 2 chunks, no necesita reordenamiento complejo
Top-K final: 2
Tiempo: 0.2s
```

#### Paso 3: Generate Answer
```
Tokens input: 1500
Tokens output: 180

Respuesta:
"El Artículo 4.5.1.2 del Acuerdo 03 de 2021 establece las
variables susceptibles de ajuste en proyectos de inversión:

1. Cronograma de ejecución
2. Presupuesto y costos
3. Productos y metas
4. Ejecutor del proyecto
..."
```

**Tiempo total**: 2.8 segundos (muy rápido)
**Costo**: $0.0001

---

## 📊 Métricas de Performance

### Tiempos Promedio por Paso

| Paso | Tiempo | % del Total |
|------|--------|-------------|
| Query Enhancement | 0.1s | 2% |
| Vector Search | 1.2s | 24% |
| Re-ranking | 0.6s | 12% |
| Generate Answer | 2.8s | 56% |
| Validate Citations | 0.1s | 2% |
| Enhance Answer | 0.2s | 4% |
| **TOTAL** | **5.0s** | **100%** |

### Costos Promedio por Query

| Componente | Costo |
|------------|-------|
| Embedding (query) | $0.00001 |
| LLM Generation | $0.0003 |
| Re-ranking | $0 (local) |
| **Total por query** | **~$0.0003** |

**Estimación mensual** (1000 queries):
- Costo: ~$0.30
- Tiempo agregado: ~1.4 horas

---

## 🎯 Conclusiones

### ¿Por Qué Este Flujo Funciona?

1. **Query Enhancement**: Mejora la precisión al detectar filtros automáticamente
2. **Vector Search**: Reduce 615 chunks a 20 candidatos relevantes en <2s
3. **Re-ranking**: Mejora precisión +15-20% al leer texto completo
4. **GPT-4o-mini**: Balance perfecto entre calidad y costo
5. **Citation Validation**: Garantiza respuestas verificables

### Limitaciones Actuales

- ❌ No hay caché (Redis planeado para futuro)
- ❌ No hay búsqueda híbrida (vector + keyword BM25)
- ❌ No hay sistema multi-agente (LangGraph planeado)
- ❌ No hay grafo de conocimiento (Neo4j planeado)

### Próximas Mejoras

Ver `docs/ANALISIS_MEJORAS_RAG.md` para roadmap completo.

---

## 📖 Referencias

- **Código fuente**: `/src/pipeline.py`
- **Configuración**: `/src/config.py`
- **Arquitectura**: `docs/ARQUITECTURA_TECNICA.md`
- **Mejoras planeadas**: `docs/ANALISIS_MEJORAS_RAG.md`

---

**Última actualización**: 2025-10-21
**Versión**: v1.1.1
**Mantenido por**: Equipo RAG

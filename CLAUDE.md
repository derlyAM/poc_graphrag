# INSTRUCCIONES PARA CLAUDE CODE

> **IMPORTANTE**: Este documento describe tanto funcionalidad **IMPLEMENTADA** (✅) como **PLANEADA** (📋).
> Verifica los badges antes de asumir que una característica está disponible.

---

## ESTADO DEL PROYECTO

**Versión Actual**: v1.1.1 (2025-10-21)
**Estado**: Producción - MVP Funcional

### Funcionalidad Implementada (✅)
- ✅ Procesamiento jerárquico universal (documentos legales, técnicos)
- ✅ Búsqueda vectorial con Qdrant
- ✅ Re-ranking con cross-encoder
- ✅ Generación con GPT-4o-mini
- ✅ Sistema de citación legal
- ✅ Interfaz Streamlit
- ✅ Expansión de contexto con chunks adyacentes

### En Desarrollo (🚧)
- 🚧 Query enhancement avanzado (detección de secciones por nombre)
- 🚧 Metadata semántico enriquecido

### Planeado (📋)
- 📋 Neo4j para grafo de conocimiento
- 📋 LangGraph para sistema multi-agente
- 📋 Redis para caché
- 📋 Búsqueda híbrida (vector + keyword BM25)
- 📋 FastAPI REST API

---

## CONTEXTO Y REQUERIMIENTOS

### Problema a Resolver
El usuario necesita consultar múltiples documentos normativos complejos (100+ páginas) que contienen:

- Estructura jerárquica profunda (Títulos → Capítulos → Artículos → Parágrafos)
- Referencias cruzadas intensivas ("conforme al artículo X", "según lo dispuesto en...")
- Tablas, anexos y flujogramas complementarios
- Actualizaciones y modificaciones entre documentos
- Conceptos especializados (ej: "OCAD", "SGR", "viabilidad técnica")

Tipos de Consultas Esperadas

Resúmenes: "Resume el Título 4 del Acuerdo 03/2021"
Búsquedas simples: "¿Qué es un OCAD?"
Búsquedas complejas: "¿Qué documentos necesito para viabilizar un proyecto de infraestructura en fase III?"
Procedimientos: "Explica el proceso de ajuste de proyectos aprobados"
Comparaciones: "Diferencias entre Acuerdo 03/2021 y Acuerdo 13/2025"
Listados: "Enumera todos los requisitos para proyectos de ciencia y tecnología"

Requerimientos Críticos

Citación precisa: Cada afirmación debe citar artículo exacto con formato legal estándar
Separabilidad: Usuario selecciona áreas/proyectos específicos para consultar
Trazabilidad: Mostrar path del grafo que llevó a la respuesta
Performance: Respuestas en 3-8 segundos
Costos: Optimizado para presupuesto mínimo (~$15/mes)
Explicabilidad multinivel: Desde citación simple hasta visualización completa del razonamiento

## ARQUITECTURA ACTUAL (✅ IMPLEMENTADA)

```
┌─────────────────────────────────────────────────────────────────┐
│                     USUARIO (Streamlit UI)                       │
│              Query → Parámetros → Visualización                  │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE RAG (src/pipeline.py)                │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐         │
│  │ QueryEnhance │→ │ VectorSearch  │→ │ LLMClient    │         │
│  │              │  │ (Qdrant)      │  │ (GPT-4o-mini)│         │
│  └──────────────┘  └───────────────┘  └──────────────┘         │
│         ↓                  ↓                   ↓                 │
│  ┌──────────────────────────────────────────────────┐          │
│  │      CitationManager (Validación de citas)        │          │
│  └──────────────────────────────────────────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    RETRIEVAL (src/retrieval/)                    │
│  ┌─────────────────────┐        ┌──────────────────────┐        │
│  │   QDRANT (Vectores) │        │  Context Expansion   │        │
│  │  • Vector search    │        │  • Adjacent chunks   │        │
│  │  • Metadata filters │        │  • Hierarchy-aware   │        │
│  └─────────────────────┘        └──────────────────────┘        │
│           ↓                              ↓                       │
│  ┌──────────────────────────────────────────────────┐          │
│  │       Reranker (cross-encoder MiniLM)             │          │
│  └──────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│               INGESTIÓN (src/ingest/)                            │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │ PyMuPDF4LLM  │→ │ Hierarchical    │→ │ OpenAI Embed.    │   │
│  │ (extracción) │  │ Processor       │  │ (vectorización)  │   │
│  └──────────────┘  └─────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Flujo de Datos IMPLEMENTADO

#### 1. INGESTIÓN (Offline, ejecutar: `python scripts/01_ingest_pdfs.py`)
```
PDF → PyMuPDF4LLM → Texto estructurado con jerarquía
  → DocumentHierarchyProcessor → Chunks multinivel (0-5)
  → OpenAI Embeddings (text-embedding-3-large) → Vectores 1536-dim
  → Carga en Qdrant con metadata jerárquica completa
```

#### 2. CONSULTA (Online, vía Streamlit o pipeline.py)
```
User Query → QueryEnhancer (detecta filtros: capítulo, artículo, etc.)
  → Embedding de query (text-embedding-3-large)
  → Búsqueda vectorial en Qdrant (top-K configurable)
  → Context Expansion (chunks adyacentes vía metadata)
  → Re-ranking con cross-encoder (MiniLM-L-6-v2)
  → GPT-4o-mini genera respuesta con contexto
  → CitationManager inyecta y valida referencias
  → Return respuesta + fuentes + métricas
```

---

## ARQUITECTURA FUTURA (📋 PLANEADA - NO IMPLEMENTADA)

> ⚠️ **Las siguientes características NO están implementadas actualmente**

### Componentes Planeados

#### Neo4j (📋 Planeado)
```python
# NO IMPLEMENTADO - Diseño propuesto
neo4j:
  deployment: "Docker local (./neo4j_data)"
  puertos: [7474, 7687]
  uso: "Graph database con vectores nativos"
  plugins: ["apoc", "graph-data-science"]
```

#### LangGraph (📋 Planeado)
```python
# NO IMPLEMENTADO - Diseño propuesto
langgraph:
  uso: "Sistema multi-agente con flujos condicionales"
  componentes:
    - QueryAnalyzer: "Clasificación inteligente de queries"
    - RetrievalAgent: "Búsquedas iterativas"
    - VerificationAgent: "Validación de completitud"
```

#### Redis (📋 Planeado)
```python
# NO IMPLEMENTADO - Diseño propuesto
redis:
  deployment: "Docker local (./redis_data)"
  uso: "Caché de queries y resultados"
```

Ver `docs/ANALISIS_MEJORAS_RAG.md` para detalles completos de mejoras planeadas


---

## STACK TECNOLÓGICO IMPLEMENTADO (✅)

### Entorno Python
```yaml
python: "3.11"
package_manager: "pip"
env_manager: "venv"
```

### Extracción y Procesamiento (✅)
```yaml
pymupdf4llm:
  version: "0.0.27"
  uso: "Extracción de texto de PDFs preservando estructura"

tiktoken:
  version: ">=0.5.2"
  uso: "Conteo de tokens para OpenAI"
```

### Almacenamiento (✅)
```yaml
qdrant_client:
  version: ">=1.7.0"
  deployment: "Docker local (./storage/qdrant_local)"
  puerto: 6333
  colección: "normativa_sgr"
  features_usadas:
    - Búsqueda vectorial (Cosine similarity)
    - Metadata filtering (capitulo, titulo, articulo, etc.)
    - Scroll API para recuperación masiva
```

### Modelos de IA (✅)
```yaml
openai:
  embeddings:
    modelo: "text-embedding-3-large"
    dimensiones: 1536
    costo: "$0.13 / 1M tokens"

  llm:
    modelo: "gpt-4o-mini"
    costo: "$0.150 / 1M tokens input, $0.600 / 1M output"
    contexto: "128k tokens"
    temperatura: 0.1
```

### Re-ranking (✅)
```yaml
sentence_transformers:
  modelo: "cross-encoder/ms-marco-MiniLM-L-6-v2"
  deployment: "Local (CPU)"
  uso: "Re-ranking de chunks post-retrieval"
```

### Interfaz (✅)
```yaml
streamlit:
  version: ">=1.30.0"
  uso: "UI interactiva para queries"
  puerto: 8501
```

### Utilidades (✅)
```yaml
loguru: "Logging estructurado"
pydantic: "Validación de configuración"
python-dotenv: "Gestión de API keys"
```

---

## DEPENDENCIAS NO USADAS (📋 Para futuras fases)

> ⚠️ **Las siguientes dependencias están en requirements.txt pero NO se usan actualmente**

```yaml
# NO IMPLEMENTADO
llama-index: "Presente pero no usado - usamos implementación custom"
neo4j: "NO conectado - planeado para Fase 2"
redis: "NO usado - planeado para caché"
langgraph: "NO usado - planeado para multi-agente"
fastapi: "NO usado - planeado para API REST"
```

### Dependencias Actuales en requirements.txt
Ver `requirements.txt` para lista completa de paquetes instalados


---

## SCHEMAS DE DATOS IMPLEMENTADOS

### Schema Qdrant Actual (✅)

**Colección única**: `normativa_sgr`

```python
# ✅ IMPLEMENTADO
collection_config = {
    "vector_size": 1536,
    "distance": "Cosine",
    "on_disk_payload": True
}
```

> ⚠️ **NO IMPLEMENTADO**: Colecciones separadas por área
>
> El diseño original contemplaba múltiples colecciones (area_juridica, area_tecnica, etc.)
> pero la implementación actual usa UNA sola colección con filtros de metadata

### Schema de Payload (Metadata por Chunk) - ✅ IMPLEMENTADO

```python
{
    # === IDENTIFICACIÓN ÚNICA ===
    "chunk_id": "uuid-string",  # UUID generado
    "documento_id": "acuerdo_03_2021",  # ID único del documento
    
    # === INFORMACIÓN DEL DOCUMENTO ===
    "documento_nombre": "Acuerdo Único del Sistema General de Regalías",
    "documento_tipo": "Acuerdo",  # Acuerdo | Decreto | Resolución | Ley
    "documento_numero": "03",
    "documento_año": 2021,
    "documento_fecha": "2021-04-08",
    
    # === TIPO DE DOCUMENTO (✅ Implementado) ===
    "tipo_documento": "legal",  # legal | technical | financial | environmental | generic

    # === CLASIFICACIÓN (📋 Planeado - NO implementado) ===
    "area": None,  # ⚠️ NO IMPLEMENTADO - Planeado para futuro
    "proyecto": None,  # ⚠️ NO IMPLEMENTADO - Planeado para futuro
    "tags": [],  # ⚠️ NO IMPLEMENTADO - Planeado para futuro

    # === ESTADO DEL DOCUMENTO (📋 Planeado - NO implementado) ===
    "vigente": None,  # ⚠️ NO IMPLEMENTADO
    "modificado_por": [],  # ⚠️ NO IMPLEMENTADO
    "fecha_modificacion": None,  # ⚠️ NO IMPLEMENTADO
    
    # === JERARQUÍA (✅ Implementado) ===
    "nivel_jerarquico": 3,  # 0=doc, 1=titulo, 2=cap, 3=art, 4=para, 5=anexo
    "parent_id": "uuid-del-padre",  # ✅ Vinculación parent-child
    "children_ids": ["uuid-hijo-1", "uuid-hijo-2"],  # ✅ Implementado
    "hierarchy_path": "Doc > Título 4 > Capítulo 5 > Artículo 4.5.1.2",  # ✅ Implementado

    # === CAMPOS JERÁRQUICOS ESPECÍFICOS (✅ Implementado) ===
    # Legal
    "titulo": "4",  # ✅ Número de título
    "capitulo": "5",  # ✅ Número de capítulo
    "articulo": "4.5.1.2",  # ✅ Número de artículo
    "paragrafo": None,  # ✅ Número de parágrafo (si existe)

    # Técnico
    "seccion": "6",  # ✅ Número de sección
    "subseccion": None,  # ✅ Número de subsección (si existe)
    "subsubseccion": None,  # ✅ Sub-subsección (si existe)

    # Anexos (universal)
    "anexo_numero": None,  # ✅ Número de anexo (si es anexo)
    "es_anexo": False,  # ✅ Boolean indicando si es anexo

    # ⚠️ NOMBRES DE ELEMENTOS - PARCIALMENTE IMPLEMENTADO
    "titulo_nombre": None,  # ⚠️ NO guardado actualmente
    "capitulo_nombre": None,  # ⚠️ NO guardado actualmente
    "seccion_nombre": None,  # 🚧 En desarrollo (extraído de hierarchy_path)
    
    # === CONTENIDO TEXTUAL (✅ Implementado) ===
    "texto": "Los ajustes a los proyectos de inversión aprobados...",  # ✅ Contenido completo
    "longitud_tokens": 214,  # ✅ Calculado con tiktoken

    # === METADATA DE PROCESAMIENTO (✅ Implementado) ===
    "fecha_procesamiento": "2025-10-21T10:30:00",  # ✅ Timestamp de ingestión
    "tipo_documento": "legal",  # ✅ legal | technical | generic

    # === CITACIÓN (✅ Implementado) ===
    "citacion_corta": "Art. 4.5.1.2, Acuerdo 03/2021",  # ✅ Formato corto

    # === CAMPOS NO IMPLEMENTADOS (📋 Planeados) ===
    "texto_limpio": None,  # ⚠️ NO IMPLEMENTADO
    "texto_previo": None,  # ⚠️ NO IMPLEMENTADO
    "texto_siguiente": None,  # ⚠️ NO IMPLEMENTADO
    "chunk_anterior_id": None,  # ⚠️ NO IMPLEMENTADO
    "chunk_siguiente_id": None,  # ⚠️ NO IMPLEMENTADO

    "resumen_chunk": None,  # ⚠️ NO IMPLEMENTADO
    "resumen_articulo": None,  # ⚠️ NO IMPLEMENTADO
    "resumen_capitulo": None,  # ⚠️ NO IMPLEMENTADO
    "es_resumen": False,  # ⚠️ NO IMPLEMENTADO

    "conceptos_clave": [],  # ⚠️ NO IMPLEMENTADO - Requiere NER
    "entidades_mencionadas": [],  # ⚠️ NO IMPLEMENTADO - Requiere NER
    "tipo_contenido": None,  # ⚠️ NO IMPLEMENTADO
    "contiene_tabla": None,  # ⚠️ NO IMPLEMENTADO
    "contiene_lista": None,  # ⚠️ NO IMPLEMENTADO

    "citacion_completa": None,  # ⚠️ NO IMPLEMENTADO
    "citacion_apa": None,  # ⚠️ NO IMPLEMENTADO

    "pagina": None,  # ⚠️ NO IMPLEMENTADO
    "posicion_inicio": None,  # ⚠️ NO IMPLEMENTADO
    "posicion_fin": None,  # ⚠️ NO IMPLEMENTADO
    "bbox": None,  # ⚠️ NO IMPLEMENTADO

    "chunk_index": None,  # ⚠️ NO IMPLEMENTADO
    "version_procesamiento": None,  # ⚠️ NO IMPLEMENTADO
    "embedding_model": "text-embedding-3-large",  # ✅ Usado pero no guardado en payload

    "referencias_a": [],  # ⚠️ NO IMPLEMENTADO - Requiere análisis de referencias
    "referenciado_por": [],  # ⚠️ NO IMPLEMENTADO
    "relacionado_con": [],  # ⚠️ NO IMPLEMENTADO

    "idioma": None,  # ⚠️ NO IMPLEMENTADO
    "pais": None,  # ⚠️ NO IMPLEMENTADO
    "jurisdiccion": None,  # ⚠️ NO IMPLEMENTADO
}
```

> **RESUMEN DE IMPLEMENTACIÓN**:
> - ✅ **Implementado (30%)**: Jerarquía completa, vectorización, citación básica
> - 🚧 **En desarrollo (5%)**: Nombres de secciones, metadata enriquecido
> - ⚠️ **NO implementado (65%)**: NER, análisis semántico, referencias cruzadas, resúmenes automáticos
>
> **Ver `docs/ARQUITECTURA_TECNICA.md`** para detalles de campos efectivamente implementados
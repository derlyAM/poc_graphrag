# INSTRUCCIONES PARA CLAUDE CODE

> **Sistema RAG para Documentos Normativos - Especificaciones Técnicas**

---

## ESTADO DEL PROYECTO

**Versión Actual**: v1.3.0 (2025-10-28)
**Estado**: ✅ **PRODUCCIÓN** - Sistema completo con Multihop, HyDE y Chatbot Conversacional
**Precisión Global**: 88-92%

---

## FUNCIONALIDAD IMPLEMENTADA ✅

### Core RAG Pipeline
- ✅ Procesamiento jerárquico universal (documentos legales, técnicos)
- ✅ Búsqueda vectorial con Qdrant (Cosine similarity)
- ✅ Re-ranking con cross-encoder (ms-marco-MiniLM-L-12-v2)
- ✅ Context expansion (chunks adyacentes con awareness jerárquico)
- ✅ Citation management (validación automática de citaciones legales)
- ✅ Generación con GPT-4o-mini (prompts especializados)
- ✅ Interfaz Streamlit (RAG tradicional + Chatbot conversacional)

### Query Processing (v1.2.0)
- ✅ **QueryEnhancer**: Detección de tipo de query y filtros estructurales
- ✅ **QueryDecomposer**: Análisis de complejidad y descomposición
- ✅ **MultihopRetriever**: Búsquedas iterativas con fusion scoring
- ✅ Estrategias especializadas (comparison, conditional, procedural)
- ✅ Adaptive top-K según área y número de documentos

### HyDE Retrieval (v1.3.0)
- ✅ **HyDERetriever**: Generación de documentos hipotéticos
- ✅ Prompts especializados por tipo de documento (legal, técnico)
- ✅ Búsqueda híbrida (70% HyDE + 30% original) con RRF fusion
- ✅ Activación selectiva (~25% de queries)
- ✅ Fallback automático si scores <0.30

### Response Validation (v1.3.0 - PHASE 3)
- ✅ **ResponseValidator**: Validación de completitud
- ✅ Detección de aspectos faltantes
- ✅ Auto-retry con queries adicionales
- ✅ Mejora iterativa de respuestas incompletas

### Chatbot Conversacional (v1.3.0)
- ✅ **ConversationalPipeline**: Orquestador multi-turno
- ✅ **ConversationHistory**: Gestión de historial (20 turnos)
- ✅ **QueryReformulator**: Reformulación contextual con LLM
- ✅ **ResponseFormatter**: Modos corto/largo
- ✅ Singleton pattern para recursos compartidos
- ✅ 100% reuso del RAG base (composición, no herencia)
- ✅ UI Streamlit dedicada (`app/pages/2_Chatbot_IA.py`)

### Separación por Áreas (PHASE 2.5)
- ✅ Áreas implementadas: `sgr`, `inteligencia_artificial`, `general`
- ✅ Filtrado por área en Qdrant
- ✅ Multi-select de documentos por área
- ✅ Metadata completa por documento

---

## ARQUITECTURA IMPLEMENTADA

```
┌─────────────────────────────────────────────────────────────────┐
│                     STREAMLIT UI                                 │
│  ┌──────────────────────┐  ┌──────────────────────────────┐    │
│  │  RAG Tradicional     │  │  Chatbot Conversacional      │    │
│  │  (streamlit_app.py)  │  │  (2_Chatbot_IA.py)           │    │
│  └──────────────────────┘  └──────────────────────────────┘    │
└────────────────────┬───────────────────┬──────────────────────────┘
                     │                   │
              ┌──────▼───────┐    ┌─────▼─────────────────┐
              │              │    │ ConversationalPipeline│
              │ RAGPipeline  │◄───┤ (COMPOSICIÓN)         │
              │ (Singleton)  │    └───────────────────────┘
              └──────┬───────┘           │
                     │                   │
        ┌────────────┴────────────┬──────┴──────────┐
        │                         │                  │
   ┌────▼─────┐            ┌─────▼──────┐   ┌──────▼──────────┐
   │  Query   │            │  Multihop  │   │     HyDE        │
   │ Enhancer │            │ Retriever  │   │   Retriever     │
   └──────────┘            └────────────┘   └─────────────────┘
        │                         │                  │
        └─────────────────┬───────┴──────────────────┘
                          │
                  ┌───────▼────────┐
                  │ Vector Search  │
                  │   (Qdrant)     │
                  └───────┬────────┘
                          │
                  ┌───────▼────────┐
                  │   Reranker     │
                  └───────┬────────┘
                          │
                  ┌───────▼────────┐
                  │  LLM Client    │
                  │ (GPT-4o-mini)  │
                  └───────┬────────┘
                          │
                  ┌───────▼────────┐
                  │   Citation     │
                  │   Manager      │
                  └────────────────┘
```

---

## STACK TECNOLÓGICO

### Lenguaje y Entorno
```yaml
python: "3.11+"
package_manager: "pip"
env_manager: "venv"
```

### Extracción y Procesamiento
```yaml
pymupdf4llm: "0.0.27"  # Extracción de PDFs
tiktoken: ">=0.5.2"     # Conteo de tokens
```

### Almacenamiento Vectorial
```yaml
qdrant_client: ">=1.7.0"
deployment: "Docker local (./storage/qdrant_local)"
puerto: 6333
coleccion: "normativa_sgr"
```

### Modelos de IA
```yaml
# Embeddings
embedding_model: "text-embedding-3-small"  # Queries
embedding_model_docs: "text-embedding-3-large"  # Documentos
dimensions: 1536

# LLM
llm_model: "gpt-4o-mini"
contexto: "128k tokens"
temperatura: 0.1
```

### Re-ranking
```yaml
modelo: "cross-encoder/ms-marco-MiniLM-L-12-v2"
deployment: "Local (CPU)"
```

### UI
```yaml
streamlit: ">=1.30.0"
puerto: 8501
```

### Utilidades
```yaml
loguru: "Logging estructurado"
pydantic: "Validación de configuración"
python-dotenv: "Variables de entorno"
```

---

## FLUJO DE DATOS IMPLEMENTADO

### 1. INGESTIÓN (Offline)

```bash
python scripts/01_ingest_pdfs.py
```

```
PDF → PyMuPDF4LLM → Markdown estructurado
  → DocumentHierarchyProcessor → Chunks multinivel (0-5)
  → OpenAI Embeddings (text-embedding-3-large) → Vectores 1536-dim
  → Carga en Qdrant con metadata completa
```

**Resultado**: 2443 chunks indexados (Legal + Técnico + IA)

### 2. CONSULTA RAG (Online)

```
User Query → QueryEnhancer (detecta tipo y filtros)
  ↓
¿Multihop necesario?
  ├─ NO → Vector Search (single-hop)
  └─ SÍ → QueryDecomposer → MultihopRetriever (sub-queries + fusion)
  ↓
¿HyDE beneficioso?
  ├─ NO → Usa query original
  └─ SÍ → HyDERetriever (doc hipotético + RRF fusion)
  ↓
Re-ranking (cross-encoder) → Top-N final
  ↓
Context Expansion (chunks adyacentes)
  ↓
LLM Generation (GPT-4o-mini con prompts especializados)
  ↓
Citation Manager (validación + inyección)
  ↓
¿Response Validation activada?
  └─ SÍ → Validar completitud → Auto-retry si incompleto
  ↓
Return respuesta + fuentes + métricas
```

### 3. CONSULTA CHATBOT (Online)

```
User Query → ConversationHistory.get_recent()
  ↓
QueryReformulator (detecta referencias + reformula con LLM)
  ↓
RAGPipeline.query(reformulated_query) [FLUJO COMPLETO ARRIBA]
  ↓
ResponseFormatter (short/long mode)
  ↓
ConversationHistory.add_turn()
  ↓
Return respuesta formateada + historial
```

---

## SCHEMAS DE DATOS (Qdrant)

### Colección Única
**Nombre**: `normativa_sgr`
**Vector size**: 1536
**Distance**: Cosine

### Payload por Chunk

```python
{
    # IDENTIFICACIÓN
    "chunk_id": "uuid",
    "documento_id": "acuerdo_03_2021",
    "area": "sgr",  # sgr | inteligencia_artificial | general

    # DOCUMENTO
    "documento_nombre": "Acuerdo Único del SGR",
    "documento_tipo": "legal",  # legal | technical | generic
    "documento_numero": "03",
    "documento_año": 2021,

    # JERARQUÍA
    "nivel_jerarquico": 3,  # 0-5
    "parent_id": "uuid-padre",
    "children_ids": ["uuid-hijo1", "uuid-hijo2"],
    "hierarchy_path": "Doc > Título 4 > Capítulo 5 > Artículo 4.5.1.2",

    # CAMPOS JERÁRQUICOS ESPECÍFICOS
    # Legal
    "titulo": "4",
    "capitulo": "5",
    "articulo": "4.5.1.2",
    "paragrafo": None,

    # Técnico
    "seccion": "6",
    "subseccion": None,
    "subsubseccion": None,

    # Anexos
    "anexo_numero": None,
    "es_anexo": False,

    # CONTENIDO
    "texto": "Los ajustes a los proyectos de inversión...",
    "longitud_tokens": 214,

    # PROCESAMIENTO
    "fecha_procesamiento": "2025-10-28T10:30:00",
    "citacion_corta": "Art. 4.5.1.2, Acuerdo 03/2021",
}
```

---

## CONFIGURACIÓN (src/config.py)

```python
# Áreas válidas
VALID_AREAS = {
    "sgr": "Sistema General de Regalías",
    "inteligencia_artificial": "Inteligencia Artificial",
    "general": "General"
}

# Retrieval
RETRIEVAL_TOP_K = 20  # Chunks iniciales
RETRIEVAL_TOP_K_RERANK = 5  # Chunks finales

# LLM
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 800

# Embeddings
EMBEDDING_MODEL = "text-embedding-3-small"  # Queries
EMBEDDING_MODEL_DOCS = "text-embedding-3-large"  # Documentos
```

---

## MÉTRICAS DE PRECISIÓN

### Por Tipo de Query

| Tipo | Técnicas | v1.0 | v1.3 | Mejora |
|------|----------|------|------|--------|
| Simple semántica | Vector + Rerank | 70% | 75% | +5% |
| Estructural | Enhancement + Filters | 60% | 85% | +25% |
| Definiciones | HyDE + RRF | 60% | 90% | +30% |
| Condicional | Multihop + Fusion | 10% | 85% | +750% |
| Comparativa | Multihop comparison | 10% | 85% | +750% |
| Terminología incorrecta | HyDE fallback | 35% | 75% | +114% |

### Performance

| Escenario | Latencia | Costo | Precisión |
|-----------|----------|-------|-----------|
| Query simple | 3-5s | $0.005 | 75% |
| Query + HyDE | 5-7s | $0.008 | 90% |
| Query multihop | 8-15s | $0.015 | 85% |
| Query completa | 15-20s | $0.025 | 88-92% |

**Promedio global**: 88-92% precisión, ~6s latencia, ~$0.007/query

---

## ESTRUCTURA DEL PROYECTO

```
Poc_Rag_Graph/
├── data/                    # PDFs de entrada
├── src/
│   ├── config.py            # Configuración centralizada
│   ├── pipeline.py          # RAG Pipeline principal
│   ├── shared_resources.py  # Singleton para recursos compartidos
│   │
│   ├── ingest/              # Pipeline de ingestión
│   │   ├── pdf_extractor.py
│   │   ├── document_hierarchy_processor.py  # Procesador universal
│   │   ├── hierarchy_config.py              # Configuración jerarquías
│   │   ├── chunker.py
│   │   └── vectorizer.py
│   │
│   ├── retrieval/           # Sistema de búsqueda
│   │   ├── vector_search.py
│   │   ├── reranker.py
│   │   ├── query_enhancer.py
│   │   ├── query_decomposer.py      # v1.2.0
│   │   ├── multihop_retriever.py    # v1.2.0
│   │   ├── hyde_retriever.py        # v1.3.0
│   │   └── response_validator.py    # v1.3.0 PHASE 3
│   │
│   ├── generation/          # Generación de respuestas
│   │   ├── llm_client.py
│   │   └── citation_manager.py
│   │
│   └── chatbot/             # Chatbot conversacional (v1.3.0)
│       ├── conversational_pipeline.py
│       ├── conversation_manager.py
│       ├── query_reformulator.py
│       ├── response_formatter.py
│       └── prompts.py
│
├── app/                     # Interfaces Streamlit
│   ├── streamlit_app.py     # RAG tradicional
│   └── pages/
│       └── 2_Chatbot_IA.py  # Chatbot conversacional
│
├── scripts/                 # Scripts de utilidad
│   ├── 01_ingest_pdfs.py    # Ingestión
│   ├── test_multihop.py     # Testing multihop
│   ├── test_hyde.py         # Testing HyDE
│   └── test_chatbot_shared_pipeline.py  # Testing chatbot
│
├── docs/                    # Documentación
│   ├── STACK_TECNOLOGICO.md          # Tecnologías y técnicas
│   ├── ARQUITECTURA_TECNICA.md       # Arquitectura detallada
│   ├── SISTEMA_MULTIHOP.md           # Sistema multihop
│   ├── SISTEMA_HYDE.md               # Sistema HyDE
│   ├── FLUJO_IMPLEMENTADO_EXPLICADO.md  # Flujo completo
│   └── chatbot/
│       └── CHATBOT_DOCUMENTACION_COMPLETA.md  # Chatbot
│
├── storage/                 # Datos de Qdrant
├── logs/                    # Logs de aplicación
├── requirements.txt
├── docker-compose.yml
├── CHANGELOG.md
├── CLAUDE.md               # ← ESTE ARCHIVO
└── README.md
```

---

## DOCUMENTOS CLAVE PARA DESARROLLADORES

### Documentación Principal

| Documento | Descripción | Cuándo Leer |
|-----------|-------------|-------------|
| **CLAUDE.md** | ← Estás aquí - Especificaciones técnicas | Primera lectura |
| **README.md** | Guía de inicio rápido y uso básico | Instalación |
| **CHANGELOG.md** | Historial de cambios por versión | Entender evolución |

### Documentación Técnica (`docs/`)

| Documento | Descripción | Audiencia |
|-----------|-------------|-----------|
| **STACK_TECNOLOGICO.md** | Listado completo de tecnologías y métricas de precisión | Todos |
| **ARQUITECTURA_TECNICA.md** | Arquitectura detallada del sistema | Desarrolladores |
| **FLUJO_IMPLEMENTADO_EXPLICADO.md** | Flujo completo paso a paso | Principiantes |
| **SISTEMA_MULTIHOP.md** | Sistema multihop retrieval (40+ páginas) | Implementadores multihop |
| **SISTEMA_HYDE.md** | Sistema HyDE con RRF fusion (40+ páginas) | Implementadores HyDE |
| **chatbot/CHATBOT_DOCUMENTACION_COMPLETA.md** | Chatbot conversacional completo | Implementadores chatbot |

### Flujo de Lectura Recomendado

**Desarrolladores nuevos**:
1. README.md (instalación)
2. CLAUDE.md (este archivo - overview técnico)
3. STACK_TECNOLOGICO.md (tecnologías y métricas)
4. FLUJO_IMPLEMENTADO_EXPLICADO.md (entender flujo completo)
5. ARQUITECTURA_TECNICA.md (profundizar)

**Implementadores de features específicas**:
- Multihop: SISTEMA_MULTIHOP.md
- HyDE: SISTEMA_HYDE.md
- Chatbot: chatbot/CHATBOT_DOCUMENTACION_COMPLETA.md

---

## USO BÁSICO

### Ingestión (una vez)

```bash
# Levantar Qdrant
docker-compose up -d

# Ingestar documentos
python scripts/01_ingest_pdfs.py
```

### Interfaz Web

```bash
streamlit run app/streamlit_app.py

# Navegar a:
# - Página principal: RAG tradicional
# - Sidebar → Chatbot IA: Chatbot conversacional
```

### Uso Programático

```python
from src.pipeline import RAGPipeline

# RAG tradicional
pipeline = RAGPipeline()
result = pipeline.query(
    question="¿Qué es un OCAD?",
    area="sgr",  # REQUERIDO
    enable_multihop=True,
    enable_hyde=True,
    enable_validation=True
)

print(result["answer"])
print(f"Precisión: {result['metrics']['hyde_used']}")
print(f"Costo: ${result['metrics']['total_cost']:.6f}")
```

```python
from src.chatbot.conversational_pipeline import ConversationalPipeline
from src.shared_resources import get_shared_pipeline

# Chatbot conversacional
shared_rag = get_shared_pipeline()
chatbot = ConversationalPipeline(
    area="inteligencia_artificial",
    shared_pipeline=shared_rag
)

# Conversación multi-turno
r1 = chatbot.query("¿Qué es TensorFlow?", response_mode="long")
r2 = chatbot.query("¿Cuáles son sus ventajas?", response_mode="short")
r3 = chatbot.query("Dame ejemplos", response_mode="long")
```

---

## TESTING

```bash
# Testing multihop
python scripts/test_multihop.py

# Testing HyDE
python scripts/test_hyde.py

# Testing chatbot
python scripts/test_chatbot_shared_pipeline.py
```

---

## COSTOS ESTIMADOS

### Ingestión (una vez)
- Embeddings: ~$0.14 (2443 chunks con text-embedding-3-large)

### Operación (por mes, 1000 queries)
- Promedio: ~$7/mes
- Rango: $5-25/mes (según complejidad de queries)

### Por Query
- Simple: $0.005
- Compleja (multihop + HyDE + validation): $0.025
- Promedio: ~$0.007

---

## LIMITACIONES CONOCIDAS

1. **Qdrant local**: No soporta concurrencia (se usa singleton)
2. **Latencia en queries complejas**: 15-20s (aceptable para precisión 90%+)
3. **Sin auto-corrección avanzada**: Planeado para v2.0
4. **Sin persistencia de historial chatbot**: Se pierde al cerrar navegador
5. **Sin búsqueda híbrida BM25+Vector**: Planeado para futuro

---

## PRÓXIMOS PASOS (NO IMPLEMENTADO)

### Planeado para v2.0
- [ ] Búsqueda híbrida (BM25 + Vector)
- [ ] Neo4j para grafo de conocimiento
- [ ] LangGraph para multi-agente avanzado
- [ ] Redis para caché
- [ ] FastAPI REST API
- [ ] Persistencia de historial chatbot
- [ ] Monitoreo con Prometheus/Grafana

---

## NOTAS IMPORTANTES

### Para Claude Code

1. **SIEMPRE consulta CHANGELOG.md** antes de sugerir features - puede que ya estén implementadas
2. **Revisa STACK_TECNOLOGICO.md** para ver técnicas y métricas actuales
3. **NO modifiques RAGPipeline** sin antes verificar impacto en chatbot (usa composición)
4. **Usa Singleton** para recursos compartidos (SharedPipelineManager)
5. **Testing**: Ejecuta scripts de testing después de cambios

### Principios de Diseño

1. **Composición sobre Herencia**: Chatbot CONTIENE RAGPipeline, no hereda
2. **Activación Selectiva**: Multihop y HyDE solo cuando benefician
3. **Fallbacks Automáticos**: Sistema degrada gracefully
4. **Zero Modificaciones al RAG**: Features nuevas vía composición
5. **Documentación Actualizada**: Mantener CHANGELOG y docs sincronizados

---

**Versión**: v1.3.0
**Última actualización**: 2025-10-28
**Estado**: ✅ Producción
**Precisión**: 88-92%
**Cobertura**: RAG + Multihop + HyDE + Chatbot

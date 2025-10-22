CONTEXTO Y REQUERIMIENTOS
Problema a Resolver
El usuario necesita consultar múltiples documentos normativos complejos (100+ páginas) que contienen:

Estructura jerárquica profunda (Títulos → Capítulos → Artículos → Parágrafos)
Referencias cruzadas intensivas ("conforme al artículo X", "según lo dispuesto en...")
Tablas, anexos y flujogramas complementarios
Actualizaciones y modificaciones entre documentos
Conceptos especializados (ej: "OCAD", "SGR", "viabilidad técnica")

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

┌─────────────────────────────────────────────────────────────────┐
│                        USUARIO (Streamlit UI)                    │
│  Selecciona: Áreas → Proyectos → Documentos → Query             │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE ORQUESTACIÓN                          │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐         │
│  │ QueryRouter  │→ │ DocumentRet.  │→ │ AnswerGen.   │         │
│  │ (LangGraph)  │  │ (LlamaIndex)  │  │ (GPT-4)      │         │
│  └──────────────┘  └───────────────┘  └──────────────┘         │
│         ↓                  ↓                   ↓                 │
│  ┌──────────────────────────────────────────────────┐          │
│  │         FactChecker (Validación)                  │          │
│  └──────────────────────────────────────────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                  CAPA DE RETRIEVAL HÍBRIDO                       │
│  ┌─────────────────────┐        ┌──────────────────────┐        │
│  │   QDRANT (Vectores) │←──────→│  NEO4J (Grafo)       │        │
│  │  • Búsqueda vector  │ sync   │  • Context expansion │        │
│  │  • Filtros metadata │        │  • Relaciones        │        │
│  │  • Colecciones/área │        │  • Entidades         │        │
│  └─────────────────────┘        └──────────────────────┘        │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE OPTIMIZACIÓN                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐        │
│  │ Redis Cache │  │ Re-ranking   │  │ Context Pruning │        │
│  │ (queries)   │  │ (cross-enc.) │  │ (token mgmt)    │        │
│  └─────────────┘  └──────────────┘  └─────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                 CAPA DE PROCESAMIENTO DE DATOS                   │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │ PyMuPDF4LLM  │→ │ Hierarchical    │→ │ OpenAI Embed.    │   │
│  │ (extracción) │  │ Chunking        │  │ (vectores)       │   │
│  └──────────────┘  └─────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Flujo de Datos Completo
```
1. INGESTIÓN (Offline, una vez por documento)
   PDF → PyMuPDF4LLM → Texto estructurado
     → HierarchicalNodeParser → Chunks multinivel
     → OpenAI Embeddings → Vectores 1536-dim
     → Carga en Qdrant (colección por área)
     → Extracción de entidades (GPT-3.5)
     → Construcción de grafo Neo4j

2. CONSULTA (Online, por cada query del usuario)
   User Query → Selector Área/Proyecto
     → Redis cache check (hit? → return cached)
     → QueryRouter clasifica tipo de query
     → Embedding de query (text-embedding-3-large)
     → Búsqueda vectorial en Qdrant (top 20, filtrado por área)
     → Expansión de contexto en Neo4j (relaciones + jerarquía)
     → Re-ranking con cross-encoder (top 10 final)
     → Context pruning (max 2000 tokens)
     → GPT-4 genera respuesta
     → CitationManager inyecta referencias
     → FactChecker valida fidelidad
     → Return respuesta + citaciones + path grafo
     → Cache en Redis (TTL 1h)


STACK TECNOLÓGICO DEFINITIVO
Componentes Core

# PYTHON ENVIRONMENT
python: "3.11"
package_manager: "pip"
env_manager: "conda" o "venv"

# EXTRACCIÓN Y PROCESAMIENTO
pymupdf4llm:
  version: ">=0.0.5"
  uso: "Extracción de texto de PDFs con estructura preservada"
  config:
    - keep_layout: true
    - preserve_tables: true
    - extract_images: false

llama_index:
  version: ">=0.10.0"
  componentes:
    - HierarchicalNodeParser: "Chunking multinivel"
    - ServiceContext: "Gestión de LLM y embeddings"
    - VectorStoreIndex: "Índice vectorial"
    - QueryEngine: "Motor de consultas"
  ventaja: "Mejor manejo de grafos que LangChain"

# ALMACENAMIENTO
qdrant_client:
  version: ">=1.7.0"
  deployment: "Docker local (./qdrant_storage)"
  puerto: 6333
  uso: "Vector database con búsqueda híbrida"
  collections:
    - area_juridica
    - area_tecnica
    - area_financiera
    - area_ambiental
  features_clave:
    - sparse_vectors: "Búsqueda keyword BM25"
    - payload_indexing: "Filtros complejos"
    - scroll_api: "Recuperación batch"

neo4j:
  version: "5.15-community"
  deployment: "Docker local (./neo4j_data)"
  puertos: [7474, 7687]
  uso: "Graph database con vectores nativos"
  plugins: ["apoc", "graph-data-science"]
  memoria: "2GB heap"

redis:
  version: "7-alpine"
  deployment: "Docker local (./redis_data)"
  puerto: 6379
  uso: "Caché de queries y resultados"
  persistencia: "AOF (append-only file)"

# MODELOS DE IA
openai:
  embeddings:
    modelo: "text-embedding-3-large"
    dimensiones: 1536
    costo: "$0.13 / 1M tokens"
    uso: "Embeddings de chunks y queries"
  
  llm_principal:
    modelo: "gpt-4-0125-preview"
    costo: "$10 input / $30 output por 1M tokens"
    contexto: "128k tokens"
    temperatura: 0.1
    uso: "Generación de respuestas, extracción de entidades"
  
  llm_secundario:
    modelo: "gpt-3.5-turbo"
    costo: "$0.50 input / $1.50 output por 1M tokens"
    uso: "Clasificación de queries, tareas simples"

# FRAMEWORK DE ORQUESTACIÓN
langgraph:
  version: ">=0.0.20"
  uso: "Sistema multi-agente con flujos condicionales"
  componentes:
    - StateGraph: "Definición de flujo"
    - Node: "Agentes individuales"
    - Edge: "Transiciones"

# RE-RANKING
sentence_transformers:
  modelo: "ms-marco-MiniLM-L-12-v2"
  deployment: "Local (CPU suficiente)"
  uso: "Re-ranking de chunks recuperados"
  mejora: "15-20% en precisión"

# INTERFAZ Y API
streamlit:
  version: ">=1.30.0"
  uso: "UI para pruebas y demostración"
  
fastapi:
  version: ">=0.109.0"
  uso: "API REST (Fase 4)"

# UTILIDADES
loguru: "Logging estructurado"
pydantic: "Validación de datos"
python-dotenv: "Gestión de variables de entorno"

Dependencias Completas (requirements.txt)

# === CORE ===
pymupdf4llm>=0.0.5
llama-index>=0.10.0
llama-index-vector-stores-qdrant>=0.2.0
llama-index-graph-stores-neo4j>=0.2.0
langgraph>=0.0.20
openai>=1.10.0
qdrant-client>=1.7.0
neo4j>=5.15.0
redis>=5.0.0

# === PROCESAMIENTO ===
sentence-transformers>=2.3.0
tiktoken>=0.5.2

# === UI Y API ===
streamlit>=1.30.0
fastapi>=0.109.0
uvicorn>=0.27.0

# === UTILIDADES ===
loguru>=0.7.2
pydantic>=2.5.0
python-dotenv>=1.0.0
pandas>=2.1.0
numpy>=1.24.0

# === TESTING (Fase 3) ===
pytest>=7.4.0
pytest-asyncio>=0.21.0


SCHEMAS DE DATOS DETALLADOS
1. Schema Qdrant (Vector Database)
Estructura de Colecciones

# COLECCIONES SEPARADAS POR ÁREA
COLECCIONES = {
    "area_juridica": {
        "vector_size": 1536,
        "distance": "Cosine",
        "on_disk": True  # Para datasets grandes
    },
    "area_tecnica": {...},
    "area_financiera": {...},
    "area_ambiental": {...}
}

Schema de Payload (Metadata por Chunk)


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
    
    # === CLASIFICACIÓN Y FILTRADO ===
    "area": "juridica",  # juridica | tecnica | financiera | ambiental
    "proyecto": "sgr_general",  # sgr_general | paz | ctei | infraestructura
    "tags": ["regalias", "OCAD", "proyectos", "viabilidad"],  # Array de keywords
    
    # === ESTADO DEL DOCUMENTO ===
    "vigente": True,
    "modificado_por": ["acuerdo_07_2022", "acuerdo_13_2025"],  # Array de IDs
    "fecha_modificacion": "2025-07-15",
    
    # === JERARQUÍA (para navegación y citación) ===
    "nivel_jerarquico": 4,  # 0=doc, 1=titulo, 2=cap, 3=art, 4=para, 5=chunk
    "titulo_numero": "4",
    "titulo_nombre": "Proyectos de Inversión",
    "capitulo_numero": "5",
    "capitulo_nombre": "Ajustes y Liberaciones",
    "articulo_numero": "4.5.1.2",
    "articulo_nombre": "Variables susceptibles de ajuste",
    "paragrafo_numero": "2",
    "seccion_numero": "1",  # Si aplica
    "anexo_numero": None,  # Si aplica
    
    # === CONTENIDO TEXTUAL ===
    "texto": "Los ajustes a los proyectos de inversión aprobados procederán...",
    "texto_limpio": "texto sin caracteres especiales para búsqueda",
    "longitud_texto": 856,  # Número de caracteres
    "longitud_tokens": 214,  # Aproximado
    
    # === CONTEXTO (para solapamiento) ===
    "texto_previo": "...últimas 50 palabras del chunk anterior",
    "texto_siguiente": "primeras 50 palabras del chunk siguiente...",
    "chunk_anterior_id": "uuid-anterior",
    "chunk_siguiente_id": "uuid-siguiente",
    
    # === RESÚMENES PRE-COMPUTADOS ===
    "resumen_chunk": "Resumen de 50-100 palabras del chunk actual",
    "resumen_articulo": "Resumen del artículo completo al que pertenece",
    "resumen_capitulo": "Resumen del capítulo al que pertenece",
    "es_resumen": False,  # True si el chunk mismo es un resumen
    
    # === ANÁLISIS SEMÁNTICO ===
    "conceptos_clave": ["ajuste", "proyecto aprobado", "ejecutor"],
    "entidades_mencionadas": ["OCAD", "Secretaría Técnica", "DNP"],
    "tipo_contenido": "procedimiento",  # definicion | requisito | procedimiento | ejemplo | tabla
    "contiene_tabla": False,
    "contiene_lista": True,
    "contiene_formula": False,
    
    # === CITACIÓN (formato legal colombiano) ===
    "citacion_corta": "Art. 4.5.1.2 Par. 2, Acuerdo 03/2021",
    "citacion_completa": "Artículo 4.5.1.2 Parágrafo 2 del Acuerdo 03 de 2021 - Acuerdo Único del Sistema General de Regalías",
    "citacion_apa": "Comisión Rectora SGR. (2021). Acuerdo 03 de 2021, Art. 4.5.1.2 Par. 2.",
    
    # === UBICACIÓN EN EL DOCUMENTO ORIGINAL ===
    "pagina": 42,
    "posicion_inicio": 1250,  # Character offset desde inicio del doc
    "posicion_fin": 1680,
    "bbox": [100, 200, 500, 300],  # Bounding box en PDF si disponible
    
    # === METADATOS DE PROCESAMIENTO ===
    "chunk_index": 425,  # Posición en secuencia de chunks del documento
    "fecha_procesamiento": "2025-01-15T10:30:00",
    "version_procesamiento": "1.0",
    "embedding_model": "text-embedding-3-large",
    
    # === RELACIONES CON OTROS CHUNKS (IDs) ===
    "referencias_a": ["acuerdo_03_2021_art_4_5_1_2_1"],  # IDs de artículos referenciados
    "referenciado_por": ["acuerdo_03_2021_art_4_5_2_1"],
    "relacionado_con": ["acuerdo_03_2021_art_2_1_1"],  # Artículos semánticamente similares
    
    # === IDIOMA Y LOCALIZACIÓN ===
    "idioma": "es",
    "pais": "CO",
    "jurisdiccion": "nacional",
}
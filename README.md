# 📚 Sistema RAG para Documentos Normativos

**Versión**: v1.3.0 | **Estado**: ✅ Producción | **Precisión**: 88-92%

Sistema avanzado de consulta inteligente de documentos usando RAG (Retrieval-Augmented Generation) con técnicas state-of-the-art: Multihop Retrieval, HyDE, Response Validation y Chatbot Conversacional.

## ✨ Características Principales

### Core RAG
- **Procesamiento Jerárquico Universal**: Maneja documentos legales, técnicos y genéricos con estructura multinivel (0-5 niveles)
- **Búsqueda Vectorial Avanzada**: Qdrant + OpenAI embeddings (text-embedding-3-large)
- **Re-ranking Inteligente**: Cross-encoder para mejorar precisión top-K
- **Expansión de Contexto**: Chunks adyacentes con awareness jerárquico
- **Citación Automática**: Sistema de citaciones legales con validación

### Técnicas Avanzadas (v1.2.0 - v1.3.0)
- **🚀 Multihop Retrieval**: Queries complejas con descomposición y fusion scoring (+10% precisión)
- **🔬 HyDE**: Documentos hipotéticos para terminología incorrecta (+8-10% precisión)
- **✅ Response Validation**: Auto-retry para completitud (+3-5% precisión)
- **💬 Chatbot Conversacional**: Multi-turno con reformulación contextual

### Interfaz
- **RAG Tradicional**: Queries únicas con todas las técnicas avanzadas
- **Chatbot IA**: Conversaciones multi-turno con memoria y contexto
- **Métricas en Tiempo Real**: Latencia, costo, tokens, precisión
- **Multi-Área**: SGR, Inteligencia Artificial, General

## 🏗️ Arquitectura del Sistema

```
Usuario → Query
    ↓
[1] Embedding (text-embedding-3-small)
    ↓
[2] Búsqueda Vectorial (Qdrant) → Top-K chunks iniciales
    ↓
[3] Re-ranking (cross-encoder) → Top-N chunks finales
    ↓
[4] Expansión de Contexto → Chunks adyacentes
    ↓
[5] Generación (GPT-4o-mini) → Respuesta con citaciones
    ↓
[6] Validación de Citaciones → Reporte de calidad
    ↓
Respuesta Final + Fuentes + Métricas
```

## Requisitos Previos

- Python 3.11+
- Docker Desktop (para Qdrant)
- API Key de OpenAI

## Instalación

### 1. Clonar y configurar entorno

```bash
cd Poc_Rag_Graph
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copiar `.env.example` a `.env` y configurar:

```bash
cp .env.example .env
```

Editar `.env` y agregar tu API key de OpenAI:

```
OPENAI_API_KEY=sk-tu-api-key-aqui
```

### 3. Levantar Qdrant

Asegúrate de que Docker Desktop esté corriendo, luego:

```bash
docker-compose up -d
```

Verificar que Qdrant está corriendo:
- Dashboard: http://localhost:6333/dashboard
- API: http://localhost:6333

### 4. Ingestar documentos (Fase 2)

```bash
python scripts/01_ingest_pdfs.py
```

Esto procesará los PDFs en `data/` y los cargará en Qdrant.

### 5. Ejecutar interfaz Streamlit (Fase 5)


```bash
streamlit run app/streamlit_app.py
```

La aplicación estará disponible en http://localhost:8501

## Estructura del Proyecto

```
Poc_Rag_Graph/
├── data/                              # PDFs de documentos normativos
├── src/                               # Código fuente
│   ├── config.py                     # Configuración centralizada
│   ├── ingest/                       # Pipeline de ingestión
│   │   ├── pdf_extractor.py         # Extracción de PDFs con detección de estructura
│   │   ├── chunker.py               # Orquestador de chunking
│   │   ├── document_hierarchy_processor.py  # ⭐ NUEVO: Procesador jerárquico universal
│   │   ├── hierarchy_config.py      # ⭐ NUEVO: Configuración de jerarquías
│   │   └── vectorizer.py            # Generación de embeddings y carga a Qdrant
│   ├── retrieval/                    # Sistema de búsqueda
│   │   ├── vector_search.py
│   │   └── reranker.py
│   ├── generation/                   # Generación de respuestas
│   │   ├── llm_client.py
│   │   └── citation_manager.py
│   └── pipeline.py                   # Orquestador principal
├── app/                              # Interfaz de usuario
│   └── streamlit_app.py
├── scripts/                          # Scripts de utilidad
│   ├── 01_ingest_pdfs.py            # Pipeline de ingestión completo
│   ├── inspect_tecnico_v2.py        # Inspección de documentos procesados
│   └── validate_new_architecture.py  # ⭐ NUEVO: Validación de arquitectura
├── docs/                             # ⭐ NUEVA: Documentación completa
│   ├── GUIA_USO_PROCESAMIENTO_JERARQUICO.md  # Guía de usuario
│   ├── ARQUITECTURA_TECNICA.md              # Arquitectura técnica detallada
│   ├── DISEÑO_ARQUITECTURA_UNIFICADA.md     # Diseño de la solución
│   └── ANALISIS_COMPLETO_ARQUITECTURA_GRAFO.md  # Análisis del sistema
├── storage/                          # Almacenamiento de Qdrant
├── logs/                             # Logs de la aplicación
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## 🚀 Uso

### Interfaz Web (Streamlit)

La forma más sencilla de usar el sistema:

```bash
streamlit run app/streamlit_app.py
```

Abre http://localhost:8501 en tu navegador y:
- Escribe tu pregunta en el campo de búsqueda
- Ajusta parámetros avanzados en la barra lateral (opcional)
- Filtra por documento específico o busca en todos
- Visualiza respuesta, fuentes consultadas y métricas de performance

### Scripts de Prueba

**Prueba Rápida** (1 query):
```bash
python scripts/test_quick.py
```

**Prueba Completa** (múltiples queries con métricas):
```bash
python scripts/test_pipeline.py
```

### Queries de Ejemplo

- "¿Qué es un OCAD?"
- "¿Cuáles son los requisitos para viabilizar un proyecto?"
- "Explica el proceso de ajuste de proyectos aprobados"
- "¿Qué es el Sistema General de Regalías?"
- "Resume el Título 4 del Acuerdo Único"

### Pipeline de Ingestión

El script `scripts/ingest_documents.py` ejecuta:

1. **Extracción**: PDFs → Markdown estructurado (PyMuPDF4LLM)
2. **Chunking**: Preserva jerarquía legal (artículos, parágrafos, numerales)
3. **Embeddings**: Genera vectores con text-embedding-3-small
4. **Indexación**: Carga en Qdrant con metadata rica

### Pipeline de Consulta (RAG)

El sistema `src/pipeline.py` ejecuta 5 pasos:

1. **Embedding**: Convierte query a vector
2. **Búsqueda Vectorial**: Recupera top-K chunks similares de Qdrant
3. **Re-ranking**: Mejora precisión con cross-encoder
4. **Expansión**: Añade chunks adyacentes para contexto
5. **Generación**: GPT-4o-mini crea respuesta con citaciones
6. **Validación**: Verifica calidad de citaciones

### Usando el Pipeline Programáticamente

```python
from src.pipeline import RAGPipeline

# Inicializar pipeline
pipeline = RAGPipeline()

# Consultar
result = pipeline.query(
    question="¿Qué es un OCAD?",
    documento_id=None,  # Opcional: filtrar por documento
    top_k_retrieval=20,  # Chunks iniciales
    top_k_rerank=5,      # Chunks finales
    expand_context=True  # Expandir contexto
)

# Acceder a resultados
print(result["answer"])           # Respuesta generada
print(result["sources"])          # Fuentes consultadas
print(result["metrics"])          # Métricas de performance
print(result["citation_report"])  # Reporte de citaciones
```

## 💰 Estimación de Costos

### Ingestión (una vez)
- **Embeddings**: ~200k tokens
- **Modelo**: text-embedding-3-small ($0.020 / 1M tokens)
- **Costo**: ~$0.004

### Queries (operación normal)
- **Por query**: ~700 tokens input + ~200 tokens output
- **Modelo**: gpt-4o-mini ($0.150 / 1M tokens input, $0.600 / 1M tokens output)
- **Costo por query**: ~$0.0002
- **100 queries**: ~$0.02

### Estimación Total MVP
- **Setup inicial**: $0.004 (una vez)
- **100 queries de prueba**: $0.02
- **Total**: < $0.03

**Nota**: Los costos reales se muestran en tiempo real en la interfaz Streamlit.

## Troubleshooting

### Docker no inicia

```bash
# Verificar que Docker Desktop esté corriendo
docker ps

# Si no funciona, reiniciar Docker Desktop
```

### Error de API Key

```bash
# Verificar que .env existe y tiene la key correcta
cat .env | grep OPENAI_API_KEY

# La key debe empezar con 'sk-'
```

### Qdrant no conecta

```bash
# Verificar que el container está corriendo
docker-compose ps

# Revisar logs
docker-compose logs qdrant

# Reiniciar servicio
docker-compose restart qdrant
```

## 📊 Componentes del Sistema

### Ingestión (`src/ingest/`)
- **pdf_extractor.py**: Extrae texto estructurado de PDFs con detección automática de tipo de documento
- **document_hierarchy_processor.py**: ⭐ Procesador jerárquico universal que maneja cualquier tipo de documento
- **hierarchy_config.py**: ⭐ Configuración centralizada de mapeos de jerarquías y niveles
- **chunker.py**: Orquestador que delega a DocumentHierarchyProcessor
- **vectorizer.py**: Genera embeddings y carga en Qdrant con metadata rica

### Retrieval (`src/retrieval/`)
- **vector_search.py**: Búsqueda semántica en Qdrant con filtros jerárquicos
- **reranker.py**: Re-ranking con cross-encoder para mejorar precisión

### Generación (`src/generation/`)
- **llm_client.py**: Cliente OpenAI con tracking de costos
- **citation_manager.py**: Validación y formateo de citaciones legales

### Pipeline (`src/pipeline.py`)
Orquestador principal que coordina todo el flujo RAG.

### Configuración (`src/config.py`)
Configuración centralizada con validación de variables de entorno.

### Documentación (`docs/`)
- **GUIA_USO_PROCESAMIENTO_JERARQUICO.md**: Guía completa de uso para usuarios
- **ARQUITECTURA_TECNICA.md**: Documentación técnica detallada para desarrolladores
- **DISEÑO_ARQUITECTURA_UNIFICADA.md**: Diseño de la arquitectura unificada
- **ANALISIS_COMPLETO_ARQUITECTURA_GRAFO.md**: Análisis del sistema y decisiones de diseño

## 🎯 Métricas y Observabilidad

El sistema proporciona métricas detalladas en cada query:

- **Performance**:
  - Tiempo total de respuesta
  - Tiempo de búsqueda vectorial
  - Tiempo de re-ranking
  - Tiempo de generación

- **Retrieval**:
  - Chunks recuperados (búsqueda inicial)
  - Chunks finales (post re-ranking)
  - Scores de relevancia

- **Generación**:
  - Tokens de entrada
  - Tokens de salida
  - Costo de la query
  - Costo acumulado de sesión

- **Calidad**:
  - Número de citaciones
  - Fuentes únicas utilizadas
  - Validación de citaciones
  - Advertencias de calidad

## 🔧 Configuración Avanzada

Edita `src/config.py` o usa variables de entorno:

```python
# Retrieval
RETRIEVAL_TOP_K = 20        # Chunks iniciales
RETRIEVAL_TOP_K_RERANK = 5  # Chunks finales
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Generación
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 1000

# Vectorización
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
```

## 🏛️ Arquitectura Jerárquica Universal (NUEVO)

### Sistema de Procesamiento Unificado

El proyecto implementa una **arquitectura jerárquica universal** que permite procesar cualquier tipo de documento con estructura multinivel usando un único código base.

#### Características Clave

✅ **Procesamiento universal** para documentos legales, técnicos, financieros y ambientales
✅ **6 niveles jerárquicos** (0=Documento → 1=División Mayor → ... → 5=Anexo)
✅ **Grafo bidireccional** con relaciones parent↔child completas
✅ **Extensible** vía configuración (sin cambios de código)
✅ **Validación automática** de completitud del grafo

#### Mejoras Implementadas

| Métrica | Antes | Ahora | Mejora |
|---------|-------|-------|--------|
| **Documentos técnicos** | 0% jerarquía | 71.9% completitud | **+71.9%** ✅ |
| **Chunks con parent_id** | 0 | 493/494 (99.8%) | **+493** ✅ |
| **Niveles detectados** | 0 | 5 niveles | **+5** ✅ |
| **Consultas funcionando** | ❌ Fallaban | ✅ Funcionan | **100%** ✅ |

#### Documentación Completa

📖 **Para Usuarios**: [`docs/GUIA_USO_PROCESAMIENTO_JERARQUICO.md`](docs/GUIA_USO_PROCESAMIENTO_JERARQUICO.md)
- Cómo usar el sistema
- Procesar nuevos documentos
- Agregar tipos de documento personalizados
- Scripts y ejemplos prácticos

🔧 **Para Desarrolladores**: [`docs/ARQUITECTURA_TECNICA.md`](docs/ARQUITECTURA_TECNICA.md)
- Principios de diseño
- Algoritmos clave
- Estructura de datos
- Extensibilidad y optimizaciones

#### Agregar Nuevo Tipo de Documento

```python
# 1. Actualizar src/ingest/hierarchy_config.py
ELEMENT_NAMES["financial"] = {
    1: {"singular": "Sección", "plural": "Secciones"},
    2: {"singular": "Categoría", "plural": "Categorías"},
    3: {"singular": "Subcategoría", "plural": "Subcategorías"},
    4: {"singular": "Cuenta", "plural": "Cuentas"},
    5: {"singular": "Nota", "plural": "Notas"},
}

# 2. ¡Listo! El procesador universal lo maneja automáticamente
python scripts/01_ingest_pdfs.py
```

#### Validación del Sistema

```bash
# Validar que todo funciona correctamente
python scripts/validate_new_architecture.py

# Inspeccionar documento específico
python scripts/inspect_tecnico_v2.py
```

---

## 📈 Próximos Pasos (Post-MVP)

### Fase de Expansión
- [ ] **Neo4j**: Grafo de conocimiento para relaciones entre documentos
- [ ] **LangGraph**: Sistema multi-agente para consultas complejas
- [ ] **Redis**: Caché de embeddings y respuestas frecuentes
- [ ] **FastAPI**: API REST para integración con otros sistemas

### Mejoras de Calidad
- [ ] **Fact-checking**: Validación automática de respuestas
- [ ] **Comparación de documentos**: Análisis de cambios entre versiones
- [ ] **Resumen automático**: Generación de resúmenes ejecutivos
- [ ] **Extracción de entidades**: Identificación de personas, lugares, fechas
- [x] **Procesamiento jerárquico universal**: ✅ COMPLETADO

### Escalabilidad
- [ ] **Batch processing**: Procesamiento masivo de documentos
- [ ] **Monitoreo**: Integración con Prometheus/Grafana
- [ ] **Testing**: Suite completa de tests unitarios e integración
- [ ] **CI/CD**: Pipeline automatizado de despliegue

## 📚 Documentación

### Documentación Principal

| Documento | Descripción | Cuándo Leer |
|-----------|-------------|-------------|
| **[README.md](README.md)** | 👈 Estás aquí - Inicio rápido | Primera lectura |
| **[CLAUDE.md](CLAUDE.md)** | Especificaciones técnicas completas | Para desarrolladores |
| **[CHANGELOG.md](CHANGELOG.md)** | Historial de cambios (v1.0 → v1.3) | Entender evolución |

### Documentación Técnica (`docs/`)

| Documento | Descripción | Audiencia |
|-----------|-------------|-----------|
| **[STACK_TECNOLOGICO.md](docs/STACK_TECNOLOGICO.md)** | 🆕 Tecnologías y métricas de precisión | Todos |
| **[ARQUITECTURA_TECNICA.md](docs/ARQUITECTURA_TECNICA.md)** | Arquitectura detallada del sistema | Desarrolladores |
| **[FLUJO_IMPLEMENTADO_EXPLICADO.md](docs/FLUJO_IMPLEMENTADO_EXPLICADO.md)** | Flujo completo paso a paso | Principiantes |
| **[SISTEMA_MULTIHOP.md](docs/SISTEMA_MULTIHOP.md)** | Sistema Multihop Retrieval (40+ páginas) | Implementadores |
| **[SISTEMA_HYDE.md](docs/SISTEMA_HYDE.md)** | Sistema HyDE con RRF fusion (40+ páginas) | Implementadores |
| **[chatbot/CHATBOT_DOCUMENTACION_COMPLETA.md](docs/chatbot/CHATBOT_DOCUMENTACION_COMPLETA.md)** | 🆕 Chatbot conversacional completo | Implementadores |

### Flujo de Lectura Recomendado

**Nuevos Usuarios**:
1. README.md (este archivo) → 2. STACK_TECNOLOGICO.md → 3. FLUJO_IMPLEMENTADO_EXPLICADO.md

**Desarrolladores**:
1. README.md → 2. CLAUDE.md → 3. STACK_TECNOLOGICO.md → 4. ARQUITECTURA_TECNICA.md

**Implementadores de Features**:
- Multihop: SISTEMA_MULTIHOP.md
- HyDE: SISTEMA_HYDE.md
- Chatbot: chatbot/CHATBOT_DOCUMENTACION_COMPLETA.md

---

## 📝 Licencia

Proyecto académico - Universidad

## 👥 Contacto

Para dudas o sugerencias sobre el proyecto, consultar la documentación o crear un issue.

---

**Versión**: v1.3.0 (2025-10-28)
**Stack**: Python 3.11 • Qdrant • OpenAI (GPT-4o-mini + text-embedding-3-large) • Streamlit
**Desarrollado por**: Universidad - Proyecto Integrador

---

## 📊 Métricas de Precisión

| Tipo de Query | v1.0.0 | v1.3.0 | Mejora | Técnicas Usadas |
|---------------|--------|--------|--------|-----------------|
| Simple semántica | 70% | 75% | +5% | Vector + Rerank |
| Definiciones | 60% | **90%** | +30% | HyDE + RRF |
| Condicional | 10% | **85%** | +750% | Multihop + Fusion |
| Comparativa | 10% | **85%** | +750% | Multihop Comparison |
| Terminología incorrecta | 35% | 75% | +114% | HyDE Fallback |

**Precisión Global**: 88-92% | **Latencia Promedio**: 6s | **Costo/Query**: ~$0.007

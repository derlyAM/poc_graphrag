# RAG System REST API

API REST para el sistema RAG (Retrieval-Augmented Generation) de consulta y gestión de documentos.

## Inicio Rápido

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Iniciar Qdrant

```bash
docker-compose up -d
```

### 3. Iniciar API

**Linux/Mac:**
```bash
./scripts/start_api.sh
```

**Windows:**
```bash
scripts\start_api.bat
```

**Manualmente:**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Verificar instalación

```bash
curl http://localhost:8000/health
```

## URLs

- **API Base**: `http://localhost:8000`
- **Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

## Endpoints Principales

### Query Documents
```bash
POST /api/v1/rag/query
```

### List Documents
```bash
GET /api/v1/documents
```

### Upload Document
```bash
POST /api/v1/documents/ingest
```

## Ejemplo de Uso

```bash
# Consultar documentos
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Qué es un OCAD?",
    "area": "sgr"
  }'

# Listar documentos
curl http://localhost:8000/api/v1/documents

# Subir documento
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -F "file=@documento.pdf" \
  -F "area=sgr"
```

## Documentación Completa

Ver [API_DOCUMENTATION.md](../docs/API_DOCUMENTATION.md) para documentación detallada con todos los endpoints, ejemplos y códigos de error.

## Estructura del Código

```
api/
├── main.py              # FastAPI app principal
├── dependencies.py      # Inyección de dependencias
├── middleware.py        # Middleware (CORS, logging)
├── models/              # Modelos Pydantic
│   ├── requests.py      # Request models
│   └── responses.py     # Response models
├── routers/             # Endpoints
│   ├── health.py        # Health & status
│   ├── rag.py           # RAG queries
│   ├── documents.py     # Document management
│   └── ingestion.py     # Document upload
└── utils/               # Utilidades
    ├── error_handlers.py
    └── task_manager.py  # Task tracking
```

## Características (Fase 1 - MVP)

✅ Health check y system status
✅ RAG query con configuración completa
✅ Listado y detalle de documentos
✅ Eliminación de documentos
✅ Carga y procesamiento de PDFs
✅ Tracking de tareas de ingestión
✅ Validación automática con Pydantic
✅ Documentación interactiva (Swagger/ReDoc)
✅ Logging estructurado
✅ Manejo de errores

## Próximas Características (Fase 2+)

🔜 Autenticación (API Keys / JWT)
🔜 Rate limiting
🔜 Persistencia de tareas (Redis)
🔜 WebSockets para progreso en tiempo real
🔜 Batch operations
🔜 Métricas (Prometheus)

## Notas de Desarrollo

- La API usa el `SharedPipelineManager` para compartir la instancia de `RAGPipeline` con Streamlit
- Las tareas de ingestión se procesan en background con FastAPI `BackgroundTasks`
- Solo una ingestión puede ejecutarse simultáneamente (limitación de Qdrant local)
- Los archivos temporales se limpian automáticamente después de procesar

## Troubleshooting

### Error: "Cannot connect to Qdrant"
```bash
# Verificar que Qdrant esté corriendo
docker-compose ps
curl http://localhost:6333/health

# Reiniciar Qdrant
docker-compose restart qdrant
```

### Error: "OpenAI API key not found"
```bash
# Verificar .env
cat .env | grep OPENAI_API_KEY

# Asegurar que está exportada
export OPENAI_API_KEY="sk-..."
```

### Error al importar módulos
```bash
# Asegurar que estás en el directorio raíz del proyecto
cd Poc_Rag_Graph

# Verificar estructura
ls -la api/
```

## Licencia

MIT

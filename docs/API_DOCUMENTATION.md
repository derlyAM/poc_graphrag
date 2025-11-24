# API REST - Documentación Completa

**Versión**: 1.3.0 (Fase 1 - MVP)
**Base URL**: `http://localhost:8000`
**Documentación interactiva**: `http://localhost:8000/docs`

---

## Tabla de Contenidos

- [Instalación y Configuración](#instalación-y-configuración)
- [Inicio Rápido](#inicio-rápido)
- [Autenticación](#autenticación)
- [Endpoints](#endpoints)
  - [Health & Status](#health--status)
  - [RAG Query](#rag-query)
  - [Documents Management](#documents-management)
  - [Document Ingestion](#document-ingestion)
- [Ejemplos con cURL](#ejemplos-con-curl)
- [Ejemplos con Python](#ejemplos-con-python)
- [Códigos de Error](#códigos-de-error)
- [Rate Limiting](#rate-limiting)

---

## Instalación y Configuración

### Requisitos Previos

- Python 3.11+
- Qdrant running (Docker)
- OpenAI API Key

### Instalación

```bash
# 1. Clonar repositorio y navegar al directorio
cd Poc_Rag_Graph

# 2. Crear y activar entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env y agregar OPENAI_API_KEY

# 5. Iniciar Qdrant
docker-compose up -d

# 6. Verificar que Qdrant esté corriendo
curl http://localhost:6333/health
```

### Iniciar el API Server

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

El servidor estará disponible en:
- API: `http://localhost:8000`
- Documentación Swagger: `http://localhost:8000/docs`
- Documentación ReDoc: `http://localhost:8000/redoc`

---

## Inicio Rápido

### 1. Verificar estado del sistema

```bash
curl http://localhost:8000/health
```

### 2. Consultar documentos

```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Qué es un OCAD?",
    "area": "sgr"
  }'
```

### 3. Listar documentos

```bash
curl http://localhost:8000/api/v1/documents
```

### 4. Subir nuevo documento

```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -F "file=@/path/to/document.pdf" \
  -F "area=sgr"
```

---

## Autenticación

**Fase 1 (MVP)**: No requiere autenticación.

**Futuro (Fase 2+)**: Se implementará autenticación con API Keys o JWT.

```bash
# Futuro
curl -H "X-API-Key: your-api-key" \
     http://localhost:8000/api/v1/rag/query
```

---

## Endpoints

### Health & Status

#### `GET /health`

**Descripción**: Verifica el estado del sistema y sus dependencias.

**Response (200)**:
```json
{
  "status": "healthy",
  "version": "1.3.0",
  "timestamp": "2025-11-24T12:00:00Z",
  "services": {
    "qdrant": "connected",
    "openai": "available"
  }
}
```

**Estados posibles**:
- `healthy`: Todos los servicios funcionando
- `degraded`: Algunos servicios con problemas
- `unhealthy`: Sistema no operativo

---

#### `GET /api/v1/status`

**Descripción**: Estadísticas detalladas del sistema.

**Response (200)**:
```json
{
  "pipeline_stats": {
    "llm_total_cost": 10.45,
    "model": "gpt-4o-mini",
    "reranker_model": "cross-encoder/ms-marco-MiniLM-L-12-v2"
  },
  "collection_stats": {
    "total_chunks": 2443,
    "by_area": {
      "sgr": 856,
      "inteligencia_artificial": 1247,
      "general": 340
    },
    "collection_name": "normativa_sgr"
  },
  "uptime_seconds": 3600.5
}
```

---

### RAG Query

#### `POST /api/v1/rag/query`

**Descripción**: Consultar documentos con una pregunta en lenguaje natural.

**Request Body**:
```json
{
  "question": "¿Qué es un OCAD y cuáles son sus funciones?",
  "area": "sgr",
  "documento_ids": ["acuerdo_03_2021"],  // Opcional
  "config": {
    "top_k_retrieval": 20,
    "top_k_rerank": 5,
    "expand_context": true,
    "enable_multihop": true,
    "enable_hyde": true,
    "enable_validation": true
  }
}
```

**Parámetros**:

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `question` | string | Sí | Pregunta en lenguaje natural (3-1000 chars) |
| `area` | string | Sí | Área de conocimiento: `sgr`, `inteligencia_artificial`, `general` |
| `documento_ids` | array | No | Filtrar por documentos específicos |
| `config` | object | No | Configuración avanzada del pipeline RAG |

**Response (200)**:
```json
{
  "success": true,
  "answer": "Los OCAD (Órganos Colegiados de Administración y Decisión)...",
  "sources": [
    {
      "chunk_id": "uuid-123",
      "texto": "Los OCAD son instancias de planeación...",
      "citacion_corta": "Art. 4.5.1.2, Acuerdo 03/2021",
      "score": 0.92,
      "documento_id": "acuerdo_03_2021",
      "nivel_jerarquico": 3
    }
  ],
  "num_sources": 5,
  "metrics": {
    "total_time": 4.2,
    "search_time": 1.5,
    "rerank_time": 0.8,
    "generation_time": 1.9,
    "chunks_retrieved": 20,
    "chunks_reranked": 5,
    "total_cost": 0.007,
    "query_type": "definition",
    "retrieval_strategy": "semantic",
    "multihop_used": false,
    "hyde_used": true,
    "validation_retry_used": false
  },
  "query_metadata": {
    "query_enhancement": {...},
    "hyde_metadata": {...}
  }
}
```

**Errores**:

| Código | Descripción |
|--------|-------------|
| 400 | Área inválida o pregunta vacía |
| 500 | Error en el pipeline RAG |

---

### Documents Management

#### `GET /api/v1/documents`

**Descripción**: Lista todos los documentos indexados.

**Query Parameters**:
- `area` (opcional): Filtrar por área

**Ejemplo**:
```bash
GET /api/v1/documents?area=sgr
```

**Response (200)**:
```json
{
  "documents": [
    {
      "documento_id": "acuerdo_03_2021",
      "documento_nombre": "Acuerdo Único del SGR",
      "area": "sgr",
      "documento_tipo": "legal",
      "total_chunks": 856,
      "fecha_procesamiento": "2025-10-28T10:30:00Z"
    }
  ],
  "total": 3,
  "areas": {
    "sgr": 1,
    "inteligencia_artificial": 1,
    "general": 1
  }
}
```

---

#### `GET /api/v1/documents/{documento_id}`

**Descripción**: Obtiene detalles de un documento específico.

**Response (200)**:
```json
{
  "documento_id": "acuerdo_03_2021",
  "documento_nombre": "Acuerdo Único del SGR",
  "area": "sgr",
  "documento_tipo": "legal",
  "metadata": {
    "documento_numero": "03",
    "documento_año": 2021,
    "total_chunks": 856,
    "documento_tipo": "legal"
  },
  "hierarchy_summary": {
    "titulos": 7,
    "capitulos": 42,
    "articulos": 234,
    "secciones": 0
  },
  "total_chunks": 856
}
```

**Errores**:
- `404`: Documento no encontrado

---

#### `DELETE /api/v1/documents/{documento_id}`

**Descripción**: Elimina un documento y todos sus chunks.

⚠️ **ADVERTENCIA**: Esta operación es irreversible!

**Response (200)**:
```json
{
  "success": true,
  "message": "Document 'acuerdo_03_2021' deleted successfully",
  "chunks_deleted": 856
}
```

**Errores**:
- `404`: Documento no encontrado

---

### Document Ingestion

#### `POST /api/v1/documents/ingest`

**Descripción**: Sube y procesa un nuevo documento PDF.

**Request**: `multipart/form-data`

**Campos**:

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `file` | file | Sí | Archivo PDF (max 50 MB) |
| `area` | string | Sí | Área del documento |
| `documento_id` | string | No | ID personalizado (se genera automáticamente si no se provee) |
| `metadata` | string | No | Metadata adicional como JSON string |

**Ejemplo con cURL**:
```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -F "file=@/path/to/document.pdf" \
  -F "area=sgr" \
  -F "documento_id=nuevo_doc_2025" \
  -F 'metadata={"documento_nombre":"Nuevo Documento","documento_año":2025}'
```

**Response (202 Accepted)**:
```json
{
  "task_id": "task_abc123xyz",
  "status": "pending",
  "message": "Document ingestion started",
  "estimated_time_seconds": 120,
  "status_url": "/api/v1/documents/ingest/task_abc123xyz"
}
```

**Errores**:

| Código | Error Code | Descripción |
|--------|------------|-------------|
| 400 | `INVALID_AREA` | Área inválida |
| 400 | `INVALID_FILE_TYPE` | Solo se aceptan PDFs |
| 400 | `INVALID_METADATA` | JSON de metadata inválido |
| 413 | `FILE_TOO_LARGE` | Archivo excede 50 MB |

---

#### `GET /api/v1/documents/ingest/{task_id}`

**Descripción**: Consulta el estado de una tarea de ingestión.

**Response (200) - En progreso**:
```json
{
  "task_id": "task_abc123xyz",
  "status": "processing",
  "area": "sgr",
  "documento_id": "nuevo_doc_2025",
  "filename": "documento.pdf",
  "file_size": 2500000,
  "progress": {
    "percent": 45,
    "current_phase": "vectorizing",
    "phases": {
      "extracting": "completed",
      "chunking": "completed",
      "vectorizing": "in_progress"
    }
  },
  "uploaded_at": "2025-11-24T12:00:00Z",
  "started_at": "2025-11-24T12:00:05Z",
  "elapsed_seconds": 45,
  "estimated_remaining_seconds": 55
}
```

**Response (200) - Completado**:
```json
{
  "task_id": "task_abc123xyz",
  "status": "completed",
  "area": "sgr",
  "documento_id": "nuevo_doc_2025",
  "filename": "documento.pdf",
  "file_size": 2500000,
  "results": {
    "chunks_created": 856,
    "vectors_uploaded": 856,
    "total_cost": 0.085,
    "processing_time_seconds": 120.5
  },
  "uploaded_at": "2025-11-24T12:00:00Z",
  "started_at": "2025-11-24T12:00:05Z",
  "completed_at": "2025-11-24T12:02:05Z"
}
```

**Response (200) - Fallido**:
```json
{
  "task_id": "task_abc123xyz",
  "status": "failed",
  "error": "PDF extraction failed: File appears to be encrypted",
  "error_code": "EXTRACTION_FAILED",
  "failed_at": "2025-11-24T12:00:45Z"
}
```

**Fases de procesamiento**:
1. `extracting`: Extracción de texto del PDF
2. `chunking`: Segmentación en chunks
3. `vectorizing`: Generación de embeddings y carga a Qdrant

---

#### `GET /api/v1/documents/ingest`

**Descripción**: Lista todas las tareas de ingestión.

**Query Parameters**:
- `status`: Filtrar por estado (`pending`, `processing`, `completed`, `failed`)
- `area`: Filtrar por área

**Response (200)**:
```json
{
  "tasks": [
    {
      "task_id": "task_abc123xyz",
      "status": "processing",
      "area": "sgr",
      "filename": "documento.pdf",
      "progress_percent": 45,
      "started_at": "2025-11-24T12:00:00Z"
    }
  ],
  "total": 5,
  "by_status": {
    "pending": 0,
    "processing": 1,
    "completed": 3,
    "failed": 1,
    "cancelled": 0
  }
}
```

---

#### `DELETE /api/v1/documents/ingest/{task_id}`

**Descripción**: Cancela una tarea de ingestión.

⚠️ **Nota**: Solo marca la tarea como cancelada. Si ya está procesando, puede que complete de todas formas.

**Response (200)**:
```json
{
  "success": true,
  "message": "Ingestion task cancelled",
  "task_id": "task_abc123xyz",
  "status": "cancelled"
}
```

---

## Ejemplos con cURL

### Consulta simple

```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Qué es un OCAD?",
    "area": "sgr"
  }'
```

### Consulta con configuración personalizada

```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuáles son las funciones de los OCAD regionales?",
    "area": "sgr",
    "documento_ids": ["acuerdo_03_2021"],
    "config": {
      "top_k_retrieval": 30,
      "enable_multihop": true,
      "enable_hyde": true
    }
  }'
```

### Subir documento

```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -F "file=@documento.pdf" \
  -F "area=sgr" \
  -F "documento_id=doc_2025_01" \
  -F 'metadata={"documento_nombre":"Documento Técnico SGR","documento_tipo":"technical","documento_año":2025}'
```

### Consultar estado de ingestión

```bash
curl http://localhost:8000/api/v1/documents/ingest/task_abc123xyz
```

### Listar documentos filtrados

```bash
curl http://localhost:8000/api/v1/documents?area=inteligencia_artificial
```

---

## Ejemplos con Python

### Usando `requests`

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# 1. Health check
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# 2. Query documents
query_payload = {
    "question": "¿Qué es un OCAD?",
    "area": "sgr",
    "config": {
        "enable_multihop": True,
        "enable_hyde": True
    }
}

response = requests.post(
    f"{BASE_URL}/api/v1/rag/query",
    json=query_payload
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Cost: ${result['metrics']['total_cost']:.6f}")
print(f"Sources: {result['num_sources']}")

# 3. Upload document
with open("documento.pdf", "rb") as f:
    files = {"file": f}
    data = {
        "area": "sgr",
        "documento_id": "doc_2025_01",
        "metadata": json.dumps({
            "documento_nombre": "Nuevo Documento",
            "documento_año": 2025
        })
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/documents/ingest",
        files=files,
        data=data
    )

    task = response.json()
    task_id = task["task_id"]
    print(f"Upload initiated: {task_id}")

# 4. Check ingestion status
import time

while True:
    response = requests.get(
        f"{BASE_URL}/api/v1/documents/ingest/{task_id}"
    )
    status = response.json()

    print(f"Status: {status['status']} - {status.get('progress', {}).get('percent', 0)}%")

    if status["status"] in ["completed", "failed"]:
        break

    time.sleep(5)

if status["status"] == "completed":
    print(f"Ingestion completed!")
    print(f"Chunks created: {status['results']['chunks_created']}")
    print(f"Cost: ${status['results']['total_cost']:.6f}")
else:
    print(f"Ingestion failed: {status['error']}")
```

### Cliente reutilizable

```python
class RAGClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def query(self, question, area, **kwargs):
        """Query the RAG system."""
        payload = {
            "question": question,
            "area": area,
            **kwargs
        }
        response = requests.post(
            f"{self.base_url}/api/v1/rag/query",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def list_documents(self, area=None):
        """List all documents."""
        params = {"area": area} if area else {}
        response = requests.get(
            f"{self.base_url}/api/v1/documents",
            params=params
        )
        response.raise_for_status()
        return response.json()

    def upload_document(self, file_path, area, **kwargs):
        """Upload and ingest a document."""
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"area": area, **kwargs}

            if "metadata" in data:
                data["metadata"] = json.dumps(data["metadata"])

            response = requests.post(
                f"{self.base_url}/api/v1/documents/ingest",
                files=files,
                data=data
            )
            response.raise_for_status()
            return response.json()

    def get_ingestion_status(self, task_id):
        """Get ingestion task status."""
        response = requests.get(
            f"{self.base_url}/api/v1/documents/ingest/{task_id}"
        )
        response.raise_for_status()
        return response.json()

# Usage
client = RAGClient()

# Query
result = client.query(
    question="¿Qué es un OCAD?",
    area="sgr"
)
print(result["answer"])

# Upload
task = client.upload_document(
    file_path="documento.pdf",
    area="sgr",
    metadata={"documento_nombre": "Nuevo Doc"}
)
print(f"Task ID: {task['task_id']}")
```

---

## Códigos de Error

### Generales

| Código HTTP | Error Code | Descripción |
|-------------|------------|-------------|
| 400 | `VALIDATION_ERROR` | Error de validación en parámetros |
| 404 | `NOT_FOUND` | Recurso no encontrado |
| 500 | `INTERNAL_ERROR` | Error interno del servidor |

### RAG Query

| Error Code | Descripción |
|------------|-------------|
| `INVALID_AREA` | Área no válida (debe ser sgr, inteligencia_artificial, general) |
| `QUERY_FAILED` | Error al ejecutar la consulta RAG |

### Document Ingestion

| Error Code | Descripción |
|------------|-------------|
| `INVALID_FILE_TYPE` | Solo se aceptan archivos PDF |
| `FILE_TOO_LARGE` | Archivo excede el límite de 50 MB |
| `EMPTY_FILE` | El archivo está vacío |
| `INVALID_METADATA` | Formato JSON de metadata inválido |
| `EXTRACTION_FAILED` | Error al extraer contenido del PDF |
| `INGESTION_FAILED` | Error general en el proceso de ingestión |

### Documents

| Error Code | Descripción |
|------------|-------------|
| `DOCUMENT_NOT_FOUND` | Documento no encontrado en la colección |
| `DELETE_FAILED` | Error al eliminar documento |
| `LIST_FAILED` | Error al listar documentos |

---

## Rate Limiting

**Fase 1 (MVP)**: No implementado.

**Futuro (Fase 2+)**: Se implementará rate limiting con los siguientes límites:

```
Sin autenticación:
  - 10 requests/minuto por IP

Con API Key:
  - 100 requests/minuto
  - 1000 requests/día

Headers de respuesta:
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 95
  X-RateLimit-Reset: 1635789600
```

---

## Notas de Implementación

### Limitaciones Actuales (MVP)

1. **Sin autenticación**: Cualquiera con acceso al servidor puede usar la API
2. **Sin rate limiting**: No hay límites de uso
3. **Tareas en memoria**: Las tareas de ingestión se pierden si el servidor reinicia
4. **Sin WebSockets**: No hay streaming de respuestas
5. **Qdrant local**: Solo soporta una ingestión simultánea

### Próximas Mejoras (Fase 2+)

- Autenticación con API Keys o JWT
- Rate limiting por usuario
- Persistencia de tareas con Redis
- WebSockets para progreso en tiempo real
- Batch operations
- Métricas con Prometheus
- Deployment con Docker

---

## Soporte

Para reportar problemas o solicitar features:
- GitHub Issues: [enlace]
- Email: [email]

---

**Última actualización**: 2025-11-24
**Versión de API**: 1.3.0

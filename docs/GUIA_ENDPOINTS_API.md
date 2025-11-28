# 📡 Guía Completa de Endpoints API REST

**Versión**: 1.3.0  
**Base URL**: `http://localhost:8000`  
**Documentación Interactiva**: `http://localhost:8000/docs` (Swagger) o `http://localhost:8000/redoc` (ReDoc)

---

## 📋 Tabla de Contenidos

1. [Inicio Rápido](#inicio-rápido)
2. [Endpoints de Health Check](#1-endpoints-de-health-check)
3. [Endpoints de RAG (Consultas)](#2-endpoints-de-rag-consultas)
4. [Endpoints de Documentos](#3-endpoints-de-documentos)
5. [Endpoints de Ingestión](#4-endpoints-de-ingestión)
6. [Ejemplos de Uso](#ejemplos-de-uso)
7. [Códigos de Error](#códigos-de-error)

---

## 🚀 Inicio Rápido

### Iniciar el Servidor API

```bash
# Opción 1: Script (Linux/Mac)
./scripts/start_api.sh

# Opción 2: Script (Windows)
scripts\start_api.bat

# Opción 3: Manual
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Verificar que está funcionando

```bash
curl http://localhost:8000/health
```

---

## 1. Endpoints de Health Check

### 1.1. GET `/health`

**Descripción**: Verifica el estado de salud básico de la API y sus dependencias.

**Respuesta**:
```json
{
  "status": "healthy",
  "version": "1.3.0",
  "timestamp": "2025-01-15T10:30:00",
  "services": {
    "qdrant": "connected",
    "openai": "available"
  }
}
```

**Estados posibles**:
- `healthy`: Todo funciona correctamente
- `degraded`: Algunos servicios no están disponibles
- `unhealthy`: Servicios críticos no disponibles

**Ejemplo con cURL**:
```bash
curl http://localhost:8000/health
```

**Ejemplo con Python**:
```python
import requests

response = requests.get("http://localhost:8000/health")
print(response.json())
```

---

### 1.2. GET `/api/v1/status`

**Descripción**: Obtiene el estado detallado del sistema con estadísticas completas.

**Respuesta**:
```json
{
  "pipeline_stats": {
    "collection": {
      "vectors_count": 2443,
      "points_count": 2443
    },
    "llm_total_cost": 0.05,
    "model": "gpt-4o-mini",
    "reranker_model": "cross-encoder/ms-marco-MiniLM-L-12-v2"
  },
  "collection_stats": {
    "total_chunks": 2443,
    "by_area": {
      "sgr": 1200,
      "inteligencia_artificial": 800,
      "general": 443
    },
    "collection_name": "normativa_sgr"
  },
  "uptime_seconds": 3600.5
}
```

**Ejemplo con cURL**:
```bash
curl http://localhost:8000/api/v1/status
```

**Ejemplo con Python**:
```python
import requests

response = requests.get("http://localhost:8000/api/v1/status")
status = response.json()

print(f"Total chunks: {status['collection_stats']['total_chunks']}")
print(f"Uptime: {status['uptime_seconds']:.0f} segundos")
```

---

## 2. Endpoints de RAG (Consultas)

### 2.1. POST `/api/v1/rag/query`

**Descripción**: Consulta el sistema RAG con una pregunta en lenguaje natural y obtiene una respuesta con fuentes.

**Request Body**:
```json
{
  "question": "¿Qué es un OCAD?",
  "area": "sgr",
  "documento_ids": null,
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
- `question` (requerido): Pregunta del usuario (3-1000 caracteres)
- `area` (requerido): Área de conocimiento (`sgr`, `inteligencia_artificial`, `general`)
- `documento_ids` (opcional): Lista de IDs de documentos para filtrar
- `config` (opcional): Configuración avanzada del pipeline

**Response**:
```json
{
  "success": true,
  "answer": "El OCAD (Órgano Colegiado de Administración y Decisión) es...",
  "sources": [
    {
      "chunk_id": "chunk_123",
      "texto": "El OCAD es la instancia...",
      "citacion_corta": "Acuerdo Único 2025, Art. 2.1.1",
      "score": 0.92,
      "documento_id": "acuerdo_unico_2025",
      "nivel_jerarquico": 3
    }
  ],
  "num_sources": 5,
  "metrics": {
    "total_time": 6.2,
    "search_time": 1.5,
    "rerank_time": 0.8,
    "generation_time": 3.2,
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
    "query_decomposition": null,
    "hyde_metadata": {...},
    "validation_metadata": {...}
  }
}
```

**Ejemplo con cURL**:
```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Qué es un OCAD?",
    "area": "sgr"
  }'
```

**Ejemplo con Python**:
```python
import requests

url = "http://localhost:8000/api/v1/rag/query"
payload = {
    "question": "¿Qué es un OCAD?",
    "area": "sgr",
    "config": {
        "enable_multihop": True,
        "enable_hyde": True
    }
}

response = requests.post(url, json=payload)
result = response.json()

print(f"Respuesta: {result['answer']}")
print(f"Fuentes: {result['num_sources']}")
print(f"Costo: ${result['metrics']['total_cost']:.6f}")
```

**Ejemplo con JavaScript (fetch)**:
```javascript
const response = await fetch('http://localhost:8000/api/v1/rag/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    question: '¿Qué es un OCAD?',
    area: 'sgr',
    config: {
      enable_multihop: true,
      enable_hyde: true
    }
  })
});

const result = await response.json();
console.log('Respuesta:', result.answer);
console.log('Fuentes:', result.num_sources);
```

**Casos de Uso**:

1. **Consulta Simple**:
```json
{
  "question": "¿Qué es el Sistema General de Regalías?",
  "area": "sgr"
}
```

2. **Consulta con Filtro de Documentos**:
```json
{
  "question": "¿Cuáles son los requisitos para viabilizar un proyecto?",
  "area": "sgr",
  "documento_ids": ["acuerdo_unico_2025"]
}
```

3. **Consulta Compleja (Multihop)**:
```json
{
  "question": "¿Puedo ajustar el cronograma si estoy en fase II?",
  "area": "sgr",
  "config": {
    "enable_multihop": true
  }
}
```

---

## 3. Endpoints de Documentos

### 3.1. GET `/api/v1/documents`

**Descripción**: Lista todos los documentos indexados, opcionalmente filtrados por área.

**Query Parameters**:
- `area` (opcional): Filtrar por área (`sgr`, `inteligencia_artificial`, `general`)

**Response**:
```json
{
  "documents": [
    {
      "documento_id": "acuerdo_unico_2025",
      "documento_nombre": "Acuerdo Único 2025",
      "area": "sgr",
      "documento_tipo": "legal",
      "total_chunks": 450,
      "fecha_procesamiento": "2025-01-10T08:00:00"
    }
  ],
  "total": 10,
  "areas": {
    "sgr": 5,
    "inteligencia_artificial": 3,
    "general": 2
  }
}
```

**Ejemplo con cURL**:
```bash
# Listar todos los documentos
curl http://localhost:8000/api/v1/documents

# Filtrar por área
curl "http://localhost:8000/api/v1/documents?area=sgr"
```

**Ejemplo con Python**:
```python
import requests

# Listar todos
response = requests.get("http://localhost:8000/api/v1/documents")
docs = response.json()

print(f"Total documentos: {docs['total']}")
for doc in docs['documents']:
    print(f"- {doc['documento_nombre']}: {doc['total_chunks']} chunks")

# Filtrar por área
response = requests.get(
    "http://localhost:8000/api/v1/documents",
    params={"area": "sgr"}
)
```

---

### 3.2. GET `/api/v1/documents/{documento_id}`

**Descripción**: Obtiene información detallada de un documento específico.

**Path Parameters**:
- `documento_id` (requerido): ID del documento

**Response**:
```json
{
  "documento_id": "acuerdo_unico_2025",
  "documento_nombre": "Acuerdo Único 2025",
  "area": "sgr",
  "documento_tipo": "legal",
  "metadata": {
    "documento_numero": "13/2025",
    "documento_año": 2025,
    "total_chunks": 450,
    "documento_tipo": "legal"
  },
  "hierarchy_summary": {
    "titulos": 5,
    "capitulos": 12,
    "articulos": 45,
    "secciones": 120
  },
  "total_chunks": 450
}
```

**Ejemplo con cURL**:
```bash
curl http://localhost:8000/api/v1/documents/acuerdo_unico_2025
```

**Ejemplo con Python**:
```python
import requests

documento_id = "acuerdo_unico_2025"
response = requests.get(
    f"http://localhost:8000/api/v1/documents/{documento_id}"
)
doc = response.json()

print(f"Documento: {doc['documento_nombre']}")
print(f"Chunks: {doc['total_chunks']}")
print(f"Artículos: {doc['hierarchy_summary']['articulos']}")
```

---

### 3.3. DELETE `/api/v1/documents/{documento_id}`

**Descripción**: Elimina un documento y todos sus chunks de la colección.

**⚠️ ADVERTENCIA**: Esta operación es **irreversible**.

**Path Parameters**:
- `documento_id` (requerido): ID del documento a eliminar

**Response**:
```json
{
  "success": true,
  "message": "Document 'acuerdo_unico_2025' deleted successfully",
  "chunks_deleted": 450
}
```

**Ejemplo con cURL**:
```bash
curl -X DELETE http://localhost:8000/api/v1/documents/acuerdo_unico_2025
```

**Ejemplo con Python**:
```python
import requests

documento_id = "acuerdo_unico_2025"
response = requests.delete(
    f"http://localhost:8000/api/v1/documents/{documento_id}"
)
result = response.json()

print(f"Eliminados: {result['chunks_deleted']} chunks")
```

---

## 4. Endpoints de Ingestión

### 4.1. POST `/api/v1/documents/ingest`

**Descripción**: Sube y procesa un nuevo documento PDF. El procesamiento se realiza de forma asíncrona.

**Request** (multipart/form-data):
- `file` (requerido): Archivo PDF (máx. 50 MB)
- `area` (requerido): Área del documento (`sgr`, `inteligencia_artificial`, `general`)
- `documento_id` (opcional): ID del documento (si no se proporciona, se genera automáticamente)
- `metadata` (opcional): Metadata en formato JSON string

**Response** (202 Accepted):
```json
{
  "task_id": "task_abc123",
  "status": "pending",
  "message": "Document ingestion started",
  "estimated_time_seconds": 120,
  "status_url": "/api/v1/documents/ingest/task_abc123"
}
```

**Ejemplo con cURL**:
```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -F "file=@documento.pdf" \
  -F "area=sgr" \
  -F "documento_id=mi_documento_2025" \
  -F 'metadata={"documento_nombre": "Mi Documento", "documento_tipo": "legal"}'
```

**Ejemplo con Python**:
```python
import requests

url = "http://localhost:8000/api/v1/documents/ingest"

files = {
    'file': ('documento.pdf', open('documento.pdf', 'rb'), 'application/pdf')
}

data = {
    'area': 'sgr',
    'documento_id': 'mi_documento_2025',
    'metadata': '{"documento_nombre": "Mi Documento", "documento_tipo": "legal"}'
}

response = requests.post(url, files=files, data=data)
task = response.json()

print(f"Task ID: {task['task_id']}")
print(f"Status URL: {task['status_url']}")
```

**Ejemplo con JavaScript (FormData)**:
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('area', 'sgr');
formData.append('documento_id', 'mi_documento_2025');
formData.append('metadata', JSON.stringify({
  documento_nombre: 'Mi Documento',
  documento_tipo: 'legal'
}));

const response = await fetch('http://localhost:8000/api/v1/documents/ingest', {
  method: 'POST',
  body: formData
});

const task = await response.json();
console.log('Task ID:', task.task_id);
```

---

### 4.2. GET `/api/v1/documents/ingest/{task_id}`

**Descripción**: Consulta el estado de una tarea de ingestión.

**Path Parameters**:
- `task_id` (requerido): ID de la tarea

**Response**:
```json
{
  "task_id": "task_abc123",
  "status": "processing",
  "phase": "vectorizing",
  "progress": 75,
  "area": "sgr",
  "filename": "documento.pdf",
  "file_size": 1024000,
  "documento_id": "mi_documento_2025",
  "chunks_created": 0,
  "vectors_uploaded": 0,
  "total_cost": 0.0,
  "error": null,
  "created_at": "2025-01-15T10:00:00",
  "updated_at": "2025-01-15T10:01:30"
}
```

**Estados posibles**:
- `pending`: Esperando procesamiento
- `processing`: En proceso
- `completed`: Completado exitosamente
- `failed`: Falló
- `cancelled`: Cancelado

**Fases del procesamiento**:
- `extracting`: Extrayendo PDF
- `chunking`: Dividiendo en chunks
- `vectorizing`: Generando embeddings y subiendo

**Ejemplo con cURL**:
```bash
curl http://localhost:8000/api/v1/documents/ingest/task_abc123
```

**Ejemplo con Python (polling)**:
```python
import requests
import time

task_id = "task_abc123"
url = f"http://localhost:8000/api/v1/documents/ingest/{task_id}"

while True:
    response = requests.get(url)
    task = response.json()
    
    print(f"Status: {task['status']} - Progress: {task['progress']}%")
    
    if task['status'] in ['completed', 'failed', 'cancelled']:
        break
    
    time.sleep(2)  # Esperar 2 segundos antes de consultar de nuevo

if task['status'] == 'completed':
    print(f"✅ Completado: {task['chunks_created']} chunks creados")
    print(f"Costo: ${task['total_cost']:.6f}")
else:
    print(f"❌ Error: {task['error']}")
```

---

### 4.3. GET `/api/v1/documents/ingest`

**Descripción**: Lista todas las tareas de ingestión, opcionalmente filtradas.

**Query Parameters**:
- `status` (opcional): Filtrar por estado (`pending`, `processing`, `completed`, `failed`, `cancelled`)
- `area` (opcional): Filtrar por área

**Response**:
```json
{
  "tasks": [
    {
      "task_id": "task_abc123",
      "status": "completed",
      "phase": "completed",
      "progress": 100,
      "area": "sgr",
      "filename": "documento.pdf",
      "chunks_created": 150,
      "total_cost": 0.003
    }
  ],
  "total": 1,
  "by_status": {
    "completed": 1,
    "pending": 0,
    "processing": 0,
    "failed": 0,
    "cancelled": 0
  }
}
```

**Ejemplo con cURL**:
```bash
# Listar todas
curl http://localhost:8000/api/v1/documents/ingest

# Filtrar por estado
curl "http://localhost:8000/api/v1/documents/ingest?status=completed"

# Filtrar por área
curl "http://localhost:8000/api/v1/documents/ingest?area=sgr"
```

---

### 4.4. DELETE `/api/v1/documents/ingest/{task_id}`

**Descripción**: Cancela una tarea de ingestión pendiente o en proceso.

**Path Parameters**:
- `task_id` (requerido): ID de la tarea

**Response**:
```json
{
  "success": true,
  "message": "Ingestion task cancelled",
  "task_id": "task_abc123",
  "status": "cancelled"
}
```

**Nota**: Solo se pueden cancelar tareas con estado `pending` o `processing`. Las tareas `completed` o `failed` no se pueden cancelar.

**Ejemplo con cURL**:
```bash
curl -X DELETE http://localhost:8000/api/v1/documents/ingest/task_abc123
```

---

## 📝 Ejemplos de Uso

### Flujo Completo: Subir y Consultar un Documento

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# 1. Subir documento
print("1. Subiendo documento...")
with open("documento.pdf", "rb") as f:
    files = {"file": f}
    data = {"area": "sgr", "documento_id": "mi_doc_2025"}
    response = requests.post(
        f"{BASE_URL}/api/v1/documents/ingest",
        files=files,
        data=data
    )
    task = response.json()
    task_id = task["task_id"]
    print(f"   Task ID: {task_id}")

# 2. Esperar a que termine el procesamiento
print("2. Esperando procesamiento...")
while True:
    response = requests.get(
        f"{BASE_URL}/api/v1/documents/ingest/{task_id}"
    )
    task = response.json()
    
    if task["status"] == "completed":
        print(f"   ✅ Completado: {task['chunks_created']} chunks")
        break
    elif task["status"] == "failed":
        print(f"   ❌ Error: {task['error']}")
        exit(1)
    
    print(f"   Progreso: {task['progress']}%")
    time.sleep(2)

# 3. Consultar el documento
print("3. Consultando documento...")
response = requests.post(
    f"{BASE_URL}/api/v1/rag/query",
    json={
        "question": "¿Qué es este documento?",
        "area": "sgr",
        "documento_ids": ["mi_doc_2025"]
    }
)
result = response.json()
print(f"   Respuesta: {result['answer'][:100]}...")
print(f"   Fuentes: {result['num_sources']}")
```

---

### Consulta con Configuración Avanzada

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/rag/query",
    json={
        "question": "¿Puedo ajustar el cronograma si estoy en fase II?",
        "area": "sgr",
        "config": {
            "top_k_retrieval": 30,      # Más chunks iniciales
            "top_k_rerank": 8,          # Más chunks finales
            "expand_context": True,      # Expandir contexto
            "enable_multihop": True,     # Activar multihop
            "enable_hyde": True,         # Activar HyDE
            "enable_validation": True    # Activar validación
        }
    }
)

result = response.json()

print("Respuesta:", result["answer"])
print("\nMétricas:")
print(f"  - Tiempo total: {result['metrics']['total_time']:.2f}s")
print(f"  - Costo: ${result['metrics']['total_cost']:.6f}")
print(f"  - Multihop usado: {result['metrics']['multihop_used']}")
print(f"  - HyDE usado: {result['metrics']['hyde_used']}")
print(f"  - Fuentes: {result['num_sources']}")
```

---

## ❌ Códigos de Error

### Códigos HTTP

- `200 OK`: Operación exitosa
- `202 Accepted`: Tarea aceptada (ingestión)
- `400 Bad Request`: Solicitud inválida
- `404 Not Found`: Recurso no encontrado
- `413 Request Entity Too Large`: Archivo muy grande (>50 MB)
- `500 Internal Server Error`: Error del servidor

### Códigos de Error Personalizados

| Código | Descripción |
|--------|-------------|
| `INVALID_AREA` | Área no válida |
| `INVALID_FILE_TYPE` | Tipo de archivo no soportado |
| `FILE_TOO_LARGE` | Archivo excede el límite |
| `EMPTY_FILE` | Archivo vacío |
| `QUERY_FAILED` | Error al procesar query |
| `DOCUMENT_NOT_FOUND` | Documento no encontrado |
| `TASK_NOT_FOUND` | Tarea no encontrada |
| `CANNOT_CANCEL` | No se puede cancelar la tarea |
| `INGESTION_FAILED` | Error en la ingestión |
| `INTERNAL_ERROR` | Error interno del servidor |

### Ejemplo de Manejo de Errores

```python
import requests

try:
    response = requests.post(
        "http://localhost:8000/api/v1/rag/query",
        json={
            "question": "¿Qué es un OCAD?",
            "area": "area_invalida"  # ❌ Área inválida
        }
    )
    
    if response.status_code == 400:
        error = response.json()
        print(f"Error: {error['detail']['error']}")
        print(f"Código: {error['detail']['error_code']}")
    else:
        response.raise_for_status()
        result = response.json()
        print(result["answer"])
        
except requests.exceptions.RequestException as e:
    print(f"Error de conexión: {e}")
```

---

## 🔧 Configuración Avanzada

### Variables de Entorno

La API usa las mismas variables de entorno que el resto del sistema:

```bash
# .env
OPENAI_API_KEY=sk-...
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=normativa_sgr
```

### Headers Personalizados

Actualmente no se requiere autenticación, pero puedes agregar headers personalizados:

```python
headers = {
    "Content-Type": "application/json",
    "X-Request-ID": "mi-request-id-123"
}

response = requests.post(
    "http://localhost:8000/api/v1/rag/query",
    json=payload,
    headers=headers
)
```

---

## 📚 Documentación Interactiva

La API incluye documentación interactiva generada automáticamente:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

Desde Swagger UI puedes:
- Ver todos los endpoints
- Probar los endpoints directamente
- Ver los esquemas de request/response
- Ver ejemplos de uso

---

## 🚨 Notas Importantes

1. **Área es obligatoria**: Todos los endpoints de consulta requieren especificar el área (`sgr`, `inteligencia_artificial`, `general`)

2. **Procesamiento asíncrono**: La ingestión de documentos es asíncrona. Usa el `task_id` para consultar el estado.

3. **Límite de archivos**: El tamaño máximo de archivo es 50 MB.

4. **Una ingestión a la vez**: Solo se puede procesar un documento a la vez (limitación de Qdrant local).

5. **Costo**: Cada query tiene un costo asociado (mostrado en `metrics.total_cost`). El costo incluye embeddings y generación LLM.

---

## 📞 Soporte

Para más información:
- Ver documentación técnica: `docs/ARQUITECTURA_TECNICA.md`
- Ver README principal: `README.md`
- Ver documentación de la API: `api/README.md`

---

**Última actualización**: 2025-01-15  
**Versión API**: 1.3.0





# Plan de Integración con API Externa usando GUIDs

**Fecha**: 2025-01-15  
**Versión**: 1.0.0  
**Tipo**: Arquitectura e Integración

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura Propuesta](#arquitectura-propuesta)
3. [Componentes a Implementar](#componentes-a-implementar)
4. [Endpoints Detallados](#endpoints-detallados)
5. [Cambios en el Sistema](#cambios-en-el-sistema)
6. [Flujos de Integración](#flujos-de-integración)
7. [Ejemplos de Consumo](#ejemplos-de-consumo)
8. [Impacto y Consideraciones](#impacto-y-consideraciones)

---

## 📋 Resumen Ejecutivo

Este documento describe el plan completo para integrar el sistema RAG con una API externa que gestiona áreas y documentos usando identificadores GUID. 

**Objetivo Principal**: Mantener **intacta la lógica de ingesta y consulta** existente, agregando una **capa de mapeo** entre GUIDs externos y códigos internos.

**Principio Clave**: **Cero cambios en la lógica de negocio**. Solo agregamos una capa de traducción GUID ↔ Código Interno.

---

## 🏗️ Arquitectura Propuesta

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────┐
│                    API EXTERNA (Sistema Principal)            │
│  - Gestiona áreas con GUIDs                                  │
│  - Gestiona documentos con GUIDs                             │
│  - Tiene nombres y descripciones de áreas                   │
│  - IDs: GUID (UUID v4)                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTP Requests (REST API)
                     │ - POST /api/v1/integration/areas
                     │ - POST /api/v1/integration/documents
                     │ - POST /api/v1/integration/ingest
                     │ - POST /api/v1/rag/query-with-guids
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              API RAG (Este Sistema)                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  CAPA DE MAPEO (NUEVA)                                │  │
│  │  - GUID Área → Código Interno                        │  │
│  │  - GUID Documento → documento_id                      │  │
│  │  - Almacenamiento: JSON                              │  │
│  │  - Archivo: config/area_guid_mapping.json            │  │
│  └────────────────────┬─────────────────────────────────┘  │
│                       │                                     │
│                       ↓                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  LÓGICA EXISTENTE (SIN CAMBIOS)                      │  │
│  │  - PDFExtractor                                      │  │
│  │  - HierarchicalChunker                               │  │
│  │  - Vectorizer                                        │  │
│  │  - RAGPipeline                                       │  │
│  │  - VectorSearch                                      │  │
│  │  - Scripts de ingesta                                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Principio de Diseño

**Separación de Responsabilidades**:
- **Capa de Integración**: Traduce GUIDs ↔ Códigos Internos
- **Capa de Negocio**: Procesa documentos y consultas (sin cambios)

---

## 📁 Estructura de Carpetas Propuesta

### Decisión: Usar solo GUID para Carpetas

```
data/
├── {area_guid_1}/          # Ej: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
│   ├── {doc_guid_1}.pdf    # Ej: "doc-123e4567-e89b-12d3-a456-426614174000.pdf"
│   ├── {doc_guid_2}.pdf
│   └── ...
├── {area_guid_2}/
│   ├── {doc_guid_3}.pdf
│   └── ...
└── ...
```

**Justificación**:
- ✅ Identificación única garantizada (GUID es UUID v4)
- ✅ No hay colisiones de nombres
- ✅ Fácil de mapear desde API externa
- ✅ No depende de nombres que pueden cambiar

**Mapeo se almacena en**: `config/area_guid_mapping.json`

---

## 🔄 Componentes a Implementar

### 1. Sistema de Mapeo GUID ↔ Código Interno

#### 1.1. Módulo de Mapeo (`src/mapping/guid_mapper.py`)

**Propósito**: Gestionar la traducción bidireccional entre GUIDs externos y códigos internos.

**Estructura de Datos**:

```json
// config/area_guid_mapping.json
{
    "areas": {
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890": {
            "area_code": "sgr",
            "nombre": "Sistema General de Regalías",
            "descripcion": "Área de conocimiento sobre regalías",
            "created_at": "2025-01-15T10:00:00Z",
            "folder_path": "data/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        }
    },
    "documentos": {
        "doc-123e4567-e89b-12d3-a456-426614174000": {
            "documento_id": "sgr_acuerdo_03_2021",
            "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "area_code": "sgr",
            "nombre_archivo": "acuerdo_03_2021.pdf",
            "file_path": "data/a1b2c3d4-e5f6-7890-abcd-ef1234567890/doc-123e4567-e89b-12d3-a456-426614174000.pdf",
            "created_at": "2025-01-15T10:10:00Z"
        }
    }
}
```

**Clase GuidMapper**:

```python
class GuidMapper:
    """
    Gestiona mapeo entre GUIDs externos y códigos internos.
    
    Funciones principales:
    - get_area_code(area_guid) → area_code
    - get_area_guid(area_code) → area_guid
    - register_area(area_guid, nombre, descripcion) → area_code
    - get_documento_id(documento_guid) → documento_id
    - register_documento(documento_guid, area_guid, nombre_archivo) → documento_id
    """
```

**Cómo Afecta**:
- ✅ **Nuevo módulo**: No afecta código existente
- ✅ **Persistencia JSON**: Fácil de versionar y auditar
- ✅ **Carga bajo demanda**: Se carga solo cuando se necesita

**Resultado**:
- Sistema puede traducir entre GUIDs y códigos internos
- Mapeo persistente entre reinicios
- Fácil de consultar y actualizar

---

### 2. Endpoints de Integración

#### 2.1. Endpoint: Crear Área

**Ruta**: `POST /api/v1/integration/areas`

**Request Body**:
```json
{
    "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "nombre": "Sistema General de Regalías",
    "descripcion": "Área de conocimiento sobre regalías y normativa"
}
```

**Validaciones**:
- `area_guid` debe ser un GUID válido (UUID v4)
- `nombre` es requerido (string no vacío)
- `area_guid` no debe existir ya en el mapeo

**Lógica Interna**:
1. Validar formato GUID
2. Verificar que `area_guid` no exista (retornar 409 si existe)
3. Generar `area_code` desde nombre:
   - Normalizar: `nombre.lower().replace(" ", "_").replace("-", "_")`
   - Si ya existe en `config/areas.json`, usar ese código
   - Si no existe, generar nuevo código
4. Crear carpeta: `data/{area_guid}/`
5. Registrar en mapeo: `config/area_guid_mapping.json`
6. (Opcional) Actualizar `config/areas.json` si no existe el código

**Response Exitoso (200)**:
```json
{
    "success": true,
    "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "area_code": "sgr",
    "nombre": "Sistema General de Regalías",
    "folder_path": "data/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "message": "Área creada exitosamente"
}
```

**Response Error (409 Conflict)**:
```json
{
    "success": false,
    "error": "El área con GUID 'a1b2c3d4-e5f6-7890-abcd-ef1234567890' ya existe",
    "error_code": "AREA_ALREADY_EXISTS"
}
```

**Response Error (400 Bad Request)**:
```json
{
    "success": false,
    "error": "GUID inválido. Debe ser un UUID v4 válido",
    "error_code": "INVALID_GUID"
}
```

**Cómo Afecta**:
- ✅ **Nuevo endpoint**: No modifica endpoints existentes
- ✅ **Crea estructura**: Crea carpeta para almacenar documentos
- ✅ **Registra mapeo**: Permite futuras traducciones

**Resultado**:
- Área registrada en el sistema
- Carpeta lista para recibir documentos
- Mapeo disponible para consultas

**Ejemplo de Consumo (cURL)**:
```bash
curl -X POST "http://localhost:8000/api/v1/integration/areas" \
  -H "Content-Type: application/json" \
  -d '{
    "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "nombre": "Sistema General de Regalías",
    "descripcion": "Área de conocimiento sobre regalías"
  }'
```

**Ejemplo de Consumo (Python)**:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/integration/areas",
    json={
        "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "nombre": "Sistema General de Regalías",
        "descripcion": "Área de conocimiento sobre regalías"
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Área creada: {data['area_code']}")
    print(f"Carpeta: {data['folder_path']}")
else:
    print(f"Error: {response.json()}")
```

---

#### 2.2. Endpoint: Cargar Documento

**Ruta**: `POST /api/v1/integration/documents`

**Request (multipart/form-data)**:
```
- documento_guid: "doc-123e4567-e89b-12d3-a456-426614174000" (string)
- area_guid: "a1b2c3d4-e5f6-7890-abcd-ef1234567890" (string)
- file: (archivo PDF)
```

**Validaciones**:
- `documento_guid` debe ser un GUID válido
- `area_guid` debe existir en el mapeo (retornar 404 si no existe)
- `file` debe ser un PDF válido
- `documento_guid` no debe existir ya (retornar 409 si existe)

**Lógica Interna**:
1. Validar formato de `documento_guid` y `area_guid`
2. Verificar que `area_guid` exista en mapeo (404 si no existe)
3. Verificar que `documento_guid` no exista ya (409 si existe)
4. Validar que archivo sea PDF (verificar extensión y MIME type)
5. Obtener `area_code` desde mapeo
6. Generar `documento_id` interno:
   - Formato: `{area_code}_{nombre_archivo_sin_ext}`
   - Ejemplo: `sgr_acuerdo_03_2021`
7. Guardar PDF en: `data/{area_guid}/{documento_guid}.pdf`
8. Registrar en mapeo de documentos

**Response Exitoso (200)**:
```json
{
    "success": true,
    "documento_guid": "doc-123e4567-e89b-12d3-a456-426614174000",
    "documento_id": "sgr_acuerdo_03_2021",
    "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "area_code": "sgr",
    "file_path": "data/a1b2c3d4-e5f6-7890-abcd-ef1234567890/doc-123e4567-e89b-12d3-a456-426614174000.pdf",
    "file_size": 245678,
    "message": "Documento guardado exitosamente"
}
```

**Response Error (404 Not Found)**:
```json
{
    "success": false,
    "error": "El área con GUID 'a1b2c3d4-e5f6-7890-abcd-ef1234567890' no existe",
    "error_code": "AREA_NOT_FOUND"
}
```

**Response Error (409 Conflict)**:
```json
{
    "success": false,
    "error": "El documento con GUID 'doc-123e4567-e89b-12d3-a456-426614174000' ya existe",
    "error_code": "DOCUMENT_ALREADY_EXISTS"
}
```

**Response Error (400 Bad Request)**:
```json
{
    "success": false,
    "error": "El archivo debe ser un PDF válido",
    "error_code": "INVALID_FILE_TYPE"
}
```

**Cómo Afecta**:
- ✅ **Nuevo endpoint**: No modifica endpoints existentes
- ✅ **Almacenamiento**: Guarda PDFs en estructura organizada por área
- ✅ **Registra mapeo**: Permite futuras consultas por GUID

**Resultado**:
- PDF guardado en carpeta del área
- Mapeo documento_guid → documento_id registrado
- Listo para ingesta

**Ejemplo de Consumo (cURL)**:
```bash
curl -X POST "http://localhost:8000/api/v1/integration/documents" \
  -F "documento_guid=doc-123e4567-e89b-12d3-a456-426614174000" \
  -F "area_guid=a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -F "file=@/path/to/documento.pdf"
```

**Ejemplo de Consumo (Python)**:
```python
import requests

with open("documento.pdf", "rb") as f:
    files = {"file": ("documento.pdf", f, "application/pdf")}
    data = {
        "documento_guid": "doc-123e4567-e89b-12d3-a456-426614174000",
        "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    }
    
    response = requests.post(
        "http://localhost:8000/api/v1/integration/documents",
        files=files,
        data=data
    )

if response.status_code == 200:
    data = response.json()
    print(f"Documento guardado: {data['documento_id']}")
    print(f"Ruta: {data['file_path']}")
else:
    print(f"Error: {response.json()}")
```

---

#### 2.3. Endpoint: Iniciar Ingesta

**Ruta**: `POST /api/v1/integration/ingest`

**Request Body**:
```json
{
    "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Validaciones**:
- `area_guid` debe existir en el mapeo
- Debe haber al menos un documento en la carpeta del área

**Lógica Interna**:
1. Validar que `area_guid` exista en mapeo (404 si no existe)
2. Obtener `area_code` desde mapeo
3. Obtener ruta de carpeta: `data/{area_guid}/`
4. Verificar que existan PDFs en la carpeta
5. Crear tarea asíncrona usando `BackgroundTasks` de FastAPI
6. Ejecutar script de ingesta en segundo plano:
   ```bash
   python scripts/01_ingest_pdfs.py \
     --area {area_code} \
     --data-dir {folder_path} \
     --skip-existing
   ```
7. Retornar inmediatamente con `task_id`

**Ejecución Asíncrona**:
- Usa `subprocess.Popen()` para ejecutar script
- No bloquea el endpoint
- Logs se guardan en archivo o base de datos (opcional)

**Response Exitoso (202 Accepted)**:
```json
{
    "success": true,
    "task_id": "task_abc123def456",
    "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "area_code": "sgr",
    "folder_path": "data/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "started",
    "message": "Ingesta iniciada en segundo plano. Use task_id para consultar estado."
}
```

**Response Error (404 Not Found)**:
```json
{
    "success": false,
    "error": "El área con GUID 'a1b2c3d4-e5f6-7890-abcd-ef1234567890' no existe",
    "error_code": "AREA_NOT_FOUND"
}
```

**Response Error (400 Bad Request)**:
```json
{
    "success": false,
    "error": "No se encontraron documentos PDF en la carpeta del área",
    "error_code": "NO_DOCUMENTS_FOUND"
}
```

**Cómo Afecta**:
- ✅ **Nuevo endpoint**: No modifica endpoints existentes
- ✅ **Ejecución asíncrona**: No bloquea la API
- ✅ **Reutiliza script existente**: Usa `scripts/01_ingest_pdfs.py` sin modificaciones

**Resultado**:
- Ingesta iniciada en segundo plano
- Respuesta inmediata al cliente
- Documentos se procesan sin bloquear API

**Ejemplo de Consumo (cURL)**:
```bash
curl -X POST "http://localhost:8000/api/v1/integration/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }'
```

**Ejemplo de Consumo (Python)**:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/integration/ingest",
    json={
        "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    }
)

if response.status_code == 202:
    data = response.json()
    print(f"Ingesta iniciada: {data['task_id']}")
    print(f"Estado: {data['status']}")
else:
    print(f"Error: {response.json()}")
```

**Nota sobre Ejecución Asíncrona**:
- El script se ejecuta como subproceso independiente
- No se espera su finalización
- Los logs del script se pueden capturar y almacenar (opcional)
- El cliente puede consultar estado usando `task_id` (si se implementa endpoint de estado)

---

#### 2.4. Endpoint: Consulta RAG con GUIDs

**Ruta**: `POST /api/v1/rag/query-with-guids`

**Request Body**:
```json
{
    "question": "¿Cuál es el proceso de aprobación de proyectos?",
    "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "documento_guids": [
        "doc-123e4567-e89b-12d3-a456-426614174000",
        "doc-223e4567-e89b-12d3-a456-426614174001"
    ],
    "config": {
        "top_k_retrieval": 20,
        "top_k_rerank": 5,
        "expand_context": true,
        "enable_multihop": true,
        "enable_hyde": true
    }
}
```

**Validaciones**:
- `area_guid` debe existir en el mapeo
- `documento_guids` (opcional) deben existir en el mapeo
- `question` debe tener al menos 3 caracteres

**Lógica Interna**:
1. Validar que `area_guid` exista en mapeo (404 si no existe)
2. Convertir `area_guid` → `area_code` usando mapeo
3. Convertir `documento_guids` → `documento_ids` usando mapeo (si se proporcionan)
4. Llamar a `pipeline.query()` con códigos internos:
   ```python
   result = pipeline.query(
       question=question,
       area=area_code,  # Convertido desde GUID
       documento_ids=documento_ids,  # Convertidos desde GUIDs
       **config
   )
   ```
5. Retornar respuesta normal del RAG

**Response Exitoso (200)**:
```json
{
    "success": true,
    "answer": "El proceso de aprobación de proyectos...",
    "sources": [
        {
            "chunk_id": "chunk-123",
            "texto": "El proceso de aprobación...",
            "citacion_corta": "Acuerdo 03/2021, Artículo 15",
            "score": 0.95,
            "documento_id": "sgr_acuerdo_03_2021",
            "nivel_jerarquico": 3
        }
    ],
    "num_sources": 5,
    "metrics": {
        "total_time": 2.34,
        "search_time": 0.45,
        "rerank_time": 0.12,
        "generation_time": 1.77,
        "chunks_retrieved": 20,
        "chunks_reranked": 5,
        "total_cost": 0.001234,
        "query_type": "procedural",
        "retrieval_strategy": "hybrid",
        "multihop_used": false,
        "hyde_used": true
    }
}
```

**Response Error (404 Not Found)**:
```json
{
    "success": false,
    "error": "El área con GUID 'a1b2c3d4-e5f6-7890-abcd-ef1234567890' no existe",
    "error_code": "AREA_NOT_FOUND"
}
```

**Response Error (400 Bad Request)**:
```json
{
    "success": false,
    "error": "Uno o más documento_guids no existen en el mapeo",
    "error_code": "DOCUMENT_GUIDS_NOT_FOUND",
    "missing_guids": ["doc-invalid-guid"]
}
```

**Cómo Afecta**:
- ✅ **Nuevo endpoint**: No modifica endpoint existente `/api/v1/rag/query`
- ✅ **Reutiliza lógica**: Usa `RAGPipeline.query()` sin modificaciones
- ✅ **Solo traduce**: Convierte GUIDs a códigos internos antes de llamar

**Resultado**:
- Consulta RAG funciona con GUIDs externos
- Respuesta idéntica al endpoint original
- Compatible con API externa

**Ejemplo de Consumo (cURL)**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/query-with-guids" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuál es el proceso de aprobación?",
    "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "documento_guids": ["doc-123e4567-e89b-12d3-a456-426614174000"]
  }'
```

**Ejemplo de Consumo (Python)**:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/rag/query-with-guids",
    json={
        "question": "¿Cuál es el proceso de aprobación?",
        "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "documento_guids": ["doc-123e4567-e89b-12d3-a456-426614174000"],
        "config": {
            "top_k_retrieval": 20,
            "enable_hyde": True
        }
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Respuesta: {data['answer']}")
    print(f"Fuentes: {data['num_sources']}")
    print(f"Costo: ${data['metrics']['total_cost']:.6f}")
else:
    print(f"Error: {response.json()}")
```

---

## 🔄 Cambios en el Sistema

### Archivos Nuevos

#### 1. `src/mapping/guid_mapper.py`

**Propósito**: Gestionar mapeo entre GUIDs y códigos internos.

**Funciones Principales**:
- `get_area_code(area_guid)` → Obtiene código interno desde GUID
- `get_area_guid(area_code)` → Obtiene GUID desde código interno
- `register_area(area_guid, nombre, descripcion)` → Registra nueva área
- `get_documento_id(documento_guid)` → Obtiene documento_id desde GUID
- `register_documento(documento_guid, area_guid, nombre_archivo)` → Registra nuevo documento

**Impacto**:
- ✅ **Nuevo módulo**: No afecta código existente
- ✅ **Aislado**: Lógica de mapeo separada
- ✅ **Testeable**: Fácil de probar independientemente

---

#### 2. `api/routers/integration.py`

**Propósito**: Endpoints para integración con API externa.

**Endpoints**:
- `POST /api/v1/integration/areas` → Crear área
- `POST /api/v1/integration/documents` → Cargar documento
- `POST /api/v1/integration/ingest` → Iniciar ingesta

**Impacto**:
- ✅ **Nuevo router**: No modifica routers existentes
- ✅ **Separado**: Lógica de integración aislada
- ✅ **Extensible**: Fácil agregar más endpoints

---

#### 3. `config/area_guid_mapping.json`

**Propósito**: Almacenar mapeos entre GUIDs y códigos internos.

**Estructura**:
```json
{
    "areas": {
        "guid-1": { "area_code": "sgr", ... },
        "guid-2": { "area_code": "ia", ... }
    },
    "documentos": {
        "doc-guid-1": { "documento_id": "sgr_doc1", ... }
    }
}
```

**Impacto**:
- ✅ **Persistencia**: Mapeos sobreviven reinicios
- ✅ **Versionable**: Puede versionarse en Git
- ✅ **Auditable**: Fácil ver qué GUIDs están mapeados

---

### Archivos Modificados

#### 1. `api/routers/rag.py`

**Cambio**: Agregar nuevo endpoint `query-with-guids`.

**Modificación**:
```python
@router.post("/query-with-guids", ...)
async def query_with_guids(...):
    # Convertir GUIDs a códigos internos
    # Llamar a pipeline.query() existente
    # Retornar respuesta
```

**Impacto**:
- ✅ **Endpoint adicional**: No modifica endpoint existente
- ✅ **Reutiliza lógica**: Usa `pipeline.query()` sin cambios
- ✅ **Compatibilidad**: Endpoint original sigue funcionando

---

#### 2. `api/main.py`

**Cambio**: Registrar nuevo router de integración.

**Modificación**:
```python
from api.routers import integration

app.include_router(integration.router)
```

**Impacto**:
- ✅ **Mínimo**: Solo agrega una línea
- ✅ **Sin efectos secundarios**: No afecta otros routers

---

### Archivos NO Modificados (Lógica Intacta)

Los siguientes archivos **NO se modifican**:

- ✅ `src/ingest/pdf_extractor.py` → Sin cambios
- ✅ `src/ingest/chunker.py` → Sin cambios
- ✅ `src/ingest/vectorizer.py` → Sin cambios
- ✅ `src/pipeline.py` → Sin cambios
- ✅ `src/retrieval/vector_search.py` → Sin cambios
- ✅ `scripts/01_ingest_pdfs.py` → Sin cambios
- ✅ `api/routers/documents.py` → Sin cambios
- ✅ `api/routers/ingestion.py` → Sin cambios

**Principio**: La lógica de negocio permanece intacta.

---

## 🔄 Flujos de Integración Completos

### Flujo 1: Crear Área y Cargar Documentos

```
┌─────────────┐
│ API Externa │
└──────┬──────┘
       │
       │ 1. POST /api/v1/integration/areas
       │    { area_guid, nombre, descripcion }
       ↓
┌─────────────────────────────────────┐
│ Sistema RAG                         │
│                                     │
│ ✓ Valida GUID                       │
│ ✓ Genera area_code                  │
│ ✓ Crea carpeta: data/{area_guid}/  │
│ ✓ Guarda mapeo                      │
│ ✓ Retorna: area_code, folder_path   │
└──────┬──────────────────────────────┘
       │
       │ Response: { area_code: "sgr", ... }
       ↓
┌─────────────┐
│ API Externa │
└──────┬──────┘
       │
       │ 2. POST /api/v1/integration/documents
       │    { documento_guid, area_guid, file }
       ↓
┌─────────────────────────────────────┐
│ Sistema RAG                         │
│                                     │
│ ✓ Valida área existe                │
│ ✓ Valida PDF                        │
│ ✓ Genera documento_id               │
│ ✓ Guarda: data/{area_guid}/{doc_guid}.pdf
│ ✓ Guarda mapeo                      │
│ ✓ Retorna: documento_id, file_path  │
└──────┬──────────────────────────────┘
       │
       │ Response: { documento_id: "sgr_doc1", ... }
       ↓
┌─────────────┐
│ API Externa │
└─────────────┘
```

**Resultado**:
- Área creada y registrada
- Documento guardado en carpeta del área
- Mapeos disponibles para consultas

---

### Flujo 2: Iniciar Ingesta

```
┌─────────────┐
│ API Externa │
└──────┬──────┘
       │
       │ POST /api/v1/integration/ingest
       │ { area_guid }
       ↓
┌─────────────────────────────────────┐
│ Sistema RAG                         │
│                                     │
│ ✓ Valida área existe                │
│ ✓ Obtiene area_code                 │
│ ✓ Obtiene folder_path               │
│ ✓ Crea tarea asíncrona              │
│ ✓ Ejecuta script en background:     │
│   python scripts/01_ingest_pdfs.py  │
│     --area {area_code}              │
│     --data-dir {folder_path}        │
│ ✓ Retorna task_id inmediatamente    │
└──────┬──────────────────────────────┘
       │
       │ Response: { task_id, status: "started" }
       ↓
┌─────────────┐
│ API Externa │ (Respuesta inmediata)
└─────────────┘

       │
       │ (En segundo plano)
       ↓
┌─────────────────────────────────────┐
│ Script de Ingesta                   │
│                                     │
│ ✓ Extrae PDFs                       │
│ ✓ Chunking jerárquico               │
│ ✓ Genera embeddings                 │
│ ✓ Sube a Qdrant                     │
│ ✓ Usa documento_id interno          │
└─────────────────────────────────────┘
```

**Resultado**:
- Ingesta iniciada sin bloquear API
- Documentos procesados en segundo plano
- Vectores almacenados en Qdrant con códigos internos

---

### Flujo 3: Consulta RAG con GUIDs

```
┌─────────────┐
│ API Externa │
└──────┬──────┘
       │
       │ POST /api/v1/rag/query-with-guids
       │ {
       │   question: "...",
       │   area_guid: "...",
       │   documento_guids: [...]
       │ }
       ↓
┌─────────────────────────────────────┐
│ Sistema RAG                         │
│                                     │
│ ✓ Valida área existe                │
│ ✓ Convierte: area_guid → area_code  │
│ ✓ Convierte: doc_guids → doc_ids    │
│                                     │
│ ✓ pipeline.query(                   │
│     area=area_code,                 │
│     documento_ids=doc_ids           │
│   )                                 │
│                                     │
│ ✓ Retorna respuesta RAG             │
└──────┬──────────────────────────────┘
       │
       │ Response: { answer, sources, metrics }
       ↓
┌─────────────┐
│ API Externa │
└─────────────┘
```

**Resultado**:
- Consulta procesada con GUIDs externos
- Respuesta idéntica a consulta con códigos internos
- Fuentes incluyen documento_id interno (puede convertirse a GUID si se necesita)

---

## 📊 Ejemplos de Consumo Completos

### Escenario Completo: De Cero a Consulta

#### Paso 1: Crear Área

```python
import requests

# Crear área
response = requests.post(
    "http://localhost:8000/api/v1/integration/areas",
    json={
        "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "nombre": "Sistema General de Regalías",
        "descripcion": "Área de conocimiento sobre regalías"
    }
)

area_data = response.json()
print(f"Área creada: {area_data['area_code']}")
# Output: Área creada: sgr
```

#### Paso 2: Cargar Documentos

```python
# Cargar documento 1
with open("acuerdo_03_2021.pdf", "rb") as f:
    files = {"file": ("acuerdo_03_2021.pdf", f, "application/pdf")}
    data = {
        "documento_guid": "doc-123e4567-e89b-12d3-a456-426614174000",
        "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    }
    
    response = requests.post(
        "http://localhost:8000/api/v1/integration/documents",
        files=files,
        data=data
    )
    
    doc1_data = response.json()
    print(f"Documento guardado: {doc1_data['documento_id']}")
    # Output: Documento guardado: sgr_acuerdo_03_2021

# Cargar documento 2
with open("decreto_1082_2015.pdf", "rb") as f:
    files = {"file": ("decreto_1082_2015.pdf", f, "application/pdf")}
    data = {
        "documento_guid": "doc-223e4567-e89b-12d3-a456-426614174001",
        "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    }
    
    response = requests.post(
        "http://localhost:8000/api/v1/integration/documents",
        files=files,
        data=data
    )
    
    doc2_data = response.json()
    print(f"Documento guardado: {doc2_data['documento_id']}")
    # Output: Documento guardado: sgr_decreto_1082_2015
```

#### Paso 3: Iniciar Ingesta

```python
# Iniciar ingesta
response = requests.post(
    "http://localhost:8000/api/v1/integration/ingest",
    json={
        "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    }
)

ingest_data = response.json()
print(f"Ingesta iniciada: {ingest_data['task_id']}")
print(f"Estado: {ingest_data['status']}")
# Output: 
# Ingesta iniciada: task_abc123def456
# Estado: started

# Esperar unos minutos para que termine la ingesta...
import time
time.sleep(300)  # 5 minutos (ajustar según tamaño de documentos)
```

#### Paso 4: Consultar RAG

```python
# Consultar con GUIDs
response = requests.post(
    "http://localhost:8000/api/v1/rag/query-with-guids",
    json={
        "question": "¿Cuál es el proceso de aprobación de proyectos de inversión?",
        "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "documento_guids": [
            "doc-123e4567-e89b-12d3-a456-426614174000",
            "doc-223e4567-e89b-12d3-a456-426614174001"
        ],
        "config": {
            "top_k_retrieval": 20,
            "top_k_rerank": 5,
            "enable_hyde": True
        }
    }
)

rag_response = response.json()
print(f"Respuesta: {rag_response['answer']}")
print(f"Fuentes: {rag_response['num_sources']}")
print(f"Costo: ${rag_response['metrics']['total_cost']:.6f}")

# Mostrar fuentes
for i, source in enumerate(rag_response['sources'][:3], 1):
    print(f"\nFuente {i}:")
    print(f"  Documento: {source['documento_id']}")
    print(f"  Cita: {source['citacion_corta']}")
    print(f"  Score: {source['score']:.3f}")
```

---

## ⚠️ Impacto y Consideraciones

### Impacto en el Sistema Existente

#### ✅ Sin Impacto Negativo

1. **Lógica de Negocio Intacta**:
   - Todos los módulos de procesamiento siguen igual
   - Scripts de ingesta no se modifican
   - Pipeline RAG funciona igual

2. **Endpoints Existentes Funcionan**:
   - `/api/v1/rag/query` sigue funcionando con códigos internos
   - `/api/v1/documents` sigue funcionando
   - Compatibilidad hacia atrás garantizada

3. **Estructura de Datos en Qdrant**:
   - Sigue usando `area_code` y `documento_id` internos
   - No requiere migración de datos existentes
   - Nuevos documentos se integran sin problemas

#### ⚠️ Consideraciones

1. **Mapeo como Fuente de Verdad**:
   - Si el mapeo se corrompe, se pierde la relación GUID ↔ Código
   - **Solución**: Hacer backup regular de `config/area_guid_mapping.json`
   - **Solución**: Considerar base de datos para producción

2. **Sincronización con API Externa**:
   - Si API externa elimina un área, este sistema no lo sabe automáticamente
   - **Solución**: Agregar endpoint de sincronización
   - **Solución**: Webhook desde API externa para notificar cambios

3. **Eliminación de Documentos**:
   - Eliminar documento requiere eliminar de Qdrant también
   - **Solución**: Usar endpoint existente `DELETE /api/v1/documents/{documento_id}`
   - **Solución**: Agregar endpoint que acepte GUID

4. **Nombres de Áreas**:
   - Si nombre cambia en API externa, código interno no cambia
   - **Solución**: Actualizar solo nombre en mapeo, mantener código

5. **Validación de GUIDs**:
   - Debe validarse formato UUID v4
   - **Solución**: Usar `uuid.UUID()` para validar

---

### Rendimiento

#### Impacto en Rendimiento

1. **Consultas de Mapeo**:
   - Carga de mapeo desde JSON: ~1-5ms
   - Búsqueda en diccionario: O(1)
   - **Impacto**: Mínimo, despreciable

2. **Endpoints de Integración**:
   - Crear área: ~10-50ms (crear carpeta, escribir JSON)
   - Cargar documento: ~100-500ms (depende del tamaño del PDF)
   - Iniciar ingesta: ~10-100ms (crear proceso, retornar inmediatamente)

3. **Consulta RAG con GUIDs**:
   - Conversión GUID → código: ~1-5ms
   - Resto del pipeline: Sin cambios
   - **Impacto total**: <5ms adicionales

**Conclusión**: Impacto en rendimiento es mínimo y despreciable.

---

### Seguridad

#### Consideraciones de Seguridad

1. **Validación de Entrada**:
   - Validar formato GUID (UUID v4)
   - Validar tipo de archivo (solo PDF)
   - Validar tamaño de archivo (límite recomendado: 50MB)

2. **Autenticación**:
   - Endpoints de integración deben estar protegidos
   - **Recomendación**: Agregar autenticación API Key o JWT
   - **Recomendación**: Rate limiting

3. **Sanitización**:
   - Nombres de archivos deben sanitizarse
   - **Solución**: Usar solo GUID como nombre de archivo (ya implementado)

4. **Acceso a Archivos**:
   - Carpetas deben tener permisos adecuados
   - **Recomendación**: 755 para carpetas, 644 para archivos

---

### Escalabilidad

#### Consideraciones de Escalabilidad

1. **Mapeo en Memoria vs Disco**:
   - Actual: JSON en disco (carga bajo demanda)
   - **Escalable a**: Base de datos (PostgreSQL, MongoDB)
   - **Escalable a**: Cache en memoria (Redis)

2. **Múltiples Instancias**:
   - Si hay múltiples instancias, mapeo debe compartirse
   - **Solución**: Base de datos compartida
   - **Solución**: Sistema de archivos compartido (NFS)

3. **Volumen de Documentos**:
   - Script de ingesta maneja lotes
   - **Sin cambios**: Ya está optimizado

---

## 📝 Checklist de Implementación

### Fase 1: Mapeo
- [ ] Crear `src/mapping/__init__.py`
- [ ] Crear `src/mapping/guid_mapper.py`
- [ ] Implementar `GuidMapper` con todas las funciones
- [ ] Crear `config/area_guid_mapping.json` (estructura inicial)
- [ ] Escribir tests unitarios para `GuidMapper`

### Fase 2: Endpoints de Integración
- [ ] Crear `api/routers/integration.py`
- [ ] Implementar `POST /api/v1/integration/areas`
- [ ] Implementar `POST /api/v1/integration/documents`
- [ ] Implementar `POST /api/v1/integration/ingest`
- [ ] Agregar validaciones y manejo de errores
- [ ] Agregar logging

### Fase 3: Endpoint de Consulta
- [ ] Modificar `api/routers/rag.py`
- [ ] Agregar `POST /api/v1/rag/query-with-guids`
- [ ] Implementar conversión GUID → código
- [ ] Agregar validaciones

### Fase 4: Integración
- [ ] Modificar `api/main.py` para registrar router
- [ ] Probar flujo completo end-to-end
- [ ] Verificar que endpoints existentes siguen funcionando

### Fase 5: Documentación y Testing
- [ ] Actualizar `docs/API_DOCUMENTATION.md`
- [ ] Escribir tests de integración
- [ ] Documentar ejemplos de consumo
- [ ] Crear guía de migración (si aplica)

---

## 🚀 Próximos Pasos

1. **Revisar y Aprobar Plan**
   - Revisar con equipo
   - Aprobar estructura de carpetas
   - Aprobar estrategia de mapeo

2. **Implementar Fase 1 (Mapeo)**
   - Crear módulo de mapeo
   - Probar funciones básicas

3. **Implementar Fase 2 (Endpoints)**
   - Crear endpoints uno por uno
   - Probar cada endpoint individualmente

4. **Integración y Testing**
   - Probar flujo completo
   - Verificar compatibilidad hacia atrás

5. **Despliegue**
   - Desplegar en ambiente de desarrollo
   - Probar con API externa
   - Desplegar en producción

---

## 📚 Referencias

- Documentación FastAPI: https://fastapi.tiangolo.com/
- Documentación Background Tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
- Script de ingesta: `scripts/01_ingest_pdfs.py`
- Endpoints RAG: `api/routers/rag.py`
- Configuración de áreas: `src/config.py`

---

**Autor**: Sistema de Planificación  
**Última Actualización**: 2025-01-15  
**Versión del Documento**: 1.0.0


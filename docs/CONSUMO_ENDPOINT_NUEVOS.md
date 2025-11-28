# Consumo de Endpoints Nuevos - Integración con API Externa

**Fecha**: 2025-01-15  
**Versión**: 1.0.0

---

## 📋 Tabla de Contenidos

1. [Endpoint: Crear Área](#endpoint-crear-área)
2. [Endpoint: Cargar Documento PDF](#endpoint-cargar-documento-pdf)
3. [Endpoint: Ingerir Documentos de un Área](#endpoint-ingerir-documentos-de-un-área)
4. [Ejemplos de Consumo](#ejemplos-de-consumo)
5. [Códigos de Respuesta](#códigos-de-respuesta)
6. [Manejo de Errores](#manejo-de-errores)

---

## 🎯 Endpoint: Crear Área

### Información General

**Nombre del Endpoint**: `POST /api/v1/integration/areas`

**Descripción**: Crea una nueva área de conocimiento en el sistema RAG. El sistema normaliza automáticamente el nombre del área y crea la carpeta correspondiente para almacenar documentos.

**Tag en Swagger**: `integration`

**URL Base**: `http://localhost:8000` (o la URL de tu servidor)

**URL Completa**: `http://localhost:8000/api/v1/integration/areas`

---

### Request

#### Headers

```
Content-Type: application/json
```

#### Body (JSON)

```json
{
  "name": "string",
  "description": "string",
  "companyId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

#### Parámetros

| Campo         | Tipo          | Requerido | Descripción                                      | Ejemplo                                             |
| ------------- | ------------- | --------- | ------------------------------------------------ | --------------------------------------------------- |
| `name`        | string        | Sí        | Nombre del área (se normalizará automáticamente) | "Desarrollo de Especies"                            |
| `description` | string        | Sí        | Descripción del área                             | "Área de conocimiento sobre desarrollo de especies" |
| `companyId`   | string (UUID) | Sí        | ID de la compañía (debe ser un UUID válido)      | "3fa85f64-5717-4562-b3fc-2c963f66afa6"              |

#### Validaciones

- `name`:

  - No puede estar vacío
  - Mínimo 1 carácter, máximo 200 caracteres
  - Se normaliza automáticamente (minúsculas, espacios → guiones bajos, sin caracteres especiales)

- `description`:

  - Máximo 1000 caracteres

- `companyId`:
  - Debe ser un UUID válido (formato: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
  - Mínimo 36 caracteres, máximo 36 caracteres

#### Normalización del Nombre

El sistema normaliza automáticamente el nombre del área:

- **Minúsculas**: "Desarrollo" → "desarrollo"
- **Espacios → Guiones bajos**: "Desarrollo de Especies" → "desarrollo_de_especies"
- **Guiones → Guiones bajos**: "Desarrollo-Especies" → "desarrollo_especies"
- **Sin acentos**: "Desarrollo de Especies" → "desarrollo_de_especies"
- **Sin caracteres especiales**: Solo letras, números y guiones bajos

**Ejemplos de normalización**:

- `"Desarrollo de Especies"` → `"desarrollo_de_especies"`
- `"Sistema General de Regalías"` → `"sistema_general_de_regalias"`
- `"Inteligencia Artificial"` → `"inteligencia_artificial"`
- `"Área-Técnica"` → `"area_tecnica"`

---

### Response

#### Estructura Estándar

Todas las respuestas siguen esta estructura:

```json
{
  "statusCode": int,
  "message": "string",
  "data": { ... }
}
```

#### Response Exitoso (201 Created)

**Código HTTP**: `201`

**Body**:

```json
{
  "statusCode": 201,
  "message": "Área creada exitosamente",
  "data": {
    "area_code": "desarrollo_de_especies",
    "name": "Desarrollo de Especies",
    "description": "Área de conocimiento sobre desarrollo de especies",
    "companyId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "folder_path": "data/desarrollo_de_especies",
    "created_at": "2025-01-15T10:30:45.123456"
  }
}
```

**Campos de `data`**:

| Campo         | Tipo   | Descripción                                  |
| ------------- | ------ | -------------------------------------------- |
| `area_code`   | string | Código interno del área (nombre normalizado) |
| `name`        | string | Nombre original del área                     |
| `description` | string | Descripción del área                         |
| `companyId`   | string | ID de la compañía                            |
| `folder_path` | string | Ruta relativa de la carpeta creada           |
| `created_at`  | string | Fecha de creación en formato ISO 8601        |

#### Response Error (400 Bad Request)

**Código HTTP**: `400`

**Causas posibles**:

- `name` está vacío
- `companyId` no es un UUID válido
- Error en la normalización del nombre

**Body**:

```json
{
  "statusCode": 400,
  "message": "name no puede estar vacío",
  "data": {}
}
```

#### Response Error (409 Conflict)

**Código HTTP**: `409`

**Causa**: El área ya existe (la carpeta ya fue creada)

**Body**:

```json
{
  "statusCode": 409,
  "message": "El área 'desarrollo_de_especies' ya existe",
  "data": {
    "area_code": "desarrollo_de_especies",
    "folder_path": "data/desarrollo_de_especies"
  }
}
```

#### Response Error (500 Internal Server Error)

**Código HTTP**: `500`

**Causa**: Error interno del servidor (ej: no se pudo crear la carpeta)

**Body**:

```json
{
  "statusCode": 500,
  "message": "Error interno al crear área: [detalle del error]",
  "data": {}
}
```

---

## 📄 Endpoint: Cargar Documento PDF

### Información General

**Nombre del Endpoint**: `POST /api/v1/integration/documents`

**Descripción**: Carga un documento PDF en el área especificada. El documento se guarda en la carpeta del área pero NO se ingesta automáticamente.

**Tag en Swagger**: `integration`

**URL Completa**: `http://localhost:8000/api/v1/integration/documents`

---

### Request

#### Headers

```
Content-Type: multipart/form-data
```

#### Body (multipart/form-data)

| Campo           | Tipo   | Requerido | Descripción                                            | Ejemplo                  |
| --------------- | ------ | --------- | ------------------------------------------------------ | ------------------------ |
| `file`          | file   | Sí        | Archivo PDF a cargar                                   | documento.pdf            |
| `area_code`     | string | Sí        | Código del área (nombre normalizado)                   | "desarrollo_de_especies" |
| `document_name` | string | No        | Nombre opcional para el documento (sin extensión .pdf) | "acuerdo_03_2021"        |

#### Validaciones

- `file`:

  - Debe ser un archivo PDF (extensión `.pdf`)
  - Tamaño máximo: 50 MB
  - No puede estar vacío

- `area_code`:

  - Debe existir (la carpeta debe haber sido creada previamente)
  - Formato: nombre normalizado (minúsculas, guiones bajos, sin espacios)

- `document_name` (opcional):
  - Si se proporciona, se normaliza automáticamente
  - Si no se proporciona, se usa el nombre del archivo original (normalizado)

---

### Response

#### Response Exitoso (201 Created)

**Código HTTP**: `201`

**Body**:

```json
{
  "statusCode": 201,
  "message": "Documento guardado exitosamente",
  "data": {
    "filename": "acuerdo_03_2021.pdf",
    "original_filename": "Acuerdo 03-2021.pdf",
    "area_code": "desarrollo_de_especies",
    "file_path": "data/desarrollo_de_especies/acuerdo_03_2021.pdf",
    "file_size": 245678,
    "uploaded_at": "2025-01-15T10:45:30.123456"
  }
}
```

**Campos de `data`**:

| Campo               | Tipo   | Descripción                               |
| ------------------- | ------ | ----------------------------------------- |
| `filename`          | string | Nombre del archivo guardado (normalizado) |
| `original_filename` | string | Nombre original del archivo subido        |
| `area_code`         | string | Código del área donde se guardó           |
| `file_path`         | string | Ruta relativa del archivo guardado        |
| `file_size`         | int    | Tamaño del archivo en bytes               |
| `uploaded_at`       | string | Fecha de carga en formato ISO 8601        |

#### Response Error (400 Bad Request)

**Código HTTP**: `400`

**Causas posibles**:

- El archivo no es un PDF
- El archivo está vacío
- El archivo no tiene nombre
- Error en la normalización del nombre

**Body**:

```json
{
  "statusCode": 400,
  "message": "El archivo debe ser un PDF. Extensión recibida: .docx",
  "data": {}
}
```

#### Response Error (404 Not Found)

**Código HTTP**: `404`

**Causa**: El área no existe (la carpeta no fue creada)

**Body**:

```json
{
  "statusCode": 404,
  "message": "El área 'desarrollo_de_especies' no existe. Cree el área primero.",
  "data": {}
}
```

#### Response Error (409 Conflict)

**Código HTTP**: `409`

**Causa**: El documento ya existe en el área

**Body**:

```json
{
  "statusCode": 409,
  "message": "El documento 'acuerdo_03_2021.pdf' ya existe en el área 'desarrollo_de_especies'",
  "data": {
    "filename": "acuerdo_03_2021.pdf",
    "area_code": "desarrollo_de_especies",
    "file_path": "data/desarrollo_de_especies/acuerdo_03_2021.pdf"
  }
}
```

#### Response Error (413 Request Entity Too Large)

**Código HTTP**: `413`

**Causa**: El archivo excede el tamaño máximo (50 MB)

**Body**:

```json
{
  "statusCode": 413,
  "message": "El archivo es demasiado grande. Tamaño máximo: 50 MB",
  "data": {}
}
```

---

## 🔄 Endpoint: Ingerir Documentos de un Área

### Información General

**Nombre del Endpoint**: `POST /api/v1/integration/ingest`

**Descripción**: Inicia el proceso de ingesta de todos los documentos PDF de un área específica. El proceso se ejecuta en background y el endpoint retorna inmediatamente sin esperar a que termine.

**Tag en Swagger**: `integration`

**URL Completa**: `http://localhost:8000/api/v1/integration/ingest`

**⚠️ Importante**: Este proceso es **asíncrono** y puede tardar varios minutos dependiendo de la cantidad y tamaño de los documentos. El endpoint **NO bloquea** y retorna inmediatamente.

---

### Request

#### Headers

```
Content-Type: multipart/form-data
```

#### Body (multipart/form-data)

| Campo             | Tipo    | Requerido | Descripción                                                | Ejemplo                  |
| ----------------- | ------- | --------- | ---------------------------------------------------------- | ------------------------ |
| `area_code`       | string  | Sí        | Código del área (nombre normalizado)                       | "desarrollo_de_especies" |
| `recreate`        | boolean | No        | Si es `true`, recrea la colección (BORRA datos existentes) | false                    |
| `force_reprocess` | boolean | No        | Si es `true`, fuerza el reprocesamiento de todos los PDFs  | false                    |

#### Validaciones

- `area_code`:

  - Debe existir (la carpeta debe haber sido creada previamente)
  - Debe ser un área válida según el sistema
  - Debe contener al menos un documento PDF

- `recreate`:

  - Si es `true`, **elimina todos los datos existentes** de la colección
  - Use con precaución, solo para primer área o reset completo

- `force_reprocess`:
  - Si es `true`, reprocesa todos los PDFs incluso si ya existen
  - Si es `false` (default), salta documentos que ya existen

---

### Response

#### Response Exitoso (202 Accepted)

**Código HTTP**: `202`

**Body**:

```json
{
  "statusCode": 202,
  "message": "Proceso de ingesta iniciado para área 'desarrollo_de_especies'. Procesando 5 documento(s).",
  "data": {
    "process_id": "ingest_desarrollo_de_especies_20250115_104530",
    "area_code": "desarrollo_de_especies",
    "pid": 12345,
    "status": "running",
    "total_documents": 5,
    "log_file": "logs/ingest_desarrollo_de_especies_20250115_104530.log",
    "started_at": "2025-01-15T10:45:30.123456",
    "recreate": false,
    "force_reprocess": false
  }
}
```

**Campos de `data`**:

| Campo             | Tipo    | Descripción                                      |
| ----------------- | ------- | ------------------------------------------------ |
| `process_id`      | string  | ID único del proceso de ingesta                  |
| `area_code`       | string  | Código del área siendo procesada                 |
| `pid`             | int     | Process ID del proceso en background             |
| `status`          | string  | Estado del proceso (siempre "running" al inicio) |
| `total_documents` | int     | Número total de documentos PDF a procesar        |
| `log_file`        | string  | Ruta relativa del archivo de log                 |
| `started_at`      | string  | Fecha de inicio en formato ISO 8601              |
| `recreate`        | boolean | Si se recreó la colección                        |
| `force_reprocess` | boolean | Si se fuerza el reprocesamiento                  |

#### Response Error (400 Bad Request)

**Código HTTP**: `400`

**Causas posibles**:

- No hay documentos PDF en el área
- Área inválida según el sistema

**Body**:

```json
{
  "statusCode": 400,
  "message": "No hay documentos PDF en el área 'desarrollo_de_especies'. Cargue documentos primero.",
  "data": {
    "area_code": "desarrollo_de_especies",
    "folder_path": "data/desarrollo_de_especies"
  }
}
```

#### Response Error (404 Not Found)

**Código HTTP**: `404`

**Causa**: El área no existe (la carpeta no fue creada)

**Body**:

```json
{
  "statusCode": 404,
  "message": "El área 'desarrollo_de_especies' no existe. Cree el área primero.",
  "data": {}
}
```

#### Response Error (500 Internal Server Error)

**Código HTTP**: `500`

**Causa**: Error interno del servidor (ej: script no encontrado, error al iniciar proceso)

**Body**:

```json
{
  "statusCode": 500,
  "message": "Error al iniciar proceso de ingesta: [detalle del error]",
  "data": {}
}
```

---

### ⚠️ Notas Importantes

1. **Proceso Asíncrono**: El endpoint retorna inmediatamente. El proceso de ingesta continúa en background.

2. **Tiempo de Procesamiento**: Puede tardar varios minutos dependiendo de:

   - Cantidad de documentos
   - Tamaño de los PDFs
   - Complejidad del contenido

3. **Logs**: El proceso genera un archivo de log en `logs/ingest_{area_code}_{timestamp}.log` que puedes consultar para ver el progreso.

4. **MODO RECREATE**: Si `recreate=true`, se **eliminan todos los datos existentes** de la colección. Use con precaución.

5. **Verificación**: Para verificar el estado del proceso, consulta el archivo de log o verifica los documentos en Qdrant.

---

## 📝 Ejemplos de Consumo

### Ejemplo 1: cURL (Básico)

```bash
curl -X POST "http://localhost:8000/api/v1/integration/areas" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Desarrollo de Especies",
    "description": "Área de conocimiento sobre desarrollo de especies",
    "companyId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }'
```

**Respuesta esperada**:

```json
{
  "statusCode": 201,
  "message": "Área creada exitosamente",
  "data": {
    "area_code": "desarrollo_de_especies",
    "name": "Desarrollo de Especies",
    "description": "Área de conocimiento sobre desarrollo de especies",
    "companyId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "folder_path": "data/desarrollo_de_especies",
    "created_at": "2025-01-15T10:30:45.123456"
  }
}
```

---

### Ejemplo 2: cURL (Con Pretty Print)

```bash
curl -X POST "http://localhost:8000/api/v1/integration/areas" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sistema General de Regalías",
    "description": "Área de conocimiento sobre regalías y normativa",
    "companyId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }' | jq
```

**Respuesta**:

```json
{
  "statusCode": 201,
  "message": "Área creada exitosamente",
  "data": {
    "area_code": "sistema_general_de_regalias",
    "name": "Sistema General de Regalías",
    "description": "Área de conocimiento sobre regalías y normativa",
    "companyId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "folder_path": "data/sistema_general_de_regalias",
    "created_at": "2025-01-15T10:35:12.789012"
  }
}
```

---

### Ejemplo 3: cURL (Con Manejo de Errores)

```bash
#!/bin/bash

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:8000/api/v1/integration/areas" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Inteligencia Artificial",
    "description": "Documentos sobre IA",
    "companyId": "b2c3d4e5-f6a7-8901-bcde-f12345678901"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 201 ]; then
  echo "✅ Área creada exitosamente"
  echo "$BODY" | jq '.data.area_code'
  echo "$BODY" | jq '.data.folder_path'
else
  echo "❌ Error: HTTP $HTTP_CODE"
  echo "$BODY" | jq '.message'
fi
```

---

### Ejemplo 4: Python (requests)

```python
import requests
import json

url = "http://localhost:8000/api/v1/integration/areas"

payload = {
    "name": "Desarrollo de Especies",
    "description": "Área de conocimiento sobre desarrollo de especies",
    "companyId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}

headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()  # Lanza excepción si hay error HTTP

    data = response.json()

    print(f"✅ {data['message']}")
    print(f"   Área: {data['data']['area_code']}")
    print(f"   Carpeta: {data['data']['folder_path']}")
    print(f"   Creada: {data['data']['created_at']}")

except requests.exceptions.HTTPError as e:
    error_data = e.response.json()
    print(f"❌ Error {error_data['statusCode']}: {error_data['message']}")
except requests.exceptions.RequestException as e:
    print(f"❌ Error de conexión: {e}")
```

**Salida esperada**:

```
✅ Área creada exitosamente
   Área: desarrollo_de_especies
   Carpeta: data/desarrollo_de_especies
   Creada: 2025-01-15T10:30:45.123456
```

---

### Ejemplo 5: Python (Cliente Reutilizable)

```python
import requests
from typing import Dict, Optional

class RAGIntegrationClient:
    """Cliente para integrar con API RAG."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Inicializar cliente.

        Args:
            base_url: URL base de la API RAG
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def create_area(
        self,
        name: str,
        description: str,
        company_id: str
    ) -> Dict:
        """
        Crear área en el sistema RAG.

        Args:
            name: Nombre del área
            description: Descripción del área
            company_id: ID de la compañía (UUID)

        Returns:
            Dict con información del área creada

        Raises:
            requests.HTTPError: Si hay error en la petición
        """
        url = f"{self.base_url}/api/v1/integration/areas"

        payload = {
            "name": name,
            "description": description,
            "companyId": company_id
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()

        return response.json()


# Uso
if __name__ == "__main__":
    client = RAGIntegrationClient(base_url="http://localhost:8000")

    try:
        result = client.create_area(
            name="Desarrollo de Especies",
            description="Área de conocimiento sobre desarrollo de especies",
            company_id="3fa85f64-5717-4562-b3fc-2c963f66afa6"
        )

        print(f"✅ {result['message']}")
        print(f"   Código: {result['data']['area_code']}")
        print(f"   Carpeta: {result['data']['folder_path']}")

    except requests.HTTPError as e:
        error = e.response.json()
        print(f"❌ Error {error['statusCode']}: {error['message']}")
```

---

### Ejemplo 6: JavaScript/TypeScript (fetch)

```javascript
async function createArea(name, description, companyId) {
  const url = "http://localhost:8000/api/v1/integration/areas";

  const payload = {
    name: name,
    description: description,
    companyId: companyId,
  };

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (response.ok) {
      console.log(`✅ ${data.message}`);
      console.log(`   Área: ${data.data.area_code}`);
      console.log(`   Carpeta: ${data.data.folder_path}`);
      return data;
    } else {
      console.error(`❌ Error ${data.statusCode}: ${data.message}`);
      throw new Error(data.message);
    }
  } catch (error) {
    console.error("❌ Error de conexión:", error);
    throw error;
  }
}

// Uso
createArea(
  "Desarrollo de Especies",
  "Área de conocimiento sobre desarrollo de especies",
  "3fa85f64-5717-4562-b3fc-2c963f66afa6"
);
```

---

### Ejemplo 7: JavaScript/TypeScript (Clase Cliente)

```typescript
interface CreateAreaRequest {
  name: string;
  description: string;
  companyId: string;
}

interface StandardResponse<T> {
  statusCode: number;
  message: string;
  data: T;
}

interface AreaData {
  area_code: string;
  name: string;
  description: string;
  companyId: string;
  folder_path: string;
  created_at: string;
}

class RAGIntegrationClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async createArea(
    name: string,
    description: string,
    companyId: string
  ): Promise<StandardResponse<AreaData>> {
    const url = `${this.baseUrl}/api/v1/integration/areas`;

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name,
        description,
        companyId,
      }),
    });

    const data: StandardResponse<AreaData> = await response.json();

    if (!response.ok) {
      throw new Error(`Error ${data.statusCode}: ${data.message}`);
    }

    return data;
  }
}

// Uso
const client = new RAGIntegrationClient("http://localhost:8000");

client
  .createArea(
    "Desarrollo de Especies",
    "Área de conocimiento sobre desarrollo de especies",
    "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  )
  .then((result) => {
    console.log(`✅ ${result.message}`);
    console.log(`   Área: ${result.data.area_code}`);
  })
  .catch((error) => {
    console.error(`❌ ${error.message}`);
  });
```

---

### Ejemplo 8: cURL - Cargar Documento PDF

```bash
curl -X POST "http://localhost:8000/api/v1/integration/documents" \
  -F "file=@/ruta/al/documento.pdf" \
  -F "area_code=desarrollo_de_especies" \
  -F "document_name=acuerdo_03_2021"
```

**Respuesta esperada**:

```json
{
  "statusCode": 201,
  "message": "Documento guardado exitosamente",
  "data": {
    "filename": "acuerdo_03_2021.pdf",
    "original_filename": "documento.pdf",
    "area_code": "desarrollo_de_especies",
    "file_path": "data/desarrollo_de_especies/acuerdo_03_2021.pdf",
    "file_size": 245678,
    "uploaded_at": "2025-01-15T10:45:30.123456"
  }
}
```

---

### Ejemplo 9: cURL - Cargar Documento sin Nombre Personalizado

```bash
curl -X POST "http://localhost:8000/api/v1/integration/documents" \
  -F "file=@/ruta/al/Acuerdo 03-2021.pdf" \
  -F "area_code=desarrollo_de_especies"
```

**Nota**: El nombre se normalizará automáticamente desde el nombre original del archivo.

---

### Ejemplo 10: Python - Cargar Documento PDF

```python
import requests

url = "http://localhost:8000/api/v1/integration/documents"

# Abrir archivo
with open("documento.pdf", "rb") as f:
    files = {
        "file": ("documento.pdf", f, "application/pdf")
    }
    data = {
        "area_code": "desarrollo_de_especies",
        "document_name": "acuerdo_03_2021"  # Opcional
    }

    response = requests.post(url, files=files, data=data)

if response.status_code == 201:
    result = response.json()
    print(f"✅ {result['message']}")
    print(f"   Archivo: {result['data']['filename']}")
    print(f"   Ruta: {result['data']['file_path']}")
    print(f"   Tamaño: {result['data']['file_size']} bytes")
else:
    error = response.json()
    print(f"❌ Error {error['statusCode']}: {error['message']}")
```

---

### Ejemplo 11: Python - Cliente para Cargar Documentos

```python
import requests
from pathlib import Path
from typing import Optional

class RAGIntegrationClient:
    """Cliente para integrar con API RAG."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def upload_document(
        self,
        file_path: str,
        area_code: str,
        document_name: Optional[str] = None
    ) -> dict:
        """
        Cargar documento PDF en un área.

        Args:
            file_path: Ruta al archivo PDF
            area_code: Código del área (nombre normalizado)
            document_name: Nombre opcional para el documento

        Returns:
            Dict con información del documento guardado
        """
        url = f"{self.base_url}/api/v1/integration/documents"

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        with open(file_path_obj, "rb") as f:
            files = {
                "file": (file_path_obj.name, f, "application/pdf")
            }
            data = {
                "area_code": area_code
            }
            if document_name:
                data["document_name"] = document_name

            response = self.session.post(url, files=files, data=data)
            response.raise_for_status()

            return response.json()


# Uso
client = RAGIntegrationClient("http://localhost:8000")

try:
    result = client.upload_document(
        file_path="./documentos/acuerdo.pdf",
        area_code="desarrollo_de_especies",
        document_name="acuerdo_03_2021"
    )

    print(f"✅ {result['message']}")
    print(f"   Archivo guardado: {result['data']['file_path']}")

except requests.HTTPError as e:
    error = e.response.json()
    print(f"❌ Error {error['statusCode']}: {error['message']}")
```

---

### Ejemplo 12: JavaScript/TypeScript - Cargar Documento

```javascript
async function uploadDocument(file, areaCode, documentName = null) {
  const url = "http://localhost:8000/api/v1/integration/documents";

  const formData = new FormData();
  formData.append("file", file);
  formData.append("area_code", areaCode);
  if (documentName) {
    formData.append("document_name", documentName);
  }

  try {
    const response = await fetch(url, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (response.ok) {
      console.log(`✅ ${data.message}`);
      console.log(`   Archivo: ${data.data.filename}`);
      console.log(`   Ruta: ${data.data.file_path}`);
      return data;
    } else {
      console.error(`❌ Error ${data.statusCode}: ${data.message}`);
      throw new Error(data.message);
    }
  } catch (error) {
    console.error("❌ Error de conexión:", error);
    throw error;
  }
}

// Uso
const fileInput = document.querySelector('input[type="file"]');
const file = fileInput.files[0];

uploadDocument(file, "desarrollo_de_especies", "acuerdo_03_2021");
```

---

### Ejemplo 13: Postman - Cargar Documento

1. **Método**: `POST`
2. **URL**: `http://localhost:8000/api/v1/integration/documents`
3. **Body** (form-data):
   - `file`: (Seleccionar archivo) - documento.pdf
   - `area_code`: desarrollo_de_especies
   - `document_name`: acuerdo_03_2021 (opcional)

---

### Ejemplo 14: Postman - Crear Área

1. **Método**: `POST`
2. **URL**: `http://localhost:8000/api/v1/integration/areas`
3. **Headers**:
   - `Content-Type: application/json`
4. **Body** (raw JSON):
   ```json
   {
     "name": "Desarrollo de Especies",
     "description": "Área de conocimiento sobre desarrollo de especies",
     "companyId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
   }
   ```

---

### Ejemplo 15: cURL - Ingerir Documentos de un Área

```bash
curl -X POST "http://localhost:8000/api/v1/integration/ingest" \
  -F "area_code=desarrollo_de_especies" \
  -F "recreate=false" \
  -F "force_reprocess=false"
```

**Respuesta esperada**:

```json
{
  "statusCode": 202,
  "message": "Proceso de ingesta iniciado para área 'desarrollo_de_especies'. Procesando 5 documento(s).",
  "data": {
    "process_id": "ingest_desarrollo_de_especies_20250115_104530",
    "area_code": "desarrollo_de_especies",
    "pid": 12345,
    "status": "running",
    "total_documents": 5,
    "log_file": "logs/ingest_desarrollo_de_especies_20250115_104530.log",
    "started_at": "2025-01-15T10:45:30.123456",
    "recreate": false,
    "force_reprocess": false
  }
}
```

---

### Ejemplo 16: cURL - Ingerir con RECREATE (Elimina datos existentes)

```bash
curl -X POST "http://localhost:8000/api/v1/integration/ingest" \
  -F "area_code=desarrollo_de_especies" \
  -F "recreate=true"
```

**⚠️ Advertencia**: Esto eliminará todos los datos existentes de la colección.

---

### Ejemplo 17: Python - Ingerir Documentos

```python
import requests

url = "http://localhost:8000/api/v1/integration/ingest"

data = {
    "area_code": "desarrollo_de_especies",
    "recreate": False,
    "force_reprocess": False
}

response = requests.post(url, data=data)

if response.status_code == 202:
    result = response.json()
    print(f"✅ {result['message']}")
    print(f"   Proceso ID: {result['data']['process_id']}")
    print(f"   PID: {result['data']['pid']}")
    print(f"   Documentos: {result['data']['total_documents']}")
    print(f"   Log: {result['data']['log_file']}")
else:
    error = response.json()
    print(f"❌ Error {error['statusCode']}: {error['message']}")
```

**Salida esperada**:

```
✅ Proceso de ingesta iniciado para área 'desarrollo_de_especies'. Procesando 5 documento(s).
   Proceso ID: ingest_desarrollo_de_especies_20250115_104530
   PID: 12345
   Documentos: 5
   Log: logs/ingest_desarrollo_de_especies_20250115_104530.log
```

---

### Ejemplo 18: Python - Cliente para Ingerir Documentos

```python
import requests
from typing import Optional

class RAGIntegrationClient:
    """Cliente para integrar con API RAG."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def ingest_area(
        self,
        area_code: str,
        recreate: bool = False,
        force_reprocess: bool = False
    ) -> dict:
        """
        Ingerir todos los documentos PDF de un área.

        Args:
            area_code: Código del área (nombre normalizado)
            recreate: Si es True, recrea la colección (elimina datos existentes)
            force_reprocess: Si es True, fuerza el reprocesamiento

        Returns:
            Dict con información del proceso iniciado
        """
        url = f"{self.base_url}/api/v1/integration/ingest"

        data = {
            "area_code": area_code,
            "recreate": recreate,
            "force_reprocess": force_reprocess
        }

        response = self.session.post(url, data=data)
        response.raise_for_status()

        return response.json()


# Uso
client = RAGIntegrationClient("http://localhost:8000")

try:
    result = client.ingest_area(
        area_code="desarrollo_de_especies",
        recreate=False,
        force_reprocess=False
    )

    print(f"✅ {result['message']}")
    print(f"   Proceso ID: {result['data']['process_id']}")
    print(f"   Log: {result['data']['log_file']}")

except requests.HTTPError as e:
    error = e.response.json()
    print(f"❌ Error {error['statusCode']}: {error['message']}")
```

---

### Ejemplo 19: JavaScript/TypeScript - Ingerir Documentos

```javascript
async function ingestArea(areaCode, recreate = false, forceReprocess = false) {
  const url = "http://localhost:8000/api/v1/integration/ingest";

  const formData = new FormData();
  formData.append("area_code", areaCode);
  formData.append("recreate", recreate.toString());
  formData.append("force_reprocess", forceReprocess.toString());

  try {
    const response = await fetch(url, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (response.ok) {
      console.log(`✅ ${data.message}`);
      console.log(`   Proceso ID: ${data.data.process_id}`);
      console.log(`   PID: ${data.data.pid}`);
      console.log(`   Documentos: ${data.data.total_documents}`);
      console.log(`   Log: ${data.data.log_file}`);
      return data;
    } else {
      console.error(`❌ Error ${data.statusCode}: ${data.message}`);
      throw new Error(data.message);
    }
  } catch (error) {
    console.error("❌ Error de conexión:", error);
    throw error;
  }
}

// Uso
ingestArea("desarrollo_de_especies", false, false);
```

---

### Ejemplo 20: Postman - Ingerir Documentos

1. **Método**: `POST`
2. **URL**: `http://localhost:8000/api/v1/integration/ingest`
3. **Body** (form-data):
   - `area_code`: desarrollo_de_especies
   - `recreate`: false (opcional)
   - `force_reprocess`: false (opcional)

---

## 📊 Códigos de Respuesta

| Código HTTP | Significado              | Descripción                                             |
| ----------- | ------------------------ | ------------------------------------------------------- |
| `201`       | Created                  | Área/Documento creado exitosamente                      |
| `202`       | Accepted                 | Proceso de ingesta iniciado (asíncrono)                 |
| `400`       | Bad Request              | Error de validación (nombre vacío, UUID inválido, etc.) |
| `404`       | Not Found                | Área no encontrada                                      |
| `409`       | Conflict                 | El área/documento ya existe                             |
| `413`       | Request Entity Too Large | Archivo demasiado grande (solo para cargar documentos)  |
| `500`       | Internal Server Error    | Error interno del servidor                              |

---

## ⚠️ Manejo de Errores

### Caso 1: Nombre Vacío

**Request**:

```json
{
  "name": "",
  "description": "Descripción",
  "companyId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

**Response** (400):

```json
{
  "statusCode": 400,
  "message": "name no puede estar vacío",
  "data": {}
}
```

---

### Caso 2: UUID Inválido

**Request**:

```json
{
  "name": "Desarrollo de Especies",
  "description": "Descripción",
  "companyId": "invalid-uuid"
}
```

**Response** (400):

```json
{
  "statusCode": 400,
  "message": "companyId debe ser un UUID válido",
  "data": {}
}
```

---

### Caso 3: Área Ya Existe (Crear Área)

**Request** (segunda vez con el mismo nombre):

```json
{
  "name": "Desarrollo de Especies",
  "description": "Descripción",
  "companyId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

**Response** (409):

```json
{
  "statusCode": 409,
  "message": "El área 'desarrollo_de_especies' ya existe",
  "data": {
    "area_code": "desarrollo_de_especies",
    "folder_path": "data/desarrollo_de_especies"
  }
}
```

---

### Caso 4: Área No Existe (Cargar Documento)

**Request** (cargar documento en área inexistente):

```bash
curl -X POST "http://localhost:8000/api/v1/integration/documents" \
  -F "file=@documento.pdf" \
  -F "area_code=area_inexistente"
```

**Response** (404):

```json
{
  "statusCode": 404,
  "message": "El área 'area_inexistente' no existe. Cree el área primero.",
  "data": {}
}
```

---

### Caso 5: Archivo No es PDF (Cargar Documento)

**Request** (intentar cargar un .docx):

```bash
curl -X POST "http://localhost:8000/api/v1/integration/documents" \
  -F "file=@documento.docx" \
  -F "area_code=desarrollo_de_especies"
```

**Response** (400):

```json
{
  "statusCode": 400,
  "message": "El archivo debe ser un PDF. Extensión recibida: .docx",
  "data": {}
}
```

---

### Caso 6: Documento Ya Existe (Cargar Documento)

**Request** (cargar el mismo documento dos veces):

```bash
curl -X POST "http://localhost:8000/api/v1/integration/documents" \
  -F "file=@documento.pdf" \
  -F "area_code=desarrollo_de_especies" \
  -F "document_name=acuerdo_03_2021"
```

**Response** (409):

```json
{
  "statusCode": 409,
  "message": "El documento 'acuerdo_03_2021.pdf' ya existe en el área 'desarrollo_de_especies'",
  "data": {
    "filename": "acuerdo_03_2021.pdf",
    "area_code": "desarrollo_de_especies",
    "file_path": "data/desarrollo_de_especies/acuerdo_03_2021.pdf"
  }
}
```

---

### Caso 7: Archivo Demasiado Grande (Cargar Documento)

**Request** (archivo > 50 MB):

```bash
curl -X POST "http://localhost:8000/api/v1/integration/documents" \
  -F "file=@documento_grande.pdf" \
  -F "area_code=desarrollo_de_especies"
```

**Response** (413):

```json
{
  "statusCode": 413,
  "message": "El archivo es demasiado grande. Tamaño máximo: 50 MB",
  "data": {}
}
```

---

### Caso 8: No Hay Documentos en el Área (Ingerir)

**Request** (ingesta en área sin documentos):

```bash
curl -X POST "http://localhost:8000/api/v1/integration/ingest" \
  -F "area_code=desarrollo_de_especies"
```

**Response** (400):

```json
{
  "statusCode": 400,
  "message": "No hay documentos PDF en el área 'desarrollo_de_especies'. Cargue documentos primero.",
  "data": {
    "area_code": "desarrollo_de_especies",
    "folder_path": "data/desarrollo_de_especies"
  }
}
```

---

### Caso 9: Área No Existe (Ingerir)

**Request** (ingesta en área inexistente):

```bash
curl -X POST "http://localhost:8000/api/v1/integration/ingest" \
  -F "area_code=area_inexistente"
```

**Response** (404):

```json
{
  "statusCode": 404,
  "message": "El área 'area_inexistente' no existe. Cree el área primero.",
  "data": {}
}
```

**Request** (archivo > 50 MB):

```bash
curl -X POST "http://localhost:8000/api/v1/integration/documents" \
  -F "file=@documento_grande.pdf" \
  -F "area_code=desarrollo_de_especies"
```

**Response** (413):

```json
{
  "statusCode": 413,
  "message": "El archivo es demasiado grande. Tamaño máximo: 50 MB",
  "data": {}
}
```

**Request** (segunda vez con el mismo nombre):

```json
{
  "name": "Desarrollo de Especies",
  "description": "Descripción",
  "companyId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

**Response** (409):

```json
{
  "statusCode": 409,
  "message": "El área 'desarrollo_de_especies' ya existe",
  "data": {
    "area_code": "desarrollo_de_especies",
    "folder_path": "data/desarrollo_de_especies"
  }
}
```

---

## 🔍 Verificación en Swagger

El endpoint está disponible en la documentación interactiva de Swagger:

**URL**: `http://localhost:8000/docs`

1. Abre la URL en tu navegador
2. Busca el tag **`integration`**
3. Expande **`POST /api/v1/integration/areas`**
4. Haz clic en **"Try it out"**
5. Completa los campos:
   - `name`: "Desarrollo de Especies"
   - `description`: "Área de conocimiento sobre desarrollo de especies"
   - `companyId`: "3fa85f64-5717-4562-b3fc-2c963f66afa6"
6. Haz clic en **"Execute"**
7. Verás la respuesta en la sección **"Responses"**

---

## 📁 Estructura de Carpetas

### Después de Crear un Área

```
data/
└── desarrollo_de_especies/    ← Carpeta creada automáticamente
    └── (vacía, lista para recibir documentos)
```

### Después de Cargar un Documento

```
data/
└── desarrollo_de_especies/
    ├── acuerdo_03_2021.pdf    ← Documento guardado
    ├── decreto_1082_2015.pdf
    └── ...
```

**Nota**: Los nombres de archivo se normalizan automáticamente:

- `"Acuerdo 03-2021.pdf"` → `"acuerdo_03_2021.pdf"`
- `"Decreto 1082/2015.pdf"` → `"decreto_1082_2015.pdf"`

La ruta completa se retorna en el campo `file_path` de la respuesta.

---

## ✅ Checklist de Uso

### Para Crear Área

- [ ] Verificar que el servidor esté corriendo en `http://localhost:8000`
- [ ] Verificar que `name` no esté vacío
- [ ] Verificar que `companyId` sea un UUID válido
- [ ] Verificar que el área no exista ya (si es necesario)
- [ ] Manejar errores HTTP apropiadamente
- [ ] Guardar `area_code` y `folder_path` para uso futuro

### Para Cargar Documento

- [ ] Verificar que el servidor esté corriendo en `http://localhost:8000`
- [ ] Verificar que el área exista (crearla primero si es necesario)
- [ ] Verificar que el archivo sea un PDF válido
- [ ] Verificar que el tamaño del archivo sea menor a 50 MB
- [ ] Verificar que el documento no exista ya (si es necesario)
- [ ] Manejar errores HTTP apropiadamente
- [ ] Guardar `file_path` para referencia futura

### Para Ingerir Documentos

- [ ] Verificar que el servidor esté corriendo en `http://localhost:8000`
- [ ] Verificar que el área exista (crearla primero si es necesario)
- [ ] Verificar que haya documentos PDF en el área (cargarlos primero si es necesario)
- [ ] Decidir si usar `recreate=true` (elimina datos existentes) o `recreate=false`
- [ ] Decidir si usar `force_reprocess=true` (reprocesa todo) o `force_reprocess=false` (salta duplicados)
- [ ] Guardar `process_id` y `log_file` para monitorear el progreso
- [ ] Consultar el archivo de log para ver el estado del proceso
- [ ] No esperar respuesta inmediata (el proceso es asíncrono)

## 🔄 Flujo Completo: Crear Área, Cargar Documento e Ingerir

### Paso 1: Crear Área

```bash
curl -X POST "http://localhost:8000/api/v1/integration/areas" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Desarrollo de Especies",
    "description": "Área de conocimiento sobre desarrollo de especies",
    "companyId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }'
```

**Respuesta**:

```json
{
  "statusCode": 201,
  "message": "Área creada exitosamente",
  "data": {
    "area_code": "desarrollo_de_especies",
    "folder_path": "data/desarrollo_de_especies",
    ...
  }
}
```

### Paso 2: Cargar Documento en el Área

```bash
curl -X POST "http://localhost:8000/api/v1/integration/documents" \
  -F "file=@documento.pdf" \
  -F "area_code=desarrollo_de_especies" \
  -F "document_name=acuerdo_03_2021"
```

**Respuesta**:

```json
{
  "statusCode": 201,
  "message": "Documento guardado exitosamente",
  "data": {
    "filename": "acuerdo_03_2021.pdf",
    "file_path": "data/desarrollo_de_especies/acuerdo_03_2021.pdf",
    ...
  }
}
```

### Paso 3: Ingerir Documentos del Área

```bash
curl -X POST "http://localhost:8000/api/v1/integration/ingest" \
  -F "area_code=desarrollo_de_especies" \
  -F "recreate=false" \
  -F "force_reprocess=false"
```

**Respuesta**:

```json
{
  "statusCode": 202,
  "message": "Proceso de ingesta iniciado para área 'desarrollo_de_especies'. Procesando 1 documento(s).",
  "data": {
    "process_id": "ingest_desarrollo_de_especies_20250115_104530",
    "pid": 12345,
    "status": "running",
    "total_documents": 1,
    "log_file": "logs/ingest_desarrollo_de_especies_20250115_104530.log",
    ...
  }
}
```

**Resultado**:

- El documento está guardado
- El proceso de ingesta está corriendo en background
- Puedes consultar el log en `logs/ingest_desarrollo_de_especies_20250115_104530.log` para ver el progreso
- Una vez completado, el documento estará disponible para consultas RAG

---

## 📋 Flujo Completo: Crear Área y Cargar Documento (Versión Anterior)

### Paso 1: Crear Área

```bash
curl -X POST "http://localhost:8000/api/v1/integration/areas" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Desarrollo de Especies",
    "description": "Área de conocimiento sobre desarrollo de especies",
    "companyId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }'
```

**Respuesta**:

```json
{
  "statusCode": 201,
  "message": "Área creada exitosamente",
  "data": {
    "area_code": "desarrollo_de_especies",
    "folder_path": "data/desarrollo_de_especies",
    ...
  }
}
```

### Paso 2: Cargar Documento en el Área

```bash
curl -X POST "http://localhost:8000/api/v1/integration/documents" \
  -F "file=@documento.pdf" \
  -F "area_code=desarrollo_de_especies" \
  -F "document_name=acuerdo_03_2021"
```

**Respuesta**:

```json
{
  "statusCode": 201,
  "message": "Documento guardado exitosamente",
  "data": {
    "filename": "acuerdo_03_2021.pdf",
    "file_path": "data/desarrollo_de_especies/acuerdo_03_2021.pdf",
    ...
  }
}
```

**Resultado**: El documento está guardado y listo para ser ingerido.

---

**Autor**: Sistema de Documentación  
**Última Actualización**: 2025-01-15  
**Versión**: 1.0.0

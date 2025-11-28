# Guía: Endpoint para Crear Área desde API Externa

**Fecha**: 2025-01-15  
**Versión**: 1.0.0

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Cómo Funciona](#cómo-funciona)
3. [Implementación Paso a Paso](#implementación-paso-a-paso)
4. [Cómo Consumir desde el Otro Proyecto](#cómo-consumir-desde-el-otro-proyecto)
5. [Ejemplos Prácticos](#ejemplos-prácticos)
6. [Manejo de Errores](#manejo-de-errores)
7. [Flujo Completo](#flujo-completo)

---

## 🎯 Visión General

### Objetivo

Cuando el **otro proyecto (API Externa)** crea una nueva área en su sistema, debe poder notificar a este sistema RAG para que:

1. **Registre el área** con su GUID
2. **Cree la carpeta** donde se almacenarán los documentos
3. **Genere el código interno** que usará el sistema RAG
4. **Guarde el mapeo** GUID ↔ Código Interno

### Endpoint

```
POST /api/v1/integration/areas
```

### Flujo Simplificado

```
┌─────────────────┐
│  API Externa    │
│  (Otro Proyecto)│
└────────┬────────┘
         │
         │ 1. Crea área en su BD
         │    - Genera GUID: "a1b2c3d4-..."
         │    - Nombre: "Sistema General de Regalías"
         │
         │ 2. Llama a este endpoint
         │    POST /api/v1/integration/areas
         │    {
         │      "area_guid": "a1b2c3d4-...",
         │      "nombre": "Sistema General de Regalías",
         │      "descripcion": "..."
         │    }
         ↓
┌─────────────────────────────────────┐
│  Sistema RAG (Este Proyecto)        │
│                                     │
│  ✓ Valida GUID                      │
│  ✓ Genera código: "sgr"            │
│  ✓ Crea carpeta: data/a1b2c3d4-.../│
│  ✓ Guarda mapeo                     │
│  ✓ Retorna respuesta                │
└────────┬────────────────────────────┘
         │
         │ Response: {
         │   "area_code": "sgr",
         │   "folder_path": "data/a1b2c3d4-...",
         │   ...
         │ }
         ↓
┌─────────────────┐
│  API Externa    │
│  (Guarda mapeo) │
└─────────────────┘
```

---

## 🔄 Cómo Funciona

### Paso a Paso Interno

#### 1. **Recepción del Request**

El endpoint recibe:
```json
{
    "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "nombre": "Sistema General de Regalías",
    "descripcion": "Área de conocimiento sobre regalías y normativa"
}
```

#### 2. **Validaciones**

- ✅ **GUID válido**: Verifica que sea un UUID v4 válido
- ✅ **GUID único**: Verifica que no exista ya en el mapeo
- ✅ **Nombre requerido**: Verifica que nombre no esté vacío

#### 3. **Generación de Código Interno**

El sistema genera un `area_code` desde el nombre:

```python
# Normalización del nombre
nombre_normalizado = nombre.lower()
nombre_normalizado = nombre_normalizado.replace(" ", "_")
nombre_normalizado = nombre_normalizado.replace("-", "_")
nombre_normalizado = nombre_normalizado.replace("á", "a")
nombre_normalizado = nombre_normalizado.replace("é", "e")
# ... más normalizaciones

# Ejemplo:
# "Sistema General de Regalías" → "sistema_general_de_regalias"
# Se acorta si es muy largo: "sgr" (si ya existe en config/areas.json)
```

**Estrategia**:
1. Si el código generado ya existe en `config/areas.json`, lo usa
2. Si no existe, crea uno nuevo basado en el nombre
3. Si hay colisión, agrega sufijo numérico: `sgr_2`, `sgr_3`, etc.

#### 4. **Creación de Carpeta**

```python
folder_path = Path("data") / area_guid
folder_path.mkdir(parents=True, exist_ok=True)
```

**Estructura resultante**:
```
data/
└── a1b2c3d4-e5f6-7890-abcd-ef1234567890/
    └── (aquí se guardarán los PDFs)
```

#### 5. **Registro en Mapeo**

Se guarda en `config/area_guid_mapping.json`:

```json
{
    "areas": {
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890": {
            "area_code": "sgr",
            "nombre": "Sistema General de Regalías",
            "descripcion": "Área de conocimiento sobre regalías",
            "created_at": "2025-01-15T10:00:00Z",
            "folder_path": "data/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        }
    }
}
```

#### 6. **Actualización de Config (Opcional)**

Si el `area_code` no existe en `config/areas.json`, se agrega:

```json
{
    "areas": {
        "sgr": "Sistema General de Regalías",
        "inteligencia_artificial": "Inteligencia Artificial",
        "general": "General"
    }
}
```

#### 7. **Respuesta al Cliente**

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

---

## 🛠️ Implementación Paso a Paso

### Paso 1: Crear Módulo de Mapeo

**Archivo**: `src/mapping/guid_mapper.py`

```python
"""
Módulo para gestionar mapeo entre GUIDs externos y códigos internos.
"""
import json
import uuid
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
from loguru import logger

from src.config import BASE_DIR


class GuidMapper:
    """
    Gestiona mapeo entre GUIDs externos y códigos internos.
    """
    
    def __init__(self):
        """Inicializar mapper."""
        self.mapping_file = BASE_DIR / "config" / "area_guid_mapping.json"
        self._ensure_mapping_file()
    
    def _ensure_mapping_file(self):
        """Asegurar que el archivo de mapeo existe."""
        if not self.mapping_file.exists():
            self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump({"areas": {}, "documentos": {}}, f, indent=2, ensure_ascii=False)
            logger.info(f"Created mapping file: {self.mapping_file}")
    
    def _load_mapping(self) -> Dict:
        """Cargar mapeo desde archivo."""
        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading mapping: {e}")
            return {"areas": {}, "documentos": {}}
    
    def _save_mapping(self, mapping: Dict):
        """Guardar mapeo en archivo."""
        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, indent=2, ensure_ascii=False)
            logger.debug(f"Mapping saved to {self.mapping_file}")
        except Exception as e:
            logger.error(f"Error saving mapping: {e}")
            raise
    
    def is_valid_guid(self, guid: str) -> bool:
        """Validar que un GUID sea válido (UUID v4)."""
        try:
            uuid.UUID(guid, version=4)
            return True
        except (ValueError, AttributeError):
            return False
    
    def area_exists(self, area_guid: str) -> bool:
        """Verificar si un área ya existe."""
        mapping = self._load_mapping()
        return area_guid in mapping.get("areas", {})
    
    def get_area_code(self, area_guid: str) -> Optional[str]:
        """Obtener código interno desde GUID de área."""
        mapping = self._load_mapping()
        area_data = mapping.get("areas", {}).get(area_guid)
        return area_data.get("area_code") if area_data else None
    
    def get_area_guid(self, area_code: str) -> Optional[str]:
        """Obtener GUID desde código interno."""
        mapping = self._load_mapping()
        for guid, data in mapping.get("areas", {}).items():
            if data.get("area_code") == area_code:
                return guid
        return None
    
    def _generate_area_code(self, nombre: str) -> str:
        """
        Generar código interno desde nombre.
        
        Estrategia:
        1. Normalizar nombre (lowercase, sin acentos, espacios → guiones bajos)
        2. Verificar si ya existe en config/areas.json
        3. Si no existe, usar el normalizado (o versión corta)
        4. Si hay colisión, agregar sufijo numérico
        """
        import re
        from src.config import VALID_AREAS
        
        # Normalizar
        code = nombre.lower()
        code = code.replace(" ", "_")
        code = code.replace("-", "_")
        # Remover acentos
        code = code.replace("á", "a").replace("é", "e").replace("í", "i")
        code = code.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        # Remover caracteres especiales
        code = re.sub(r'[^a-z0-9_]', '', code)
        # Limitar longitud
        if len(code) > 30:
            # Tomar primeras palabras o acrónimo
            words = code.split("_")
            if len(words) > 1:
                code = "_".join([w[0] for w in words if w])
            else:
                code = code[:30]
        
        # Verificar si ya existe en VALID_AREAS
        if code in VALID_AREAS:
            return code
        
        # Verificar colisiones en mapeo
        mapping = self._load_mapping()
        existing_codes = {data.get("area_code") for data in mapping.get("areas", {}).values()}
        
        original_code = code
        counter = 1
        while code in existing_codes:
            code = f"{original_code}_{counter}"
            counter += 1
        
        return code
    
    def register_area(
        self,
        area_guid: str,
        nombre: str,
        descripcion: Optional[str] = None
    ) -> Dict:
        """
        Registrar nueva área.
        
        Args:
            area_guid: GUID de la área (UUID v4)
            nombre: Nombre de la área
            descripcion: Descripción opcional
        
        Returns:
            Dict con información de la área registrada
        
        Raises:
            ValueError: Si GUID es inválido o ya existe
        """
        # Validar GUID
        if not self.is_valid_guid(area_guid):
            raise ValueError(f"GUID inválido: {area_guid}. Debe ser un UUID v4 válido")
        
        # Verificar que no exista
        if self.area_exists(area_guid):
            raise ValueError(f"El área con GUID '{area_guid}' ya existe")
        
        # Generar código interno
        area_code = self._generate_area_code(nombre)
        
        # Crear carpeta
        folder_path = BASE_DIR / "data" / area_guid
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # Guardar en mapeo
        mapping = self._load_mapping()
        mapping["areas"][area_guid] = {
            "area_code": area_code,
            "nombre": nombre,
            "descripcion": descripcion or "",
            "created_at": datetime.now().isoformat(),
            "folder_path": str(folder_path.relative_to(BASE_DIR))
        }
        self._save_mapping(mapping)
        
        # (Opcional) Actualizar config/areas.json
        self._update_areas_config(area_code, nombre)
        
        logger.info(f"Área registrada: {area_guid} → {area_code}")
        
        return {
            "area_guid": area_guid,
            "area_code": area_code,
            "nombre": nombre,
            "folder_path": str(folder_path.relative_to(BASE_DIR))
        }
    
    def _update_areas_config(self, area_code: str, nombre: str):
        """Actualizar config/areas.json si no existe el código."""
        from src.config import _load_areas_from_json, BASE_DIR
        
        areas_file = BASE_DIR / "config" / "areas.json"
        areas = _load_areas_from_json() or {}
        
        if area_code not in areas:
            areas[area_code] = nombre
            try:
                with open(areas_file, 'w', encoding='utf-8') as f:
                    json.dump({"areas": areas}, f, indent=2, ensure_ascii=False)
                logger.info(f"Updated areas.json with new area: {area_code}")
            except Exception as e:
                logger.warning(f"Could not update areas.json: {e}")


# Instancia singleton
_guid_mapper_instance = None

def get_guid_mapper() -> GuidMapper:
    """Obtener instancia singleton del mapper."""
    global _guid_mapper_instance
    if _guid_mapper_instance is None:
        _guid_mapper_instance = GuidMapper()
    return _guid_mapper_instance
```

---

### Paso 2: Crear Modelos de Request/Response

**Archivo**: `api/models/requests.py` (agregar al final)

```python
class CreateAreaRequest(BaseModel):
    """Request para crear área desde API externa."""
    
    area_guid: str = Field(
        ...,
        description="GUID único de la área (UUID v4)",
        min_length=36,
        max_length=36
    )
    nombre: str = Field(
        ...,
        description="Nombre de la área",
        min_length=1,
        max_length=200
    )
    descripcion: Optional[str] = Field(
        default=None,
        description="Descripción de la área",
        max_length=1000
    )
    
    @field_validator("area_guid")
    @classmethod
    def validate_guid(cls, v: str) -> str:
        """Validar formato GUID."""
        from src.mapping.guid_mapper import get_guid_mapper
        mapper = get_guid_mapper()
        if not mapper.is_valid_guid(v):
            raise ValueError("area_guid debe ser un UUID v4 válido")
        return v
    
    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        """Validar nombre."""
        if not v or not v.strip():
            raise ValueError("nombre no puede estar vacío")
        return v.strip()
```

**Archivo**: `api/models/responses.py` (agregar al final)

```python
class CreateAreaResponse(BaseModel):
    """Response para creación de área."""
    
    success: bool = Field(default=True, description="Indica si la operación fue exitosa")
    area_guid: str = Field(..., description="GUID de la área creada")
    area_code: str = Field(..., description="Código interno generado")
    nombre: str = Field(..., description="Nombre de la área")
    folder_path: str = Field(..., description="Ruta de la carpeta creada")
    message: str = Field(..., description="Mensaje descriptivo")
```

---

### Paso 3: Crear Router de Integración

**Archivo**: `api/routers/integration.py`

```python
"""
Endpoints de integración con API externa.
Gestiona áreas y documentos usando GUIDs.
"""
from fastapi import APIRouter, status, HTTPException
from loguru import logger

from api.models.requests import CreateAreaRequest
from api.models.responses import CreateAreaResponse, ErrorResponse
from src.mapping.guid_mapper import get_guid_mapper

router = APIRouter(prefix="/api/v1/integration", tags=["integration"])


@router.post(
    "/areas",
    response_model=CreateAreaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear área",
    description="Crea una nueva área de conocimiento desde API externa usando GUID",
    responses={
        201: {"description": "Área creada exitosamente"},
        400: {"model": ErrorResponse, "description": "Request inválido"},
        409: {"model": ErrorResponse, "description": "Área ya existe"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def create_area(request: CreateAreaRequest) -> CreateAreaResponse:
    """
    Crear nueva área de conocimiento.
    
    Este endpoint es llamado por la API externa cuando se crea una nueva área.
    El sistema RAG:
    1. Valida el GUID
    2. Genera un código interno
    3. Crea la carpeta para almacenar documentos
    4. Guarda el mapeo GUID ↔ código interno
    
    Args:
        request: Request con GUID, nombre y descripción de la área
    
    Returns:
        CreateAreaResponse con información de la área creada
    
    Raises:
        HTTPException: Si hay error en la creación
    """
    logger.info(f"Crear área solicitada: GUID={request.area_guid}, Nombre={request.nombre}")
    
    try:
        mapper = get_guid_mapper()
        
        # Verificar que no exista
        if mapper.area_exists(request.area_guid):
            logger.warning(f"Área ya existe: {request.area_guid}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "success": False,
                    "error": f"El área con GUID '{request.area_guid}' ya existe",
                    "error_code": "AREA_ALREADY_EXISTS"
                }
            )
        
        # Registrar área
        area_data = mapper.register_area(
            area_guid=request.area_guid,
            nombre=request.nombre,
            descripcion=request.descripcion
        )
        
        logger.success(
            f"Área creada exitosamente: {request.area_guid} → {area_data['area_code']}"
        )
        
        return CreateAreaResponse(
            success=True,
            area_guid=area_data["area_guid"],
            area_code=area_data["area_code"],
            nombre=area_data["nombre"],
            folder_path=area_data["folder_path"],
            message="Área creada exitosamente"
        )
    
    except ValueError as e:
        # Error de validación (GUID inválido, etc.)
        logger.error(f"Error de validación: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": str(e),
                "error_code": "VALIDATION_ERROR"
            }
        )
    
    except HTTPException:
        # Re-lanzar excepciones HTTP
        raise
    
    except Exception as e:
        # Error inesperado
        logger.error(f"Error inesperado al crear área: {e}")
        logger.exception("Traceback completo:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": f"Error interno al crear área: {str(e)}",
                "error_code": "INTERNAL_ERROR"
            }
        )
```

---

### Paso 4: Registrar Router en Main

**Archivo**: `api/main.py` (modificar)

```python
# Agregar import
from api.routers import health, rag, documents, ingestion, integration

# ... código existente ...

# Include routers
app.include_router(health.router)
app.include_router(rag.router)
app.include_router(documents.router)
app.include_router(ingestion.router)
app.include_router(integration.router)  # ← NUEVO
```

---

### Paso 5: Crear Archivo __init__.py para Módulo Mapping

**Archivo**: `src/mapping/__init__.py`

```python
"""
Módulo de mapeo entre GUIDs externos y códigos internos.
"""
from src.mapping.guid_mapper import GuidMapper, get_guid_mapper

__all__ = ["GuidMapper", "get_guid_mapper"]
```

---

## 🌐 Cómo Consumir desde el Otro Proyecto

### Opción 1: Consumo desde Python

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
        # Aquí puedes agregar autenticación si es necesaria
        # self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def create_area(
        self,
        area_guid: str,
        nombre: str,
        descripcion: Optional[str] = None
    ) -> Dict:
        """
        Crear área en el sistema RAG.
        
        Args:
            area_guid: GUID único de la área (UUID v4)
            nombre: Nombre de la área
            descripcion: Descripción opcional
        
        Returns:
            Dict con información de la área creada
        
        Raises:
            requests.HTTPError: Si hay error en la petición
        """
        url = f"{self.base_url}/api/v1/integration/areas"
        
        payload = {
            "area_guid": area_guid,
            "nombre": nombre,
            "descripcion": descripcion
        }
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()  # Lanza excepción si hay error HTTP
        
        return response.json()


# Ejemplo de uso en el otro proyecto
def on_area_created(area_guid: str, nombre: str, descripcion: str):
    """
    Función que se llama cuando se crea un área en el otro proyecto.
    
    Esta función debe ser llamada desde el código que crea áreas en la BD.
    """
    client = RAGIntegrationClient(base_url="http://rag-api:8000")
    
    try:
        result = client.create_area(
            area_guid=area_guid,
            nombre=nombre,
            descripcion=descripcion
        )
        
        print(f"✅ Área creada en RAG: {result['area_code']}")
        print(f"   Carpeta: {result['folder_path']}")
        
        # Opcional: Guardar mapeo en tu BD
        # save_area_mapping(area_guid, result['area_code'])
        
        return result
    
    except requests.HTTPError as e:
        if e.response.status_code == 409:
            print(f"⚠️  Área ya existe en RAG: {area_guid}")
            # Puedes obtener el área existente
            # existing_area = get_existing_area(area_guid)
        else:
            print(f"❌ Error al crear área en RAG: {e}")
            raise
```

**Integración en el código del otro proyecto:**

```python
# En tu modelo/servicio de áreas
class AreaService:
    def create_area(self, nombre: str, descripcion: str) -> Area:
        # 1. Crear área en tu BD
        area = Area(
            id=uuid.uuid4(),  # Generar GUID
            nombre=nombre,
            descripcion=descripcion
        )
        db.session.add(area)
        db.session.commit()
        
        # 2. Notificar al sistema RAG
        try:
            from integrations.rag_client import RAGIntegrationClient
            rag_client = RAGIntegrationClient()
            rag_result = rag_client.create_area(
                area_guid=str(area.id),
                nombre=nombre,
                descripcion=descripcion
            )
            
            # 3. (Opcional) Guardar código interno en tu BD
            area.rag_area_code = rag_result['area_code']
            db.session.commit()
            
        except Exception as e:
            # Log error pero no fallar la creación del área
            logger.error(f"Error al notificar RAG: {e}")
            # Puedes implementar retry aquí
        
        return area
```

---

### Opción 2: Consumo desde JavaScript/TypeScript

```typescript
// rag-client.ts
interface CreateAreaRequest {
  area_guid: string;
  nombre: string;
  descripcion?: string;
}

interface CreateAreaResponse {
  success: boolean;
  area_guid: string;
  area_code: string;
  nombre: string;
  folder_path: string;
  message: string;
}

class RAGIntegrationClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async createArea(
    areaGuid: string,
    nombre: string,
    descripcion?: string
  ): Promise<CreateAreaResponse> {
    const url = `${this.baseUrl}/api/v1/integration/areas`;
    
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // "Authorization": `Bearer ${token}` // Si necesitas auth
      },
      body: JSON.stringify({
        area_guid: areaGuid,
        nombre: nombre,
        descripcion: descripcion,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Error al crear área");
    }

    return response.json();
  }
}

// Uso
async function onAreaCreated(areaGuid: string, nombre: string) {
  const client = new RAGIntegrationClient("http://rag-api:8000");
  
  try {
    const result = await client.createArea(areaGuid, nombre);
    console.log(`✅ Área creada: ${result.area_code}`);
    return result;
  } catch (error) {
    console.error("❌ Error:", error);
    throw error;
  }
}
```

---

### Opción 3: Consumo con cURL (Testing)

```bash
# Crear área
curl -X POST "http://localhost:8000/api/v1/integration/areas" \
  -H "Content-Type: application/json" \
  -d '{
    "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "nombre": "Sistema General de Regalías",
    "descripcion": "Área de conocimiento sobre regalías y normativa"
  }'

# Respuesta esperada:
# {
#   "success": true,
#   "area_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "area_code": "sgr",
#   "nombre": "Sistema General de Regalías",
#   "folder_path": "data/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "message": "Área creada exitosamente"
# }
```

---

## 📝 Ejemplos Prácticos

### Ejemplo 1: Crear Área desde Django

```python
# models.py
from django.db import models
import uuid

class Area(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    rag_area_code = models.CharField(max_length=50, blank=True)  # Código interno del RAG
    
    def __str__(self):
        return self.nombre

# services.py
import requests
from django.conf import settings

class RAGService:
    BASE_URL = settings.RAG_API_URL  # "http://rag-api:8000"
    
    @classmethod
    def create_area(cls, area: Area):
        """Notificar al RAG sobre nueva área."""
        url = f"{cls.BASE_URL}/api/v1/integration/areas"
        
        try:
            response = requests.post(
                url,
                json={
                    "area_guid": str(area.id),
                    "nombre": area.nombre,
                    "descripcion": area.descripcion
                },
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            area.rag_area_code = data['area_code']
            area.save(update_fields=['rag_area_code'])
            
            return data
        except requests.RequestException as e:
            logger.error(f"Error al crear área en RAG: {e}")
            # No lanzar excepción para no bloquear la creación del área

# views.py o signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Area)
def on_area_created(sender, instance, created, **kwargs):
    """Cuando se crea un área, notificar al RAG."""
    if created:
        RAGService.create_area(instance)
```

---

### Ejemplo 2: Crear Área desde Flask

```python
# app.py
from flask import Flask, request, jsonify
import uuid
import requests

app = Flask(__name__)

RAG_API_URL = "http://rag-api:8000"

@app.route("/api/areas", methods=["POST"])
def create_area():
    """Crear área en este sistema y notificar al RAG."""
    data = request.json
    area_guid = str(uuid.uuid4())
    
    # 1. Guardar en tu BD
    area = {
        "id": area_guid,
        "nombre": data["nombre"],
        "descripcion": data.get("descripcion", "")
    }
    # db.session.add(Area(**area))
    # db.session.commit()
    
    # 2. Notificar al RAG
    try:
        rag_response = requests.post(
            f"{RAG_API_URL}/api/v1/integration/areas",
            json={
                "area_guid": area_guid,
                "nombre": area["nombre"],
                "descripcion": area["descripcion"]
            },
            timeout=10
        )
        rag_response.raise_for_status()
        
        rag_data = rag_response.json()
        area["rag_area_code"] = rag_data["area_code"]
        
        return jsonify(area), 201
    except requests.RequestException as e:
        # Log pero no fallar
        app.logger.error(f"Error al notificar RAG: {e}")
        return jsonify(area), 201  # Retornar área creada de todas formas
```

---

## ⚠️ Manejo de Errores

### Códigos de Error

| Código HTTP | Error Code | Descripción |
|------------|------------|-------------|
| 201 | - | Área creada exitosamente |
| 400 | `VALIDATION_ERROR` | GUID inválido o nombre vacío |
| 409 | `AREA_ALREADY_EXISTS` | El área ya existe |
| 500 | `INTERNAL_ERROR` | Error interno del servidor |

### Ejemplo de Manejo de Errores

```python
def create_area_with_retry(area_guid: str, nombre: str, max_retries: int = 3):
    """Crear área con reintentos."""
    client = RAGIntegrationClient()
    
    for attempt in range(max_retries):
        try:
            return client.create_area(area_guid, nombre)
        except requests.HTTPError as e:
            if e.response.status_code == 409:
                # Área ya existe, obtener información
                logger.info(f"Área ya existe: {area_guid}")
                # Puedes hacer GET para obtener info
                return None  # o lanzar excepción específica
            elif e.response.status_code >= 500:
                # Error del servidor, reintentar
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Backoff exponencial
                    continue
                raise
            else:
                # Error del cliente, no reintentar
                raise
        except requests.RequestException as e:
            # Error de red, reintentar
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
```

---

## 🔄 Flujo Completo

```
┌─────────────────────────────────────────────────────────────┐
│  OTRO PROYECTO (API Externa)                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ 1. Usuario crea área en interfaz
                     │    - Nombre: "Sistema General de Regalías"
                     │    - Descripción: "..."
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Backend del Otro Proyecto                                   │
│                                                              │
│  ✓ Genera GUID: uuid.uuid4()                                │
│  ✓ Guarda en BD:                                            │
│    INSERT INTO areas (id, nombre, ...)                      │
│    VALUES ('a1b2c3d4-...', 'Sistema General...', ...)       │
│                                                              │
│  ✓ Llama a RAG API:                                         │
│    POST /api/v1/integration/areas                           │
│    {                                                        │
│      "area_guid": "a1b2c3d4-...",                          │
│      "nombre": "Sistema General de Regalías",              │
│      "descripcion": "..."                                   │
│    }                                                        │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ HTTP Request
       ↓
┌─────────────────────────────────────────────────────────────┐
│  SISTEMA RAG (Este Proyecto)                                 │
│                                                              │
│  1. Valida Request:                                         │
│     ✓ GUID válido (UUID v4)                                 │
│     ✓ Nombre no vacío                                       │
│     ✓ GUID no existe ya                                     │
│                                                              │
│  2. Genera Código Interno:                                  │
│     "Sistema General de Regalías"                           │
│     → "sistema_general_de_regalias"                         │
│     → "sgr" (si existe en config)                           │
│                                                              │
│  3. Crea Carpeta:                                           │
│     mkdir data/a1b2c3d4-e5f6-7890-abcd-ef1234567890/       │
│                                                              │
│  4. Guarda Mapeo:                                           │
│     config/area_guid_mapping.json:                          │
│     {                                                       │
│       "areas": {                                            │
│         "a1b2c3d4-...": {                                   │
│           "area_code": "sgr",                              │
│           "nombre": "...",                                  │
│           "folder_path": "data/a1b2c3d4-..."               │
│         }                                                   │
│       }                                                     │
│     }                                                       │
│                                                              │
│  5. (Opcional) Actualiza config/areas.json                 │
│                                                              │
│  6. Retorna Response:                                       │
│     {                                                       │
│       "area_code": "sgr",                                   │
│       "folder_path": "data/a1b2c3d4-...",                   │
│       ...                                                   │
│     }                                                       │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ HTTP Response (201 Created)
       ↓
┌─────────────────────────────────────────────────────────────┐
│  OTRO PROYECTO                                               │
│                                                              │
│  ✓ Recibe respuesta                                         │
│  ✓ (Opcional) Guarda area_code en BD:                      │
│    UPDATE areas SET rag_area_code = 'sgr'                   │
│    WHERE id = 'a1b2c3d4-...'                                │
│                                                              │
│  ✓ Área lista para recibir documentos                       │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Checklist de Implementación

- [ ] Crear `src/mapping/__init__.py`
- [ ] Crear `src/mapping/guid_mapper.py` con clase `GuidMapper`
- [ ] Crear modelos `CreateAreaRequest` y `CreateAreaResponse`
- [ ] Crear `api/routers/integration.py` con endpoint
- [ ] Registrar router en `api/main.py`
- [ ] Probar endpoint con cURL
- [ ] Integrar en el otro proyecto
- [ ] Manejar errores y casos edge
- [ ] Documentar en Swagger (`/docs`)

---

**Autor**: Sistema de Documentación  
**Última Actualización**: 2025-01-15


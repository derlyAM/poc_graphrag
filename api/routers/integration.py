"""
Endpoints de integración con API externa.
Gestiona áreas y documentos desde sistema externo.
"""
import re
import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, status, HTTPException, UploadFile, File, Form
from loguru import logger

from api.models.requests import CreateAreaRequest
from api.models.responses import StandardResponse, AreaData, ErrorResponse
from src.config import BASE_DIR, config

# File size limit (50 MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

router = APIRouter(prefix="/api/v1/integration", tags=["integration"])


def add_area_to_config(area_code: str, area_name: str) -> None:
    """
    Agrega un área a config/areas.json.
    
    Si el archivo no existe, lo crea con la estructura correcta.
    Si el área ya existe, no hace nada.
    
    Args:
        area_code: Código del área (normalizado)
        area_name: Nombre completo del área
    
    Raises:
        Exception: Si hay error al escribir el archivo
    """
    areas_file = BASE_DIR / "config" / "areas.json"
    areas_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Estructura por defecto del archivo
    default_structure = {
        "_comment": "Configuración de Áreas de Conocimiento",
        "_instructions": [
            "Para agregar una nueva área:",
            "1. Agregar entrada: 'codigo_area': 'Nombre Completo del Área'",
            "2. Guardar archivo (sin reiniciar servicios)",
            "3. Usar: python scripts/01_ingest_pdfs.py --area codigo_area",
            "",
            "NOTA: Si este archivo no existe, el sistema auto-detectará áreas desde Qdrant automáticamente."
        ],
        "areas": {}
    }
    
    # Cargar archivo existente o usar estructura por defecto
    if areas_file.exists():
        try:
            with open(areas_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Asegurar que existe la clave "areas"
                if "areas" not in data:
                    data["areas"] = {}
        except Exception as e:
            logger.warning(f"Error al leer areas.json, usando estructura por defecto: {e}")
            data = default_structure
    else:
        data = default_structure
    
    # Agregar área si no existe
    if area_code not in data["areas"]:
        data["areas"][area_code] = area_name
        logger.info(f"Agregando área '{area_code}' a config/areas.json")
    else:
        logger.info(f"Área '{area_code}' ya existe en config/areas.json, actualizando nombre")
        data["areas"][area_code] = area_name
    
    # Guardar archivo
    try:
        with open(areas_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.success(f"Archivo config/areas.json actualizado correctamente")
    except Exception as e:
        logger.error(f"Error al escribir areas.json: {e}")
        raise


def normalize_area_name(name: str) -> str:
    """
    Normaliza el nombre del área para usar como código de carpeta.
    
    Reglas:
    - Convertir a minúsculas
    - Reemplazar espacios y guiones con guiones bajos
    - Remover caracteres especiales
    - Remover acentos
    
    Args:
        name: Nombre original del área
    
    Returns:
        Nombre normalizado
    """
    # Convertir a minúsculas
    normalized = name.lower().strip()
    
    # Reemplazar espacios y guiones con guiones bajos
    normalized = normalized.replace(" ", "_")
    normalized = normalized.replace("-", "_")
    
    # Remover acentos
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n", "ü": "u"
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    
    # Remover caracteres especiales (solo permitir letras, números y guiones bajos)
    normalized = re.sub(r'[^a-z0-9_]', '', normalized)
    
    # Remover guiones bajos múltiples
    normalized = re.sub(r'_+', '_', normalized)
    
    # Remover guiones bajos al inicio y final
    normalized = normalized.strip('_')
    
    # Validar que no esté vacío
    if not normalized:
        raise ValueError("No se pudo generar un nombre válido después de la normalización")
    
    return normalized


@router.post(
    "/areas",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear área",
    description="""
    Crea una nueva área de conocimiento desde API externa.
    
    El sistema:
    1. Normaliza el nombre del área (minúsculas, guiones bajos, sin caracteres especiales)
    2. Crea la carpeta en `data/{nombre_normalizado}/`
    3. Agrega el área a `config/areas.json` para que esté disponible para ingesta
    4. Valida que el nombre no tenga espacios ni caracteres especiales (los normaliza si los tiene)
    5. Retorna información del área creada
    
    **Ejemplo**: "Desarrollo de Especies" → "desarrollo_de_especies"
    
    **Nota**: El área queda lista para ingesta inmediatamente después de crearse.
    """,
    responses={
        201: {
            "description": "Área creada exitosamente",
            "model": StandardResponse
        },
        400: {
            "description": "Request inválido",
            "model": ErrorResponse
        },
        409: {
            "description": "Área ya existe",
            "model": ErrorResponse
        },
        500: {
            "description": "Error interno del servidor",
            "model": ErrorResponse
        }
    }
)
async def create_area(request: CreateAreaRequest) -> StandardResponse:
    """
    Crear nueva área de conocimiento.
    
    Este endpoint es llamado por la API externa cuando se crea una nueva área.
    El sistema RAG:
    1. Normaliza el nombre del área
    2. Crea la carpeta para almacenar documentos
    3. Agrega el área a config/areas.json para que esté disponible para ingesta
    4. Valida que no exista ya
    
    Args:
        request: Request con name y description
    
    Returns:
        StandardResponse con información del área creada
    
    Raises:
        HTTPException: Si hay error en la creación
    """
    logger.info(f"Crear área solicitada: name={request.name}")
    
    try:
        # Normalizar nombre del área
        area_code = normalize_area_name(request.name)
        logger.info(f"Nombre normalizado: '{request.name}' → '{area_code}'")
        
        # Crear ruta de carpeta
        folder_path = BASE_DIR / "data" / area_code
        
        # Verificar si la carpeta ya existe
        if folder_path.exists() and folder_path.is_dir():
            logger.warning(f"Área ya existe: {area_code}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "statusCode": 409,
                    "message": f"El área '{area_code}' ya existe",
                    "data": {
                        "area_code": area_code,
                        "folder_path": str(folder_path.relative_to(BASE_DIR))
                    }
                }
            )
        
        # Crear carpeta
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            logger.success(f"Carpeta creada: {folder_path}")
        except Exception as e:
            logger.error(f"Error al crear carpeta: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "statusCode": 500,
                    "message": f"Error al crear carpeta: {str(e)}",
                    "data": {}
                }
            )
        
        # Agregar área a config/areas.json
        try:
            add_area_to_config(area_code, request.name)
        except Exception as e:
            logger.warning(f"Error al agregar área a config/areas.json: {e}")
            # No fallar la creación si hay error al escribir el JSON
            # El área ya está creada en el sistema de archivos
            logger.warning("El área fue creada pero no se pudo actualizar config/areas.json. Puede agregarla manualmente.")
        
        # Preparar datos de respuesta
        area_data = AreaData(
            area_code=area_code,
            name=request.name,
            description=request.description,
            folder_path=str(folder_path.relative_to(BASE_DIR)),
            created_at=datetime.now().isoformat()
        )
        
        logger.success(f"Área creada exitosamente: {area_code}")
        
        return StandardResponse(
            statusCode=201,
            message="Área creada exitosamente",
            data=area_data.model_dump()
        )
    
    except HTTPException:
        # Re-lanzar excepciones HTTP
        raise
    
    except ValueError as e:
        # Error de validación
        logger.error(f"Error de validación: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "statusCode": 400,
                "message": str(e),
                "data": {}
            }
        )
    
    except Exception as e:
        # Error inesperado
        logger.error(f"Error inesperado al crear área: {e}")
        logger.exception("Traceback completo:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "statusCode": 500,
                "message": f"Error interno al crear área: {str(e)}",
                "data": {}
            }
        )


@router.post(
    "/documents",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cargar documento PDF",
    description="""
    Carga un documento PDF en el área especificada.
    
    El sistema:
    1. Valida que el área exista
    2. Valida que el archivo sea un PDF válido
    3. Genera el nombre del archivo:
       - Si se proporciona `document_name`: se normaliza ese nombre
       - Si NO se proporciona: se usa el nombre del archivo normalizado
         (minúsculas, sin caracteres especiales, espacios/guiones → guiones bajos)
    4. Guarda el PDF en la carpeta `data/{area_code}/`
    5. Retorna información del documento guardado
    
    **Ejemplo de normalización automática**:
    - Archivo: "Mi Documento-2024.pdf" → Guardado como: "mi_documento_2024.pdf"
    - Archivo: "Informe Final (v2).pdf" → Guardado como: "informe_final_v2.pdf"
    
    **Nota**: El documento se guarda pero NO se ingesta automáticamente.
    Para ingestar el documento, usar el endpoint de ingesta.
    """,
    responses={
        201: {
            "description": "Documento guardado exitosamente",
            "model": StandardResponse
        },
        400: {
            "description": "Request inválido",
            "model": ErrorResponse
        },
        404: {
            "description": "Área no encontrada",
            "model": ErrorResponse
        },
        413: {
            "description": "Archivo demasiado grande",
            "model": ErrorResponse
        },
        500: {
            "description": "Error interno del servidor",
            "model": ErrorResponse
        }
    }
)
async def upload_document(
    file: UploadFile = File(..., description="Archivo PDF a cargar"),
    area_code: str = Form(..., description="Código del área (nombre normalizado)"),
    document_name: Optional[str] = Form(None, description="Nombre opcional para el documento (sin extensión)")
) -> StandardResponse:
    """
    Cargar documento PDF en un área.
    
    Este endpoint guarda el PDF en la carpeta del área especificada.
    El documento NO se ingesta automáticamente.
    
    Args:
        file: Archivo PDF a cargar
        area_code: Código del área (nombre normalizado, ej: "desarrollo_de_especies")
        document_name: Nombre opcional para el documento (sin extensión .pdf).
                      Si no se proporciona, se usa el nombre del archivo normalizado:
                      - Minúsculas
                      - Sin caracteres especiales
                      - Espacios y guiones convertidos a guiones bajos
                      - Ejemplo: "Mi Documento-2024.pdf" → "mi_documento_2024.pdf"
    
    Returns:
        StandardResponse con información del documento guardado
    
    Raises:
        HTTPException: Si hay error en la carga
    """
    logger.info(f"Cargar documento solicitado: {file.filename} (área: {area_code})")
    
    try:
        # Validar que el área exista
        area_folder = BASE_DIR / "data" / area_code
        if not area_folder.exists() or not area_folder.is_dir():
            logger.warning(f"Área no encontrada: {area_code}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "statusCode": 404,
                    "message": f"El área '{area_code}' no existe. Cree el área primero.",
                    "data": {}
                }
            )
        
        # Validar tipo de archivo
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "statusCode": 400,
                    "message": "El archivo debe tener un nombre",
                    "data": {}
                }
            )
        
        # Validar extensión PDF
        file_extension = Path(file.filename).suffix.lower()
        if file_extension != ".pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "statusCode": 400,
                    "message": f"El archivo debe ser un PDF. Extensión recibida: {file_extension}",
                    "data": {}
                }
            )
        
        # Validar Content-Type
        content_type = file.content_type
        if content_type and content_type not in ["application/pdf", "application/octet-stream"]:
            logger.warning(f"Content-Type inesperado: {content_type}")
            # No fallar, solo advertir
        
        # Leer contenido del archivo
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validar tamaño
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "statusCode": 413,
                    "message": f"El archivo es demasiado grande. Tamaño máximo: {MAX_FILE_SIZE / (1024*1024):.0f} MB",
                    "data": {}
                }
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "statusCode": 400,
                    "message": "El archivo está vacío",
                    "data": {}
                }
            )
        
        # Generar nombre del archivo
        if document_name:
            # Si se proporciona nombre, normalizarlo
            doc_name_normalized = normalize_area_name(document_name)
            filename = f"{doc_name_normalized}.pdf"
        else:
            # Si no se proporciona nombre, usar el nombre del archivo normalizado
            # Se quita la extensión y se normaliza: minúsculas, sin caracteres especiales, con guiones bajos
            original_name = Path(file.filename).stem  # Nombre sin extensión
            doc_name_normalized = normalize_area_name(original_name)
            filename = f"{doc_name_normalized}.pdf"
            logger.info(f"Nombre de documento no proporcionado, usando nombre normalizado del archivo: '{original_name}' → '{doc_name_normalized}'")
        
        # Ruta completa del archivo
        file_path = area_folder / filename
        
        # Verificar si el archivo ya existe
        if file_path.exists():
            logger.warning(f"El archivo ya existe: {filename}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "statusCode": 409,
                    "message": f"El documento '{filename}' ya existe en el área '{area_code}'",
                    "data": {
                        "filename": filename,
                        "area_code": area_code,
                        "file_path": str(file_path.relative_to(BASE_DIR))
                    }
                }
            )
        
        # Guardar archivo
        try:
            with open(file_path, "wb") as f:
                f.write(file_content)
            logger.success(f"Documento guardado: {file_path}")
        except Exception as e:
            logger.error(f"Error al guardar archivo: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "statusCode": 500,
                    "message": f"Error al guardar archivo: {str(e)}",
                    "data": {}
                }
            )
        
        # Preparar datos de respuesta
        document_data = {
            "filename": filename,
            "original_filename": file.filename,
            "area_code": area_code,
            "file_path": str(file_path.relative_to(BASE_DIR)),
            "file_size": file_size,
            "uploaded_at": datetime.now().isoformat()
        }
        
        logger.success(f"Documento cargado exitosamente: {filename} en área {area_code}")
        
        return StandardResponse(
            statusCode=201,
            message="Documento guardado exitosamente",
            data=document_data
        )
    
    except HTTPException:
        # Re-lanzar excepciones HTTP
        raise
    
    except ValueError as e:
        # Error de validación
        logger.error(f"Error de validación: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "statusCode": 400,
                "message": str(e),
                "data": {}
            }
        )
    
    except Exception as e:
        # Error inesperado
        logger.error(f"Error inesperado al cargar documento: {e}")
        logger.exception("Traceback completo:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "statusCode": 500,
                "message": f"Error interno al cargar documento: {str(e)}",
                "data": {}
            }
        )


@router.post(
    "/ingest",
    response_model=StandardResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingerir documentos de un área",
    description="""
    Inicia el proceso de ingesta de todos los documentos PDF de un área específica.
    
    El sistema:
    1. Valida que el área exista
    2. Ejecuta el script de ingesta en background (no bloquea el endpoint)
    3. Retorna inmediatamente con información del proceso iniciado
    
    **Nota**: Este proceso es asíncrono y puede tardar varios minutos dependiendo
    de la cantidad y tamaño de los documentos. El endpoint retorna inmediatamente
    sin esperar a que termine la ingesta.
    
    **Parámetros opcionales**:
    - `recreate`: Si es `true`, recrea la colección (BORRA datos existentes)
    - `force_reprocess`: Si es `true`, fuerza el reprocesamiento de todos los PDFs
    """,
    responses={
        202: {
            "description": "Proceso de ingesta iniciado",
            "model": StandardResponse
        },
        400: {
            "description": "Request inválido",
            "model": ErrorResponse
        },
        404: {
            "description": "Área no encontrada",
            "model": ErrorResponse
        },
        500: {
            "description": "Error interno del servidor",
            "model": ErrorResponse
        }
    }
)
async def ingest_area_documents(
    area_code: str = Form(..., description="Código del área (nombre normalizado)"),
    recreate: bool = Form(False, description="Recrear colección (BORRA datos existentes)"),
    force_reprocess: bool = Form(False, description="Forzar reprocesamiento de todos los PDFs")
) -> StandardResponse:
    """
    Ingerir todos los documentos PDF de un área.
    
    Este endpoint ejecuta el script de ingesta en background para procesar
    todos los PDFs del área especificada. El proceso es asíncrono y no bloquea
    el endpoint.
    
    Args:
        area_code: Código del área (nombre normalizado, ej: "desarrollo_de_especies")
        recreate: Si es True, recrea la colección (elimina datos existentes)
        force_reprocess: Si es True, fuerza el reprocesamiento de todos los PDFs
    
    Returns:
        StandardResponse con información del proceso iniciado
    
    Raises:
        HTTPException: Si hay error al iniciar el proceso
    """
    logger.info(f"Iniciar ingesta solicitada para área: {area_code}")
    
    try:
        # Validar que el área exista
        area_folder = BASE_DIR / "data" / area_code
        if not area_folder.exists() or not area_folder.is_dir():
            logger.warning(f"Área no encontrada: {area_code}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "statusCode": 404,
                    "message": f"El área '{area_code}' no existe. Cree el área primero.",
                    "data": {}
                }
            )
        
        # Validar que el área sea válida según el sistema
        try:
            from src.config import validate_area
            validated_area = validate_area(area_code)
        except ValueError as e:
            logger.error(f"Área inválida: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "statusCode": 400,
                    "message": f"Área inválida: {str(e)}",
                    "data": {}
                }
            )
        
        # Verificar que haya documentos en el área
        pdf_files = list(area_folder.glob("*.pdf"))
        if not pdf_files:
            logger.warning(f"No hay documentos PDF en el área: {area_code}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "statusCode": 400,
                    "message": f"No hay documentos PDF en el área '{area_code}'. Cargue documentos primero.",
                    "data": {
                        "area_code": area_code,
                        "folder_path": str(area_folder.relative_to(BASE_DIR))
                    }
                }
            )
        
        # Construir comando para ejecutar el script
        script_path = BASE_DIR / "scripts" / "01_ingest_pdfs.py"
        
        if not script_path.exists():
            logger.error(f"Script de ingesta no encontrado: {script_path}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "statusCode": 500,
                    "message": "Script de ingesta no encontrado",
                    "data": {}
                }
            )
        
        # Construir argumentos del comando
        cmd = [
            sys.executable,  # Python interpreter
            str(script_path),
            "--area", validated_area,
            "--data-dir", str(area_folder)
        ]
        
        if recreate:
            cmd.append("--recreate")
            logger.warning(f"⚠️  MODO RECREATE: Se eliminarán datos existentes de la colección")
        
        if force_reprocess:
            cmd.append("--force-reprocess")
        else:
            cmd.append("--skip-existing")
        
        # Generar ID único para el proceso
        process_id = f"ingest_{area_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Preparar archivo de log para este proceso
        log_file = BASE_DIR / "logs" / f"ingest_{area_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Ejecutar script en background (no bloquea)
        try:
            # Abrir archivo de log
            with open(log_file, "w", encoding="utf-8") as log_f:
                # Iniciar proceso en background
                process = subprocess.Popen(
                    cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,  # Redirigir stderr a stdout
                    cwd=str(BASE_DIR),
                    env=os.environ.copy()
                )
            
            logger.success(f"Proceso de ingesta iniciado: PID={process.pid}, ID={process_id}")
            logger.info(f"Comando ejecutado: {' '.join(cmd)}")
            logger.info(f"Log guardado en: {log_file}")
            
        except Exception as e:
            logger.error(f"Error al iniciar proceso de ingesta: {e}")
            logger.exception("Traceback completo:")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "statusCode": 500,
                    "message": f"Error al iniciar proceso de ingesta: {str(e)}",
                    "data": {}
                }
            )
        
        # Preparar datos de respuesta
        ingestion_data = {
            "process_id": process_id,
            "area_code": validated_area,
            "pid": process.pid,
            "status": "running",
            "total_documents": len(pdf_files),
            "log_file": str(log_file.relative_to(BASE_DIR)),
            "started_at": datetime.now().isoformat(),
            "recreate": recreate,
            "force_reprocess": force_reprocess
        }
        
        logger.success(f"Proceso de ingesta iniciado exitosamente: {process_id}")
        
        return StandardResponse(
            statusCode=202,
            message=f"Proceso de ingesta iniciado para área '{validated_area}'. Procesando {len(pdf_files)} documento(s).",
            data=ingestion_data
        )
    
    except HTTPException:
        # Re-lanzar excepciones HTTP
        raise
    
    except ValueError as e:
        # Error de validación
        logger.error(f"Error de validación: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "statusCode": 400,
                "message": str(e),
                "data": {}
            }
        )
    
    except Exception as e:
        # Error inesperado
        logger.error(f"Error inesperado al iniciar ingesta: {e}")
        logger.exception("Traceback completo:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "statusCode": 500,
                "message": f"Error interno al iniciar ingesta: {str(e)}",
                "data": {}
            }
        )


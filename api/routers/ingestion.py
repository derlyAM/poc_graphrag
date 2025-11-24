"""
Document ingestion endpoints.
Upload and process new documents.
"""
import os
import json
import tempfile
from pathlib import Path
from typing import Optional, List
from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    Query
)
from loguru import logger

from api.models.responses import (
    IngestionTaskResponse,
    IngestionStatusResponse,
    ErrorResponse
)
from api.dependencies import get_pipeline
from api.utils.task_manager import (
    get_task_manager,
    TaskManager,
    TaskPhase,
    TaskStatus
)
from src.pipeline import RAGPipeline
from src.config import config, VALID_AREAS
from src.ingest.pdf_extractor import PDFExtractor
from src.ingest.chunker import chunk_documents
from src.ingest.vectorizer import Vectorizer

router = APIRouter(prefix="/api/v1/documents/ingest", tags=["ingestion"])

# File size limit (50 MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


async def process_document_ingestion(
    task_id: str,
    pdf_path: Path,
    area: str,
    documento_id: str,
    metadata: dict
):
    """
    Background task to process document ingestion.

    This runs asynchronously after the upload endpoint returns.

    Args:
        task_id: Task ID
        pdf_path: Path to uploaded PDF
        area: Document area
        documento_id: Document ID
        metadata: Document metadata
    """
    task_manager = get_task_manager()
    task = task_manager.get_task(task_id)

    if not task:
        logger.error(f"Task {task_id} not found in background processing")
        return

    try:
        task.start()

        # PHASE 1: Extract PDF
        logger.info(f"[{task_id}] Phase 1: Extracting PDF")
        task.update_phase(TaskPhase.EXTRACTING, 10)

        extractor = PDFExtractor()
        document = extractor.extract_pdf(pdf_path)

        # Add metadata
        document["metadata"]["area"] = area
        document["metadata"]["documento_id"] = documento_id

        # Merge user metadata
        if metadata:
            document["metadata"].update(metadata)

        task.update_phase(TaskPhase.EXTRACTING, 30)
        logger.info(f"[{task_id}] Extraction complete: {len(document['content'])} chars")

        # PHASE 2: Chunk documents
        logger.info(f"[{task_id}] Phase 2: Chunking document")
        task.update_phase(TaskPhase.CHUNKING, 40)

        chunks = chunk_documents(
            [document],
            chunk_size=config.retrieval.chunk_size
        )

        task.update_phase(TaskPhase.CHUNKING, 60)
        logger.info(f"[{task_id}] Chunking complete: {len(chunks)} chunks")

        # PHASE 3: Vectorize and upload
        logger.info(f"[{task_id}] Phase 3: Vectorizing and uploading")
        task.update_phase(TaskPhase.VECTORIZING, 70)

        # Initialize vectorizer (do NOT recreate collection)
        vectorizer = Vectorizer(use_hybrid_search=False)

        # Ensure collection exists
        vectorizer.create_collection(recreate=False)

        task.update_phase(TaskPhase.VECTORIZING, 80)

        # Generate embeddings and upload
        vectorizer.vectorize_and_upload(chunks)

        task.update_phase(TaskPhase.VECTORIZING, 95)

        # Complete task
        task.complete(
            chunks_created=len(chunks),
            vectors_uploaded=len(chunks),
            total_cost=vectorizer.total_cost
        )

        logger.info(
            f"[{task_id}] Ingestion completed successfully: "
            f"{len(chunks)} chunks, ${vectorizer.total_cost:.6f}"
        )

    except Exception as e:
        logger.error(f"[{task_id}] Ingestion failed: {e}")
        logger.exception("Full traceback:")
        task.fail(
            error=str(e),
            error_code="INGESTION_FAILED"
        )

    finally:
        # Cleanup temporary file
        try:
            if pdf_path.exists():
                pdf_path.unlink()
                logger.debug(f"[{task_id}] Temporary file cleaned up")
        except Exception as e:
            logger.warning(f"[{task_id}] Failed to cleanup temp file: {e}")


@router.post(
    "",
    response_model=IngestionTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest new document",
    description="Upload and process a new PDF document",
    responses={
        202: {"description": "Document ingestion started"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        413: {"model": ErrorResponse, "description": "File too large"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to ingest"),
    area: str = Form(..., description="Document area (sgr, inteligencia_artificial, general)"),
    documento_id: Optional[str] = Form(None, description="Optional document ID"),
    metadata: Optional[str] = Form(None, description="Optional metadata as JSON string"),
    pipeline: RAGPipeline = Depends(get_pipeline)
) -> IngestionTaskResponse:
    """
    Upload and ingest a new document.

    The document will be processed asynchronously. Use the returned task_id
    to check the processing status.

    Args:
        background_tasks: FastAPI background tasks
        file: PDF file to upload
        area: Document area
        documento_id: Optional document ID
        metadata: Optional metadata as JSON string
        pipeline: Injected RAGPipeline

    Returns:
        IngestionTaskResponse with task ID and status URL

    Raises:
        HTTPException: If validation fails or upload errors
    """
    logger.info(f"Document ingestion requested: {file.filename} (area: {area})")

    try:
        # Validate area
        if area not in VALID_AREAS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": f"Invalid area. Must be one of: {', '.join(VALID_AREAS.keys())}",
                    "error_code": "INVALID_AREA"
                }
            )

        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": "Only PDF files are supported",
                    "error_code": "INVALID_FILE_TYPE"
                }
            )

        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error": "Invalid metadata JSON format",
                        "error_code": "INVALID_METADATA"
                    }
                )

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "success": False,
                    "error": f"File too large. Max size: {MAX_FILE_SIZE / (1024*1024):.0f} MB",
                    "error_code": "FILE_TOO_LARGE"
                }
            )

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": "File is empty",
                    "error_code": "EMPTY_FILE"
                }
            )

        # Create task
        task_manager = get_task_manager()
        task = task_manager.create_task(
            area=area,
            filename=file.filename,
            file_size=file_size,
            documento_id=documento_id,
            metadata=parsed_metadata
        )

        # Save file to temporary location
        temp_dir = Path(tempfile.gettempdir()) / "rag_ingestion"
        temp_dir.mkdir(exist_ok=True)

        temp_file = temp_dir / f"{task.task_id}_{file.filename}"

        with open(temp_file, "wb") as f:
            f.write(file_content)

        logger.info(f"File saved to temporary location: {temp_file}")

        # Schedule background processing
        background_tasks.add_task(
            process_document_ingestion,
            task_id=task.task_id,
            pdf_path=temp_file,
            area=area,
            documento_id=task.documento_id,
            metadata=parsed_metadata
        )

        # Estimate processing time (simple heuristic: ~1 second per 20KB)
        estimated_time = int(file_size / (20 * 1024)) + 30  # Minimum 30 seconds

        logger.info(f"Ingestion task created: {task.task_id}")

        return IngestionTaskResponse(
            task_id=task.task_id,
            status="pending",
            message="Document ingestion started",
            estimated_time_seconds=estimated_time,
            status_url=f"/api/v1/documents/ingest/{task.task_id}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error in document ingestion: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": f"Failed to start ingestion: {str(e)}",
                "error_code": "INGESTION_START_FAILED"
            }
        )


@router.get(
    "/{task_id}",
    response_model=IngestionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get ingestion status",
    description="Check the status of an ingestion task",
    responses={
        200: {"description": "Task status"},
        404: {"model": ErrorResponse, "description": "Task not found"}
    }
)
async def get_ingestion_status(
    task_id: str
) -> IngestionStatusResponse:
    """
    Get the status of an ingestion task.

    Args:
        task_id: Task ID

    Returns:
        IngestionStatusResponse with current status

    Raises:
        HTTPException: If task not found
    """
    logger.debug(f"Ingestion status requested: {task_id}")

    task_manager = get_task_manager()
    task = task_manager.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": f"Task '{task_id}' not found",
                "error_code": "TASK_NOT_FOUND"
            }
        )

    # Convert task to response model
    task_dict = task.to_dict()

    return IngestionStatusResponse(**task_dict)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List ingestion tasks",
    description="List all ingestion tasks with optional filters"
)
async def list_ingestion_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    area: Optional[str] = Query(None, description="Filter by area")
):
    """
    List all ingestion tasks.

    Args:
        status: Optional status filter
        area: Optional area filter

    Returns:
        List of tasks
    """
    logger.debug("Ingestion tasks list requested")

    task_manager = get_task_manager()
    tasks = task_manager.list_tasks(status=status, area=area)

    # Convert to dict
    tasks_data = [task.to_dict() for task in tasks]

    # Get statistics
    stats = task_manager.get_stats()

    return {
        "tasks": tasks_data,
        "total": len(tasks_data),
        "by_status": stats["by_status"]
    }


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_200_OK,
    summary="Cancel ingestion task",
    description="Cancel a pending or processing ingestion task"
)
async def cancel_ingestion_task(
    task_id: str
):
    """
    Cancel an ingestion task.

    Note: This only marks the task as cancelled. If processing has already
    started, it may still complete.

    Args:
        task_id: Task ID

    Returns:
        Success message

    Raises:
        HTTPException: If task not found
    """
    logger.warning(f"Ingestion task cancellation requested: {task_id}")

    task_manager = get_task_manager()
    task = task_manager.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": f"Task '{task_id}' not found",
                "error_code": "TASK_NOT_FOUND"
            }
        )

    # Only cancel if not completed or failed
    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": f"Cannot cancel task with status '{task.status}'",
                "error_code": "CANNOT_CANCEL"
            }
        )

    task.cancel()

    return {
        "success": True,
        "message": "Ingestion task cancelled",
        "task_id": task_id,
        "status": "cancelled"
    }

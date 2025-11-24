"""
Task manager for ingestion tasks.
In-memory storage for background task tracking (MVP).
"""
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from enum import Enum
from loguru import logger
import asyncio


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPhase(str, Enum):
    """Processing phase enumeration."""
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    VECTORIZING = "vectorizing"
    COMPLETED = "completed"


class IngestionTask:
    """
    Represents an ingestion task.

    Tracks the state and progress of a document ingestion operation.
    """

    def __init__(
        self,
        task_id: str,
        area: str,
        filename: str,
        file_size: int,
        documento_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        self.task_id = task_id
        self.status = TaskStatus.PENDING
        self.area = area
        self.documento_id = documento_id
        self.filename = filename
        self.file_size = file_size
        self.metadata = metadata or {}

        # Timestamps
        self.uploaded_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.failed_at: Optional[datetime] = None

        # Progress tracking
        self.current_phase = TaskPhase.EXTRACTING
        self.progress_percent = 0
        self.phases_status: Dict[str, str] = {
            TaskPhase.EXTRACTING: "pending",
            TaskPhase.CHUNKING: "pending",
            TaskPhase.VECTORIZING: "pending"
        }

        # Results
        self.chunks_created: Optional[int] = None
        self.vectors_uploaded: Optional[int] = None
        self.total_cost: Optional[float] = None
        self.processing_time_seconds: Optional[float] = None

        # Error handling
        self.error: Optional[str] = None
        self.error_code: Optional[str] = None

    def start(self):
        """Mark task as started."""
        self.status = TaskStatus.PROCESSING
        self.started_at = datetime.now()
        logger.info(f"Task {self.task_id} started")

    def update_phase(self, phase: TaskPhase, progress: int):
        """
        Update current phase and progress.

        Args:
            phase: Current processing phase
            progress: Progress percentage (0-100)
        """
        self.current_phase = phase
        self.progress_percent = progress

        # Update phase status
        for p in TaskPhase:
            if p == phase:
                self.phases_status[p] = "in_progress"
            elif list(TaskPhase).index(p) < list(TaskPhase).index(phase):
                self.phases_status[p] = "completed"
            else:
                self.phases_status[p] = "pending"

        logger.debug(f"Task {self.task_id}: {phase} - {progress}%")

    def complete(
        self,
        chunks_created: int,
        vectors_uploaded: int,
        total_cost: float
    ):
        """
        Mark task as completed.

        Args:
            chunks_created: Number of chunks created
            vectors_uploaded: Number of vectors uploaded
            total_cost: Total cost in USD
        """
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.progress_percent = 100
        self.current_phase = TaskPhase.COMPLETED

        # Mark all phases as completed
        for phase in self.phases_status:
            self.phases_status[phase] = "completed"

        # Store results
        self.chunks_created = chunks_created
        self.vectors_uploaded = vectors_uploaded
        self.total_cost = total_cost

        if self.started_at:
            self.processing_time_seconds = (
                self.completed_at - self.started_at
            ).total_seconds()

        logger.info(
            f"Task {self.task_id} completed: "
            f"{chunks_created} chunks, ${total_cost:.6f}"
        )

    def fail(self, error: str, error_code: str = "UNKNOWN_ERROR"):
        """
        Mark task as failed.

        Args:
            error: Error message
            error_code: Machine-readable error code
        """
        self.status = TaskStatus.FAILED
        self.failed_at = datetime.now()
        self.error = error
        self.error_code = error_code
        logger.error(f"Task {self.task_id} failed: {error}")

    def cancel(self):
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        logger.warning(f"Task {self.task_id} cancelled")

    def to_dict(self) -> Dict:
        """
        Convert task to dictionary for API response.

        Returns:
            Dictionary representation
        """
        data = {
            "task_id": self.task_id,
            "status": self.status,
            "area": self.area,
            "documento_id": self.documento_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "uploaded_at": self.uploaded_at,
        }

        # Add timestamps based on status
        if self.started_at:
            data["started_at"] = self.started_at
            elapsed = (datetime.now() - self.started_at).total_seconds()
            data["elapsed_seconds"] = elapsed

        if self.completed_at:
            data["completed_at"] = self.completed_at

        if self.failed_at:
            data["failed_at"] = self.failed_at

        # Add progress if processing
        if self.status == TaskStatus.PROCESSING:
            data["progress"] = {
                "percent": self.progress_percent,
                "current_phase": self.current_phase,
                "phases": self.phases_status
            }

            # Estimate remaining time (simple heuristic)
            if self.started_at and self.progress_percent > 0:
                elapsed = (datetime.now() - self.started_at).total_seconds()
                estimated_total = elapsed / (self.progress_percent / 100)
                data["estimated_remaining_seconds"] = int(
                    estimated_total - elapsed
                )

        # Add results if completed
        if self.status == TaskStatus.COMPLETED:
            data["results"] = {
                "chunks_created": self.chunks_created,
                "vectors_uploaded": self.vectors_uploaded,
                "total_cost": self.total_cost,
                "processing_time_seconds": self.processing_time_seconds
            }
            data["documento_metadata"] = self.metadata

        # Add error if failed
        if self.status == TaskStatus.FAILED:
            data["error"] = self.error
            data["error_code"] = self.error_code

        return data


class TaskManager:
    """
    Singleton manager for ingestion tasks.

    Provides in-memory storage and retrieval of task state.
    """

    _instance: Optional['TaskManager'] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tasks: Dict[str, IngestionTask] = {}
            logger.info("TaskManager initialized")
        return cls._instance

    def create_task(
        self,
        area: str,
        filename: str,
        file_size: int,
        documento_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> IngestionTask:
        """
        Create a new ingestion task.

        Args:
            area: Document area
            filename: Original filename
            file_size: File size in bytes
            documento_id: Optional document ID
            metadata: Optional metadata

        Returns:
            Created task
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        # Generate documento_id if not provided
        if not documento_id:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            documento_id = f"doc_{timestamp}"

        task = IngestionTask(
            task_id=task_id,
            area=area,
            filename=filename,
            file_size=file_size,
            documento_id=documento_id,
            metadata=metadata
        )

        self._tasks[task_id] = task
        logger.info(f"Task created: {task_id}")

        return task

    def get_task(self, task_id: str) -> Optional[IngestionTask]:
        """
        Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None if not found
        """
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        area: Optional[str] = None
    ) -> List[IngestionTask]:
        """
        List all tasks with optional filters.

        Args:
            status: Optional status filter
            area: Optional area filter

        Returns:
            List of tasks
        """
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        if area:
            tasks = [t for t in tasks if t.area == area]

        # Sort by upload time (newest first)
        tasks.sort(key=lambda t: t.uploaded_at, reverse=True)

        return tasks

    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False if not found
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            logger.info(f"Task deleted: {task_id}")
            return True
        return False

    def get_stats(self) -> Dict:
        """
        Get task statistics.

        Returns:
            Statistics dictionary
        """
        tasks = list(self._tasks.values())

        by_status = {}
        for status in TaskStatus:
            by_status[status] = len([t for t in tasks if t.status == status])

        return {
            "total_tasks": len(tasks),
            "by_status": by_status
        }


# Global instance
_task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """
    Get the global task manager instance.

    Returns:
        TaskManager singleton
    """
    return _task_manager

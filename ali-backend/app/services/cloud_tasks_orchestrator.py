"""
Cloud Tasks Orchestration Service
Spec v1.2 §4.2: Asynchronous Operations via Cloud Tasks

Provides:
1. Task queue creation and management
2. Async job dispatching for long-running operations
3. Retry policies and dead-letter handling
4. Progress tracking integration
"""
import os
import json
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

try:
    from google.cloud import tasks_v2
    from google.protobuf import timestamp_pb2, duration_pb2
    TASKS_AVAILABLE = True
except ImportError:
    TASKS_AVAILABLE = False
    tasks_v2 = None

try:
    from google.cloud import firestore
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    firestore = None

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Supported task types for orchestration."""
    TUTORIAL_GENERATION = "tutorial_generation"
    AD_CREATIVE_GENERATION = "ad_creative_generation"
    PREDICTION_COMPUTE = "prediction_compute"
    ASSET_PROCESSING = "asset_processing"
    WEB_RESEARCH = "web_research"
    ANALYTICS_SYNC = "analytics_sync"


class TaskStatus(str, Enum):
    """Task execution statuses."""
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class TaskConfig:
    """Configuration for a task queue."""
    queue_name: str
    max_dispatches_per_second: float = 10.0
    max_concurrent_dispatches: int = 5
    max_attempts: int = 3
    min_backoff_seconds: int = 10
    max_backoff_seconds: int = 300


# Default queue configurations
QUEUE_CONFIGS = {
    TaskType.TUTORIAL_GENERATION: TaskConfig(
        queue_name="tutorial-generation-queue",
        max_dispatches_per_second=2.0,  # Rate limit for AI calls
        max_concurrent_dispatches=3,
        max_attempts=2,
    ),
    TaskType.AD_CREATIVE_GENERATION: TaskConfig(
        queue_name="ad-creative-queue",
        max_dispatches_per_second=5.0,
        max_concurrent_dispatches=5,
        max_attempts=3,
    ),
    TaskType.PREDICTION_COMPUTE: TaskConfig(
        queue_name="prediction-queue",
        max_dispatches_per_second=10.0,
        max_concurrent_dispatches=10,
        max_attempts=2,
    ),
    TaskType.ASSET_PROCESSING: TaskConfig(
        queue_name="asset-processing-queue",
        max_dispatches_per_second=20.0,
        max_concurrent_dispatches=20,
        max_attempts=3,
    ),
    TaskType.WEB_RESEARCH: TaskConfig(
        queue_name="web-research-queue",
        max_dispatches_per_second=5.0,
        max_concurrent_dispatches=5,
        max_attempts=2,
    ),
    TaskType.ANALYTICS_SYNC: TaskConfig(
        queue_name="analytics-sync-queue",
        max_dispatches_per_second=5.0,
        max_concurrent_dispatches=5,
        max_attempts=3,
    ),
}


class CloudTasksOrchestrator:
    """
    Cloud Tasks orchestration for async job management.
    Spec v1.2 §4.2: All AI-heavy operations use Cloud Tasks.
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        service_url: Optional[str] = None
    ):
        self.project_id = project_id or os.getenv(
            "GOOGLE_CLOUD_PROJECT", 
            "ali-platform-prod-73019"
        )
        self.location = location or os.getenv(
            "GOOGLE_CLOUD_REGION", 
            "us-central1"
        )
        self.service_url = service_url or os.getenv(
            "CLOUD_RUN_SERVICE_URL",
            f"https://ali-backend-{self.project_id}.{self.location}.run.app"
        )
        
        self.client = None
        self.db = None
        
        if TASKS_AVAILABLE:
            try:
                self.client = tasks_v2.CloudTasksClient()
            except Exception as e:
                logger.warning(f"⚠️ Cloud Tasks client init failed: {e}")
        
        if FIRESTORE_AVAILABLE:
            try:
                self.db = firestore.Client()
            except Exception as e:
                logger.warning(f"⚠️ Firestore client init failed: {e}")
    
    def _get_queue_path(self, queue_name: str) -> str:
        """Get full queue path."""
        return f"projects/{self.project_id}/locations/{self.location}/queues/{queue_name}"
    
    def ensure_queue_exists(self, task_type: TaskType) -> bool:
        """Create queue if it doesn't exist."""
        if not self.client:
            logger.warning("⚠️ Cloud Tasks client not available")
            return False
        
        config = QUEUE_CONFIGS.get(task_type)
        if not config:
            logger.error(f"❌ No config for task type: {task_type}")
            return False
        
        queue_path = self._get_queue_path(config.queue_name)
        parent = f"projects/{self.project_id}/locations/{self.location}"
        
        try:
            self.client.get_queue(name=queue_path)
            logger.info(f"✅ Queue exists: {config.queue_name}")
            return True
        except Exception:
            # Queue doesn't exist, create it
            try:
                queue = {
                    "name": queue_path,
                    "rate_limits": {
                        "max_dispatches_per_second": config.max_dispatches_per_second,
                        "max_concurrent_dispatches": config.max_concurrent_dispatches,
                    },
                    "retry_config": {
                        "max_attempts": config.max_attempts,
                        "min_backoff": duration_pb2.Duration(seconds=config.min_backoff_seconds),
                        "max_backoff": duration_pb2.Duration(seconds=config.max_backoff_seconds),
                    },
                }
                self.client.create_queue(parent=parent, queue=queue)
                logger.info(f"✅ Created queue: {config.queue_name}")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to create queue: {e}")
                return False
    
    def create_job_record(
        self,
        task_id: str,
        task_type: TaskType,
        user_id: str,
        payload: Dict[str, Any]
    ) -> bool:
        """Create job tracking record in Firestore."""
        if not self.db:
            logger.warning("⚠️ Firestore not available for job tracking")
            return False
        
        try:
            self.db.collection("jobs").document(task_id).set({
                "id": task_id,
                "type": task_type.value,
                "userId": user_id,
                "status": TaskStatus.PENDING.value,
                "payload": payload,
                "progress": 0,
                "progressMessage": "Queued for processing",
                "createdAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "completedAt": None,
                "result": None,
                "error": None,
            })
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create job record: {e}")
            return False
    
    def update_job_progress(
        self,
        task_id: str,
        progress: int,
        message: str,
        status: Optional[TaskStatus] = None
    ) -> bool:
        """Update job progress in Firestore."""
        if not self.db:
            return False
        
        try:
            update_data = {
                "progress": progress,
                "progressMessage": message,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }
            
            if status:
                update_data["status"] = status.value
                if status == TaskStatus.COMPLETED:
                    update_data["completedAt"] = firestore.SERVER_TIMESTAMP
            
            self.db.collection("jobs").document(task_id).update(update_data)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update job progress: {e}")
            return False
    
    def complete_job(
        self,
        task_id: str,
        result: Dict[str, Any],
        success: bool = True
    ) -> bool:
        """Mark job as completed."""
        if not self.db:
            return False
        
        try:
            self.db.collection("jobs").document(task_id).update({
                "status": TaskStatus.COMPLETED.value if success else TaskStatus.FAILED.value,
                "progress": 100 if success else -1,
                "progressMessage": "Complete" if success else "Failed",
                "result": result if success else None,
                "error": result.get("error") if not success else None,
                "completedAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            })
            return True
        except Exception as e:
            logger.error(f"❌ Failed to complete job: {e}")
            return False
    
    def dispatch_task(
        self,
        task_type: TaskType,
        user_id: str,
        payload: Dict[str, Any],
        task_id: Optional[str] = None,
        delay_seconds: int = 0,
        handler_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Dispatch a task to Cloud Tasks queue.
        
        Args:
            task_type: Type of task to run
            user_id: User who triggered the task
            payload: Task payload data
            task_id: Optional custom task ID
            delay_seconds: Delay before execution
            handler_path: API endpoint to handle the task
        
        Returns:
            Task ID if successful, None otherwise
        """
        import uuid
        
        task_id = task_id or f"{task_type.value}_{uuid.uuid4().hex[:12]}"
        
        # Create job record first
        self.create_job_record(task_id, task_type, user_id, payload)
        
        # Default handler paths
        handler_paths = {
            TaskType.TUTORIAL_GENERATION: "/api/internal/process-tutorial",
            TaskType.AD_CREATIVE_GENERATION: "/api/internal/process-ad-creative",
            TaskType.PREDICTION_COMPUTE: "/api/internal/compute-prediction",
            TaskType.ASSET_PROCESSING: "/api/internal/process-asset",
            TaskType.WEB_RESEARCH: "/api/internal/web-research",
            TaskType.ANALYTICS_SYNC: "/api/internal/sync-analytics",
        }
        
        handler_path = handler_path or handler_paths.get(task_type, "/api/internal/process")
        
        if not self.client:
            logger.warning("⚠️ Cloud Tasks not available, falling back to sync execution")
            # Update job to indicate sync execution
            self.update_job_progress(task_id, 10, "Processing synchronously")
            return task_id
        
        config = QUEUE_CONFIGS.get(task_type)
        if not config:
            logger.error(f"❌ No config for task type: {task_type}")
            return None
        
        # Ensure queue exists
        self.ensure_queue_exists(task_type)
        
        queue_path = self._get_queue_path(config.queue_name)
        
        try:
            # Build the task
            task_body = {
                "taskId": task_id,
                "userId": user_id,
                "taskType": task_type.value,
                "payload": payload,
                "createdAt": datetime.utcnow().isoformat(),
            }
            
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": f"{self.service_url}{handler_path}",
                    "headers": {
                        "Content-Type": "application/json",
                        "X-CloudTasks-TaskId": task_id,
                    },
                    "body": json.dumps(task_body).encode(),
                },
                "name": f"{queue_path}/tasks/{task_id}",
            }
            
            # Add delay if specified
            if delay_seconds > 0:
                schedule_time = datetime.utcnow() + timedelta(seconds=delay_seconds)
                timestamp = timestamp_pb2.Timestamp()
                timestamp.FromDatetime(schedule_time)
                task["schedule_time"] = timestamp
            
            # Create the task
            response = self.client.create_task(parent=queue_path, task=task)
            
            # Update job status
            self.update_job_progress(task_id, 5, "Queued in Cloud Tasks", TaskStatus.QUEUED)
            
            logger.info(f"✅ Dispatched task: {task_id} to {config.queue_name}")
            return task_id
            
        except Exception as e:
            logger.error(f"❌ Failed to dispatch task: {e}")
            self.complete_job(task_id, {"error": str(e)}, success=False)
            return None
    
    def cancel_task(self, task_type: TaskType, task_id: str) -> bool:
        """Cancel a pending task."""
        if not self.client:
            return False
        
        config = QUEUE_CONFIGS.get(task_type)
        if not config:
            return False
        
        queue_path = self._get_queue_path(config.queue_name)
        task_path = f"{queue_path}/tasks/{task_id}"
        
        try:
            self.client.delete_task(name=task_path)
            self.update_job_progress(task_id, -1, "Cancelled", TaskStatus.CANCELLED)
            logger.info(f"✅ Cancelled task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to cancel task: {e}")
            return False
    
    def get_job_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get job status from Firestore."""
        if not self.db:
            return None
        
        try:
            doc = self.db.collection("jobs").document(task_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get job status: {e}")
            return None


# Singleton instance
_orchestrator: Optional[CloudTasksOrchestrator] = None

def get_orchestrator() -> CloudTasksOrchestrator:
    """Get or create singleton CloudTasksOrchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = CloudTasksOrchestrator()
    return _orchestrator


# Convenience functions
def dispatch_tutorial_generation(
    user_id: str,
    topic: str,
    context: Optional[str] = None,
    request_id: Optional[str] = None
) -> Optional[str]:
    """Dispatch tutorial generation task."""
    orchestrator = get_orchestrator()
    return orchestrator.dispatch_task(
        TaskType.TUTORIAL_GENERATION,
        user_id,
        {
            "topic": topic,
            "context": context,
            "requestId": request_id,
        }
    )


def dispatch_asset_processing(
    user_id: str,
    asset_url: str,
    operations: Dict[str, Any]
) -> Optional[str]:
    """Dispatch asset processing task."""
    orchestrator = get_orchestrator()
    return orchestrator.dispatch_task(
        TaskType.ASSET_PROCESSING,
        user_id,
        {
            "assetUrl": asset_url,
            "operations": operations,
        }
    )

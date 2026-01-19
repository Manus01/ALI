"""
Tutorial Generation Queue
Priority queue for managing tutorial generation requests.

Features:
1. Priority-based ordering using eligibility scores
2. User-based rate limiting
3. Queue status tracking
4. Integration with tutorial generation pipeline
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import uuid
import heapq

logger = logging.getLogger(__name__)


class QueueItemStatus(str, Enum):
    """Status of items in the generation queue."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TutorialGenerationQueue:
    """
    Priority queue for tutorial generation requests.
    Manages ordering, rate limiting, and status tracking.
    """

    # Rate limiting: max tutorials per user per day
    MAX_PER_USER_PER_DAY = 3
    
    # Default priority for user-requested tutorials
    DEFAULT_USER_PRIORITY = 50

    def __init__(self, db=None):
        """Initialize with optional Firestore client for persistence."""
        self._db = db
        self._eligibility_scorer = None

    @property
    def db(self):
        if self._db is None:
            try:
                from app.core.security import db
                self._db = db
            except Exception:
                pass
        return self._db

    @property
    def scorer(self):
        if self._eligibility_scorer is None:
            try:
                from app.services.tutorial_eligibility_scorer import get_eligibility_scorer
                self._eligibility_scorer = get_eligibility_scorer()
            except Exception:
                pass
        return self._eligibility_scorer

    def enqueue(
        self,
        user_id: str,
        topic: str,
        trigger_reason: str = "user_requested",
        gap_data: Optional[Dict] = None,
        priority_override: Optional[float] = None,
        context: Optional[str] = None,
        recommendation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a tutorial generation request to the queue.
        
        Args:
            user_id: User to generate for
            topic: Tutorial topic
            trigger_reason: Why this tutorial is being generated
            gap_data: Gap analysis data if available
            priority_override: Manual priority override (0-100)
            context: Additional context for generation
            recommendation_id: ID of the recommendation that triggered this
            
        Returns:
            Queue item with ID and priority
        """
        try:
            # Check rate limit
            if not self._check_rate_limit(user_id):
                return {
                    "status": "rate_limited",
                    "message": f"User has reached daily limit ({self.MAX_PER_USER_PER_DAY} tutorials)",
                    "user_id": user_id
                }

            # Calculate priority if not overridden
            if priority_override is not None:
                priority = priority_override
                eligibility = {"total_score": priority, "eligibility": "MANUAL"}
            elif self.scorer:
                eligibility = self.scorer.score_recommendation(
                    user_id=user_id,
                    topic=topic,
                    gap_data=gap_data
                )
                priority = eligibility.get("total_score", 50)
            else:
                priority = self.DEFAULT_USER_PRIORITY
                eligibility = {"total_score": priority, "eligibility": "DEFAULT"}

            # Create queue item
            queue_id = str(uuid.uuid4())
            queue_item = {
                "queue_id": queue_id,
                "user_id": user_id,
                "topic": topic,
                "trigger_reason": trigger_reason,
                "priority": priority,
                "eligibility": eligibility,
                "context": context,
                "recommendation_id": recommendation_id,
                "status": QueueItemStatus.PENDING.value,
                "created_at": datetime.utcnow().isoformat(),
                "attempts": 0,
                "last_error": None
            }

            # Persist to Firestore
            if self.db:
                self.db.collection("tutorial_generation_queue").document(queue_id).set(queue_item)
                logger.info(f"📥 Queued tutorial: {topic} for {user_id} (priority: {priority})")

            return {
                "status": "queued",
                "queue_id": queue_id,
                "priority": priority,
                "eligibility": eligibility.get("eligibility", "DEFAULT"),
                "position": self._get_queue_position(priority)
            }

        except Exception as e:
            logger.error(f"❌ Queue enqueue failed: {e}")
            return {"status": "error", "message": str(e)}

    def dequeue(self, count: int = 1) -> List[Dict[str, Any]]:
        """
        Get the next items to process from the queue.
        
        Args:
            count: Number of items to dequeue
            
        Returns:
            List of queue items sorted by priority
        """
        if not self.db:
            return []

        try:
            # Get pending items ordered by priority (descending)
            items = list(
                self.db.collection("tutorial_generation_queue")
                .where("status", "==", QueueItemStatus.PENDING.value)
                .order_by("priority", direction="DESCENDING")
                .limit(count)
                .stream()
            )

            result = []
            for item in items:
                item_data = item.to_dict()
                item_data["queue_id"] = item.id
                
                # Mark as processing
                item.reference.update({
                    "status": QueueItemStatus.PROCESSING.value,
                    "processing_started_at": datetime.utcnow().isoformat()
                })
                
                result.append(item_data)

            return result

        except Exception as e:
            logger.error(f"❌ Queue dequeue failed: {e}")
            return []

    def mark_completed(
        self, 
        queue_id: str, 
        tutorial_id: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> bool:
        """Mark a queue item as completed or failed."""
        if not self.db:
            return False

        try:
            ref = self.db.collection("tutorial_generation_queue").document(queue_id)
            
            if success:
                ref.update({
                    "status": QueueItemStatus.COMPLETED.value,
                    "completed_at": datetime.utcnow().isoformat(),
                    "generated_tutorial_id": tutorial_id
                })
            else:
                doc = ref.get()
                if doc.exists:
                    attempts = doc.to_dict().get("attempts", 0) + 1
                    ref.update({
                        "status": QueueItemStatus.FAILED.value,
                        "failed_at": datetime.utcnow().isoformat(),
                        "last_error": error,
                        "attempts": attempts
                    })
            
            return True

        except Exception as e:
            logger.error(f"❌ Mark completed failed: {e}")
            return False

    def cancel(self, queue_id: str, reason: str = "") -> bool:
        """Cancel a queued item."""
        if not self.db:
            return False

        try:
            self.db.collection("tutorial_generation_queue").document(queue_id).update({
                "status": QueueItemStatus.CANCELLED.value,
                "cancelled_at": datetime.utcnow().isoformat(),
                "cancel_reason": reason
            })
            return True
        except Exception as e:
            logger.error(f"❌ Cancel failed: {e}")
            return False

    def get_queue_status(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get queue statistics and status."""
        if not self.db:
            return {"error": "Database not available"}

        try:
            base_query = self.db.collection("tutorial_generation_queue")
            
            # Count by status
            pending = list(base_query.where("status", "==", "pending").stream())
            processing = list(base_query.where("status", "==", "processing").stream())
            
            # User-specific counts if provided
            user_pending = 0
            user_in_progress = 0
            if user_id:
                user_pending = len([p for p in pending if p.to_dict().get("user_id") == user_id])
                user_in_progress = len([p for p in processing if p.to_dict().get("user_id") == user_id])

            return {
                "total_pending": len(pending),
                "total_processing": len(processing),
                "user_pending": user_pending if user_id else None,
                "user_in_progress": user_in_progress if user_id else None,
                "rate_limit_remaining": self._get_rate_limit_remaining(user_id) if user_id else None,
                "checked_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Queue status failed: {e}")
            return {"error": str(e)}

    def get_user_queue(self, user_id: str, include_completed: bool = False) -> List[Dict]:
        """Get all queue items for a specific user."""
        if not self.db:
            return []

        try:
            query = self.db.collection("tutorial_generation_queue").where("user_id", "==", user_id)
            
            if not include_completed:
                # Only pending and processing
                items = []
                for status in [QueueItemStatus.PENDING.value, QueueItemStatus.PROCESSING.value]:
                    items.extend(list(query.where("status", "==", status).stream()))
            else:
                items = list(query.stream())

            result = []
            for item in items:
                item_data = item.to_dict()
                item_data["queue_id"] = item.id
                result.append(item_data)

            # Sort by priority
            result.sort(key=lambda x: x.get("priority", 0), reverse=True)
            return result

        except Exception as e:
            logger.error(f"❌ Get user queue failed: {e}")
            return []

    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limit."""
        if not self.db:
            return True  # Allow if no DB

        try:
            today = datetime.utcnow().date().isoformat()
            
            # Count tutorials generated today
            generated_today = list(
                self.db.collection("tutorial_generation_queue")
                .where("user_id", "==", user_id)
                .where("status", "==", QueueItemStatus.COMPLETED.value)
                .stream()
            )
            
            count = sum(
                1 for g in generated_today 
                if g.to_dict().get("completed_at", "").startswith(today)
            )
            
            return count < self.MAX_PER_USER_PER_DAY

        except Exception:
            return True  # Allow on error

    def _get_rate_limit_remaining(self, user_id: str) -> int:
        """Get remaining tutorials for user today."""
        if not self.db:
            return self.MAX_PER_USER_PER_DAY

        try:
            today = datetime.utcnow().date().isoformat()
            
            generated_today = list(
                self.db.collection("tutorial_generation_queue")
                .where("user_id", "==", user_id)
                .where("status", "==", QueueItemStatus.COMPLETED.value)
                .stream()
            )
            
            count = sum(
                1 for g in generated_today 
                if g.to_dict().get("completed_at", "").startswith(today)
            )
            
            return max(0, self.MAX_PER_USER_PER_DAY - count)

        except Exception:
            return self.MAX_PER_USER_PER_DAY

    def _get_queue_position(self, priority: float) -> int:
        """Estimate position in queue based on priority."""
        if not self.db:
            return 1

        try:
            # Count items with higher priority
            higher_priority = list(
                self.db.collection("tutorial_generation_queue")
                .where("status", "==", QueueItemStatus.PENDING.value)
                .where("priority", ">", priority)
                .stream()
            )
            
            return len(higher_priority) + 1

        except Exception:
            return 1

    def retry_failed(self, queue_id: str) -> Dict[str, Any]:
        """Retry a failed queue item."""
        if not self.db:
            return {"status": "error", "message": "Database not available"}

        try:
            ref = self.db.collection("tutorial_generation_queue").document(queue_id)
            doc = ref.get()
            
            if not doc.exists:
                return {"status": "error", "message": "Queue item not found"}
            
            item = doc.to_dict()
            if item.get("status") != QueueItemStatus.FAILED.value:
                return {"status": "error", "message": "Item is not in failed status"}
            
            if item.get("attempts", 0) >= 3:
                return {"status": "error", "message": "Max retries (3) exceeded"}

            ref.update({
                "status": QueueItemStatus.PENDING.value,
                "retry_at": datetime.utcnow().isoformat()
            })

            return {"status": "success", "message": "Item queued for retry"}

        except Exception as e:
            logger.error(f"❌ Retry failed: {e}")
            return {"status": "error", "message": str(e)}


# Singleton instance
_generation_queue: Optional[TutorialGenerationQueue] = None


def get_generation_queue() -> TutorialGenerationQueue:
    """Get or create singleton TutorialGenerationQueue."""
    global _generation_queue
    if _generation_queue is None:
        _generation_queue = TutorialGenerationQueue()
    return _generation_queue

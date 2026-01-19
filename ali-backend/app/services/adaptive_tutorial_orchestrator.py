"""
Adaptive Tutorial Orchestrator
Central orchestrator for the Adaptive Tutorial Engine (ATE).

Responsibilities:
1. Run scheduled gap analysis for all users
2. Generate and queue tutorial recommendations
3. Process the tutorial generation queue
4. Update learning journeys when tutorials complete
5. Track system metrics and health
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class AdaptiveTutorialOrchestrator:
    """
    Central orchestrator for automated tutorial generation.
    Coordinates all ATE components for end-to-end automation.
    """

    # Processing limits per run
    MAX_USERS_PER_RUN = 50
    MAX_QUEUE_PROCESS = 10
    
    # Thresholds for alerts
    ALERT_THRESHOLD_PENDING = 20  # Alert if > 20 pending items

    def __init__(self, db=None):
        """Initialize with optional Firestore client."""
        self._db = db
        self._gap_analyzer = None
        self._eligibility_scorer = None
        self._generation_queue = None
        self._journey_planner = None
        self._analytics_service = None

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
    def gap_analyzer(self):
        if self._gap_analyzer is None:
            try:
                from app.agents.gap_analyzer_agent import get_gap_analyzer
                self._gap_analyzer = get_gap_analyzer()
            except Exception:
                pass
        return self._gap_analyzer

    @property
    def scorer(self):
        if self._eligibility_scorer is None:
            try:
                from app.services.tutorial_eligibility_scorer import get_eligibility_scorer
                self._eligibility_scorer = get_eligibility_scorer()
            except Exception:
                pass
        return self._eligibility_scorer

    @property
    def queue(self):
        if self._generation_queue is None:
            try:
                from app.services.tutorial_generation_queue import get_generation_queue
                self._generation_queue = get_generation_queue()
            except Exception:
                pass
        return self._generation_queue

    @property
    def planner(self):
        if self._journey_planner is None:
            try:
                from app.services.learning_journey_planner import get_journey_planner
                self._journey_planner = get_journey_planner()
            except Exception:
                pass
        return self._journey_planner

    @property
    def analytics(self):
        if self._analytics_service is None:
            try:
                from app.services.learning_analytics_service import get_learning_analytics_service
                self._analytics_service = get_learning_analytics_service()
            except Exception:
                pass
        return self._analytics_service

    def run_nightly_analysis(self) -> Dict[str, Any]:
        """
        Run nightly gap analysis for all active users.
        Called by GCP Cloud Scheduler.
        
        Workflow:
        1. Get all active users (completed at least 1 tutorial)
        2. Analyze gaps for each user
        3. Generate recommendations
        4. Queue high-priority tutorials for auto-generation
        5. Create admin tasks for items needing approval
        
        Returns:
            Summary of analysis run
        """
        start_time = datetime.utcnow()
        results = {
            "run_id": start_time.strftime("%Y%m%d_%H%M%S"),
            "started_at": start_time.isoformat(),
            "users_analyzed": 0,
            "gaps_detected": 0,
            "recommendations_created": 0,
            "tutorials_queued": 0,
            "admin_tasks_created": 0,
            "errors": []
        }

        try:
            logger.info("🌙 Starting nightly gap analysis run")

            # 1. Get active users
            active_users = self._get_active_users()
            results["total_active_users"] = len(active_users)

            # 2. Process each user
            for user_id in active_users[:self.MAX_USERS_PER_RUN]:
                try:
                    user_result = self._analyze_user(user_id)
                    results["users_analyzed"] += 1
                    results["gaps_detected"] += user_result.get("gaps_count", 0)
                    results["recommendations_created"] += user_result.get("recommendations_count", 0)
                    results["tutorials_queued"] += user_result.get("queued_count", 0)
                    results["admin_tasks_created"] += user_result.get("admin_tasks_count", 0)
                except Exception as e:
                    logger.error(f"❌ Error analyzing user {user_id}: {e}")
                    results["errors"].append({"user_id": user_id, "error": str(e)})

            # 3. Log run results
            results["completed_at"] = datetime.utcnow().isoformat()
            results["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()
            
            self._log_orchestration_run(results)
            
            logger.info(f"✅ Nightly analysis complete: {results['users_analyzed']} users, "
                       f"{results['gaps_detected']} gaps, {results['tutorials_queued']} queued")

            return results

        except Exception as e:
            logger.error(f"❌ Nightly analysis failed: {e}")
            results["errors"].append({"error": str(e)})
            results["completed_at"] = datetime.utcnow().isoformat()
            return results

    def _get_active_users(self) -> List[str]:
        """Get list of active users (have completed at least 1 tutorial)."""
        if not self.db:
            return []

        try:
            # Get users who have tutorial completion records
            users = self.db.collection("users").limit(200).stream()
            active_user_ids = []

            for user in users:
                user_id = user.id
                # Check if user has any completed tutorials
                completed = list(
                    self.db.collection("users").document(user_id)
                    .collection("tutorials")
                    .where("is_completed", "==", True)
                    .limit(1)
                    .stream()
                )
                if completed:
                    active_user_ids.append(user_id)

            return active_user_ids

        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []

    def _analyze_user(self, user_id: str) -> Dict[str, Any]:
        """Analyze a single user for gaps and create recommendations."""
        result = {
            "user_id": user_id,
            "gaps_count": 0,
            "recommendations_count": 0,
            "queued_count": 0,
            "admin_tasks_count": 0
        }

        try:
            # 1. Detect gaps
            if self.gap_analyzer:
                gap_result = self.gap_analyzer.analyze_user_gaps(user_id)
                gaps = gap_result.get("gaps", [])
                result["gaps_count"] = len(gaps)

                # 2. Process each gap
                for gap in gaps[:5]:  # Top 5 gaps per user
                    recommendation = self._process_gap(user_id, gap)
                    if recommendation:
                        result["recommendations_count"] += 1
                        if recommendation.get("queued"):
                            result["queued_count"] += 1
                        if recommendation.get("admin_task"):
                            result["admin_tasks_count"] += 1

            return result

        except Exception as e:
            logger.error(f"Error analyzing user {user_id}: {e}")
            return result

    def _process_gap(self, user_id: str, gap: Dict) -> Optional[Dict]:
        """Process a single gap and create recommendation/queue item."""
        try:
            topic = gap.get("topic")
            if not topic:
                return None

            # Score eligibility
            eligibility = None
            if self.scorer:
                eligibility = self.scorer.score_recommendation(
                    user_id=user_id,
                    topic=topic,
                    gap_data=gap
                )

            result = {
                "topic": topic,
                "gap_id": gap.get("gap_id"),
                "eligibility": eligibility,
                "queued": False,
                "admin_task": False
            }

            # Determine action based on trigger type and score
            trigger_type = gap.get("trigger_type", "skill_gap_detected")
            should_auto_approve = gap.get("auto_approve", False)
            total_score = eligibility.get("total_score", 50) if eligibility else 50

            if should_auto_approve and total_score >= 70:
                # Auto-queue for generation (remediation)
                if self.queue:
                    queue_result = self.queue.enqueue(
                        user_id=user_id,
                        topic=topic,
                        trigger_reason=trigger_type,
                        gap_data=gap
                    )
                    if queue_result.get("status") == "queued":
                        result["queued"] = True
                        logger.info(f"📥 Auto-queued: {topic} for {user_id}")
            else:
                # Create admin task for approval
                if self.db and total_score >= 50:  # Only for medium+ priority
                    self._create_admin_task(user_id, topic, gap, eligibility)
                    result["admin_task"] = True

            return result

        except Exception as e:
            logger.error(f"Error processing gap: {e}")
            return None

    def _create_admin_task(
        self, 
        user_id: str, 
        topic: str, 
        gap: Dict,
        eligibility: Optional[Dict]
    ):
        """Create an admin task for recommendation approval."""
        try:
            from google.cloud import firestore
            import uuid

            recommendation_id = str(uuid.uuid4())
            
            self.db.collection("admin_tasks").add({
                "type": "tutorial_recommendation",
                "recommendation_id": recommendation_id,
                "user_id": user_id,
                "topic": topic,
                "trigger_reason": gap.get("trigger_type", "skill_gap_detected"),
                "evidence": gap.get("evidence"),
                "priority": eligibility.get("total_score", 50) if eligibility else 50,
                "eligibility": eligibility.get("eligibility", "MEDIUM") if eligibility else "MEDIUM",
                "reasoning": eligibility.get("reasoning", []) if eligibility else [],
                "status": "pending",
                "created_at": firestore.SERVER_TIMESTAMP,
                "source": "nightly_analysis"
            })

            logger.info(f"📋 Created admin task for: {topic} (user: {user_id})")

        except Exception as e:
            logger.error(f"Error creating admin task: {e}")

    def process_queue(self, max_items: int = None) -> Dict[str, Any]:
        """
        Process items from the tutorial generation queue.
        Called periodically by scheduler.
        
        Returns:
            Processing results
        """
        max_items = max_items or self.MAX_QUEUE_PROCESS
        results = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "items": []
        }

        if not self.queue:
            return {"error": "Queue not available"}

        try:
            # Get items to process
            items = self.queue.dequeue(max_items)
            
            for item in items:
                item_result = self._process_queue_item(item)
                results["processed"] += 1
                results["items"].append(item_result)
                
                if item_result.get("success"):
                    results["succeeded"] += 1
                else:
                    results["failed"] += 1

            return results

        except Exception as e:
            logger.error(f"❌ Queue processing failed: {e}")
            return {"error": str(e)}

    def _process_queue_item(self, item: Dict) -> Dict[str, Any]:
        """Process a single queue item - trigger tutorial generation."""
        queue_id = item.get("queue_id")
        user_id = item.get("user_id")
        topic = item.get("topic")

        try:
            # Import tutorial generator
            from app.agents.tutorial_agent import generate_tutorial

            # Generate tutorial
            logger.info(f"🎓 Generating tutorial: {topic} for {user_id}")
            
            result = generate_tutorial(
                user_id=user_id,
                topic=topic,
                context=item.get("context"),
                is_delta=False
            )

            tutorial_id = result.get("tutorial_id") or result.get("id")
            
            # Mark queue item as completed
            if self.queue:
                self.queue.mark_completed(queue_id, tutorial_id, success=True)

            # Update learning journey if user has one
            self._update_journey_on_completion(user_id, topic, tutorial_id)

            return {
                "queue_id": queue_id,
                "success": True,
                "tutorial_id": tutorial_id,
                "topic": topic
            }

        except Exception as e:
            logger.error(f"❌ Tutorial generation failed for {queue_id}: {e}")
            
            if self.queue:
                self.queue.mark_completed(queue_id, success=False, error=str(e))

            return {
                "queue_id": queue_id,
                "success": False,
                "error": str(e),
                "topic": topic
            }

    def _update_journey_on_completion(
        self, 
        user_id: str, 
        topic: str, 
        tutorial_id: str
    ):
        """Update user's learning journey when a tutorial is generated."""
        if not self.planner:
            return

        try:
            journey = self.planner.get_active_journey(user_id)
            if not journey:
                return

            # Find matching node
            nodes = journey.get("nodes", [])
            for node in nodes:
                if node.get("topic") == topic and node.get("status") == "pending":
                    node["generated_tutorial_id"] = tutorial_id
                    node["generated_at"] = datetime.utcnow().isoformat()
                    
                    # Update in Firestore
                    self.db.collection("users").document(user_id).collection(
                        "learning_journeys"
                    ).document(journey["journey_id"]).update({
                        "nodes": nodes
                    })
                    
                    logger.info(f"🗺️ Updated journey node with generated tutorial")
                    break

        except Exception as e:
            logger.warning(f"Could not update journey: {e}")

    def _log_orchestration_run(self, results: Dict):
        """Log orchestration run to Firestore for monitoring."""
        if not self.db:
            return

        try:
            self.db.collection("orchestration_logs").add({
                "type": "nightly_analysis",
                **results
            })
        except Exception as e:
            logger.warning(f"Could not log orchestration run: {e}")

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the orchestration system."""
        status = {
            "healthy": True,
            "components": {},
            "alerts": [],
            "checked_at": datetime.utcnow().isoformat()
        }

        # Check each component
        status["components"]["gap_analyzer"] = self.gap_analyzer is not None
        status["components"]["eligibility_scorer"] = self.scorer is not None
        status["components"]["generation_queue"] = self.queue is not None
        status["components"]["journey_planner"] = self.planner is not None
        status["components"]["analytics_service"] = self.analytics is not None

        # Check for unhealthy components
        unhealthy = [k for k, v in status["components"].items() if not v]
        if unhealthy:
            status["healthy"] = False
            status["alerts"].append(f"Components unavailable: {', '.join(unhealthy)}")

        # Check queue status
        if self.queue:
            queue_status = self.queue.get_queue_status()
            pending = queue_status.get("total_pending", 0)
            status["queue_pending"] = pending
            
            if pending > self.ALERT_THRESHOLD_PENDING:
                status["alerts"].append(f"High queue backlog: {pending} pending items")

        return status


# Singleton instance
_orchestrator: Optional[AdaptiveTutorialOrchestrator] = None


def get_adaptive_orchestrator() -> AdaptiveTutorialOrchestrator:
    """Get or create singleton AdaptiveTutorialOrchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AdaptiveTutorialOrchestrator()
    return _orchestrator

"""
Learning Journey API Router
Provides endpoints for the Adaptive Tutorial Engine (ATE).

Endpoints:
- POST /learning-analytics/event - Log learning events
- GET /learning-analytics/performance - Get user performance summary
- GET /learning-analytics/gaps - Detect learning gaps
- GET /learning-analytics/recommendations - Get tutorial recommendations
- POST /learning-analytics/recommendations/{id}/approve - Approve a recommendation
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

from app.core.security import verify_token
from app.routers.admin import verify_admin
from app.services.learning_analytics_service import get_learning_analytics_service

logger = logging.getLogger(__name__)

router = APIRouter()


# --- REQUEST MODELS ---

class LearningEventRequest(BaseModel):
    """Request model for logging learning events."""
    event_type: str = Field(..., description="Event type: section_start, quiz_attempt, etc.")
    tutorial_id: Optional[str] = None
    section_index: Optional[int] = None
    section_title: Optional[str] = None
    time_spent_seconds: Optional[int] = None
    scroll_depth_percent: Optional[float] = None
    replay_count: Optional[int] = None
    quiz_score: Optional[float] = None
    device_type: Optional[str] = None
    session_id: Optional[str] = None
    # Tutorial metadata for aggregation
    tutorial_topic: Optional[str] = None
    tutorial_difficulty: Optional[str] = None
    tutorial_category: Optional[str] = None


class BatchEventsRequest(BaseModel):
    """Request model for batch event logging."""
    events: List[LearningEventRequest]


class ApprovalDecision(BaseModel):
    """Request model for recommendation approval."""
    approved: bool
    notes: Optional[str] = None


# --- ENDPOINTS ---

@router.post("/learning-analytics/event")
def log_learning_event(
    event: LearningEventRequest,
    user: dict = Depends(verify_token)
):
    """
    Log a learning event from the frontend.
    Used for tracking section views, quiz attempts, media plays, etc.
    """
    try:
        service = get_learning_analytics_service()
        
        event_data = event.dict()
        event_data["user_id"] = user["uid"]
        
        success = service.log_learning_event(event_data)
        
        return {
            "status": "logged" if success else "skipped",
            "message": "Event recorded" if success else "Analytics not available"
        }
    except Exception as e:
        logger.error(f"❌ Log event error: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/learning-analytics/events/batch")
def log_learning_events_batch(
    batch: BatchEventsRequest,
    user: dict = Depends(verify_token)
):
    """
    Log multiple learning events in batch.
    More efficient for high-frequency tracking.
    """
    try:
        service = get_learning_analytics_service()
        
        events = [
            {**e.dict(), "user_id": user["uid"]} 
            for e in batch.events
        ]
        
        count = service.log_learning_events_batch(events)
        
        return {
            "status": "success",
            "logged_count": count,
            "total_count": len(events)
        }
    except Exception as e:
        logger.error(f"❌ Batch log error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning-analytics/performance")
def get_performance_summary(
    days: int = 30,
    user: dict = Depends(verify_token)
):
    """
    Get comprehensive learning performance summary for the current user.
    
    Returns quiz pass rates, average scores, weak/strong areas, etc.
    """
    try:
        service = get_learning_analytics_service()
        summary = service.get_user_performance_summary(user["uid"], days)
        
        if "error" in summary:
            raise HTTPException(status_code=500, detail=summary["error"])
        
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Performance summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning-analytics/gaps")
def detect_learning_gaps(user: dict = Depends(verify_token)):
    """
    Analyze learning performance and detect skill gaps.
    
    Returns prioritized list of learning gaps with suggested actions.
    """
    try:
        service = get_learning_analytics_service()
        gaps = service.detect_learning_gaps(user["uid"])
        
        return {
            "gaps": gaps,
            "total": len(gaps)
        }
    except Exception as e:
        logger.error(f"❌ Gap detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning-analytics/recommendations")
def get_recommendations(
    max_count: int = 5,
    user: dict = Depends(verify_token)
):
    """
    Generate tutorial recommendations based on detected learning gaps.
    
    Remediation-triggered recommendations are auto-approved.
    Other recommendations require admin approval.
    """
    try:
        service = get_learning_analytics_service()
        recommendations = service.generate_recommendations(user["uid"], max_count)
        
        return {
            "recommendations": recommendations,
            "total": len(recommendations)
        }
    except Exception as e:
        logger.error(f"❌ Recommendations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning-analytics/recommendations/pending")
def get_pending_recommendations(admin: dict = Depends(verify_admin)):
    """
    ADMIN: Get all pending tutorial recommendations awaiting approval.
    """
    try:
        service = get_learning_analytics_service()
        pending = service.get_pending_recommendations()
        
        return {
            "recommendations": pending,
            "total": len(pending)
        }
    except Exception as e:
        logger.error(f"❌ Pending recommendations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning-analytics/recommendations/{recommendation_id}/approve")
def approve_recommendation(
    recommendation_id: str,
    decision: ApprovalDecision,
    admin: dict = Depends(verify_admin)
):
    """
    ADMIN: Approve or reject a tutorial recommendation.
    
    If approved, the tutorial will be queued for generation.
    """
    try:
        from app.core.security import db
        from google.cloud import firestore
        
        # Update admin task
        tasks = db.collection("admin_tasks").where(
            "recommendation_id", "==", recommendation_id
        ).limit(1).stream()
        
        for task in tasks:
            status = "approved" if decision.approved else "rejected"
            task.reference.update({
                "status": status,
                "resolved_by": admin.get("email", admin.get("uid")),
                "resolved_at": firestore.SERVER_TIMESTAMP,
                "notes": decision.notes
            })
            
            # If approved, trigger tutorial generation
            if decision.approved:
                task_data = task.to_dict()
                
                # Create tutorial request
                db.collection("tutorial_requests").add({
                    "userId": task_data.get("user_id"),
                    "topic": task_data.get("topic"),
                    "context": f"Auto-generated from learning gap analysis. {decision.notes or ''}",
                    "status": "APPROVED",
                    "source": "adaptive_tutorial_engine",
                    "recommendation_id": recommendation_id,
                    "createdAt": firestore.SERVER_TIMESTAMP
                })
                
                logger.info(f"✅ Recommendation {recommendation_id} approved and queued for generation")
            
            return {
                "status": "success",
                "decision": status,
                "message": f"Recommendation {status}"
            }
        
        raise HTTPException(status_code=404, detail="Recommendation not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Approval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- DECISION ENGINE ENDPOINTS ---

class QueueRequest(BaseModel):
    """Request model for queueing a tutorial."""
    topic: str
    trigger_reason: str = "user_requested"
    context: Optional[str] = None
    priority_override: Optional[float] = None


class JourneyRequest(BaseModel):
    """Request model for creating a learning journey."""
    journey_type: str = "remediation"  # remediation, skill_building, exploration
    target_skill: Optional[str] = None
    max_nodes: int = 5


@router.get("/learning-journey")
def get_active_journey(user: dict = Depends(verify_token)):
    """
    Get the user's current active learning journey.
    Returns journey with nodes and progress.
    """
    try:
        from app.services.learning_journey_planner import get_journey_planner
        
        planner = get_journey_planner()
        journey = planner.get_active_journey(user["uid"])
        
        if not journey:
            return {"journey": None, "message": "No active journey"}
        
        return {"journey": journey}
        
    except Exception as e:
        logger.error(f"❌ Get journey error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning-journey")
def create_learning_journey(
    request: JourneyRequest,
    user: dict = Depends(verify_token)
):
    """
    Create a new personalized learning journey.
    
    Journey types:
    - remediation: Gap-based, focuses on identified weaknesses
    - skill_building: Progressive path for a specific skill
    - exploration: Flexible, user-directed learning
    """
    try:
        from app.services.learning_journey_planner import get_journey_planner
        
        planner = get_journey_planner()
        journey = planner.generate_journey(
            user_id=user["uid"],
            journey_type=request.journey_type,
            target_skill=request.target_skill,
            max_nodes=min(request.max_nodes, 10)  # Cap at 10
        )
        
        if "error" in journey:
            raise HTTPException(status_code=500, detail=journey["error"])
        
        return journey
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Create journey error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning-journey/next")
def get_next_journey_node(user: dict = Depends(verify_token)):
    """
    Get the next recommended tutorial in the user's learning journey.
    """
    try:
        from app.services.learning_journey_planner import get_journey_planner
        
        planner = get_journey_planner()
        node = planner.get_next_node(user["uid"])
        
        if not node:
            return {"node": None, "message": "No pending nodes or no active journey"}
        
        return {"node": node}
        
    except Exception as e:
        logger.error(f"❌ Get next node error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning-journey/{journey_id}/complete/{node_id}")
def complete_journey_node(
    journey_id: str,
    node_id: str,
    score: Optional[float] = None,
    user: dict = Depends(verify_token)
):
    """
    Mark a journey node as completed.
    Optionally includes the score achieved.
    """
    try:
        from app.services.learning_journey_planner import get_journey_planner
        
        planner = get_journey_planner()
        result = planner.complete_node(
            user_id=user["uid"],
            journey_id=journey_id,
            node_id=node_id,
            score=score
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Complete node error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning-queue/status")
def get_queue_status(user: dict = Depends(verify_token)):
    """
    Get the user's tutorial generation queue status.
    """
    try:
        from app.services.tutorial_generation_queue import get_generation_queue
        
        queue = get_generation_queue()
        status = queue.get_queue_status(user["uid"])
        
        return status
        
    except Exception as e:
        logger.error(f"❌ Queue status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning-queue/my")
def get_my_queue(user: dict = Depends(verify_token)):
    """
    Get all queue items for the current user.
    """
    try:
        from app.services.tutorial_generation_queue import get_generation_queue
        
        queue = get_generation_queue()
        items = queue.get_user_queue(user["uid"])
        
        return {
            "queue_items": items,
            "total": len(items)
        }
        
    except Exception as e:
        logger.error(f"❌ Get my queue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning-queue/enqueue")
def enqueue_tutorial(
    request: QueueRequest,
    user: dict = Depends(verify_token)
):
    """
    Queue a tutorial for generation.
    Priority is automatically calculated based on eligibility scoring.
    """
    try:
        from app.services.tutorial_generation_queue import get_generation_queue
        
        queue = get_generation_queue()
        result = queue.enqueue(
            user_id=user["uid"],
            topic=request.topic,
            trigger_reason=request.trigger_reason,
            context=request.context,
            priority_override=request.priority_override
        )
        
        if result.get("status") == "rate_limited":
            raise HTTPException(status_code=429, detail=result["message"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Enqueue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/learning-queue/{queue_id}")
def cancel_queue_item(
    queue_id: str,
    reason: Optional[str] = None,
    user: dict = Depends(verify_token)
):
    """
    Cancel a queued tutorial generation.
    """
    try:
        from app.services.tutorial_generation_queue import get_generation_queue
        
        queue = get_generation_queue()
        success = queue.cancel(queue_id, reason or "User cancelled")
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to cancel queue item")
        
        return {"status": "cancelled", "queue_id": queue_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Cancel queue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/eligibility/{topic}")
def check_eligibility(
    topic: str,
    user: dict = Depends(verify_token)
):
    """
    Check eligibility score for generating a tutorial on a topic.
    Returns priority score and reasoning.
    """
    try:
        from app.services.tutorial_eligibility_scorer import get_eligibility_scorer
        
        scorer = get_eligibility_scorer()
        result = scorer.score_recommendation(
            user_id=user["uid"],
            topic=topic
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Eligibility check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


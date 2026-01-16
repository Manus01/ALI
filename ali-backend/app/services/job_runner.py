import time
from app.core.security import db
from firebase_admin import firestore
import logging
from typing import Any, Dict, List

# Configure logger
logger = logging.getLogger("ali_platform.services.job_runner")

def process_tutorial_job(job_id: str, user_id: str, topic: str, notification_id: str | None = None):
    """
    Background task that generates the tutorial and updates status.
    Updates the SAME notification to prevent 'stale loading' UI.
    
    NOTIFICATION STRATEGY (Spam Reduction):
    - Do NOT create intermediate "Generation Started" notifications
    - Only update the existing notification ONCE at completion ("New Lesson Ready")
    - This reduces notifications from 4+ to 2 per request
    """
    logger.info(f"⚙️ Worker: Starting Job {job_id} for {topic}...")
    
    # ⚡ AI Machine boundary: use client for generation ⚡
    try:
        from app.services.ai_service_client import generate_tutorial
    except ImportError as e:
        logger.critical(f"❌ Failed to import AI service client: {e}")
        db.collection("jobs").document(job_id).update({
             "status": "failed",
             "error": "Internal Import Error: AI service client failed to load"
        })
        return None

    job_ref = db.collection("jobs").document(job_id)

    # Track the Notification ID so we can update it at completion
    notifications_col = db.collection("users").document(user_id).collection("notifications")
    notification_ref = notifications_col.document(notification_id) if notification_id else None

    try:
        # 1. Update Status -> Processing (no notification spam here)
        job_ref.update({"status": "processing", "started_at": firestore.SERVER_TIMESTAMP})

        # ⚡ CLOUD RUN KEEP-ALIVE: Heartbeat Thread ⚡
        # This prevents CPU throttling by generating periodic log output
        import threading
        heartbeat_active = [True]  # Use list for mutable reference in closure
        
        def heartbeat_worker():
            iteration = 0
            while heartbeat_active[0]:
                iteration += 1
                logger.info(f"💓 Heartbeat #{iteration} - Job {job_id} still processing...")
                time.sleep(30)  # Log every 30 seconds
        
        heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
        heartbeat_thread.start()
        
        try:
            # 2. Run the Heavy AI Generation (Takes 60s+)
            # Note: progress_callback removed to reduce notification spam
            tutorial_data = generate_tutorial(
                user_id,
                topic,
                progress_callback=None,  # No intermediate updates
                notification_id=notification_id
            )
        finally:
            # Stop heartbeat regardless of success/failure
            heartbeat_active[0] = False
            logger.info(f"💓 Heartbeat stopped for Job {job_id}")

        # ⚡ CRITICAL: Link the generated tutorial to the original request ⚡
        # This enables the fallback GET /tutorials/by-request/{id} endpoint
        tutorial_id = tutorial_data.get("id")
        
        # Try to find and update the tutorial_requests document
        # (The job_id may match the request notification, or we search by topic/user)
        try:
            requests_ref = db.collection("tutorial_requests")
            # Query for pending requests matching this user and topic
            query = requests_ref.where("userId", "==", user_id).where("topic", "==", topic).where("status", "in", ["APPROVED", "GENERATING"]).limit(1)
            matching_requests = list(query.stream())
            
            if matching_requests:
                request_doc = matching_requests[0]
                request_doc.reference.update({
                    "generated_tutorial_id": tutorial_id,
                    "tutorialId": tutorial_id,  # Legacy field for compatibility
                    "status": "COMPLETED",
                    "completedAt": firestore.SERVER_TIMESTAMP
                })
                logger.info(f"✅ Linked tutorial {tutorial_id} to request {request_doc.id}")
            else:
                logger.warning(f"⚠️ No matching tutorial_request found for user={user_id}, topic={topic}")
        except Exception as link_err:
            # Non-fatal: log but don't fail the job
            logger.error(f"⚠️ Failed to link tutorial to request: {link_err}")

        # 3. UPDATE the Existing Notification to "Ready" (SINGLE UPDATE)
        # This is the ONLY notification update - replaces "Request Submitted" with "Success"
        if notification_ref:
            notification_ref.update({
                "type": "success",
                "status": "completed",
                "title": "New Lesson Ready",
                "message": f"Your tutorial on '{topic}' is ready.",
                "link": f"/tutorials/{tutorial_data['id']}",
                "read": False,
                "updated_at": firestore.SERVER_TIMESTAMP
            })

        # 4. Mark Job Complete
        job_ref.update({
            "status": "completed", 
            "result_id": tutorial_data["id"],
            "completed_at": firestore.SERVER_TIMESTAMP
        })
        logger.info(f"✅ Worker: Job {job_id} Finished. Tutorial ID: {tutorial_data['id']}")
        
        # Return result for caller to use
        return {"result_id": tutorial_data["id"]}

    except Exception as e:
        logger.error(f"❌ Worker Error: {e}")
        job_ref.update({"status": "failed", "error": str(e)})
        
        # Update notification to Failure state
        if notification_ref:
            notification_ref.update({
                "type": "error",
                "status": "failed",
                "title": "Generation Failed",
                "message": f"Something went wrong: {str(e)}",
                "read": False,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
        
        return None


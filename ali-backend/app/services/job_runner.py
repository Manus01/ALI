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


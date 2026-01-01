import time
from app.core.security import db
from google.cloud import firestore
import logging

logger = logging.getLogger(__name__)

try:
    from app.agents.tutorial_agent import generate_tutorial
except ImportError as e:
    logger.critical(f"❌ Failed to import generate_tutorial: {e}")
    # Define a dummy function to prevent crash, but log error
    def generate_tutorial(*args, **kwargs):
        raise ImportError(f"Tutorial Agent failed to load: {e}")

def process_tutorial_job(job_id: str, user_id: str, topic: str):
    """
    Background task that generates the tutorial and updates status.
    Updates the SAME notification to prevent 'stale loading' UI.
    """
    print(f"⚙️ Worker: Starting Job {job_id} for {topic}...")
    job_ref = db.collection("jobs").document(job_id)

    # Track the Notification ID so we can update it later
    notification_ref = None

    try:
        # 1. Update Status -> Processing
        job_ref.update({"status": "processing", "started_at": firestore.SERVER_TIMESTAMP})

        # 2. Create "Started" Notification (Spinner)
        # We capture the reference (add() returns [timestamp, doc_ref])
        # SENIOR DEV FIX: Save to user's subcollection so the frontend listener picks it up
        _, notification_ref = db.collection("users").document(user_id).collection("notifications").add({
            "user_id": user_id,
            "type": "info", # Usually renders as spinner/info icon
            "title": "Generation Started",
            "message": f"AI is crafting your course on '{topic}'. This may take a minute.",
            "link": None,
            "read": False,
            "created_at": firestore.SERVER_TIMESTAMP
        })

        # Define progress callback to update the notification in real-time
        def update_progress(msg):
            if notification_ref:
                notification_ref.update({"message": msg})

        # 3. Run the Heavy AI Generation (Takes 60s+)
        tutorial_data = generate_tutorial(user_id, topic, progress_callback=update_progress)

        # 4. UPDATE the Existing Notification to "Ready"
        # This replaces the "Started" spinner with the "Success" state!
        if notification_ref:
            notification_ref.update({
                "type": "success",
                "title": "New Lesson Ready",
                "message": f"Your tutorial on '{topic}' is ready.",
                "link": f"/tutorials/{tutorial_data['id']}",
                "read": False,
                "updated_at": firestore.SERVER_TIMESTAMP
            })

        # 5. Mark Job Complete
        job_ref.update({
            "status": "completed", 
            "result_id": tutorial_data["id"],
            "completed_at": firestore.SERVER_TIMESTAMP
        })
        print(f"✅ Worker: Job {job_id} Finished.")

    except Exception as e:
        print(f"❌ Worker Error: {e}")
        job_ref.update({"status": "failed", "error": str(e)})
        
        # Also update notification to Failure state if possible
        if notification_ref:
            notification_ref.update({
                "type": "error",
                "title": "Generation Failed",
                "message": f"Something went wrong: {str(e)}",
                "read": False
            })
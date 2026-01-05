
import os
import sys
import logging
import json
from firebase_admin import firestore
from app.core.config import settings
from app.core.security import db

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ali_platform.worker")

def main():
    """
    Entry point for the Cloud Run Job.
    Expects environment variables or arguments for the job context.
    Cloud Run Jobs allow passing arguments via the execution command.
    """
    try:
        # 1. Parse Arguments (passed via CLOUD_RUN_TASK_INDEX or custom env vars/args)
        # We expect the job to be triggered with overrides that set specific environment variables
        # or we can read from a queue. For simplicity in this direct trigger model, we'll
        # look for environment variables set during the 'run' call overrides.
        
        job_id = os.environ.get("JOB_ID")
        user_id = os.environ.get("USER_ID")
        topic = os.environ.get("TOPIC")
        notification_id = os.environ.get("NOTIFICATION_ID")

        if not all([job_id, user_id, topic]):
            logger.error("❌ Misisng required environment variables: JOB_ID, USER_ID, TOPIC")
            sys.exit(1)

        logger.info(f"🚀 Starting Cloud Run Job for: {topic} (Job ID: {job_id})")

        # 2. Import the Job Runner Logic
        # We import here to ensure all dependencies are loaded in the fresh container
        from app.services.job_runner import process_tutorial_job

        # 3. Execute the Job
        process_tutorial_job(job_id, user_id, topic, notification_id)

        logger.info("✅ Cloud Run Job Completed Successfully.")
        sys.exit(0)

    except Exception as e:
        logger.critical(f"❌ Cloud Run Job Failed: {e}")
        # Ensure we try to update the DB status if possible before dying
        try:
             if 'job_id' in locals() and db:
                db.collection("jobs").document(job_id).update({
                    "status": "failed", 
                    "error": str(e)
                })
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()

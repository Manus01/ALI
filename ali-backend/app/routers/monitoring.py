from fastapi import APIRouter, Depends, Body, BackgroundTasks
from app.core.security import verify_token, db
from google.cloud import firestore
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/logs/client")
async def ingest_client_logs(payload: dict = Body(...), user: dict = Depends(verify_token)):
    """
    Ingests logs from the Frontend (React/Next.js).
    Payload expected: { "level": "error", "message": "...", "component": "...", "stack": "..." }
    """
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": payload.get("level", "info"),
            "message": payload.get("message"),
            "component": payload.get("component", "frontend"),
            "stack_trace": payload.get("stack"),
            "user_id": user['uid'],
            "user_email": user.get('email'),
            "metadata": payload.get("meta", {})
        }

        # 1. Save to Firestore 'client_logs' for the Watchdog to find
        # We use a Time-Partitioned collection strategy in a real app, 
        # but for now a single collection with TTL is fine.
        db.collection("client_logs").add(log_entry)

        # 2. Log to Backend Console (so Cloud Logging picks it up too)
        # This double-write ensures it appears in 'Backend Logs' queries if we want centralized view
        log_msg = f"📱 CLIENT_LOG [{user['uid']}]: {log_entry['message']}"
        if log_entry['level'] == 'error':
            logger.error(log_msg)
        else:
            logger.info(log_msg)

        return {"status": "ingested"}

    except Exception as e:
        logger.error(f"❌ Failed to ingest client log: {e}")
        # Fail silently to client to not break their flow
        return {"status": "error", "reason": "internal_error"}

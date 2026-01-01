from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.core.security import verify_token, db
from app.services.maintenance_service import run_weekly_maintenance
from google.cloud import firestore

router = APIRouter()

@router.post("/maintenance/run")
def trigger_maintenance(background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    """
    Manually triggers the weekly maintenance loop.
    """
    user_id = user['uid']
    
    # Add "Started" Notification to Bell
    db.collection("users").document(user_id).collection("notifications").add({
        "title": "Maintenance Started",
        "message": "The Gardener is reviewing your curriculum.",
        "type": "info",
        "read": False,
        "created_at": firestore.SERVER_TIMESTAMP
    })

    # Run in background so request doesn't timeout
    background_tasks.add_task(run_weekly_maintenance, user_id)
    
    return {
        "status": "started", 
        "message": "The Gardener is reviewing your curriculum in the background."
    }
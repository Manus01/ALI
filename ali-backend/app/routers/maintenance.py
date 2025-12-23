from fastapi import APIRouter, Depends, BackgroundTasks
from app.core.security import verify_token
from app.services.maintenance_service import run_weekly_maintenance

router = APIRouter()

@router.post("/maintenance/run")
def trigger_maintenance(background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    """
    Manually triggers the weekly maintenance loop.
    """
    # Run in background so request doesn't timeout
    background_tasks.add_task(run_weekly_maintenance, user['uid'])
    
    return {
        "status": "started", 
        "message": "The Gardener is reviewing your curriculum in the background."
    }
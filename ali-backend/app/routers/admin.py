from fastapi import APIRouter, Depends, HTTPException, Body, Query
from app.core.security import verify_token
from app.services.performance_logger import run_nightly_performance_log
from google.cloud import firestore
from typing import Dict, List, Optional
from datetime import datetime

router = APIRouter()
db = firestore.Client()

# --- SECURITY: Simple Admin Check ---
def verify_admin(user: dict = Depends(verify_token)):
    """
    Ensures the requester is a Researcher/Admin.
    For MVP, we hardcode your email or check a custom claim.
    """
    # REPLACE WITH YOUR ACTUAL ADMIN EMAILS
    ADMIN_EMAILS = ["manoliszografos@gmail.com"] 
    
    if user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Research Access Only")
    return user

# --- USER MANAGEMENT ---

@router.post("/users/link-metricool")
def admin_link_metricool(payload: Dict[str, str] = Body(...), admin: dict = Depends(verify_admin)):
    """
    Step 2 of Flow: Admin manually inputs the blogId for a user after they accept the invite.
    Payload: { "target_user_id": "...", "metricool_blog_id": "12345" }
    """
    target_uid = payload.get("target_user_id")
    blog_id = payload.get("metricool_blog_id")
    
    if not target_uid or not blog_id:
        raise HTTPException(400, "Missing user_id or blog_id")
        
    # Update/Create the integration record
    doc_ref = db.collection("user_integrations").document(f"{target_uid}_metricool")
    doc_ref.set({
        "user_id": target_uid,
        "platform": "metricool",
        "status": "active",
        "metricool_blog_id": blog_id,
        "linked_by_admin": admin['email'],
        "linked_at": datetime.utcnow().isoformat()
    }, merge=True)
    
    return {"status": "success", "message": f"User {target_uid} linked to Brand {blog_id}"}

# --- RESEARCH DATA ACCESS ---

@router.get("/research/logs")
def get_performance_logs(target_user_id: Optional[str] = None, days: int = 30, admin: dict = Depends(verify_admin)):
    """
    Retrieves the historical performance data for analysis.
    Can filter by specific user or return all (for aggregate study).
    """
    logs_ref = db.collection("ad_performance_logs")
    
    if target_user_id:
        query = logs_ref.where("user_id", "==", target_user_id).order_by("date").limit(days)
    else:
        # Warning: Getting ALL logs might be heavy later, but fine for now
        query = logs_ref.order_by("date").limit(100)
        
    docs = query.stream()
    results = [doc.to_dict() for doc in docs]
    
    return {"count": len(results), "data": results}

# --- MANUAL TRIGGER ---

@router.post("/jobs/trigger-nightly-log")
def trigger_logging_job(admin: dict = Depends(verify_admin)):
    """
    Manually triggers the data fetch job (e.g., if Cron failed or for testing).
    """
    result = run_nightly_performance_log()
    return result
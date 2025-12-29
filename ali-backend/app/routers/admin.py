from fastapi import APIRouter, Depends, HTTPException, Body
from app.core.security import verify_token
from app.services.performance_logger import run_nightly_performance_log
from app.services.metricool_client import MetricoolClient
from google.cloud import firestore
from datetime import datetime
from typing import Dict, Optional

router = APIRouter()
db = firestore.Client()

def verify_admin(user: dict = Depends(verify_token)):
    if user.get("email") not in ["manoliszografos@gmail.com"]:
        raise HTTPException(status_code=403, detail="Research Access Only")
    return user

@router.post("/users/link-metricool")
def admin_link_metricool(payload: Dict[str, str] = Body(...), admin: dict = Depends(verify_admin)):
    target_uid = payload.get("target_user_id")
    blog_id = payload.get("metricool_blog_id")
    
    # SECURE FIX: Save to users/{uid}/user_integrations/metricool
    doc_ref = db.collection("users").document(target_uid).collection("user_integrations").document("metricool")
    doc_ref.set({
        "user_id": target_uid, "platform": "metricool", "status": "active",
        "metricool_blog_id": blog_id, "linked_at": datetime.utcnow().isoformat()
    }, merge=True)

    # Mark the admin task as completed
    db.collection("admin_tasks").document(f"connect_{target_uid}").update({"status": "completed"})
    return {"status": "success"}

@router.get("/users/{target_uid}/verify-channels")
def verify_user_channels(target_uid: str, admin: dict = Depends(verify_admin)):
    doc = db.collection("users").document(target_uid).collection("user_integrations").document("metricool").get()
    blog_id = doc.to_dict().get("metricool_blog_id") if doc.exists else None
    if not blog_id: return {"connected_channels": []}
    client = MetricoolClient(blog_id=blog_id)
    return {"connected_channels": client.get_account_info().get("connected", [])}

# PRESERVED: Original PhD Data Access
@router.get("/research/logs")
def get_performance_logs(target_user_id: Optional[str] = None, admin: dict = Depends(verify_admin)):
    query = db.collection("ad_performance_logs").order_by("date").limit(100)
    return {"data": [doc.to_dict() for doc in query.stream()]}

# PRESERVED: Original Nightly Job Trigger
@router.post("/jobs/trigger-nightly-log")
def trigger_logging_job(admin: dict = Depends(verify_admin)):
    return run_nightly_performance_log()
from fastapi import APIRouter, Depends, HTTPException, Body
from app.core.security import verify_token
from google.cloud import firestore
from datetime import datetime

router = APIRouter()
db = firestore.Client()

@router.get("/integrations")
def get_integrations(user: dict = Depends(verify_token)):
    user_id = user['uid']
    # SECURE PATH: Point to user-scoped sub-collection
    docs = db.collection("users").document(user_id).collection("user_integrations").stream()
    
    statuses = {}
    for doc in docs:
        d = doc.to_dict()
        platform = d.get("platform")
        if platform == 'metricool':
            statuses[platform] = "active" if d.get("metricool_blog_id") else "pending"
        else:
            statuses[platform] = d.get("status")
    return statuses

@router.post("/connect/metricool/request")
def request_metricool_access(user: dict = Depends(verify_token)):
    user_id = user['uid']
    user_email = user.get("email")
    doc_ref = db.collection("users").document(user_id).collection("user_integrations").document("metricool")
    
    if doc_ref.get().exists and doc_ref.get().to_dict().get("metricool_blog_id"):
        return {"status": "already_active", "message": "Already connected."}

    # 1. Update User's private folder
    doc_ref.set({
        "user_id": user_id, "platform": "metricool", "status": "pending", 
        "metricool_blog_id": None, "requested_at": datetime.utcnow().isoformat()
    })
    
    # 2. 🔔 SIGNAL ADMIN: Create task in global collection
    db.collection("admin_tasks").document(f"connect_{user_id}").set({
        "type": "METRICOOL_REQUEST",
        "user_id": user_id,
        "user_email": user_email,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    })
    return {"status": "success", "message": "Access requested."}

@router.delete("/connect/{platform}")
def disconnect_platform(platform: str, user: dict = Depends(verify_token)):
    db.collection("users").document(user['uid']).collection("user_integrations").document(platform).delete()
    return {"status": "disconnected"}
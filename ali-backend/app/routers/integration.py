from fastapi import APIRouter, Depends, HTTPException, Body
from app.core.security import verify_token
from app.services.crypto_service import CryptoService
from app.services.metricool_client import MetricoolClient
from google.cloud import firestore
from datetime import datetime
from typing import Dict

router = APIRouter()
crypto_service = CryptoService()
db = firestore.Client()

# --- 1. GET STATUSES (SECURE PATH) ---
@router.get("/integrations")
def get_integrations(user: dict = Depends(verify_token)):
    """
    Checks the status of integrations within the user's secure sub-collection.
    """
    user_id = user['uid']
    
    # SENIOR DEV FIX: Point to the user-scoped sub-collection
    # users/{user_id}/user_integrations
    docs = db.collection("users").document(user_id).collection("user_integrations").stream()
    
    statuses = {}
    for doc in docs:
        d = doc.to_dict()
        platform = d.get("platform")
        
        if platform == 'metricool':
            # Check if Admin has populated the blog_id yet
            if d.get("metricool_blog_id"):
                statuses[platform] = "active"
            else:
                statuses[platform] = "pending"
        else:
            statuses[platform] = d.get("status")
    
    return statuses

# --- 2. REQUEST METRICOOL (SECURE PATH) ---
@router.post("/connect/metricool/request")
def request_metricool_access(user: dict = Depends(verify_token)):
    """
    Creates a placeholder doc inside the user's private folder.
    """
    user_id = user['uid']
    
    # SENIOR DEV FIX: Save directly into the user's private sub-collection
    doc_ref = db.collection("users").document(user_id).collection("user_integrations").document("metricool")
    
    # Don't overwrite if already active
    doc = doc_ref.get()
    if doc.exists and doc.to_dict().get("metricool_blog_id"):
        return {"status": "already_active", "message": "Already connected."}

    # Set status to pending. 
    # ADMIN NOTE: To activate, go to users/{user_id}/user_integrations/metricool 
    # and add the 'metricool_blog_id' field.
    doc_ref.set({
        "user_id": user_id,
        "platform": "metricool",
        "status": "pending", 
        "metricool_blog_id": None,
        "requested_at": datetime.utcnow().isoformat()
    })
    
    return {"status": "success", "message": "Access requested. Check your email."}

# --- 3. DISCONNECT (SECURE PATH) ---
@router.delete("/connect/{platform}")
def disconnect_platform(platform: str, user: dict = Depends(verify_token)):
    try:
        user_id = user['uid']
        # SENIOR DEV FIX: Target the document inside the user's private folder
        db.collection("users").document(user_id).collection("user_integrations").document(platform).delete()
        return {"status": "disconnected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
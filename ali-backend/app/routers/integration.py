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

# --- 1. GET STATUSES ---
@router.get("/integrations")
def get_integrations(user: dict = Depends(verify_token)):
    """
    Checks the status of the Metricool integration.
    - If no doc exists: Status is None (User sees "Request Access").
    - If doc exists & blog_id is missing: Status is 'pending' (User sees "Check Email").
    - If doc exists & blog_id is present: Status is 'active' (User sees Green Check).
    """
    user_id = user['uid']
    docs = db.collection("user_integrations").where("user_id", "==", user_id).stream()
    
    statuses = {}
    for doc in docs:
        d = doc.to_dict()
        platform = d.get("platform")
        
        # Special logic for Metricool manual flow
        if platform == 'metricool':
            # Check if Admin has populated the blog_id yet
            if d.get("metricool_blog_id"):
                statuses[platform] = "active"
            else:
                statuses[platform] = "pending"
        else:
            statuses[platform] = d.get("status")
    
    return statuses

# --- 2. REQUEST METRICOOL (Trigger State A) ---
@router.post("/connect/metricool/request")
def request_metricool_access(user: dict = Depends(verify_token)):
    """
    User clicks 'Request Access'. 
    We create a placeholder doc so Admins know to send the invite.
    """
    user_id = user['uid']
    doc_ref = db.collection("user_integrations").document(f"{user_id}_metricool")
    
    # Don't overwrite if already active
    doc = doc_ref.get()
    if doc.exists and doc.to_dict().get("metricool_blog_id"):
        return {"status": "already_active", "message": "Already connected."}

    # Set status to pending. 
    # ADMIN INSTRUCTION: Admin must manually edit this doc in Firestore 
    # and add the field 'metricool_blog_id' (int/string) to activate.
    doc_ref.set({
        "user_id": user_id,
        "platform": "metricool",
        "status": "pending", 
        "metricool_blog_id": None, # Waiting for Admin to fill this
        "requested_at": datetime.utcnow().isoformat()
    })
    
    return {"status": "success", "message": "Access requested. Check your email."}

# --- 3. DISCONNECT ---
@router.delete("/connect/{platform}")
def disconnect_platform(platform: str, user: dict = Depends(verify_token)):
    try:
        doc_id = f"{user['uid']}_{platform}"
        db.collection("user_integrations").document(doc_id).delete()
        return {"status": "disconnected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
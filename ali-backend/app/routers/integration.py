from fastapi import APIRouter, Body, Depends, HTTPException, Request
from app.core.security import verify_token, db
from app.services.metricool_client import MetricoolClient
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/integrations/status")
def get_integrations(user: dict = Depends(verify_token)):
    user_id = user['uid']
    # SECURE PATH: Point to user-scoped sub-collection
    docs = db.collection("users").document(user_id).collection("user_integrations").stream()
    
    statuses = {}
    for doc in docs:
        d = doc.to_dict()
        platform = d.get("platform")
        if platform == 'metricool':
            # Trust the status field explicitly
            statuses[platform] = d.get("status", "pending")
        else:
            statuses[platform] = d.get("status")
    return statuses

@router.post("/connect/metricool/request")
def request_metricool_access(user: dict = Depends(verify_token)):
    user_id = user['uid']
    user_email = user.get("email")
    doc_ref = db.collection("users").document(user_id).collection("user_integrations").document("metricool")
    
    doc_snapshot = doc_ref.get()
    if doc_snapshot.exists:
        data = doc_snapshot.to_dict()
        # 1. Check if already active
        if data.get("status") == "active":
            return {"status": "already_active", "message": "Already connected."}

        # 2. Smart Reconnect: If we have a blog_id, try to re-validate it
        existing_blog_id = data.get("metricool_blog_id")
        if existing_blog_id:
            try:
                # Validate with Metricool
                client = MetricoolClient(blog_id=existing_blog_id)
                status = client.get_brand_status(existing_blog_id)
                if status:
                    # ✅ VALID: Instant Reconnect
                    doc_ref.set({
                        "status": "active",
                        "connected_providers": [], # Will be re-fetched by next status call
                        "reconnected_at": datetime.utcnow().isoformat()
                    }, merge=True)
                    return {"status": "restored", "message": "Access restored successfully."}
            except Exception as e:
                logger.warning(f"Smart reconnect failed for {user_id}: {e}")
                # Fall through to normal request flow if validation fails

    # 3. Standard Flow: Create/Update User's private folder
    doc_ref.set({
        "user_id": user_id, "platform": "metricool", "status": "pending", 
        "requested_at": datetime.utcnow().isoformat()
    }, merge=True)
    
    # 4. 🔔 SIGNAL ADMIN: Create task in global collection
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
    # Soft Disconnect: Keep the ID so we can re-connect easily later without Admin intervention
    db.collection("users").document(user['uid']).collection("user_integrations").document(platform).update({
        "status": "disconnected"
    })
    return {"status": "disconnected"}

@router.get("/connect/metricool/status")
def get_metricool_status(user: dict = Depends(verify_token)):
    """
    Fetches detailed status including connected providers from Metricool.
    """
    try:
        user_id = user['uid']
        doc = db.collection("users").document(user_id).collection("user_integrations").document("metricool").get()
        
        if not doc.exists:
            return {"status": "not_connected", "connected_providers": []}
            
        data = doc.to_dict()
        blog_id = data.get("metricool_blog_id")
        
        if not blog_id:
            return {"status": "pending", "connected_providers": []}
            
        # Fetch live data from Metricool
        try:
            client = MetricoolClient(blog_id=blog_id)
            info = client.get_account_info()
            connected = info.get("connected", [])
            
            # CACHE UPDATE: Sync to Firestore for Admin Visibility
            doc.reference.update({"connected_providers": connected})
            
            return {
                "status": "active", 
                "connected_providers": connected,
                "blog_id": blog_id
            }
        except Exception as e:
            logger.warning(f"⚠️ Metricool Status Fetch Error: {e}")
            # Return active but with error note, so UI doesn't break
            return {"status": "active", "connected_providers": data.get("connected_providers", []), "error": "Could not fetch live providers"}
            
    except Exception as e:
        logger.error(f"❌ Metricool Status Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrations/report-error")
def report_integration_error(payload: dict = Body(...), user: dict = Depends(verify_token)):
    """Record integration issues for admin visibility without surfacing to the user UI."""
    message = payload.get("message", "Unknown integration error")
    context = payload.get("context", "metricool")

    logger.error(f"🚨 [INTEGRATION_ERROR] {context}: {message} (User: {user.get('email')})")
    
    # We no longer save to 'admin_alerts'. 
    # The TroubleshootingAgent will pick this up from Cloud Logging (backend logs).

    return {"status": "recorded"}

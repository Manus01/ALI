from fastapi import APIRouter, Depends, HTTPException, Body
from app.core.security import verify_token, db
from app.services.metricool_client import MetricoolClient
from app.services.performance_logger import run_nightly_performance_log
from typing import Dict, Optional, List
from datetime import datetime
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def verify_admin(user: dict = Depends(verify_token)):
    if user.get("email") not in ["manoliszografos@gmail.com"]:
        raise HTTPException(status_code=403, detail="Research Access Only")
    return user


# --- AUDIT TRAIL LOGGING (Spec: Unified Governance) ---
def log_audit_action(
    admin_id: str,
    admin_email: str,
    action: str,
    target_id: str,
    target_type: str,
    details: Dict = None
):
    """
    Logs admin governance actions to 'audit_logs' collection.
    Every approval/denial/publish action is recorded for compliance.
    """
    try:
        audit_entry = {
            "adminId": admin_id,
            "adminEmail": admin_email,
            "action": action,
            "targetId": target_id,
            "targetType": target_type,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "details": details or {}
        }
        db.collection("audit_logs").add(audit_entry)
        logger.info(f"📝 Audit: {admin_email} performed '{action}' on {target_type}/{target_id}")
    except Exception as e:
        logger.error(f"❌ Audit Log Error: {e}")


@router.post("/users/link-metricool")
def admin_link_metricool(payload: Dict[str, str] = Body(...), admin: dict = Depends(verify_admin)):
    target_uid = payload.get("target_user_id")
    blog_id = payload.get("metricool_blog_id")
    
    if not target_uid or not blog_id:
        raise HTTPException(status_code=400, detail="Missing target_user_id or metricool_blog_id")
    
    try:
        # 1. Update the integration record in the private user folder
        doc_ref = db.collection("users").document(target_uid).collection("user_integrations").document("metricool")
        existing_doc = doc_ref.get()
        previous_blog_id = existing_doc.to_dict().get("metricool_blog_id") if existing_doc.exists else None
        doc_ref.set({
            "user_id": target_uid,
            "platform": "metricool",
            "status": "active",
            "metricool_blog_id": blog_id,
            "linked_at": datetime.utcnow().isoformat()
        }, merge=True)

        # 2. 🔔 Send "Success" Notification to the User's secure feed
        notification_ref = db.collection("users").document(target_uid).collection("notifications").document("integration_success")
        notification_ref.set({
            "title": "Platform Linked! 🚀",
            "message": "Your Social Media Suite is now active. You can now create campaigns.",
            "type": "success",
            "read": False,
            "created_at": datetime.utcnow()
        })

        if previous_blog_id and previous_blog_id != blog_id:
            doc_ref.update({
                "previous_metricool_blog_ids": firestore.ArrayUnion([previous_blog_id]),
                "connection_mismatch_detected_at": datetime.utcnow().isoformat()
            })
            mismatch_ref = db.collection("users").document(target_uid).collection("notifications").document("integration_mismatch")
            mismatch_ref.set({
                "title": "Connection Updated",
                "message": "We detected a different social account than before. If this wasn't intended, please reconnect or contact support.",
                "type": "warning",
                "read": False,
                "created_at": datetime.utcnow()
            })

        # 3. Mark the admin task as completed (use set with merge to avoid error if doc doesn't exist)
        db.collection("admin_tasks").document(f"connect_{target_uid}").set({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat()
        }, merge=True)
        
        return {"status": "success", "message": "User linked and notified."}
    
    except Exception as e:
        logger.error(f"❌ Link Metricool Error for {target_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to link user: {str(e)}")

@router.get("/users/{target_uid}/verify-channels")
def verify_user_channels(target_uid: str, admin: dict = Depends(verify_admin)):
    try:
        doc = db.collection("users").document(target_uid).collection("user_integrations").document("metricool").get()
        blog_id = doc.to_dict().get("metricool_blog_id") if doc.exists else None
        
        if not blog_id: 
            return {"connected_channels": []}
            
        # Ensure MetricoolClient doesn't crash if init fails
        try:
            client = MetricoolClient(blog_id=blog_id)
            info = client.get_account_info()
            
            # CACHE UPDATE: Sync to Firestore
            if info.get("connected"):
                db.collection("users").document(target_uid).collection("user_integrations").document("metricool").update({
                    "connected_providers": info.get("connected")
                })
            
            # Handle case where get_account_info returns None or error dict
            if not info or "error" in info:
                logger.error(f"?? Metricool API Error for {target_uid}: {info}")
                return {"connected_channels": [], "error": "Metricool API unavailable"}
                
            return {"connected_channels": info.get("connected", [])}
        except Exception as e:
            logger.error(f"? Metricool Client Error: {e}")
            return {"connected_channels": [], "error": str(e)}
            
    except Exception as e:
        logger.error(f"? Verify Channels Error: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

# PRESERVED: Original PhD Data Access
@router.get("/research/logs")
def get_performance_logs(target_user_id: Optional[str] = None, admin: dict = Depends(verify_admin)):
    query = db.collection("ad_performance_logs").order_by("date").limit(100)
    return {"data": [doc.to_dict() for doc in query.stream()]}


# /integration-alerts endpoint removed

@router.get("/research/users")
def get_research_users(admin: dict = Depends(verify_admin)):
    """
    Aggregates user statistics for the Research Admin Dashboard.
    Returns: List of users with Profile, Integrations, and Performance Stats.
    """
    users_ref = db.collection("users").limit(100) # Increased limit for better visibility
    users = users_ref.stream()
    
    results = []
    for user_doc in users:
        uid = user_doc.id
        data = user_doc.to_dict()
        profile = data.get("profile", {})
        
        # 1. Integrations
        integrations = []
        int_docs = db.collection("users").document(uid).collection("user_integrations").stream()
        for d in int_docs:
            i_data = d.to_dict()
            if i_data.get("status") == "active" or i_data.get("metricool_blog_id"):
                integrations.append(i_data.get("platform", "unknown"))
        
        # 2. Performance (Quick Aggregation)
        # Note: In a real app, this should be pre-calculated. Here we scan the last 20 logs.
        perf_docs = db.collection("users").document(uid).collection("campaign_performance").limit(20).stream()
        total_spend = 0.0
        total_clicks = 0
        count = 0
        
        # New: Get Active Channels directly from Integration Status if available
        active_channels = set()
        
        # Check metricool integration doc for cached connection data
        metricool_doc = db.collection("users").document(uid).collection("user_integrations").document("metricool").get()
        if metricool_doc.exists:
            m_data = metricool_doc.to_dict()
            if m_data.get("status") == "active":
                for provider in m_data.get("connected_providers", []):
                    active_channels.add(provider)
        
        for p in perf_docs:
            p_data = p.to_dict()
            total_spend += float(p_data.get("spend", 0))
            total_clicks += int(p_data.get("clicks", 0))
            count += 1
            
        avg_ctr = 0
        if count > 0:
            # Simple average of CTRs might be misleading, but sufficient for "at a glance"
            # Better: Total Clicks / Total Impressions (if we had impressions)
            pass 

        # 3. Get ads_generated from root-level stats (Atomic Counter)
        user_stats = data.get("stats", {})
        ads_generated = user_stats.get("ads_generated", 0)
        
        results.append({
            "uid": uid,
            "email": data.get("email", "Unknown"),
            "name": data.get("name", "Anonymous"),
            "learning_style": profile.get("cognitive_style", "Not Assessed"),
            "marketing_level": profile.get("marketing_knowledge", "N/A"),
            "connected_platforms": integrations,
            "active_channels": list(active_channels),
            "stats": {
                "total_spend": round(total_spend, 2),
                "total_clicks": total_clicks,
                "data_points": count,
                "ads_generated": ads_generated
            }
        })
        
    return {"users": results}

# PRESERVED: Original Nightly Job Trigger
@router.post("/jobs/trigger-nightly-log")
def trigger_logging_job(admin: dict = Depends(verify_admin)):
    return run_nightly_performance_log()

@router.get("/users/{target_uid}/analytics")
def get_user_analytics(target_uid: str, user: dict = Depends(verify_token)):
    """
    Fetches Metricool Analytics (Clicks, CTR, Spend) for a specific user.
    Accessible by the user themselves or an admin.
    """
    # Security Check: User can only access their own data unless they are admin
    if user['uid'] != target_uid and user.get("email") not in ["manoliszografos@gmail.com"]:
        raise HTTPException(status_code=403, detail="Unauthorized access to user analytics")

    try:
        # 1. Fetch metricool_blog_id
        doc = db.collection("users").document(target_uid).collection("user_integrations").document("metricool").get()
        if not doc.exists:
            return {"clicks": 0, "spend": 0.0, "ctr": 0.0, "status": "not_connected"}
            
        data = doc.to_dict()
        blog_id = data.get("metricool_blog_id")
        
        if not blog_id:
            return {"clicks": 0, "spend": 0.0, "ctr": 0.0, "status": "no_blog_id"}

        # 2. Fetch Stats from Metricool
        client = MetricoolClient(blog_id=blog_id)
        stats = client.get_ads_stats(blog_id)
        
        return stats

    except Exception as e:
        logger.error(f"❌ Analytics Fetch Error: {e}")
        # Return zero state instead of 500 to prevent frontend crash
        return {"clicks": 0, "spend": 0.0, "ctr": 0.0, "error": str(e)}

@router.get("/tutorials")
def get_all_tutorials(admin: dict = Depends(verify_admin)):
    """
    Fetches ALL generated tutorials for the Admin Dashboard.
    Enriches with User Email for identification.
    """
    try:
        # Fetch all global tutorials
        tutorials_ref = db.collection("tutorials").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(100)
        tutorials = tutorials_ref.stream()
        
        results = []
        user_cache = {} # Cache user emails to reduce reads

        for doc in tutorials:
            data = doc.to_dict()
            owner_id = data.get("owner_id")
            
            # Resolve User Email
            user_email = "Unknown"
            if owner_id:
                if owner_id in user_cache:
                    user_email = user_cache[owner_id]
                else:
                    user_doc = db.collection("users").document(owner_id).get()
                    if user_doc.exists:
                        user_email = user_doc.to_dict().get("email", "Unknown")
                        user_cache[owner_id] = user_email
            
            results.append({
                "id": doc.id,
                "title": data.get("title", "Untitled"),
                "owner_id": owner_id,
                "owner_email": user_email,
                "category": data.get("category", "General"),
                "created_at": data.get("timestamp")
            })
            
        return {"tutorials": results}
    except Exception as e:
        logger.error(f"❌ Admin Tutorials Fetch Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tutorials/{tutorial_id}")
def delete_tutorial(tutorial_id: str, admin: dict = Depends(verify_admin)):
    """
    Hard Deletes a tutorial from:
    1. Global 'tutorials' collection
    2. User's private 'users/{uid}/tutorials' subcollection
    """
    try:
        # 1. Get Global Doc to find Owner
        global_ref = db.collection("tutorials").document(tutorial_id)
        doc = global_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Tutorial not found")
            
        owner_id = doc.to_dict().get("owner_id")
        
        # 2. Delete Global
        global_ref.delete()
        
        # 3. Delete Private (if owner exists)
        if owner_id:
            private_ref = db.collection("users").document(owner_id).collection("tutorials").document(tutorial_id)
            private_ref.delete()
            
        return {"status": "success", "message": "Tutorial deleted successfully"}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"❌ Admin Tutorial Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/research/troubleshoot")
def trigger_troubleshooting_agent(admin: dict = Depends(verify_admin)):
    """
    Triggers the AI Troubleshooting Agent to:
    1. Scan Backend Logs (last 24h) for ERRORS
    2. Analyze them with Gemini + Web Search
    3. File 'error_report' tasks in Admin Dashboard
    """
    from app.agents.troubleshooting_agent import TroubleshootingAgent
    try:
        agent = TroubleshootingAgent()
        report = agent.run_troubleshooter()
        return report
    except Exception as e:
        logger.error(f"❌ Troubleshooter Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/reports")
def get_admin_reports(limit: int = 50, admin: dict = Depends(verify_admin)):
    """
    Fetches AI Troubleshooting Reports from 'admin_tasks'.
    Uses single-field sort on 'created_at' to avoid composite index requirements.
    """
    try:
        # WORKAROUND: Query by created_at only (Single Field Index) then filter by type in memory.
        # This avoids the strict composite index requirement (type + created_at) which causes 400s.
        # We fetch 5x the limit to ensure we find enough error reports mingled with other tasks.
        tasks_ref = db.collection("admin_tasks")\
                      .order_by("created_at", direction=firestore.Query.DESCENDING)\
                      .limit(limit * 5)
        
        tasks = []
        for doc in tasks_ref.stream():
            t = doc.to_dict()
            # In-memory Filter
            if t.get("type") == "error_report":
                t["id"] = doc.id
                tasks.append(t)
                if len(tasks) >= limit:
                    break
            
        return {"reports": tasks}
    except Exception as e:
        logger.error(f"❌ Fetch Reports Error: {e}")
        return {"reports": [], "error": str(e)}

@router.get("/metricool/brands")
def get_metricool_brands(admin: dict = Depends(verify_admin)):
    """
    Fetches all available Metricool Brands for the dropdown selector.
    """
    try:
        client = MetricoolClient()
        brands = client.get_all_brands()
        # Simplify for frontend
        results = []
        for b in brands:
            results.append({
                "id": b.get("id") or b.get("blogId"),
                "name": b.get("name") or "Unnamed Brand",
                "provider": b.get("mainProvider", "unknown")
            })
        return {"brands": results}
    except Exception as e:
        logger.error(f"❌ Fetch Brands Error: {e}")
        return {"brands": []}

@router.get("/tasks/pending")
def get_pending_tasks(admin: dict = Depends(verify_admin)):
    """
    Fetches pending Metricool connection requests.
    """
    try:
        tasks_ref = db.collection("admin_tasks")\
                      .where(filter=FieldFilter("type", "==", "METRICOOL_REQUEST"))\
                      .where(filter=FieldFilter("status", "==", "pending"))\
                      .limit(20)
        
        tasks = []
        for doc in tasks_ref.stream():
            t = doc.to_dict()
            t["id"] = doc.id
            tasks.append(t)
            
        return {"tasks": tasks}
    except Exception as e:
        logger.error(f"❌ Fetch Pending Tasks Error: {e}")
        return {"tasks": []}

@router.delete("/tasks/{task_id}")
def delete_admin_task(task_id: str, admin: dict = Depends(verify_admin)):
    """
    Deletes an admin task (e.g., Error Report) from the 'admin_tasks' collection.
    """
    try:
        db.collection("admin_tasks").document(task_id).delete()
        return {"status": "success", "message": "Task deleted."}
    except Exception as e:
        logger.error(f"❌ Delete Task Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/connections")
def get_established_connections(admin: dict = Depends(verify_admin)):
    """
    Fetches all users with established Metricool connections.
    Returns: List of connected users with their linked brand info.
    """
    try:
        users_ref = db.collection("users").limit(200)
        users = users_ref.stream()
        
        connections = []
        for user_doc in users:
            uid = user_doc.id
            user_data = user_doc.to_dict()
            
            # Check for Metricool integration
            metricool_doc = db.collection("users").document(uid).collection("user_integrations").document("metricool").get()
            if metricool_doc.exists:
                m_data = metricool_doc.to_dict()
                blog_id = m_data.get("metricool_blog_id")
                if blog_id and m_data.get("status") == "active":
                    connections.append({
                        "uid": uid,
                        "email": user_data.get("email", "Unknown"),
                        "name": user_data.get("name", "Anonymous"),
                        "blog_id": blog_id,
                        "linked_at": m_data.get("linked_at"),
                        "connected_providers": m_data.get("connected_providers", [])
                    })
        
        return {"connections": connections}
    except Exception as e:
        logger.error(f"❌ Fetch Connections Error: {e}")
        return {"connections": [], "error": str(e)}


# --- TUTORIAL REQUEST MANAGEMENT (Spec v1.2 §4.1 Admin-Gated) ---

@router.get("/tutorial-requests")
def get_tutorial_requests(status: Optional[str] = None, admin: dict = Depends(verify_admin)):
    """
    Fetches pending/approved tutorial requests for admin approval queue.
    """
    try:
        query = db.collection("tutorial_requests")
        
        if status:
            query = query.where(filter=FieldFilter("status", "==", status))
        
        # Order by creation time, newest first
        query = query.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(50)
        
        requests = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            requests.append(data)
        
        return {"requests": requests}
    except Exception as e:
        logger.error(f"❌ Fetch Tutorial Requests Error: {e}")
        return {"requests": [], "error": str(e)}


@router.post("/tutorial-requests/{request_id}/approve")
def approve_tutorial_request(request_id: str, admin: dict = Depends(verify_admin)):
    """
    Approve a tutorial request for generation.
    """
    try:
        doc_ref = db.collection("tutorial_requests").document(request_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Request not found")
        
        data = doc.to_dict()
        if data.get("status") != "PENDING":
            raise HTTPException(status_code=400, detail=f"Request already {data.get('status')}")
        
        doc_ref.update({
            "status": "APPROVED",
            "adminDecision": {
                "action": "approved",
                "approvedBy": admin.get("email"),
                "approvedAt": firestore.SERVER_TIMESTAMP
            }
        })
        
        # Notify user
        user_id = data.get("userId")
        if user_id:
            db.collection("users").document(user_id).collection("notifications").document(f"{request_id}_approved").set({
                "user_id": user_id,
                "type": "success",
                "title": "Request Approved!",
                "message": f"Your tutorial request for '{data.get('topic')}' has been approved and is queued for generation.",
                "read": False,
                "created_at": firestore.SERVER_TIMESTAMP
            })
        
        logger.info(f"✅ Tutorial request {request_id} approved by {admin.get('email')}")
        
        # Audit Trail
        log_audit_action(
            admin_id=admin.get("uid", "unknown"),
            admin_email=admin.get("email"),
            action="APPROVE_TUTORIAL_REQUEST",
            target_id=request_id,
            target_type="tutorialRequest",
            details={"topic": data.get("topic"), "userId": data.get("userId")}
        )
        
        return {"status": "APPROVED", "message": "Request approved. Ready for generation."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Approve Request Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tutorial-requests/{request_id}/deny")
def deny_tutorial_request(request_id: str, reason: Optional[str] = None, admin: dict = Depends(verify_admin)):
    """
    Deny a tutorial request.
    """
    try:
        doc_ref = db.collection("tutorial_requests").document(request_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Request not found")
        
        data = doc.to_dict()
        
        doc_ref.update({
            "status": "DENIED",
            "adminDecision": {
                "action": "denied",
                "deniedBy": admin.get("email"),
                "deniedAt": firestore.SERVER_TIMESTAMP,
                "reason": reason or "Request not approved"
            }
        })
        
        # Notify user
        user_id = data.get("userId")
        if user_id:
            db.collection("users").document(user_id).collection("notifications").add({
                "user_id": user_id,
                "type": "warning",
                "title": "Request Declined",
                "message": f"Your tutorial request for '{data.get('topic')}' was not approved. Reason: {reason or 'Not specified'}",
                "read": False,
                "created_at": firestore.SERVER_TIMESTAMP
            })
        
        logger.info(f"❌ Tutorial request {request_id} denied by {admin.get('email')}")
        
        # Audit Trail
        log_audit_action(
            admin_id=admin.get("uid", "unknown"),
            admin_email=admin.get("email"),
            action="DENY_TUTORIAL_REQUEST",
            target_id=request_id,
            target_type="tutorialRequest",
            details={"topic": data.get("topic"), "reason": reason or "Not specified"}
        )
        
        return {"status": "DENIED", "message": "Request denied."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Deny Request Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tutorial-requests/{request_id}/generate")
def trigger_request_generation(request_id: str, admin: dict = Depends(verify_admin)):
    """
    Trigger generation for an approved request.
    This endpoint creates a generation job and updates the request status.
    
    SAGA MAP INTEGRATION (v2.2 §4.3):
    - Assigns generated tutorial to default Course/Module
    - Updates Module's tutorialIds for learner path tracking
    - Enables ProgressRecord calculation after completion
    """
    try:
        doc_ref = db.collection("tutorial_requests").document(request_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Request not found")
        
        data = doc.to_dict()
        if data.get("status") != "APPROVED":
            raise HTTPException(status_code=400, detail=f"Request must be APPROVED first. Current: {data.get('status')}")
        
        # Update status to GENERATING
        doc_ref.update({"status": "GENERATING"})
        
        # Create generation job
        topic = data.get("topic")
        user_id = data.get("userId")
        
        job_ref = db.collection("jobs").document()
        job_id = job_ref.id
        
        # --- SAGA MAP INTEGRATION ---
        # Get or create default Course/Module for the generated tutorial
        saga_map_data = None
        try:
            from app.services.saga_map_service import get_saga_map_service
            saga_service = get_saga_map_service()
            
            default_course = saga_service.get_or_create_default_course("default")
            default_module = saga_service.get_or_create_default_module(default_course.get("id"))
            
            saga_map_data = {
                "courseId": default_course.get("id"),
                "moduleId": default_module.get("id"),
            }
            
            logger.info(f"🗺️ Saga Map: Tutorial will be assigned to Course '{default_course.get('title')}' / Module '{default_module.get('title')}'")
        except Exception as saga_err:
            logger.warning(f"⚠️ Saga Map integration skipped (non-fatal): {saga_err}")
            saga_map_data = {}
        
        job_ref.set({
            "id": job_id,
            "user_id": user_id,
            "type": "tutorial_generation",
            "topic": topic,
            "status": "queued",
            "request_id": request_id,  # Link back to request
            "created_at": firestore.SERVER_TIMESTAMP,
            "triggered_by": admin.get("email"),
            # Saga Map metadata for the job
            **saga_map_data
        })
        
        # Create notification for user
        notification_ref = db.collection("users").document(user_id).collection("notifications").document(job_id)
        notification_ref.set({
            "user_id": user_id,
            "type": "info",
            "status": "generating",
            "title": "Tutorial Generation Started",
            "message": f"'{topic}' is now being generated. You'll be notified when ready.",
            "read": False,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        
        # Trigger background job (imports here to avoid circular dependencies)
        from app.services.job_runner import process_tutorial_job
        import threading
        
        def run_job():
            try:
                result = process_tutorial_job(job_id, user_id, topic, notification_ref.id)
                
                # Get the actual tutorial ID from the job result
                tutorial_id = result.get("result_id", job_id) if isinstance(result, dict) else job_id
                
                # --- SAGA MAP: Update Module's tutorialIds ---
                if saga_map_data.get("moduleId"):
                    try:
                        module_ref = db.collection("modules").document(saga_map_data["moduleId"])
                        module_ref.update({
                            "tutorialIds": firestore.ArrayUnion([tutorial_id]),
                            "updatedAt": datetime.utcnow().isoformat()
                        })
                        logger.info(f"🗺️ Saga Map: Added tutorial {tutorial_id} to module {saga_map_data['moduleId']}")
                    except Exception as module_err:
                        logger.warning(f"⚠️ Failed to update module tutorialIds: {module_err}")
                
                # --- SAGA MAP: Assign courseId/moduleId to the tutorial document ---
                if saga_map_data:
                    try:
                        # Update global tutorial
                        db.collection("tutorials").document(tutorial_id).update({
                            "courseId": saga_map_data.get("courseId"),
                            "moduleId": saga_map_data.get("moduleId"),
                        })
                        # Update user's private copy
                        db.collection("users").document(user_id).collection("tutorials").document(tutorial_id).update({
                            "courseId": saga_map_data.get("courseId"),
                            "moduleId": saga_map_data.get("moduleId"),
                        })
                        logger.info(f"🗺️ Saga Map: Tutorial {tutorial_id} assigned to hierarchy")
                    except Exception as assign_err:
                        logger.warning(f"⚠️ Failed to assign tutorial to hierarchy: {assign_err}")
                
                # Update request on completion
                doc_ref.update({
                    "status": "COMPLETED",
                    "tutorialId": tutorial_id
                })
                
            except Exception as e:
                logger.error(f"❌ Generation job failed: {e}")
                doc_ref.update({"status": "FAILED"})
        
        # Start in background thread
        thread = threading.Thread(target=run_job)
        thread.start()
        
        logger.info(f"🚀 Generation triggered for request {request_id} by {admin.get('email')}")
        
        # Audit Trail
        log_audit_action(
            admin_id=admin.get("uid", "unknown"),
            admin_email=admin.get("email"),
            action="TRIGGER_TUTORIAL_GENERATION",
            target_id=request_id,
            target_type="tutorialRequest",
            details={"topic": topic, "jobId": job_id, "userId": user_id}
        )
        
        return {
            "status": "GENERATING",
            "job_id": job_id,
            "message": "Generation started in background.",
            "saga_map": saga_map_data if saga_map_data else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Trigger Generation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- ALI ORCHESTRATION HUB ENDPOINTS (Spec: Unified Governance) ---

@router.get("/creative-drafts")
def get_creative_drafts(status: Optional[str] = None, admin: dict = Depends(verify_admin)):
    """
    Fetches creative drafts pending review/publish.
    Status filter: DRAFT, PENDING_REVIEW, PUBLISHED
    """
    try:
        query = db.collection("creative_drafts")
        
        if status:
            query = query.where(filter=FieldFilter("status", "==", status))
        else:
            # Default: show non-published drafts
            query = query.where(filter=FieldFilter("status", "in", ["DRAFT", "PENDING_REVIEW"]))
        
        query = query.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(50)
        
        drafts = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            drafts.append(data)
        
        return {"drafts": drafts}
    except Exception as e:
        logger.error(f"❌ Fetch Creative Drafts Error: {e}")
        return {"drafts": [], "error": str(e)}


@router.post("/creative-drafts/{draft_id}/publish")
def publish_creative_draft(draft_id: str, admin: dict = Depends(verify_admin)):
    """
    Publish a creative draft - updates status to PUBLISHED.
    """
    try:
        doc_ref = db.collection("creative_drafts").document(draft_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        doc_ref.update({
            "status": "PUBLISHED",
            "publishedAt": firestore.SERVER_TIMESTAMP,
            "publishedBy": admin.get("email")
        })
        
        # Log to audit trail
        log_audit_action(
            admin_id=admin.get("uid", "unknown"),
            admin_email=admin.get("email"),
            action="PUBLISH_CREATIVE",
            target_id=draft_id,
            target_type="creativeDraft",
            details={"previousStatus": doc.to_dict().get("status")}
        )
        
        logger.info(f"✅ Creative draft {draft_id} published by {admin.get('email')}")
        return {"status": "PUBLISHED", "message": "Draft published successfully."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Publish Draft Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
def get_recommendations(status: Optional[str] = None, admin: dict = Depends(verify_admin)):
    """
    Fetches 'Next Best Action' recommendations requiring admin approval.
    These are generated by the Prediction Engine for optimizing campaigns.
    """
    try:
        query = db.collection("recommendations")
        
        if status:
            query = query.where(filter=FieldFilter("status", "==", status))
        else:
            # Default: show pending recommendations
            query = query.where(filter=FieldFilter("status", "==", "PENDING"))
        
        query = query.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(50)
        
        recommendations = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            recommendations.append(data)
        
        return {"recommendations": recommendations}
    except Exception as e:
        logger.error(f"❌ Fetch Recommendations Error: {e}")
        return {"recommendations": [], "error": str(e)}


@router.post("/recommendations/{recommendation_id}/approve")
def approve_recommendation(recommendation_id: str, admin: dict = Depends(verify_admin)):
    """
    Approve a Next Best Action recommendation for execution.
    """
    try:
        doc_ref = db.collection("recommendations").document(recommendation_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        data = doc.to_dict()
        
        doc_ref.update({
            "status": "APPROVED",
            "approvedAt": firestore.SERVER_TIMESTAMP,
            "approvedBy": admin.get("email")
        })
        
        # Log to audit trail
        log_audit_action(
            admin_id=admin.get("uid", "unknown"),
            admin_email=admin.get("email"),
            action="APPROVE_RECOMMENDATION",
            target_id=recommendation_id,
            target_type="recommendation",
            details={"actionType": data.get("actionType"), "priority": data.get("priority")}
        )
        
        logger.info(f"✅ Recommendation {recommendation_id} approved by {admin.get('email')}")
        return {"status": "APPROVED", "message": "Recommendation approved for execution."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Approve Recommendation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/research-alerts")
def get_research_alerts(severity: Optional[str] = None, admin: dict = Depends(verify_admin)):
    """
    Fetches research alerts from the Web Engine / Knowledge Packs monitoring.
    Severity levels: CRITICAL, IMPORTANT, INFORMATIONAL
    """
    try:
        # Fetch from knowledge pack change logs and consolidate alerts
        alerts = []
        
        # Query knowledge_packs for recent change logs
        packs_query = db.collection("knowledge_packs")\
            .order_by("createdAt", direction=firestore.Query.DESCENDING)\
            .limit(100)
        
        for pack_doc in packs_query.stream():
            pack_data = pack_doc.to_dict()
            change_log = pack_data.get("changeLog", [])
            
            for change in change_log:
                change_severity = change.get("severity", "INFORMATIONAL")
                
                # Filter by severity if specified
                if severity and change_severity != severity:
                    continue
                
                # Only include CRITICAL and IMPORTANT by default
                if not severity and change_severity not in ["CRITICAL", "IMPORTANT"]:
                    continue
                
                alerts.append({
                    "id": f"{pack_doc.id}_{change.get('detectedAt', '')}",
                    "packId": pack_doc.id,
                    "topicTags": pack_data.get("topicTags", []),
                    "severity": change_severity,
                    "changes": change.get("changes", []),
                    "detectedAt": change.get("detectedAt"),
                    "status": change.get("status", "NEW")
                })
        
        # Also check for standalone alerts in admin_tasks collection
        alerts_query = db.collection("admin_tasks")\
            .where(filter=FieldFilter("type", "==", "research_alert"))\
            .order_by("created_at", direction=firestore.Query.DESCENDING)\
            .limit(50)
        
        for alert_doc in alerts_query.stream():
            alert_data = alert_doc.to_dict()
            alert_severity = alert_data.get("severity", "INFORMATIONAL")
            
            if severity and alert_severity != severity:
                continue
            if not severity and alert_severity not in ["CRITICAL", "IMPORTANT"]:
                continue
            
            alerts.append({
                "id": alert_doc.id,
                "title": alert_data.get("title"),
                "description": alert_data.get("description"),
                "severity": alert_severity,
                "createdAt": alert_data.get("created_at"),
                "status": alert_data.get("status", "NEW")
            })
        
        # Sort by severity (CRITICAL first) then by date
        severity_order = {"CRITICAL": 0, "IMPORTANT": 1, "INFORMATIONAL": 2}
        alerts.sort(key=lambda x: (severity_order.get(x.get("severity"), 3), x.get("detectedAt") or ""))
        
        return {"alerts": alerts[:50]}
    except Exception as e:
        logger.error(f"❌ Fetch Research Alerts Error: {e}")
        return {"alerts": [], "error": str(e)}


@router.post("/research-alerts/{alert_id}/acknowledge")
def acknowledge_research_alert(alert_id: str, admin: dict = Depends(verify_admin)):
    """
    Acknowledge a research alert, marking it as reviewed.
    """
    try:
        # Check if it's a knowledge pack change log or standalone alert
        if "_" in alert_id:
            # Knowledge pack change log format: packId_timestamp
            pack_id = alert_id.split("_")[0]
            # For now, we'll mark it in the admin_tasks as acknowledged
            db.collection("admin_tasks").document(f"ack_{alert_id}").set({
                "type": "alert_acknowledgement",
                "alertId": alert_id,
                "packId": pack_id,
                "acknowledgedBy": admin.get("email"),
                "acknowledgedAt": firestore.SERVER_TIMESTAMP
            })
        else:
            # Standalone alert in admin_tasks
            doc_ref = db.collection("admin_tasks").document(alert_id)
            doc = doc_ref.get()
            
            if doc.exists:
                doc_ref.update({
                    "status": "ACKNOWLEDGED",
                    "acknowledgedBy": admin.get("email"),
                    "acknowledgedAt": firestore.SERVER_TIMESTAMP
                })
        
        # Log to audit trail
        log_audit_action(
            admin_id=admin.get("uid", "unknown"),
            admin_email=admin.get("email"),
            action="ACKNOWLEDGE_ALERT",
            target_id=alert_id,
            target_type="researchAlert"
        )
        
        logger.info(f"✅ Alert {alert_id} acknowledged by {admin.get('email')}")
        return {"status": "ACKNOWLEDGED", "message": "Alert acknowledged."}
        
    except Exception as e:
        logger.error(f"❌ Acknowledge Alert Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

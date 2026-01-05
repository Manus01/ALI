from fastapi import APIRouter, Depends, HTTPException, Body
from app.core.security import verify_token, db
from app.services.metricool_client import MetricoolClient
from app.services.performance_logger import run_nightly_performance_log
from typing import Dict, Optional
from datetime import datetime
from google.cloud import firestore
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def verify_admin(user: dict = Depends(verify_token)):
    if user.get("email") not in ["manoliszografos@gmail.com"]:
        raise HTTPException(status_code=403, detail="Research Access Only")
    return user

@router.post("/users/link-metricool")
def admin_link_metricool(payload: Dict[str, str] = Body(...), admin: dict = Depends(verify_admin)):
    target_uid = payload.get("target_user_id")
    blog_id = payload.get("metricool_blog_id")
    
    # 1. Update the integration record in the private user folder
    doc_ref = db.collection("users").document(target_uid).collection("user_integrations").document("metricool")
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

    # 3. Mark the admin task as completed
    db.collection("admin_tasks").document(f"connect_{target_uid}").update({"status": "completed"})
    
    return {"status": "success", "message": "User linked and notified."}

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


@router.get("/integration-alerts")
def get_integration_alerts(admin: dict = Depends(verify_admin)):
    alerts_query = db.collection("admin_alerts").order_by("created_at", direction=firestore.Query.DESCENDING).limit(50)
    alerts = []

    for doc in alerts_query.stream():
        entry = doc.to_dict()
        entry["id"] = doc.id
        alerts.append(entry)

    return {"alerts": alerts}

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
                "data_points": count
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
                      .where("type", "==", "METRICOOL_REQUEST")\
                      .where("status", "==", "pending")\
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

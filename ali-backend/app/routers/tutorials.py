from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from app.core.security import verify_token, db
import os
import json
import logging
import traceback
from typing import Callable, List, Dict
import httpx # For async media health checks
from firebase_admin import firestore

logger = logging.getLogger("ali_platform.routers.tutorials")

# Admin Configuration - comma-separated list of admin emails
ADMIN_EMAILS = [
    email.strip().lower() 
    for email in os.getenv("ADMIN_EMAILS", "").split(",") 
    if email.strip()
]

def _require_admin(user: dict, action: str):
    """Verify user has admin privileges via is_admin flag or email allowlist."""
    user_email = user.get('email', '').lower()
    is_admin = user.get('is_admin', False)
    
    if not is_admin and user_email not in ADMIN_EMAILS:
        logger.warning(f"🚫 Unauthorized admin action '{action}' by {user_email}")
        raise HTTPException(status_code=403, detail="Admin access required")
    
    logger.info(f"✅ Admin action '{action}' authorized for {user_email}")

# NOTE: We intentionally delay heavy imports (Job Runner, LLM Factory) to runtime
# inside each endpoint. This prevents startup crashes that would stop the tutorials
# router from registering, which in turn produced 404s for /api/generate/tutorial
# whenever Vertex AI or other dependencies weren't ready.
process_tutorial_job = None
get_model = None

router = APIRouter()


def _require_db(action: str) -> Callable[[], None]:
    """Ensure Firestore is available before performing a DB-bound action."""

    def _guard():
        if not db:
            logger.error(f"❌ Database not initialized during {action}")
            raise HTTPException(status_code=503, detail="Database not initialized")

    return _guard

class CompletionRequest(BaseModel):
    score: float = Field(..., ge=0, le=100)
    quiz_results: list[dict] = Field(default_factory=list, description="Detailed results per quiz/section")

# --- 1. ASYNC GENERATION (Standard) ---
@router.post("/generate/tutorial")
def start_tutorial_job(topic: str, background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    try:
        global process_tutorial_job
        if process_tutorial_job is None:
            try:
                from app.services.job_runner import process_tutorial_job as _process
                process_tutorial_job = _process
            except Exception as imp_err:
                logger.critical(f"❌ Tutorial Job Runner failed to import: {imp_err}")
                raise HTTPException(status_code=503, detail="Tutorial worker unavailable. Please try again shortly.")

        if not db:
            raise HTTPException(status_code=503, detail="Database not initialized")

        job_ref = db.collection("jobs").document()
        job_id = job_ref.id
        job_ref.set({
            "id": job_id, "user_id": user['uid'], "type": "tutorial_generation",
            "topic": topic.strip(), "status": "queued", "created_at": firestore.SERVER_TIMESTAMP
        })

        # Immediately create a notification so the UI updates instantly
        notification_ref = db.collection("users").document(user['uid']).collection("notifications").document(job_id)
        notification_ref.set({
            "user_id": user['uid'],
            "type": "info",
            "status": "queued",
            "title": "Tutorial Requested",
            "message": f"Queued: '{topic.strip()}' is about to start processing...",
            "link": None,
            "read": False,
            "created_at": firestore.SERVER_TIMESTAMP
        })

        # --- WORKER DISPATCH STRATEGY ---
        # Option 1: Use Cloud Run Job (if explicitly configured)
        # Option 2: Use local BackgroundTasks (default fallback)
        
        use_cloud_worker = os.getenv("USE_CLOUD_RUN_WORKER", "false").lower() == "true"
        worker_dispatched = False
        
        if use_cloud_worker:
            try:
                from google.cloud import run_v2
                
                project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "ali-platform-prod-73019") 
                location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
                job_name = os.getenv("CLOUD_RUN_WORKER_JOB", "ali-worker")

                client = run_v2.JobsClient()
                name = client.job_path(project_id, location, job_name)
                
                # Validate job exists BEFORE dispatching
                try:
                    client.get_job(name=name)
                    logger.info(f"✅ Cloud Run Job '{job_name}' validated.")
                except Exception as get_err:
                    logger.warning(f"⚠️ Cloud Run Job '{job_name}' not found: {get_err}")
                    raise Exception(f"Job not found: {job_name}")
                
                overrides = {
                    "container_overrides": [
                        {
                            "env": [
                                {"name": "JOB_ID", "value": job_id},
                                {"name": "USER_ID", "value": user['uid']},
                                {"name": "TOPIC", "value": topic.strip()},
                                {"name": "NOTIFICATION_ID", "value": notification_ref.id}
                            ]
                        }
                    ]
                }

                request = run_v2.RunJobRequest(name=name, overrides=overrides)
                operation = client.run_job(request=request)
                logger.info(f"🚀 Dispatched Cloud Run Job: {operation.operation.name}")
                worker_dispatched = True

            except Exception as cloud_err:
                logger.error(f"❌ Cloud Run Job dispatch failed: {cloud_err}")
                logger.warning("⚠️ Falling back to local background worker...")
        
        # LOCAL FALLBACK (Default path when USE_CLOUD_RUN_WORKER is not set)
        if not worker_dispatched:
            logger.info(f"🏠 Using LOCAL background worker for job {job_id}")
            
            if process_tutorial_job is None:
                from app.services.job_runner import process_tutorial_job as _process
                process_tutorial_job = _process
                
            background_tasks.add_task(process_tutorial_job, job_id, user['uid'], topic.strip(), notification_ref.id)
            logger.info(f"✅ Background task scheduled for job {job_id}")

        return {"status": "queued", "job_id": job_id, "notification_id": notification_ref.id}
    except HTTPException:
        # Re-raise intentional HTTP responses without wrapping
        raise
    except Exception as e:
        logger.error(f"❌ Start Tutorial Job Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to queue tutorial generation. Please try again.")

# --- 2. GRANULAR SKILL SUGGESTIONS ---
@router.get("/tutorials/suggestions")
def get_tutorial_suggestions(user: dict = Depends(verify_token)):
    try:
        user_id = user['uid']

        _require_db("get_tutorial_suggestions")()

        # Fetch Granular Skills
        user_doc = db.collection('users').document(user_id).get()
        user_data = user_doc.to_dict() or {} if user_doc.exists else {}
        profile = user_data.get("profile", {})
        
        # Get Matrix (defaulting to Novice)
        skills = profile.get("marketing_skills", {
            "paid_ads": "NOVICE", "content": "NOVICE", "analytics": "NOVICE", "seo": "NOVICE"
        })
        
        # Identify Weak Areas (General)
        weak_areas = [k for k, v in skills.items() if v == "NOVICE"]
        if not weak_areas: weak_areas = ["Advanced Optimization"] 

        # --- PERSONALIZATION LOOP FIX ---
        # Fetch from Private Collection to access 'quiz_results'
        existing_docs = db.collection('users').document(user_id).collection('tutorials').stream()
        
        existing_titles = []
        recent_struggles = []
        
        for doc in existing_docs:
            data = doc.to_dict()
            existing_titles.append(data.get('title', ''))
            
            # Analyze Struggles (Score < 70% or Low Quiz Section Scores)
            if data.get('is_completed'):
                # Check Global Score
                if data.get('completion_score', 100) < 75:
                    recent_struggles.append(f"Low score in '{data.get('title')}'")
                
                # Check Sectional Quiz Results
                for qr in data.get('quiz_results', []):
                    if qr.get('score', 100) < 60:
                        recent_struggles.append(f"Struggled with '{qr.get('section_title', 'Unknown Section')}' in '{data.get('title')}'")

        global get_model
        if get_model is None:
            try:
                from app.services.llm_factory import get_model as _get_model
                get_model = _get_model
            except Exception as imp_err:
                logger.error(f"❌ LLM Factory import failed: {imp_err}")
                raise HTTPException(status_code=503, detail="Suggestions temporarily unavailable.")

        model = get_model(intent='fast')
         
        prompt = f"""
        Act as an AI Mentor.
        
        USER SKILL MATRIX: {json.dumps(skills)}
        WEAKEST AREAS: {weak_areas}
        Please prioritize fixing these RECENT STRUGGLES: {json.dumps(recent_struggles)}
        ALREADY COMPLETED: {existing_titles}
        
        TASK:
        Suggest 3 highly specific tutorial titles.
        1. Prioritize addressing the 'Recent Struggles' if any.
        2. Then focus on 'Weakest Areas'.
        3. Do not suggest topics they have already done.
        
        Return STRICT JSON list: ["Title 1", "Title 2", "Title 3"]
        """
        
        response = model.generate_content(prompt)
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
 
    except HTTPException as he:
        raise he
    except Exception as e:
        # Detailed logging for debugging Cloud Run issues
        logger.error(f"❌ Suggestion Error: {e}")
        traceback.print_exc()
        return ["Marketing Strategy 101", "Content Creation", "ROI Analysis"]

def _process_tutorial_doc(doc, user_id, db):
    """Helper to process tutorial document and apply fallbacks."""
    t = doc.to_dict()
    # Explicitly set ID if not in dict
    t['id'] = doc.id
    
    # Debug Log: Inspect Raw Data from DB
    logger.debug(f"🔍 Processing Doc {doc.id} (User: {user_id})")
    
    # Check completion status
    user_doc = db.collection('users').document(user_id).get()
    completed_ids = user_doc.to_dict().get("completed_tutorials", []) if user_doc.exists else []
    t['is_completed'] = doc.id in completed_ids
    
    # ROBUSTNESS FIX: Ensure sections structure exists
    if 'sections' not in t or t['sections'] is None:
        t['sections'] = []
    
    # Fallback: If sections empty but blocks exist (Legacy/Flat structure), create default section
    if not t['sections'] and t.get('blocks'):
        logger.warning(f"⚠️ Tutorial {doc.id} has blocks but no sections. Applying fallback.")
        t['sections'] = [{ "title": "Lesson Content", "blocks": t['blocks'] }]
    
    return t
 
from functools import lru_cache
import time

# ... (imports)

@lru_cache(maxsize=100)
def _fetch_cached_global_tutorial(tutorial_id: str):
    """
    Cached helper for Global Content (Public).
    TTL: 1 hour (implied by just existing in memory until restart or eviction, 
    but for true TTL we'd need a wrapper. Simple LRU is fine for mostly static content).
    """
    if not db: return None # Safety
    try:
        doc = db.collection('tutorials').document(tutorial_id).get()
        if doc.exists:
            return doc.to_dict()
    except:
        return None
    return None

@router.get("/tutorials/{tutorial_id}")
def get_tutorial_details(tutorial_id: str, user: dict = Depends(verify_token)):
    """
    Fetches a single tutorial by ID.
    Checks User's Private Collection first, then Global Public Collection.
    """
    try:
        user_id = user['uid']

        _require_db("get_tutorial_details")()

        # 1. Try Private (User Subcollection) - Strong Consistency
        doc_ref = db.collection('users').document(user_id).collection('tutorials').document(tutorial_id)
        doc = doc_ref.get()

        if doc.exists:
            t = _process_tutorial_doc(doc, user_id, db)
            
            # HIDDEN CHECK: If soft-deleted by user, return 404
            if t.get('is_hidden') is True:
                 raise HTTPException(status_code=404, detail="Tutorial deleted by user.")

            # Debug Log
            sec_count = len(t.get('sections', []))
            logger.debug(f"🔍 Fetch Private Tutorial {tutorial_id}: Found {sec_count} sections.")

            # If the private copy is missing content, fall back to the global public copy
            # (this helps when a legacy write left an empty shell in the user's subcollection).
            if sec_count == 0 and len(t.get('blocks', [])) == 0:
                global_doc = db.collection('tutorials').document(tutorial_id).get()

                if global_doc.exists:
                    g = _process_tutorial_doc(global_doc, user_id, db)

                    if g.get('sections') or g.get('blocks'):
                        logger.warning(
                            f"⚠️ Private tutorial {tutorial_id} was empty; using global content instead."
                        )

                        # Preserve completion status from the private doc while using the global content
                        g['is_completed'] = t.get('is_completed', g.get('is_completed', False))
                        return g

            return t
            
        # 2. Try Global (Public)
        # OPTIMIZATION: Use In-Memory Cache for Global Content
        t_global = _fetch_cached_global_tutorial(tutorial_id)
        
        if not t_global:
             logger.warning(f"⚠️ Tutorial {tutorial_id} not found in Global collection (Cache Miss/Empty).")
             # Try direct fetch just in case cache returned None erroneously? No, trust cache for now or simple miss.
             # Actually, if cache returns None it means doc didn't exist when cached.
             raise HTTPException(status_code=404, detail="Tutorial not found")

        # Create a deep copy to avoid mutating the cached object with user-specific flags
        import copy
        t = copy.deepcopy(t_global)
        t['id'] = tutorial_id # Ensure ID is set

        # Process standard fields
        # Note: _process_tutorial_doc expects a DOC snapshot usually, but we adapted logic.
        # Let's manually apply the necessary flags since we have a dict now.
        
        # Check completion status
        user_doc_ref = db.collection('users').document(user_id)
        user_doc = user_doc_ref.get()
        completed_ids = user_doc.to_dict().get("completed_tutorials", []) if user_doc.exists else []
        t['is_completed'] = tutorial_id in completed_ids
        
        if 'sections' not in t: t['sections'] = []

        # Debug Log
        sec_count = len(t.get('sections', []))
        logger.debug(f"🔍 Fetch Global Tutorial {tutorial_id} (Cached): Found {sec_count} sections.")
        return t
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"❌ Fetch Details Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. GRANULAR AUTO-LEVELING ---

@router.get("/tutorials/{tutorial_id}/health")
async def check_tutorial_media_health(tutorial_id: str, user: dict = Depends(verify_token)):
    """
    Validates all media URLs in a tutorial are accessible.
    Returns health status for each media block.
    """
    try:
        user_id = user['uid']
        _require_db("check_tutorial_media_health")()
        
        # Fetch tutorial (try private first, then global)
        doc_ref = db.collection('users').document(user_id).collection('tutorials').document(tutorial_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            doc = db.collection('tutorials').document(tutorial_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Tutorial not found")
        
        tutorial_data = doc.to_dict()
        
        # Collect all media URLs
        media_checks: List[Dict] = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for sec_idx, section in enumerate(tutorial_data.get('sections', [])):
                for block_idx, block in enumerate(section.get('blocks', [])):
                    url = block.get('url')
                    if not url:
                        continue
                    
                    block_type = block.get('type', 'unknown')
                    
                    try:
                        # HEAD request to check accessibility without downloading
                        response = await client.head(url, follow_redirects=True)
                        status = "healthy" if response.status_code == 200 else "error"
                        status_code = response.status_code
                    except Exception as e:
                        status = "unreachable"
                        status_code = None
                    
                    media_checks.append({
                        "section_index": sec_idx,
                        "block_index": block_idx,
                        "type": block_type,
                        "status": status,
                        "status_code": status_code,
                        "url_preview": url[:80] + "..." if len(url) > 80 else url
                    })
        
        # Summary
        total = len(media_checks)
        healthy = sum(1 for m in media_checks if m['status'] == 'healthy')
        
        return {
            "tutorial_id": tutorial_id,
            "overall_status": "healthy" if healthy == total else "degraded",
            "summary": f"{healthy}/{total} media assets accessible",
            "details": media_checks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Media Health Check Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. GRANULAR AUTO-LEVELING ---
@router.post("/tutorials/{tutorial_id}/complete")
def mark_complete(tutorial_id: str, payload: CompletionRequest, user: dict = Depends(verify_token)):
    """
    Marks complete AND updates specific skill bucket based on tutorial category.
    Saves detailed quiz results for future personalization.
    """
    try:
        if payload.score < 75: return {"status": "failed", "message": "Score too low."}

        _require_db("mark_complete")()

        user_ref = db.collection('users').document(user['uid'])
        
        # SENIOR DEV FIX: Check User Subcollection FIRST (Private), then Global (Public)
        tut_ref = user_ref.collection('tutorials').document(tutorial_id)
        tut_doc = tut_ref.get()
        
        if not tut_doc.exists:
            # Fallback to global
            tut_ref = db.collection('tutorials').document(tutorial_id)
            tut_doc = tut_ref.get()
        
        # Fetch Tutorial Metadata to know WHICH skill to upgrade
        if not tut_doc.exists: return {"status": "error", "message": "Tutorial not found"}
        
        tut_data = tut_doc.to_dict()
        category = tut_data.get("category", "general") # e.g., "paid_ads"
        difficulty = tut_data.get("difficulty", "NOVICE")

        # Update Lists & Save Quiz Results
        update_data = {
            "is_completed": True,
            "completion_score": payload.score,
            "completed_at": firestore.SERVER_TIMESTAMP
        }
        
        # Only save granular results if provided
        if payload.quiz_results:
             update_data["quiz_results"] = payload.quiz_results

        tut_ref.update(update_data)

        user_ref.update({
            "completed_tutorials": firestore.ArrayUnion([tutorial_id]),
            "rank_score": firestore.Increment(100) 
        })

        # --- AUTO-LEVELING LOGIC ---
        if payload.score >= 95: # High bar for promotion
            logger.info(f"🚀 Promoting User in skill: {category} (Current: {difficulty})")
            
            # Map next levels
            next_level = None
            if difficulty == "NOVICE": next_level = "INTERMEDIATE"
            elif difficulty == "INTERMEDIATE": next_level = "EXPERT"
            
            if next_level:
                # Update specific field in the map using dot notation
                user_ref.update({
                    f"profile.marketing_skills.{category}": next_level
                })

        return {"status": "success", "message": "Tutorial complete. Profile updated."}
        
    except Exception as e:
        logger.error(f"❌ Completion Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tutorials/{tutorial_id}")
def delete_user_tutorial(tutorial_id: str, user: dict = Depends(verify_token)):
    """
    User Soft Delete:
    - Hides from User.
    - Creates Admin Request to decide on permanent deletion.
    """
    try:
        user_id = user['uid']
        _require_db("delete_user_tutorial")()

        # 1. Hide from User (Soft Delete)
        user_doc_ref = db.collection('users').document(user_id).collection('tutorials').document(tutorial_id)
        user_doc_ref.set({
            "is_hidden": True,
            "deletion_requested": True,
            "deleted_at": firestore.SERVER_TIMESTAMP
        }, merge=True)

        # 2. Create Admin Notification / Task
        # Check if request already exists to avoid duplicates
        existing = db.collection("admin_tasks").where("tutorial_id", "==", tutorial_id).where("status", "==", "pending").limit(1).stream()
        if not any(existing):
            db.collection("admin_tasks").add({
                "type": "delete_tutorial_request",
                "tutorial_id": tutorial_id,
                "requester_id": user_id,
                "reason": "User requested deletion",
                "status": "pending",
                "created_at": firestore.SERVER_TIMESTAMP
            })

        return {"status": "success", "message": "Tutorial removed from your view. Pending admin review for permanent deletion."}
    except Exception as e:
        logger.error(f"❌ Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- ADMIN DELETION LOGIC ---

def _delete_storage_assets(tutorial_data: dict) -> dict:
    """
    Parses tutorial structure and deletes all referenced assets from Cloud Storage.
    Returns a summary of deletion results.
    """
    results = {"deleted": 0, "failed": 0, "errors": []}
    
    try:
        from google.cloud import storage
        import urllib.parse
        
        storage_client = storage.Client()
        # Fallback bucket name if not found in URL (though URL usually has it)
        default_bucket = os.getenv("GCS_BUCKET_NAME", "ali-platform-prod-73019.firebasestorage.app")
        
        urls_to_delete = []
        
        for section in tutorial_data.get('sections', []):
            for block in section.get('blocks', []):
                if block.get('url'):
                    urls_to_delete.append(block['url'])
                # Also check for gcs_object_key (new field for auditability)
                if block.get('gcs_object_key'):
                    # Format as scheme to distinguish from HTTP URLs
                    urls_to_delete.append(f"gcs://{block.get('bucket', default_bucket)}/{block['gcs_object_key']}")
        
        for url in urls_to_delete:
            try:
                blob = None
                
                # Case A: Firebase Persistent URL
                if "firebasestorage.googleapis.com" in url:
                    # Extract path
                    # Example: https://firebasestorage.googleapis.com/v0/b/{bucket}/o/{path}?alt=media...
                    parts = url.split("/o/")
                    if len(parts) < 2: continue
                    
                    bucket_part = parts[0].split("/b/")[-1]
                    path_part = parts[1].split("?")[0]
                    # Decode URL path (e.g., tutorials%2Fvideo.mp4 -> tutorials/video.mp4)
                    blob_name = urllib.parse.unquote(path_part)
                    
                    bucket = storage_client.bucket(bucket_part)
                    blob = bucket.blob(blob_name)
                
                # Case B: Direct GCS Reference
                elif url.startswith("gcs://"):
                    parts = url.split("gcs://")[1].split("/")
                    bucket_name = parts[0]
                    blob_name = "/".join(parts[1:])
                    bucket = storage_client.bucket(bucket_name)
                    blob = bucket.blob(blob_name)

                if blob:
                    if blob.exists():
                        blob.delete()
                        results["deleted"] += 1
                        logger.info(f"   🗑️ Deleted Asset: {blob.name}")
                    else:
                        logger.warning(f"   ⚠️ Asset not found (already deleted?): {blob.name}")
                        
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"url": url[:50], "error": str(e)})
                logger.warning(f"   ⚠️ Failed to delete asset {url[:50]}: {e}")
                
        logger.info(f"✅ Cleanup Complete: {results['deleted']} deleted, {results['failed']} failed")
        return results

    except Exception as e:
        logger.error(f"❌ Asset Deletion Logic Failed: {e}")
        # Don't raise, we want to continue deleting the metadata docs
        results["errors"].append({"url": "Global Logic", "error": str(e)})
        return results

@router.delete("/admin/tutorials/{tutorial_id}")
def admin_delete_tutorial(tutorial_id: str, confirm: bool = False, user: dict = Depends(verify_token)):
    """
    ADMIN: Completely deletes a tutorial and ALL generated assets.
    """
    try:
        # Admin role verification
        _require_admin(user, f"delete_tutorial:{tutorial_id}")
        
        if not confirm:
             raise HTTPException(status_code=400, detail="Must set confirm=true for permanent deletion.")

        _require_db("admin_delete_tutorial")()
        
        # 1. Fetch Global Data to get Assets
        global_ref = db.collection('tutorials').document(tutorial_id)
        doc = global_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            # 2. Delete Assets
            logger.info(f"🗑️ Admin wiping assets for {tutorial_id}...")
            _delete_storage_assets(data)
            
            # 3. Delete Global Doc
            global_ref.delete()
        else:
            logger.warning(f"Global doc {tutorial_id} not found during admin delete.")

        # 4. Delete ALL User Copies (Collection Group Query)
        # We want to remove it from every user's private collection
        instances = db.collection_group('tutorials').where('id', '==', tutorial_id).stream()
        batch = db.batch()
        count = 0
        for instance in instances:
            batch.delete(instance.reference)
            count += 1
            if count > 400: 
                batch.commit()
                batch = db.batch()
                count = 0
        if count > 0: batch.commit()
        
        # 5. Clean Admin Tasks
        tasks = db.collection("admin_tasks").where("tutorial_id", "==", tutorial_id).stream()
        for t in tasks:
            t.reference.delete()

        return {"status": "success", "message": "Tutorial and all assets deleted permanently."}

    except Exception as e:
        logger.error(f"❌ Admin Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/requests/{request_id}/decide")
def admin_decide_deletion(request_id: str, decision: str, user: dict = Depends(verify_token)):
    """
    Decide on a deletion request.
    decision: 'delete' | 'keep'
    """
    try:
        # Admin role verification
        _require_admin(user, f"decide_deletion:{request_id}")
        
        _require_db("admin_decide_deletion")()
        
        task_ref = db.collection("admin_tasks").document(request_id)
        task = task_ref.get()
        if not task.exists:
            raise HTTPException(404, "Request not found")
            
        task_data = task.to_dict()
        tutorial_id = task_data.get("tutorial_id")
        
        if decision == 'delete':
            # Execute Hard Delete
            admin_delete_tutorial(tutorial_id, confirm=True, user=user)
            task_ref.update({"status": "approved", "resolved_at": firestore.SERVER_TIMESTAMP})
            return {"status": "success", "message": "Tutorial permanently deleted."}
            
        elif decision == 'keep':
            # Just mark resolution. User copy remains hidden (soft deleted for them).
            task_ref.update({"status": "rejected", "resolved_at": firestore.SERVER_TIMESTAMP})
            return {"status": "success", "message": "Tutorial kept public. Hidden for original user."}
        
        else:
            raise HTTPException(400, "Invalid decision. Use 'delete' or 'keep'.")

    except HTTPException as he:
        raise he
    except Exception as e:
         logger.error(f"❌ Decision Error: {e}")
         raise HTTPException(status_code=500, detail=str(e))
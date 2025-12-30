from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from app.core.security import verify_token
from app.services.job_runner import process_tutorial_job
from app.agents.nodes import analyst_node
from google.cloud import firestore
from app.services.llm_factory import get_model
import os
import json
import datetime

router = APIRouter()

class CompletionRequest(BaseModel):
    score: float = Field(..., ge=0, le=100)

# --- 1. ASYNC GENERATION (Standard) ---
@router.post("/generate/tutorial")
def start_tutorial_job(topic: str, background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    try:
        db = firestore.Client()
        job_ref = db.collection("jobs").document()
        job_id = job_ref.id
        job_ref.set({
            "id": job_id, "user_id": user['uid'], "type": "tutorial_generation",
            "topic": topic, "status": "queued", "created_at": firestore.SERVER_TIMESTAMP
        })
        background_tasks.add_task(process_tutorial_job, job_id, user['uid'], topic)
        return {"status": "queued", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 2. GRANULAR SKILL SUGGESTIONS ---
@router.get("/tutorials/suggestions")
def get_tutorial_suggestions(user: dict = Depends(verify_token)):
    try:
        db = firestore.Client()
        user_id = user['uid']

        # Fetch Granular Skills
        user_doc = db.collection('users').document(user_id).get()
        user_data = user_doc.to_dict() or {}
        profile = user_data.get("profile", {})
        
        # Get Matrix (defaulting to Novice)
        skills = profile.get("marketing_skills", {
            "paid_ads": "NOVICE", "content": "NOVICE", "analytics": "NOVICE", "seo": "NOVICE"
        })

        # Fetch Completed Titles
        existing_docs = db.collection('tutorials').where('owner_id', '==', user_id).stream()
        existing_titles = [doc.to_dict().get('title', '') for doc in existing_docs]
        
        # Identify Weaknesses
        weak_areas = [k for k, v in skills.items() if v == "NOVICE"]
        if not weak_areas: weak_areas = ["Advanced Optimization"] # If they are expert everywhere

        model = get_model(intent='fast')
         
        prompt = f"""
        Act as an AI Mentor.
        
        USER SKILL MATRIX: {json.dumps(skills)}
        WEAKEST AREAS: {weak_areas}
        COMPLETED COURSES: {existing_titles}
        
        TASK:
        Suggest 3 highly specific tutorial titles to improve the user's WEAKEST areas.
        Do not suggest topics they have already done.
        
        Return STRICT JSON list: ["Title 1", "Title 2", "Title 3"]
        """
        
        response = model.generate_content(prompt)
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())

    except Exception as e:
        print(f"❌ Suggestion Error: {e}")
        return ["Marketing Strategy 101", "Content Creation", "ROI Analysis"]

def _process_tutorial_doc(doc, user_id, db):
    """Helper to process tutorial document and apply fallbacks."""
    t = doc.to_dict()
    t['id'] = doc.id
    
    # Check completion status
    user_doc = db.collection('users').document(user_id).get()
    completed_ids = user_doc.to_dict().get("completed_tutorials", []) if user_doc.exists else []
    t['is_completed'] = doc.id in completed_ids
    
    # ROBUSTNESS FIX: Ensure sections structure exists
    if 'sections' not in t or t['sections'] is None:
        t['sections'] = []
    
    # Fallback: If sections empty but blocks exist (Legacy/Flat structure), create default section
    if not t['sections'] and t.get('blocks'):
        print(f"⚠️ Tutorial {doc.id} has blocks but no sections. Applying fallback.")
        t['sections'] = [{ "title": "Lesson Content", "blocks": t['blocks'] }]
    
    return t
 
@router.get("/tutorials/{tutorial_id}")
def get_tutorial_details(tutorial_id: str, user: dict = Depends(verify_token)):
    """
    Fetches a single tutorial by ID.
    Checks User's Private Collection first, then Global Public Collection.
    """
    try:
        db = firestore.Client()
        user_id = user['uid']
        
        # 1. Try Private (User Subcollection) - Strong Consistency
        doc_ref = db.collection('users').document(user_id).collection('tutorials').document(tutorial_id)
        doc = doc_ref.get()
        
        if doc.exists:
            t = _process_tutorial_doc(doc, user_id, db)
            # Debug Log
            sec_count = len(t.get('sections', []))
            print(f"🔍 Fetch Private Tutorial {tutorial_id}: Found {sec_count} sections.")
            
            return t
            
        # 2. Try Global (Public)
        doc_ref = db.collection('tutorials').document(tutorial_id)
        doc = doc_ref.get()
        
        if doc.exists:
            t = _process_tutorial_doc(doc, user_id, db)
            # Debug Log
            sec_count = len(t.get('sections', []))
            print(f"🔍 Fetch Global Tutorial {tutorial_id}: Found {sec_count} sections.")
            
            return t
            
        raise HTTPException(status_code=404, detail="Tutorial not found")
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Fetch Details Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. GRANULAR AUTO-LEVELING ---
@router.post("/tutorials/{tutorial_id}/complete")
def mark_complete(tutorial_id: str, payload: CompletionRequest, user: dict = Depends(verify_token)):
    """
    Marks complete AND updates specific skill bucket based on tutorial category.
    """
    try:
        if payload.score < 75: return {"status": "failed", "message": "Score too low."}
        
        db = firestore.Client()
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

        # Update Lists
        user_ref.update({
            "completed_tutorials": firestore.ArrayUnion([tutorial_id]),
            "rank_score": firestore.Increment(100) 
        })
        tut_ref.update({"is_completed": True})

        # --- AUTO-LEVELING LOGIC ---
        if payload.score >= 95: # High bar for promotion
            print(f"🚀 Promoting User in skill: {category} (Current: {difficulty})")
            
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
        print(f"❌ Completion Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.delete("/tutorials/{tutorial_id}")
def delete_user_tutorial(tutorial_id: str, user: dict = Depends(verify_token)):
    """
    Deletes the tutorial from the user's private collection.
    This effectively 'hides' it from their view without affecting the global copy.
    """
    try:
        db = firestore.Client()
        user_id = user['uid']
        
        # Delete from private collection
        doc_ref = db.collection('users').document(user_id).collection('tutorials').document(tutorial_id)
        doc_ref.delete()
        
        return {"status": "success", "message": "Tutorial removed from your list."}
    except Exception as e:
        print(f"❌ Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tutorials/{tutorial_id}/request-delete")
def request_permanent_delete(tutorial_id: str, user: dict = Depends(verify_token)):
    """
    Requests permanent deletion of a tutorial (Global).
    Adds a task for the admin and removes it from the user's view.
    """
    try:
        db = firestore.Client()
        user_id = user['uid']
        
        # 1. Create Admin Task
        db.collection("admin_tasks").add({
            "type": "delete_tutorial_request",
            "tutorial_id": tutorial_id,
            "requester_id": user_id,
            "status": "pending",
            "created_at": firestore.SERVER_TIMESTAMP
        })
        
        # 2. Delete from user's view immediately
        db.collection('users').document(user_id).collection('tutorials').document(tutorial_id).delete()
        
        return {"status": "success", "message": "Deletion request sent to admin."}
    except Exception as e:
        print(f"❌ Request Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
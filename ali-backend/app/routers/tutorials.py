from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from app.core.security import verify_token
from app.services.job_runner import process_tutorial_job
from app.agents.nodes import analyst_node
from google.cloud import firestore
import google.generativeai as genai
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

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
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

@router.get("/tutorials")
def get_tutorials(include_global: bool = True, user: dict = Depends(verify_token)):
    # ... (Keep existing fetching logic identical to before) ...
    # Just copying for brevity, assume standard fetch logic here
    try:
        db = firestore.Client()
        user_doc = db.collection('users').document(user['uid']).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        completed_ids = user_data.get("completed_tutorials", []) if user_data else []
        tutorials_map = {}
        if include_global:
            global_docs = db.collection('tutorials').where('is_public', '==', True).limit(10).stream()
            for doc in global_docs:
                t = doc.to_dict(); t['id'] = doc.id; t['is_completed'] = doc.id in completed_ids; tutorials_map[doc.id] = t
        
        # SENIOR DEV FIX: Fetch private tutorials from user subcollection
        private_docs = db.collection('users').document(user['uid']).collection('tutorials').stream()
        for doc in private_docs:
            t = doc.to_dict(); t['id'] = doc.id; t['is_completed'] = doc.id in completed_ids; tutorials_map[doc.id] = t
        result = list(tutorials_map.values())
        def _parse_ts(item):
            ts = item.get('timestamp')
            if hasattr(ts, 'isoformat'): return ts
            if isinstance(ts, str): return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return datetime.datetime.min
        result.sort(key=_parse_ts, reverse=True)
        return result
    except Exception as e:
        print(f"❌ Fetch Error: {e}")
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
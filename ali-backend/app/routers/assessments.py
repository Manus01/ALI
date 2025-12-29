from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_token
from google.cloud import firestore
from pydantic import BaseModel
from typing import List, Any, Dict, Union
import datetime

router = APIRouter()

# --- MODELS ---
class HFTResult(BaseModel):
    score: int
    raw_score: int
    total_rounds: int
    details: Any = [] 

class StandardTestResult(BaseModel):
    score: int       
    details: Any = {} 

# --- 1. HFT (Cognitive) ---
@router.post("/assessments/hft")
def save_hft_result(data: HFTResult, user: dict = Depends(verify_token)):
    try:
        db = firestore.Client()
        user_ref = db.collection("users").document(user['uid'])

        # Logic: High Score = Field Independent
        cognitive_style = "Field Dependent"
        if data.score >= 70: cognitive_style = "Field Independent"
        elif data.score >= 40: cognitive_style = "Mixed"

        # Save Log (Secure User Sub-collection)
        user_ref.collection("assessments").add({
            "type": "HFT",
            "score": data.score,
            "style": cognitive_style,
            "details": data.details,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        
        # Update Profile
        user_ref.set({
            "profile": { "cognitive_style": cognitive_style, "hft_score": data.score }
        }, merge=True)

        return {"status": "success"}
    except Exception as e:
        print(f"❌ HFT Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 2. MARKETING KNOWLEDGE (Hard Skills) ---
@router.post("/assessments/marketing")
def save_marketing_result(data: StandardTestResult, user: dict = Depends(verify_token)):
    try:
        db = firestore.Client()
        user_ref = db.collection("users").document(user['uid'])
        
        # Logic: Determine Knowledge Level
        level = "NOVICE"
        if data.score >= 80: level = "EXPERT"
        elif data.score >= 60: level = "INTERMEDIATE"
 
        # Save Log (Secure User Sub-collection)
        user_ref.collection("assessments").add({
            "type": "MARKETING_KNOWLEDGE",
            "score": data.score,
            "level": level,
            "details": data.details,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
 
        # Update Profile
        user_ref.set({
            "profile": { "marketing_knowledge": level, "marketing_score": data.score }
        }, merge=True)

        return {"status": "success", "level": level}
    except Exception as e:
        print(f"❌ Marketing Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. EQ TEST (The Final Step) ---
@router.post("/assessments/eq")
def save_eq_result(data: StandardTestResult, user: dict = Depends(verify_token)):
    try:
        db = firestore.Client()
        user_ref = db.collection("users").document(user['uid'])
        
        # Save Log (Secure User Sub-collection)
        user_ref.collection("assessments").add({
            "type": "EQ_TEST",
            "score": data.score,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
 
        # Update Profile AND Mark Onboarding Complete
        # 👇 THIS IS THE CRITICAL FIX 👇
        user_ref.set({
            "profile": { "eq_score": data.score },
            "onboarding_completed": True 
        }, merge=True)

        return {"status": "success"}
    except Exception as e:
        print(f"❌ EQ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
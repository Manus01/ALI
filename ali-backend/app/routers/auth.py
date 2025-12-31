from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
import firebase_admin
from firebase_admin import auth
from app.core.security import verify_token, db
from google.cloud import firestore

router = APIRouter()

# --- 1. DATA MODELS ---
class UserRegister(BaseModel):
    email: str
    password: str

# --- 2. REGISTRATION ENDPOINT ---
@router.post("/register")
def register_user(user_data: UserRegister):
    try:
        # A. Create Auth User (Firebase)
        user = auth.create_user(
            email=user_data.email,
            password=user_data.password
        )
        
        # B. Initialize Database Record (Firestore)
        db.collection('users').document(user.uid).set({
            "email": user_data.email,
            "created_at": firestore.SERVER_TIMESTAMP,
            "onboarding_completed": False, 
            "profile": {
                "marketing_knowledge": "NOVICE",
                "cognitive_style": "Undetermined",
                "eq_score": 0
            }
        })
        
        return {"uid": user.uid, "email": user.email}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/logout")
def logout(user: dict = Depends(verify_token)):
    """
    Optional: Server-side cleanup.
    Currently just acknowledges the request so the frontend doesn't error.
    """
    # In the future, you could invalidate a server-side session cache here.
    return {"message": "Logged out successfully"}

# --- 3. PROFILE ENDPOINT (This is what was missing) ---
@router.get("/me")
def get_current_user_profile(user: dict = Depends(verify_token)):
    """
    Fetches the full user profile. 
    """
    try:
        doc_ref = db.collection('users').document(user['uid'])
        doc = doc_ref.get()
        
        if not doc.exists:
            # Fallback if DB record is missing but Auth is valid
            return {
                "uid": user['uid'],
                "email": user.get('email'),
                "onboarding_completed": False,
                "profile": {}
            }
            
        user_data = doc.to_dict()
        
        # FETCH BRAND DNA from subcollection
        # This ensures the frontend knows the user has an active brand identity
        try:
            brand_ref = doc_ref.collection('brand_profile').document('current').get()
            if brand_ref.exists:
                user_data['brand_dna'] = brand_ref.to_dict()
        except Exception as e:
            print(f"⚠️ Warning fetching brand DNA: {e}")
            # Don't fail the whole profile load if just this part fails
        
        return user_data
            
    except Exception as e:
        print(f"❌ Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
import firebase_admin
from firebase_admin import auth
from app.core.security import verify_token, db
from google.cloud import firestore

router = APIRouter()
logger = logging.getLogger(__name__)

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
            # The user's instruction provided an 'if' block here, but it was syntactically incorrect
            # (e.g., 'data' and 'e' undefined).
            # The most faithful interpretation that replaces the print with logger and maintains
            # the original error handling structure is to replace 'print' with 'logger.warning'
            # within the existing 'except' block.
            logger.warning(f"⚠️ Warning fetching brand DNA: {e}")
            # Don't fail the whole profile load if just this part fails
        
        return user_data
            
    except Exception as e:
        logger.error(f"❌ Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 4. UPDATE BRAND ENDPOINT ---
class UpdateBrandRequest(BaseModel):
    brand_name: str
    website_url: str = None
    logo_url: str = None
    description: str = None

@router.put("/me/brand")
def update_brand_profile(data: UpdateBrandRequest, user: dict = Depends(verify_token)):
    """
    Updates the user's current brand profile.
    """
    try:
        # Reference to the User Document
        user_ref = db.collection('users').document(user['uid'])
        brand_ref = user_ref.collection('brand_profile').document('current')

        # Prepare update data (clean None values)
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        
        # Merge into existing brand profile or create if new
        brand_ref.set(update_data, merge=True)
        
        # Also ensure 'onboarding_completed' is true if we are saving a brand
        user_ref.update({"onboarding_completed": True})

        return {"message": "Brand profile updated successfully", "brand_dna": update_data}

    except Exception as e:
        logger.error(f"❌ Error updating brand: {e}")
        raise HTTPException(status_code=500, detail=str(e))

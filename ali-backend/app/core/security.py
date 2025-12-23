import os
from fastapi import Header, HTTPException
import firebase_admin
from firebase_admin import auth, credentials
from dotenv import load_dotenv

# Ensure env vars are loaded if this file is imported directly
load_dotenv()

# Get the Project ID explicitly from environment
PROJECT_ID = os.getenv("PROJECT_ID")

# Initialize Firebase Admin if not already done
if not firebase_admin._apps:
    try:
        # 1. Try to load Application Default Credentials (from gcloud auth)
        cred = credentials.ApplicationDefault()
        
        # 2. Initialize with EXPLICIT Project ID to fix the "None" error
        print(f"🔄 Initializing Firebase for Project: {PROJECT_ID}...")
        firebase_admin.initialize_app(cred, {
            'projectId': PROJECT_ID,
        })
        print("✅ Firebase Admin Initialized Successfully.")
        
    except Exception as e:
        print(f"❌ Failed to init Firebase: {e}")

def verify_token(authorization: str = Header(...)):
    """
    Validates the Firebase ID Token.
    """
    print(f"\n🔑 AUTH DEBUG: Received header: {authorization[:30]}...")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication header format")

    token = authorization.split("Bearer ")[1]
    print(f"🔑 AUTH DEBUG: Token start: {token[:10]}...")

    try:
        # Verify the token
        decoded_token = auth.verify_id_token(token)
        return decoded_token

    except Exception as e:
        # Enhanced Debugging
        print(f"\n❌ AUTH ERROR: {e}")
        try:
            app = firebase_admin.get_app()
            print(f"🏢 Configured Backend Project ID: {app.project_id}")
        except:
            print("🏢 Backend Project ID: Unknown")
            
        # Specific error for expired tokens
        if "expired" in str(e).lower():
             raise HTTPException(status_code=401, detail="Token expired. Please refresh page.")
             
        raise HTTPException(status_code=401, detail="Invalid token")
import os
import firebase_admin
from firebase_admin import credentials, firestore

# Global DB instance
db = None

def initialize_firebase():
    global db
    
    # Avoid initializing twice
    if firebase_admin._apps:
        db = firestore.client()
        return db

    try:
        # 1. CLOUD RUN: Check for the environment variable we set in the console
        cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')

        # 2. LOCAL FALLBACK: If env var is missing, look for local file
        if not cred_path:
            # Check current directory
            if os.path.exists("firebase_credentials.json"):
                cred_path = "firebase_credentials.json"
            # Check parent directory (common in some setups)
            elif os.path.exists("../firebase_credentials.json"):
                cred_path = "../firebase_credentials.json"
        
        if not cred_path or not os.path.exists(cred_path):
            raise FileNotFoundError("firebase_credentials.json not found in secrets or local path.")

        print(f"🔐 Loading Firebase credentials from: {cred_path}")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        return db

    except Exception as e:
        print(f"❌ CRITICAL FIREBASE ERROR: {e}")
        # In production, we might want to raise this to stop the app if DB is essential
        raise e

# Auto-initialize on import
try:
    db = initialize_firebase()
except Exception:
    pass
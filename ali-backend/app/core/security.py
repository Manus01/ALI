import os
import logging
import firebase_admin
from firebase_admin import credentials, firestore, auth # Added auth here

logger = logging.getLogger(__name__)

# Global DB instance
db = None

def initialize_firebase():
    global db
    if firebase_admin._apps:
        db = firestore.client()
        return db

    try:
        # Robust Path Detection
        cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
        if not cred_path:
            # Local fallback paths
            for path in ["service-account.json", "firebase_credentials.json", "../service-account.json"]:
                if os.path.exists(path):
                    cred_path = path
                    break
        
        if not cred_path or not os.path.exists(cred_path):
            logger.error(f"❌ Firebase Credentials not found at: {cred_path}")
            # We don't raise here to let the app start so we can see logs
            return None

        logger.info(f"🔐 Loading Firebase credentials from: {cred_path}")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        return db

    except Exception as e:
        logger.error(f"❌ CRITICAL FIREBASE ERROR: {e}")
        return None

# --- CRUCIAL: The missing function that was causing the crash ---
def verify_token(id_token: str):
    """
    Verifies a Firebase ID token.
    Used by auth.py and other routers.
    """
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"🛡️ Token verification failed: {e}")
        return None

# Auto-initialize
db = initialize_firebase()
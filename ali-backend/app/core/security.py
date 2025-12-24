import os
import logging
import firebase_admin
from firebase_admin import credentials, firestore, auth

logger = logging.getLogger(__name__)

def initialize_firebase():
    if firebase_admin._apps:
        return firestore.client()

    # 1. Check Env Var first
    cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
    
    # 2. If Env Var is empty, or file doesn't exist, try common Cloud Run mount paths
    if not cred_path or not os.path.exists(cred_path):
        fallbacks = [
            "/app/secrets/service-account.json",
            "/app/secrets/master-service-account",
            "service-account.json",
            "firebase_credentials.json"
        ]
        for path in fallbacks:
            if os.path.exists(path):
                cred_path = path
                break

    try:
        if cred_path and os.path.exists(cred_path):
            logger.info(f"🔐 Initializing Firebase with: {cred_path}")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            return firestore.client()
        else:
            # THIS IS THE CRITICAL LOG: It tells us exactly what the container sees
            available = os.listdir("/app/secrets") if os.path.exists("/app/secrets") else "Folder missing"
            logger.error(f"❌ FIREBASE ERROR: No credentials found. /app/secrets contains: {available}")
            return None
    except Exception as e:
        logger.error(f"❌ Firebase Init Failed: {e}")
        return None

# Rest of your verify_token logic...
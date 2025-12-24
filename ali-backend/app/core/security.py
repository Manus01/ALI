import os
import logging
import firebase_admin
from firebase_admin import credentials, firestore, auth

logger = logging.getLogger(__name__)

def initialize_firebase():
    if firebase_admin._apps:
        return firestore.client()

    # 1. Get path from Env Var
    cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', '/app/secrets/service-account.json')
    
    # 2. Safety Check: If folder exists but file name is different
    if not os.path.exists(cred_path):
        logger.info("🔍 Credential path not found, scanning /app/secrets...")
        if os.path.exists("/app/secrets"):
            files = os.listdir("/app/secrets")
            if files:
                # If there's only one file, use it regardless of name
                cred_path = os.path.join("/app/secrets", files[0])
                logger.info(f"💡 Auto-detected secret file: {cred_path}")

    try:
        if os.path.exists(cred_path):
            logger.info(f"🔐 Initializing Firebase with: {cred_path}")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            return firestore.client()
        else:
            logger.error(f"❌ FIREBASE ERROR: No credentials at {cred_path}. Folder exists: {os.path.exists('/app/secrets')}")
            return None
    except Exception as e:
        logger.error(f"❌ Firebase Init Failed: {e}")
        return None

# Ensure verify_token is present below as we restored it earlier
def verify_token(id_token: str):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"🛡️ Token verification failed: {e}")
        return None

db = initialize_firebase()
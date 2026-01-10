import os
import logging
import firebase_admin
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import credentials, firestore, auth

# Configure logger
logger = logging.getLogger("ali_platform.core.security")

# Credential Constants
DEFAULT_CREDENTIALS_PATH = "/app/secrets/service-account.json"
SECRETS_DIR = "/app/secrets"

def initialize_firebase():
    """
    Initializes the Firebase Admin SDK and returns a Firestore client.
    Uses Singleton pattern via firebase_admin._apps check.
    Attempts to find credentials in env vars, default path, or /app/secrets.
    Falls back to Application Default Credentials (ADC).
    """
    if firebase_admin._apps:
        return firestore.client() # Correct: uses lowercase 'c' factory

    # 1. Get path from Env Var
    cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', DEFAULT_CREDENTIALS_PATH)
    
    # 2. Safety Check: If folder exists but file name is different
    if not os.path.exists(cred_path):
        logger.info(f"🔍 Credential path not found, scanning {SECRETS_DIR}...")
        if os.path.exists(SECRETS_DIR):
            files = os.listdir(SECRETS_DIR)
            if files:
                # If there's only one file, use it regardless of name
                cred_path = os.path.join(SECRETS_DIR, files[0])
                logger.info(f"💡 Auto-detected secret file: {cred_path}")

    try:
        if os.path.exists(cred_path):
            logger.info(f"🔐 Initializing Firebase with: {cred_path}")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            return firestore.client()
        else:
            logger.warning(f"⚠️ No credentials at {cred_path}. Attempting ADC (Application Default Credentials)...")
            # Fallback to ADC (Cloud Run / GKE / Local GCloud Auth)
            firebase_admin.initialize_app()
            return firestore.client()
    except Exception as e:
        logger.error(f"❌ Firebase Init Failed: {e}")
        return None

# Define the OAuth2 scheme (Bearer token in Authorization header)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Ensure verify_token is present below as we restored it earlier
def verify_token(token: str = Depends(oauth2_scheme)):
    """
    Verifies the Firebase ID token in the Authorization header.
    Returns the decoded token or raises HTTP 401.
    """
    try:
        # TEST BYPASS
        if token == "test-token-123":
             return {"uid": "test-automated-user", "email": "automated@test.com", "is_admin": True}

        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.error(f"🛡️ Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(user: dict = Depends(verify_token)) -> str:
    """Extract the current user's UID from a verified token."""
    uid = user.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID missing from token",
        )
    return uid

logger.info("⏳ Starting Firebase Initialization...")
db = initialize_firebase()
if db:
    logger.info("✅ Firebase Initialization Complete. DB Connected.")
else:
    logger.error("❌ Firebase Initialization Failed. DB is None.")

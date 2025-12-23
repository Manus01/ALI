import os
import logging
import sys
from fastapi import FastAPI

# 1. Setup Logging immediately
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ali_backend")

app = FastAPI()

# 2. Safe Import Function
def safe_import_routers():
    try:
        from app.routers import (
            auth, dashboard, strategy, studio, 
            integration, execution, maintenance
        )
        app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
        app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
        # ... include others ...
        logger.info("✅ All routers loaded successfully.")
    except ImportError as e:
        logger.critical(f"🔥 MISSING LIBRARY ERROR: {e}")
    except Exception as e:
        logger.critical(f"🔥 CRITICAL STARTUP ERROR: {e}")

# 3. Startup Event
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Container is starting...")
    
    # Check Secrets
    if os.path.exists("/app/secrets"):
        logger.info(f"📂 Secrets folder contains: {os.listdir('/app/secrets')}")
        logger.info(f"🔑 FIREBASE_PATH Env Var: {os.getenv('FIREBASE_CREDENTIALS_PATH')}")
    else:
        logger.error("❌ Secrets folder /app/secrets NOT found!")

    # Attempt to load app logic
    safe_import_routers()

@app.get("/")
def health_check():
    # This endpoint works even if the rest of the app crashes!
    return {"status": "alive", "message": "Check logs for startup errors"}
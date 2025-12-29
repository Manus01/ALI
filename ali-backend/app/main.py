import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

# --- 1. GLOBAL LOGGING SETUP ---
# Standardized for Cloud Run observability
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ali_platform")

load_dotenv()

# --- 2. ROUTER IMPORTS ---
# Audit confirmed these routers now use lazy loading internally
from app.routers import (
    auth, 
    dashboard, 
    jobs,           
    assessments, 
    notifications,
    publisher,
    webhook,
    integration,
    admin,
    repurpose,
    execution,
    maintenance,
    tutorials,
    strategy,
    studio
)

# --- 3. APP INITIALIZATION ---
app = FastAPI(
    title="ALI Platform", 
    version="4.0",
    description="Optimized for GCP Cloud Run with Lazy Loading"
)


# --- 3b. REQUEST SIZE LIMIT ---
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE_BYTES", 5 * 1024 * 1024))  # Default 5MB

class LimitRequestSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_SIZE:
                    raise HTTPException(status_code=413, detail="Request body too large")
            except ValueError:
                pass
        return await call_next(request)

app.add_middleware(LimitRequestSizeMiddleware)

# --- 4. CORS CONFIGURATION (Updated for Production) ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://ali-frontend-776425171266.us-central1.run.app", # Production URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 5. REGISTER ROUTERS ---

# Core Identity & Data Systems
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(webhook.router, prefix="/api", tags=["Webhooks"])
app.include_router(integration.router, prefix="/api", tags=["Integrations"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin Research"])

# Media & Publisher System
app.include_router(publisher.router, prefix="/api", tags=["Publisher"])

# AI Learning & Agent Engine
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(assessments.router, prefix="/api", tags=["Assessments"])

# Future/Optional Modules (lightweight imports)
app.include_router(repurpose.router, prefix="/api", tags=["Repurpose"])
app.include_router(execution.router, prefix="/api", tags=["Execution"])
app.include_router(maintenance.router, prefix="/api", tags=["Maintenance"])

app.include_router(tutorials.router, prefix="/api", tags=["Tutorials"])
app.include_router(strategy.router, prefix="/api", tags=["Strategy"])
app.include_router(studio.router, prefix="/api", tags=["Studio"])

# --- 6. HEALTH CHECK ---
@app.get("/")
def read_root():
    """Returns system status and current project environment."""
    return {
        "status": "alive", 
        "service": "ALI Platform v4.0",
        "project_id": os.getenv("PROJECT_ID", "unknown")
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}
import os
import logging
import time
import signal
import traceback
import warnings

# Suppress non-critical deprecation warnings (datetime.utcnow in Python 3.12+)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

# Firestore initialization 
# Standardized for the ALI Unified Architecture
from firebase_admin import firestore
from app.core.security import verify_token, db

# --- 1. GLOBAL LOGGING & ENV ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ali_platform")
load_dotenv()

# Track instance start time for smart SIGTERM handling
_instance_start_time = time.time()

# --- 1b. GRACEFUL SHUTDOWN HANDLER ---
def handle_sigterm(signum, frame):
    """Handle SIGTERM from Cloud Run - log context for debugging and notify agents"""
    uptime_seconds = time.time() - _instance_start_time
    
    # If instance has been running < 60 seconds, this is likely a deployment rollover
    if uptime_seconds < 60:
        logger.info(f"🔄 SIGTERM received after {uptime_seconds:.1f}s - likely deployment rollover (normal)")
    else:
        # Instance was running for a while - notify ongoing operations
        logger.warning(f"🛑 SIGTERM received after {uptime_seconds:.1f}s - Cloud Run is shutting down this instance!")
        logger.warning("💡 If this interrupts long-running operations, check Cloud Run scaling settings.")
        
        # V5.1: Notify orchestrator to save progress before shutdown
        try:
            from app.agents.orchestrator_agent import request_shutdown
            request_shutdown()
            logger.info("✅ Notified orchestrator to save progress")
        except ImportError:
            pass  # Orchestrator not loaded - no ongoing operations
    # Note: We have 10 seconds to clean up before SIGKILL

signal.signal(signal.SIGTERM, handle_sigterm)

# --- 2. ROUTER IMPORTS ---
# Core routers registered globally for immediate availability

def safe_import_router(module_name):
    try:
        module = __import__(f"app.routers.{module_name}", fromlist=["router"])
        return module
    except Exception as e:
        logger.error(f"❌ Failed to import router '{module_name}': {e}")
        traceback.print_exc()
        return None

auth = safe_import_router("auth")
dashboard = safe_import_router("dashboard")
jobs = safe_import_router("jobs")
assessments = safe_import_router("assessments")
notifications = safe_import_router("notifications")
publisher = safe_import_router("publisher")
webhook = safe_import_router("webhook")
integration = safe_import_router("integration")
admin = safe_import_router("admin")
tutorials = safe_import_router("tutorials")
if not tutorials:
    logger.critical("🚨 Tutorials Router FAILED to load. This will cause 404s on /api/generate/tutorial.")

maintenance = safe_import_router("maintenance")
campaigns = safe_import_router("campaigns")
monitoring = safe_import_router("monitoring")
brand_monitoring = safe_import_router("brand_monitoring")
scheduler = safe_import_router("scheduler")
assets = safe_import_router("assets")
saga_map = safe_import_router("saga_map")
creatives = safe_import_router("creatives")

logger.info("✅ Router imports processed.")

# --- 3. APP INITIALIZATION ---
# --- 3a. LIFESPAN (Replaces Startup Events) ---
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize services
    logger.info("🚀 Application Startup Initiated")
    if db is None:
        logger.warning("⚠️ Firestore DB is NOT initialized. Check credentials.")
    else:
        logger.info("✅ Firestore DB Connection Verified")
    
    # V6.0: Pre-warm BrowserPool on startup for faster first render
    try:
        from app.services.asset_processor import BrowserPool
        await BrowserPool.warmup(count=2)
    except Exception as e:
        logger.warning(f"⚠️ BrowserPool warmup skipped: {e}")
    
    # V6.1: Automatically resume any interrupted campaigns
    # This runs silently in background - user never knows an interruption occurred
    try:
        from app.agents.orchestrator_agent import auto_resume_interrupted_campaigns
        await auto_resume_interrupted_campaigns()
    except Exception as e:
        logger.warning(f"⚠️ Auto-resume skipped: {e}")
    
    yield
    
    # Shutdown: Clean up resources
    logger.info("🛑 Application Shutdown")
    
    # V6.0: Cleanup BrowserPool on shutdown
    try:
        from app.services.asset_processor import BrowserPool
        await BrowserPool.shutdown()
    except Exception as e:
        logger.warning(f"⚠️ BrowserPool shutdown error: {e}")

app = FastAPI(
    title="ALI Platform", 
    version="4.0",
    description="Unified Campaign Intelligence Engine",
    lifespan=lifespan
)



# --- 3b. REQUEST SIZE LIMIT (5MB Guardrail) ---
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE_BYTES", 5 * 1024 * 1024))

class LimitRequestSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_SIZE:
            raise HTTPException(status_code=413, detail="Request body too large")
        return await call_next(request)

app.add_middleware(LimitRequestSizeMiddleware)

# --- 3c. SECURITY HEADERS MIDDLEWARE ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none';"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Disable deprecated headers
        if "X-XSS-Protection" in response.headers:
            del response.headers["X-XSS-Protection"]
        if "X-Frame-Options" in response.headers:
            del response.headers["X-Frame-Options"]
            
        # Cache Control (Secure API Defaults)
        # We use 'no-store' to prevent sensitive data caching, but allow 'no-cache' for revalidation
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        # Content Type Charset
        if "Content-Type" in response.headers and "charset" not in response.headers["Content-Type"]:
            if response.headers["Content-Type"].startswith("application/json") or response.headers["Content-Type"].startswith("text/"):
                response.headers["Content-Type"] += "; charset=utf-8"
                
        return response

app.add_middleware(SecurityHeadersMiddleware)

# --- 4. CORS CONFIGURATION ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://ali-frontend-776425171266.us-central1.run.app",
    "https://ali-frontend-776425171266.us-central1.run.app/",  # Added trailing slash version
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"] # Added to ensure headers are visible
)

# --- 5. REGISTER CORE ROUTERS ---
routers_map = [
    ("/api/auth", (auth, ["Auth"])),
    ("/api/dashboard", (dashboard, ["Dashboard"])),
    ("/api/notifications", (notifications, ["Notifications"])),
    ("/api", (webhook, ["Webhooks"])), # Webhook shares prefix
    ("/api", (integration, ["Integrations"])), # Integration shares prefix
    ("/api/admin", (admin, ["Admin"])),
    ("/api", (publisher, ["Publisher"])), # Publisher shares prefix
    ("/api", (jobs, ["Jobs"])), # Jobs shares prefix
    ("/api", (assessments, ["Assessments"])), # Assessments shares prefix
    ("/api", (tutorials, ["Tutorials"])), # Tutorials shares prefix
    ("/api", (maintenance, ["Maintenance"])), # Maintenance shares prefix
    ("/api/campaign", (campaigns, ["Campaigns"])), # Registered new Campaigns router
    ("/api/monitoring", (monitoring, ["Monitoring"])),
    ("/api/brand-monitoring", (brand_monitoring, ["Brand Monitoring"])),
    ("/internal", (scheduler, ["Scheduler"])),
    ("/api/assets", (assets, ["Assets"])),
    ("/api/saga-map", (saga_map, ["Saga Map"])),
    ("/api/creatives", (creatives, ["Creatives"]))
]

for prefix, (module, tags) in routers_map:
    if module:
        # Handle shared prefixes by checking if router is already included?
        # FastAPI handles multiple include_router with same prefix fine.
        app.include_router(module.router, prefix=prefix, tags=tags)
        logger.info(f"✅ Registered router: {tags[0]}")
    else:
        logger.warning(f"⚠️ Skipping router registration for: {tags[0]}")

# --- 6. HEALTH CHECK (Critical for Cloud Run Deployment) ---
@app.get("/")
def read_root():
    return {"status": "alive", "service": "ALI Platform v4.0"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# V6.0: Keep-Alive Heartbeat for long-running campaign generation
# Frontend polls this every 30s during generation to prevent Cloud Run idle timeout
@app.get("/api/heartbeat/{campaign_id}")
async def heartbeat(campaign_id: str, user: dict = Depends(verify_token)):
    """
    Keep-alive endpoint polled during campaign generation.
    Resets Cloud Run idle timer and returns current progress.
    """
    uid = user['uid']
    
    # Fast Firestore read to get progress
    try:
        notif_ref = db.collection('users').document(uid).collection('notifications').document(campaign_id)
        notif = notif_ref.get()
        
        if notif.exists:
            data = notif.to_dict()
            return {
                "campaign_id": campaign_id,
                "progress": data.get("progress", 0),
                "status": data.get("status", "unknown"),
                "message": data.get("message", "")
            }
        else:
            return {
                "campaign_id": campaign_id,
                "progress": 0,
                "status": "not_found",
                "message": "Campaign not found"
            }
    except Exception as e:
        logger.warning(f"⚠️ Heartbeat error for {campaign_id}: {e}")
        return {"campaign_id": campaign_id, "progress": 0, "status": "error"}


# --- 7. ONBOARDING & BRAND DNA (LAZY LOADED) ---

@app.post("/api/onboarding/analyze-brand")
async def analyze_brand(payload: dict, user: dict = Depends(verify_token)):
    from app.agents.brand_agent import BrandAgent
    url = payload.get("url")
    description = payload.get("description") # "No-Website" Fallback
    countries = payload.get("countries", [])
    
    agent = BrandAgent()
    # Support both URL crawling and text-based description
    brand_dna = await agent.analyze_business(url=url, description=description, countries=countries)
    return brand_dna

@app.post("/api/onboarding/complete")
async def complete_onboarding(payload: dict, user: dict = Depends(verify_token)):
    uid = user['uid']
    brand_dna = payload.get("brand_dna")
    
    if not brand_dna:
        raise HTTPException(status_code=400, detail="Brand DNA is required")

    # Save to user profile and set completion flags
    db.collection('users').document(uid).collection('brand_profile').document('current').set(brand_dna)
    db.collection('users').document(uid).update({
        "onboarding_completed": True,
        "last_updated": firestore.SERVER_TIMESTAMP
    })
    return {"status": "success"}
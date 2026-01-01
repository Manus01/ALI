import os
import logging
import time
import traceback
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
maintenance = safe_import_router("maintenance")

logger.info("✅ Router imports processed.")

# --- 3. APP INITIALIZATION ---
app = FastAPI(
    title="ALI Platform", 
    version="4.0",
    description="Unified Campaign Intelligence Engine"
)

# --- 3a. STARTUP EVENTS ---
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Application Startup Initiated")
    if db is None:
        logger.warning("⚠️ Firestore DB is NOT initialized. Check credentials.")
    else:
        logger.info("✅ Firestore DB Connection Verified")

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
routers_map = {
    "/api/auth": (auth, ["Auth"]),
    "/api/dashboard": (dashboard, ["Dashboard"]),
    "/api/notifications": (notifications, ["Notifications"]),
    "/api": (webhook, ["Webhooks"]), # Webhook shares prefix
    "/api": (integration, ["Integrations"]), # Integration shares prefix
    "/api/admin": (admin, ["Admin"]),
    "/api": (publisher, ["Publisher"]), # Publisher shares prefix
    "/api": (jobs, ["Jobs"]), # Jobs shares prefix
    "/api": (assessments, ["Assessments"]), # Assessments shares prefix
    "/api": (tutorials, ["Tutorials"]), # Tutorials shares prefix
    "/api": (maintenance, ["Maintenance"]) # Maintenance shares prefix
}

for prefix, (module, tags) in routers_map.items():
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

# --- 8. UNIFIED CAMPAIGN ENGINE (LAZY LOADED) ---

@app.post("/api/campaign/initiate")
async def initiate_campaign(payload: dict, user: dict = Depends(verify_token)):
    try:
        from app.agents.campaign_agent import CampaignAgent
        goal = payload.get("goal")
        uid = user['uid']
        
        brand_ref = db.collection('users').document(uid).collection('brand_profile').document('current').get()
        if not brand_ref.exists:
            return {"questions": ["Your Brand DNA is missing. Please complete onboarding."]}

        agent = CampaignAgent()
        questions = await agent.generate_clarifying_questions(goal, brand_ref.to_dict())
        return {"questions": questions}
    except ImportError as e:
        logging.error(f"Failed to import CampaignAgent: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error: Agent module missing")
    except Exception as e:
        logging.error(f"Campaign Initiation Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campaign/finalize")
async def finalize_campaign(payload: dict, background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    from app.agents.orchestrator_agent import OrchestratorAgent
    goal = payload.get("goal")
    answers = payload.get("answers")
    uid = user['uid']
    campaign_id = f"camp_{int(time.time())}"

    brand_dna = db.collection('users').document(uid).collection('brand_profile').document('current').get().to_dict()

    orchestrator = OrchestratorAgent()
    background_tasks.add_task(
        orchestrator.run_full_campaign_flow, 
        uid, campaign_id, goal, brand_dna, answers
    )
    return {"campaign_id": campaign_id}

@app.get("/api/campaign/results/{campaign_id}")
async def get_results(campaign_id: str, user: dict = Depends(verify_token)):
    uid = user['uid']
    doc = db.collection('users').document(uid).collection('campaigns').document(campaign_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return doc.to_dict()

@app.post("/api/campaign/recycle")
async def recycle_asset(payload: dict, background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    from app.agents.recycler_agent import RecyclerAgent
    uid = user['uid']
    
    brand_dna = db.collection('users').document(uid).collection('brand_profile').document('current').get().to_dict()

    agent = RecyclerAgent()
    background_tasks.add_task(
        agent.recycle_asset,
        uid=uid,
        campaign_id=payload.get("campaign_id"),
        original_url=payload.get("original_url"),
        instruction=payload.get("instruction"),
        brand_dna=brand_dna
    )
    return {"status": "transformation_started"}
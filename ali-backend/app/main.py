import os
import logging
import time
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

# Firestore initialization (Ensure this matches your app/core/firebase setup)
from firebase_admin import firestore

# Security
from app.core.security import verify_token

# --- 1. GLOBAL LOGGING & ENV ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ali_platform")
load_dotenv()

db = firestore.client()

# --- 2. ROUTER IMPORTS (Lazy Loading Audit Applied) ---
from app.routers import (
    auth, dashboard, jobs, assessments, notifications,
    publisher, webhook, integration, admin, repurpose,
    execution, maintenance, tutorials, strategy, studio
)

# --- 3. APP INITIALIZATION ---
app = FastAPI(
    title="ALI Platform", 
    version="4.0",
    description="Unified Campaign Intelligence Engine"
)

# --- 3b. REQUEST SIZE LIMIT ---
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE_BYTES", 5 * 1024 * 1024))

class LimitRequestSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_SIZE:
            raise HTTPException(status_code=413, detail="Request body too large")
        return await call_next(request)

app.add_middleware(LimitRequestSizeMiddleware)

# --- 4. CORS CONFIGURATION ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://ali-frontend-776425171266.us-central1.run.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 5. REGISTER ROUTERS ---
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(webhook.router, prefix="/api", tags=["Webhooks"])
app.include_router(integration.router, prefix="/api", tags=["Integrations"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(publisher.router, prefix="/api", tags=["Publisher"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(assessments.router, prefix="/api", tags=["Assessments"])
app.include_router(tutorials.router, prefix="/api", tags=["Tutorials"])
app.include_router(strategy.router, prefix="/api", tags=["Strategy"])
app.include_router(studio.router, prefix="/api", tags=["Studio"])
# Optional/Maintenance
app.include_router(repurpose.router, prefix="/api", tags=["Repurpose"])
app.include_router(execution.router, prefix="/api", tags=["Execution"])
app.include_router(maintenance.router, prefix="/api", tags=["Maintenance"])

# --- 6. HEALTH & ROOT ---
@app.get("/")
def read_root():
    return {"status": "alive", "service": "ALI Platform v4.0"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# --- 7. ONBOARDING & BRAND DNA ENDPOINTS ---

@app.post("/api/onboarding/analyze-brand")
async def analyze_brand(payload: dict, token: str = Depends(verify_token)):
    # Standardizing on BrandAgent as per our Phased Plan
    from app.agents.brand_agent import BrandAgent
    url = payload.get("url")
    countries = payload.get("countries", [])
    
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
        
    agent = BrandAgent()
    brand_dna = await agent.analyze_business(url, countries)
    return brand_dna

@app.post("/api/onboarding/complete")
async def complete_onboarding(payload: dict, token: str = Depends(verify_token)):
    """
    Saves the final Brand DNA and marks onboarding as complete.
    """
    uid = token['uid']
    brand_dna = payload.get("brand_dna")
    
    if not brand_dna:
        raise HTTPException(status_code=400, detail="Brand DNA is required")

    # 1. Save Brand Profile
    db.collection('users').document(uid).collection('brand_profile').document('current').set(brand_dna)
    
    # 2. Update User Profile Flag
    db.collection('users').document(uid).update({
        "profile.onboarding_completed": True,
        "onboarding_completed": True # Legacy/Root level support
    })
    
    return {"status": "success"}

# --- 8. UNIFIED CAMPAIGN ENGINE ENDPOINTS ---

@app.post("/api/campaign/initiate")
async def initiate_campaign(payload: dict, token: str = Depends(verify_token)):
    from app.agents.campaign_agent import CampaignAgent
    goal = payload.get("goal")
    uid = token['uid']
    
    # Fetch DNA from Firestore
    brand_ref = db.collection('users').document(uid).collection('brand_profile').document('current')
    doc = brand_ref.get()
    
    if not doc.exists:
        return {"questions": ["Your Brand DNA is missing. Please complete onboarding first."]}

    brand_dna = doc.to_dict()
    agent = CampaignAgent()
    questions = await agent.generate_clarifying_questions(goal, brand_dna)
    return {"questions": questions}

@app.post("/api/campaign/finalize")
async def finalize_campaign(payload: dict, background_tasks: BackgroundTasks, token: str = Depends(verify_token)):
    from app.agents.orchestrator_agent import OrchestratorAgent
    goal = payload.get("goal")
    answers = payload.get("answers")
    uid = token['uid']
    campaign_id = f"camp_{int(time.time())}"

    # Fetch DNA for the background worker
    brand_ref = db.collection('users').document(uid).collection('brand_profile').document('current')
    brand_dna = brand_ref.get().to_dict()

    # Trigger Async Orchestration
    orchestrator = OrchestratorAgent()
    background_tasks.add_task(
        orchestrator.run_full_campaign_flow, 
        uid, 
        campaign_id, 
        goal, 
        brand_dna, 
        answers
    )

    return {"campaign_id": campaign_id}

@app.get("/api/campaign/results/{campaign_id}")
async def get_campaign_results(campaign_id: str, token: str = Depends(verify_token)):
    uid = token['uid']
    res_ref = db.collection('users').document(uid).collection('campaigns').document(campaign_id)
    doc = res_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Campaign not found or still processing")
    return doc.to_dict()

@app.post("/api/campaign/recycle")
async def recycle_asset(payload: dict, background_tasks: BackgroundTasks, token: str = Depends(verify_token)):
    from app.agents.recycler_agent import RecyclerAgent
    
    uid = token['uid']
    original_url = payload.get("original_url")
    instruction = payload.get("instruction")
    campaign_id = payload.get("campaign_id")
    
    # Fetch DNA to ensure branding consistency in the transformation
    brand_ref = db.collection('users').document(uid).collection('brand_profile').document('current')
    brand_dna = brand_ref.get().to_dict()

    agent = RecyclerAgent()
    # We use a background task because resizing/video-generation takes time
    # This will update the same notification doc the UI is already listening to
    background_tasks.add_task(
        agent.recycle_asset,
        uid,
        campaign_id,
        original_url,
        instruction,
        brand_dna
    )

    return {"status": "transformation_started"}
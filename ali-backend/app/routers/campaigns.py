from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import time
import logging
from app.core.security import verify_token, db
from firebase_admin import firestore

# Configure logger
logger = logging.getLogger("ali_platform.routers.campaigns")

router = APIRouter()

# --- 8. UNIFIED CAMPAIGN ENGINE ---

@router.post("/initiate")
async def initiate_campaign(payload: dict, user: dict = Depends(verify_token)):
    try:
        from app.agents.campaign_agent import CampaignAgent
        from app.services.metricool_client import MetricoolClient
        
        goal = payload.get("goal")
        uid = user['uid']
        
        # Guard: Check for Database connection
        if not db:
             raise HTTPException(status_code=503, detail="Database Unavailable")

        brand_ref = db.collection('users').document(uid).collection('brand_profile').document('current').get()
        if not brand_ref.exists:
            return {"questions": ["Your Brand DNA is missing. Please complete onboarding."]}

        # --- SMART INTEGRATION CHECK ---
        connected_platforms = []
        try:
            metricool_ref = db.collection('users').document(uid).collection('user_integrations').document('metricool').get()
            if metricool_ref.exists and metricool_ref.to_dict().get('status') == 'active':
                blog_id = metricool_ref.to_dict().get('blog_id')
                client = MetricoolClient(blog_id=blog_id)
                # Fetch live providers to know exactly what is connected
                account_info = client.get_account_info()
                connected_platforms = account_info.get('connected', [])
                logger.info(f"💡 Smart Campaign: Detected platforms for {uid}: {connected_platforms}")
        except Exception as e:
            logger.warning(f"Failed to fetch integrations for campaign context: {e}")
        # -------------------------------

        agent = CampaignAgent()
        questions = await agent.generate_clarifying_questions(goal, brand_ref.to_dict(), connected_platforms=connected_platforms)
        return {"questions": questions}
    except ImportError as e:
        logger.error(f"Failed to import CampaignAgent: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error: Agent module missing")
    except Exception as e:
        logger.error(f"Campaign Initiation Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/finalize")
async def finalize_campaign(payload: dict, background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    try:
        from app.agents.orchestrator_agent import OrchestratorAgent
        from app.services.metricool_client import MetricoolClient

        goal = payload.get("goal")
        answers = payload.get("answers")
        uid = user['uid']
        campaign_id = f"camp_{int(time.time())}"
        
        # Guard
        if not db: raise HTTPException(status_code=503, detail="Database Unavailable")

        brand_dna = db.collection('users').document(uid).collection('brand_profile').document('current').get().to_dict()

        # --- SMART INTEGRATION CHECK (Re-verify for Execution) ---
        connected_platforms = []
        try:
            metricool_ref = db.collection('users').document(uid).collection('user_integrations').document('metricool').get()
            if metricool_ref.exists and metricool_ref.to_dict().get('status') == 'active':
                blog_id = metricool_ref.to_dict().get('blog_id')
                client = MetricoolClient(blog_id=blog_id)
                account_info = client.get_account_info()
                connected_platforms = account_info.get('connected', [])
        except Exception:
            pass # Fail silently on execution, default logic in Agent will handle checks
        # ---------------------------------------------------------

        orchestrator = OrchestratorAgent()
        background_tasks.add_task(
            orchestrator.run_full_campaign_flow, 
            uid, campaign_id, goal, brand_dna, answers, connected_platforms
        )
        return {"campaign_id": campaign_id}
    except Exception as e:
        logger.error(f"Campaign Finalization Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{campaign_id}")
async def get_results(campaign_id: str, user: dict = Depends(verify_token)):
    uid = user['uid']
    if not db: raise HTTPException(status_code=503, detail="Database Unavailable")
    
    doc = db.collection('users').document(uid).collection('campaigns').document(campaign_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return doc.to_dict()

@router.post("/recycle")
async def recycle_asset(payload: dict, background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    try:
        from app.agents.recycler_agent import RecyclerAgent
        uid = user['uid']
        
        if not db: raise HTTPException(status_code=503, detail="Database Unavailable")
        
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
    except Exception as e:
        logger.error(f"Recycle Asset Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

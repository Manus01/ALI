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
        selected_channels = payload.get("selected_channels", []) # V3.0 Fix: Extract channels
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
        questions = await agent.generate_clarifying_questions(
            goal, 
            brand_ref.to_dict(), 
            connected_platforms=connected_platforms,
            selected_channels=selected_channels # V3.0 Fix: Respect user selection
        )
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
        selected_channels = payload.get("selected_channels", [])  # New v3.0: User-selected channels
        uid = user['uid']
        campaign_id = f"camp_{int(time.time())}"
        
        # Guard
        if not db: raise HTTPException(status_code=503, detail="Database Unavailable")

        brand_dna = db.collection('users').document(uid).collection('brand_profile').document('current').get().to_dict()

        # --- SMART FALLBACK: If no channels selected, detect from integrations ---
        if not selected_channels:
            try:
                metricool_ref = db.collection('users').document(uid).collection('user_integrations').document('metricool').get()
                if metricool_ref.exists and metricool_ref.to_dict().get('status') == 'active':
                    blog_id = metricool_ref.to_dict().get('blog_id')
                    client = MetricoolClient(blog_id=blog_id)
                    account_info = client.get_account_info()
                    selected_channels = account_info.get('connected', ["instagram", "linkedin"])
            except Exception:
                selected_channels = ["instagram", "linkedin"]  # Default fallback
        # ---------------------------------------------------------

        logger.info(f"🚀 Campaign finalize for user {uid} with channels: {selected_channels}")

        orchestrator = OrchestratorAgent()
        background_tasks.add_task(
            orchestrator.run_full_campaign_flow, 
            uid, campaign_id, goal, brand_dna, answers, selected_channels
        )
        
        # ATOMIC INCREMENT: Track ads_generated for user leaderboard (Admin Hub)
        try:
            user_ref = db.collection('users').document(uid)
            user_ref.update({
                "stats.ads_generated": firestore.Increment(1)
            })
            logger.info(f"📊 Incremented ads_generated for user {uid}")
        except Exception as stats_err:
            # Non-fatal - don't block campaign if stats update fails
            logger.warning(f"⚠️ Failed to increment ads_generated for {uid}: {stats_err}")
        
        return {"campaign_id": campaign_id, "selected_channels": selected_channels}
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


@router.post("/regenerate")
async def regenerate_channel_asset(payload: dict, background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    """
    Regenerate a single channel's asset based on rejection feedback.
    Used by the Review Feed rejection flow.
    """
    try:
        from app.agents.orchestrator_agent import OrchestratorAgent, CHANNEL_SPECS
        from app.services.image_agent import ImageAgent
        
        uid = user['uid']
        campaign_id = payload.get("campaign_id")
        channel = payload.get("channel")  # e.g., "linkedin", "tiktok"
        feedback = payload.get("feedback", "")  # User's rejection feedback
        
        if not campaign_id or not channel:
            raise HTTPException(status_code=400, detail="campaign_id and channel are required")
        
        if not db:
            raise HTTPException(status_code=503, detail="Database Unavailable")
        
        # Get existing campaign data
        campaign_doc = db.collection('users').document(uid).collection('campaigns').document(campaign_id).get()
        if not campaign_doc.exists:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        campaign_data = campaign_doc.to_dict()
        brand_dna = db.collection('users').document(uid).collection('brand_profile').document('current').get().to_dict()
        
        # Get channel specs
        spec = CHANNEL_SPECS.get(channel)
        if not spec:
            raise HTTPException(status_code=400, detail=f"Unknown channel: {channel}")
        
        primary_format = spec["formats"][0]
        width, height = primary_format["size"]
        
        # Build regeneration prompt incorporating feedback
        original_blueprint = campaign_data.get("blueprint", {}).get(channel, {})
        visual_prompt = original_blueprint.get("visual_prompt", "Professional brand promotional image")
        
        enhanced_prompt = f"""
        {visual_prompt}
        
        USER FEEDBACK FOR REVISION: {feedback}
        
        DIMENSIONS: {width}x{height}px
        TONE: {spec.get('tone', 'professional')}
        """
        
        logger.info(f"🔄 Regenerating {channel} asset for campaign {campaign_id} with feedback: {feedback[:50]}...")
        
        # Generate new asset
        image_agent = ImageAgent()
        dna_str = f"Style {brand_dna.get('visual_styles', [])}. Colors {brand_dna.get('color_palette', {})}"
        
        result = image_agent.generate_image(enhanced_prompt, brand_dna=dna_str, folder=f"campaigns/{channel}")
        
        new_url = result.get('url') if isinstance(result, dict) else result
        
        if not new_url:
            raise HTTPException(status_code=500, detail="Asset regeneration failed")
        
        # Update campaign assets
        db.collection('users').document(uid).collection('campaigns').document(campaign_id).update({
            f"assets.{channel}": new_url
        })
        
        # Update draft
        draft_id = f"draft_{campaign_id}_{channel}"
        db.collection('creative_drafts').document(draft_id).update({
            "thumbnailUrl": new_url,
            "status": "DRAFT",
            "approvalStatus": "pending",
            "regeneratedAt": firestore.SERVER_TIMESTAMP,
            "regenerationFeedback": feedback
        })
        
        logger.info(f"✅ Regenerated {channel} asset for campaign {campaign_id}")
        
        return {
            "status": "regenerated",
            "channel": channel,
            "new_url": new_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Channel Regeneration Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

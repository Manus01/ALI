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
                blog_id = metricool_ref.to_dict().get('metricool_blog_id') or metricool_ref.to_dict().get('blog_id')
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
                    blog_id = metricool_ref.to_dict().get('metricool_blog_id') or metricool_ref.to_dict().get('blog_id')
                    client = MetricoolClient(blog_id=blog_id)
                    account_info = client.get_account_info()
                    selected_channels = account_info.get('connected', ["instagram", "linkedin"])
            except Exception as e:
                logger.warning(f"Smart fallback failed, using default: {e}")
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


@router.post("/resume/{campaign_id}")
async def resume_campaign(campaign_id: str, background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    """
    V6.1: Resume an interrupted campaign generation.
    Checks for checkpoint and continues from where it left off.
    """
    try:
        from app.agents.orchestrator_agent import OrchestratorAgent
        
        uid = user['uid']
        
        if not db:
            raise HTTPException(status_code=503, detail="Database Unavailable")
        
        # Check for existing checkpoint
        checkpoint_doc = db.collection('generation_checkpoints').document(campaign_id).get()
        if not checkpoint_doc.exists:
            raise HTTPException(status_code=404, detail="No checkpoint found for this campaign")
        
        checkpoint = checkpoint_doc.to_dict()
        
        # Verify ownership
        if checkpoint.get("userId") != uid:
            raise HTTPException(status_code=403, detail="Not authorized to resume this campaign")
        
        # Get original campaign data
        campaign_doc = db.collection('users').document(uid).collection('campaigns').document(campaign_id).get()
        if not campaign_doc.exists:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        campaign_data = campaign_doc.to_dict()
        brand_dna = db.collection('users').document(uid).collection('brand_profile').document('current').get().to_dict()
        
        completed_channels = checkpoint.get("completedChannels", [])
        all_channels = campaign_data.get("selected_channels", [])
        
        # Calculate pending channels (channels that haven't been completed)
        pending_channels = []
        for ch in all_channels:
            # Check if this channel (with any format label) is completed
            if not any(comp.startswith(ch) for comp in completed_channels):
                pending_channels.append(ch)
        
        if not pending_channels:
            # All channels are already completed
            return {
                "status": "already_complete",
                "campaign_id": campaign_id,
                "completed_count": len(completed_channels)
            }
        
        logger.info(f"🔄 Resuming campaign {campaign_id} - {len(pending_channels)} channels remaining: {pending_channels}")
        
        # Resume generation for pending channels only
        orchestrator = OrchestratorAgent()
        background_tasks.add_task(
            orchestrator.run_full_campaign_flow,
            uid, campaign_id, 
            campaign_data.get("goal", ""),
            brand_dna,
            {},  # answers not needed for resume
            pending_channels  # Only generate for pending channels
        )
        
        return {
            "status": "resuming",
            "campaign_id": campaign_id,
            "completed_channels": completed_channels,
            "pending_channels": pending_channels
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume Campaign Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/checkpoint/{campaign_id}")
async def get_checkpoint(campaign_id: str, user: dict = Depends(verify_token)):
    """
    Check if a campaign has an interrupted checkpoint.
    Frontend can use this to show a "Resume" button.
    """
    uid = user['uid']
    
    if not db:
        raise HTTPException(status_code=503, detail="Database Unavailable")
    
    checkpoint_doc = db.collection('generation_checkpoints').document(campaign_id).get()
    
    if not checkpoint_doc.exists:
        return {"has_checkpoint": False, "campaign_id": campaign_id}
    
    checkpoint = checkpoint_doc.to_dict()
    
    # Verify ownership
    if checkpoint.get("userId") != uid:
        return {"has_checkpoint": False, "campaign_id": campaign_id}
    
    return {
        "has_checkpoint": True,
        "campaign_id": campaign_id,
        "completed_channels": checkpoint.get("completedChannels", []),
        "updated_at": checkpoint.get("updatedAt")
    }


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
        from app.agents.orchestrator_agent import CHANNEL_SPECS
        from app.services.image_agent import ImageAgent
        
        uid = user['uid']
        campaign_id = payload.get("campaign_id")
        channel = payload.get("channel")  # e.g., "linkedin", "tiktok"
        feedback = payload.get("feedback", "")  # User's rejection feedback
        format_label = (payload.get("format_label") or "primary").lower()
        
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
        
        def resolve_format():
            if format_label == "story":
                return next((fmt for fmt in spec["formats"] if fmt.get("ratio") == "9:16"), None)
            if format_label == "feed":
                return next((fmt for fmt in spec["formats"] if fmt.get("ratio") in ["1:1", "4:5"]), None)
            return next((fmt for fmt in spec["formats"] if fmt.get("type") == format_label), None)

        primary_format = resolve_format() or spec["formats"][0]
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
        
        logger.info(f"🔄 Regenerating {channel} ({format_label}) asset for campaign {campaign_id} with feedback: {feedback[:50]}...")
        
        # Generate new asset
        image_agent = ImageAgent()
        dna_str = f"Style {brand_dna.get('visual_styles', [])}. Colors {brand_dna.get('color_palette', {})}"
        
        result = image_agent.generate_image(enhanced_prompt, brand_dna=dna_str, folder=f"campaigns/{channel}")
        
        new_url = result.get('url') if isinstance(result, dict) else result
        
        if not new_url:
            raise HTTPException(status_code=500, detail="Asset regeneration failed")
        
        asset_key = f"{channel}_{format_label}" if format_label != "primary" else channel
        db.collection('users').document(uid).collection('campaigns').document(campaign_id).update({
            f"assets.{asset_key}": new_url
        })
        
        # Update draft
        clean_channel = channel.lower().replace(" ", "_").replace("-", "_")
        draft_id = (
            f"draft_{campaign_id}_{clean_channel}_{format_label}"
            if format_label not in ["primary", "feed"]
            else f"draft_{campaign_id}_{clean_channel}"
        )
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


@router.post("/competitors/analyse")
async def analyse_competitors(payload: dict, user: dict = Depends(verify_token)):
    """
    Store competitor analysis snapshot metadata for auditability.
    This endpoint expects a list of competitor URLs or names and records the snapshot.
    """
    uid = user['uid']
    competitors = payload.get("competitors", [])
    themes = payload.get("themes", [])
    angles = payload.get("creative_angles", [])

    if not db:
        raise HTTPException(status_code=503, detail="Database Unavailable")

    snapshot_id = f"comp_{int(time.time())}"
    snapshot_data = {
        "competitorList": competitors,
        "themes": themes,
        "creativeAngles": angles,
        "createdAt": firestore.SERVER_TIMESTAMP
    }

    db.collection('competitiveInsights').document(uid).collection('snapshots').document(snapshot_id).set(snapshot_data)

    return {
        "status": "stored",
        "snapshot_id": snapshot_id,
        "competitor_count": len(competitors)
    }


# --- WIZARD DRAFT PERSISTENCE (v4.0) ---

@router.post("/save-draft")
async def save_campaign_draft(payload: dict, user: dict = Depends(verify_token)):
    """
    Save campaign wizard state as a draft.
    Allows users to resume incomplete campaigns if they leave mid-wizard.
    
    Also handles saving generating campaigns so users can track progress.
    """
    try:
        uid = user['uid']
        draft_id = payload.get("draft_id") or f"wizard_draft_{int(time.time())}"
        
        if not db:
            raise HTTPException(status_code=503, detail="Database Unavailable")
        
        draft_data = {
            "userId": uid,
            "draftId": draft_id,
            "goal": payload.get("goal", ""),
            "selected_channels": payload.get("selected_channels", []),
            "questions": payload.get("questions", []),
            "answers": payload.get("answers", {}),
            "wizard_stage": payload.get("stage", "input"),
            "status": "WIZARD_DRAFT",
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        
        # Preserve createdAt if updating existing draft
        existing = db.collection('users').document(uid).collection('campaign_drafts').document(draft_id).get()
        if existing.exists:
            existing_data = existing.to_dict()
            draft_data["createdAt"] = existing_data.get("createdAt")
        
        db.collection('users').document(uid).collection('campaign_drafts').document(draft_id).set(draft_data, merge=True)
        logger.info(f"💾 Saved wizard draft {draft_id} for user {uid} (stage: {payload.get('stage')})")
        
        return {"draft_id": draft_id, "status": "saved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save Draft Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-wizard-drafts")
async def get_wizard_drafts(user: dict = Depends(verify_token)):
    """
    Fetch incomplete wizard drafts for the current user.
    Returns drafts sorted by most recently updated.
    """
    try:
        uid = user['uid']
        
        if not db:
            raise HTTPException(status_code=503, detail="Database Unavailable")
        
        docs = db.collection('users').document(uid).collection('campaign_drafts').stream()
        drafts = [doc.to_dict() for doc in docs]
        
        # Filter to WIZARD_DRAFT status only
        drafts = [d for d in drafts if d.get("status") == "WIZARD_DRAFT"]
        
        # Sort by updatedAt descending (handle missing values)
        drafts.sort(key=lambda x: x.get("updatedAt") or 0, reverse=True)
        
        logger.info(f"📋 Retrieved {len(drafts)} wizard drafts for user {uid}")
        return {"drafts": drafts[:10]}
    except Exception as e:
        logger.error(f"Get Wizard Drafts Failed: {e}")
        return {"drafts": []}


@router.delete("/wizard-draft/{draft_id}")
async def delete_wizard_draft(draft_id: str, user: dict = Depends(verify_token)):
    """
    Delete a wizard draft after completion or manual discard.
    Called automatically when campaign is finalized.
    """
    try:
        uid = user['uid']
        
        if not db:
            raise HTTPException(status_code=503, detail="Database Unavailable")
        
        db.collection('users').document(uid).collection('campaign_drafts').document(draft_id).delete()
        logger.info(f"🗑️ Deleted wizard draft {draft_id} for user {uid}")
        
        return {"status": "deleted", "draft_id": draft_id}
    except Exception as e:
        logger.error(f"Delete Wizard Draft Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

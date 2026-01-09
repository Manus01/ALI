"""
User-facing Creative Endpoints for Self-Approval Workflow.

This router allows users to:
- View their own draft creatives
- Publish their own drafts (without admin intervention)
- View their published creatives

Spec: User Self-Approval Model (replacing Admin-Approval for creatives)
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_token, db
from google.cloud import firestore
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/my-drafts")
def get_my_drafts(user: dict = Depends(verify_token)):
    """
    Fetch current user's draft creatives (status IN [DRAFT, PENDING]).
    Returns only creatives owned by the authenticated user.
    """
    try:
        uid = user['uid']
        
        # Query creativeDrafts collection for user's own drafts
        query = db.collection("creativeDrafts")\
            .where("userId", "==", uid)\
            .where("status", "in", ["DRAFT", "PENDING"])\
            .order_by("createdAt", direction=firestore.Query.DESCENDING)\
            .limit(50)
        
        drafts = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            drafts.append(data)
        
        return {"drafts": drafts}
    except Exception as e:
        logger.error(f"❌ Fetch My Drafts Error: {e}")
        return {"drafts": [], "error": str(e)}


@router.post("/{draft_id}/publish")
def publish_my_draft(draft_id: str, user: dict = Depends(verify_token)):
    """
    Allow OWNER to publish their own draft.
    
    Permission Logic:
    - Verify draft.userId == current_user.uid
    - If not owner → 403 Forbidden
    - If owner → update status to PUBLISHED
    """
    try:
        uid = user['uid']
        
        doc_ref = db.collection("creativeDrafts").document(draft_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        data = doc.to_dict()
        
        # OWNERSHIP CHECK - Core of Self-Approval Model
        if data.get("userId") != uid:
            logger.warning(f"⚠️ Unauthorized publish attempt: User {uid} tried to publish draft {draft_id} owned by {data.get('userId')}")
            raise HTTPException(status_code=403, detail="You can only publish your own creatives")
        
        # Check if already published
        if data.get("status") == "PUBLISHED":
            return {"status": "PUBLISHED", "message": "Draft is already published."}
        
        # Update to PUBLISHED
        doc_ref.update({
            "status": "PUBLISHED",
            "publishedAt": firestore.SERVER_TIMESTAMP,
            "publishedBy": user.get("email", uid)
        })
        
        # ATOMIC INCREMENT: Track ads_generated for user leaderboard (Admin Hub)
        try:
            user_ref = db.collection("users").document(uid)
            user_ref.update({
                "stats.ads_generated": firestore.Increment(1)
            })
            logger.info(f"📊 Incremented ads_generated for user {uid}")
        except Exception as stats_err:
            # Non-fatal - don't block publish if stats update fails
            logger.warning(f"⚠️ Failed to increment ads_generated for {uid}: {stats_err}")
        
        logger.info(f"✅ Creative {draft_id} self-published by owner {uid}")
        
        return {"status": "PUBLISHED", "message": "Creative published successfully."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Publish My Draft Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-published")
def get_my_published(user: dict = Depends(verify_token)):
    """
    Fetch current user's published creatives (status = PUBLISHED).
    Returns only creatives owned by the authenticated user.
    """
    try:
        uid = user['uid']
        
        # Query creativeDrafts collection for user's published creatives
        query = db.collection("creativeDrafts")\
            .where("userId", "==", uid)\
            .where("status", "==", "PUBLISHED")\
            .order_by("publishedAt", direction=firestore.Query.DESCENDING)\
            .limit(50)
        
        published = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            published.append(data)
        
        return {"published": published}
    except Exception as e:
        logger.error(f"❌ Fetch My Published Error: {e}")
        return {"published": [], "error": str(e)}


@router.post("/{campaign_id}/export-zip")
async def export_campaign_zip(campaign_id: str, user: dict = Depends(verify_token)):
    """
    Export all APPROVED assets for a campaign as a ZIP file.
    
    File naming convention:
    - {channel}-{format}-image.jpg (e.g., linkedin-feed-image.jpg)
    - {channel}-text.txt (e.g., linkedin-post-text.txt)
    
    Returns: StreamingResponse with ZIP file
    """
    import io
    import zipfile
    import httpx
    from fastapi.responses import StreamingResponse
    
    try:
        uid = user['uid']
        
        # Fetch campaign data
        campaign_doc = db.collection('users').document(uid).collection('campaigns').document(campaign_id).get()
        if not campaign_doc.exists:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        campaign_data = campaign_doc.to_dict()
        assets = campaign_data.get("assets", {})
        blueprint = campaign_data.get("blueprint", {})
        selected_channels = campaign_data.get("selected_channels", [])
        
        if not assets:
            raise HTTPException(status_code=400, detail="No assets to export")
        
        # Fetch approved drafts only
        approved_channels = []
        for channel in selected_channels:
            draft_id = f"draft_{campaign_id}_{channel}"
            draft_doc = db.collection('creative_drafts').document(draft_id).get()
            if draft_doc.exists:
                draft_data = draft_doc.to_dict()
                if draft_data.get("approvalStatus") == "approved" or draft_data.get("status") == "PUBLISHED":
                    approved_channels.append(channel)
        
        # If no approvals found, export all (for backwards compatibility)
        if not approved_channels:
            approved_channels = list(assets.keys())
            logger.warning(f"No approved assets found for {campaign_id}, exporting all available")
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        async with httpx.AsyncClient() as client:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for channel in approved_channels:
                    asset_payload = assets.get(channel)
                    channel_blueprint = blueprint.get(channel, {})
                    
                    # Helper to process single file
                    async def add_file_to_zip(payload, base_filename):
                        if not payload:
                            return
                            
                        # Case A: Data URI (HTML Motion)
                        if isinstance(payload, str) and payload.startswith("data:"):
                            try:
                                header, encoded = payload.split(",", 1)
                                import base64
                                decoded = base64.b64decode(encoded)
                                # Determine ext
                                ext = "html" if "text/html" in header else "bin"
                                filename = f"{base_filename}.{ext}"
                                zip_file.writestr(filename, decoded)
                                logger.info(f"📦 Added {filename} (DataURI) to ZIP")
                            except Exception as e:
                                logger.warning(f"Failed to process DataURI for {base_filename}: {e}")
                                
                        # Case B: Standard URL
                        elif isinstance(payload, str) and payload.startswith("http"):
                            try:
                                response = await client.get(payload)
                                if response.status_code == 200:
                                    content_type = response.headers.get("content-type", "image/png")
                                    ext = "jpg" if "jpeg" in content_type else "png"
                                    # If HTML content type
                                    if "text/html" in content_type:
                                        ext = "html"
                                    
                                    filename = f"{base_filename}.{ext}"
                                    zip_file.writestr(filename, response.content)
                                    logger.info(f"📦 Added {filename} to ZIP")
                            except Exception as e:
                                logger.warning(f"Failed to download {base_filename}: {e}")

                    # Handle Payload Type
                    if isinstance(asset_payload, list):
                        # Carousel (List of URLs)
                        for idx, slide_url in enumerate(asset_payload):
                            await add_file_to_zip(slide_url, f"{channel}-slide-{idx+1}")
                    else:
                        # Single Asset (Motion or Image)
                        await add_file_to_zip(asset_payload, f"{channel}-asset")
                    
                    # Add text copy
                    text_content = ""
                    if channel_blueprint.get("caption"):
                        text_content = channel_blueprint["caption"]
                    elif channel_blueprint.get("body"):
                        text_content = f"Subject: {channel_blueprint.get('subject', 'Campaign')}\n\n{channel_blueprint['body']}"
                    elif channel_blueprint.get("headlines"):
                        text_content = "HEADLINES:\n" + "\n".join(channel_blueprint["headlines"])
                        if channel_blueprint.get("descriptions"):
                            text_content += "\n\nDESCRIPTIONS:\n" + "\n".join(channel_blueprint["descriptions"])
                    elif channel_blueprint.get("video_script"):
                        text_content = f"VIDEO SCRIPT:\n{channel_blueprint['video_script']}"
                    
                    if text_content:
                        text_filename = f"{channel}-copy.txt"
                        zip_file.writestr(text_filename, text_content)
                        logger.info(f"📝 Added {text_filename} to ZIP")
        
        # Prepare response
        zip_buffer.seek(0)
        
        logger.info(f"✅ Exported {len(approved_channels)} channel assets for campaign {campaign_id}")
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=campaign_{campaign_id}_assets.zip"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:

@router.post("/{draft_id}/remix")
async def remix_draft(draft_id: str, background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    """
    Trigger a REMIX (Generation Variant) for a specific draft.
    
    Logic:
    1. Fetch draft to get original prompt & config
    2. Check ownership
    3. Trigger ImageAgent with same prompt but force new generation
    4. Save as NEW draft (status=DRAFT, origin=remix)
    5. Return new draft ID immediately
    """
    try:
        from app.services.image_agent import ImageAgent
        from app.agents.orchestrator_agent import CHANNEL_SPECS
        
        uid = user['uid']
        
        # 1. Fetch Original Draft
        doc_ref = db.collection("creativeDrafts").document(draft_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Original draft not found")
            
        data = doc.to_dict()
        
        # 2. Ownership Check
        if data.get("userId") != uid:
             raise HTTPException(status_code=403, detail="Unauthorized")
             
        # 3. Prepare Remix Data
        campaign_id = data.get("campaignId")
        channel = data.get("channel", "unknown")
        
        # Get specs for dimensions
        spec = CHANNEL_SPECS.get(channel, {})
        primary_format = spec.get("formats", [{}])[0]
        size = primary_format.get("size", (1024, 1024))
        
        # Create NEW Draft Entry immediately (placeholder)
        new_draft_ref = db.collection("creativeDrafts").document()
        new_draft_id = new_draft_ref.id
        
        new_draft_data = {
            "id": new_draft_id,
            "userId": uid,
            "campaignId": campaign_id,
            "channel": channel,
            "status": "DRAFT",  # Pending generation
            "approvalStatus": "pending",
            "type": "image",
            "format": data.get("format", "feed-image"),
            "size": f"{size[0]}x{size[1]}",
            "createdAt": firestore.SERVER_TIMESTAMP,
            "origin": "remix",
            "originalDraftId": draft_id,
            "thumbnailUrl": None, # Will be updated after generation
            "title": f"{data.get('title', 'Remix')} (Variant)",
            "campaignGoal": data.get("campaignGoal", "Remix")
        }
        
        new_draft_ref.set(new_draft_data)
        
        # 4. Background Generation Task
        async def generate_remix_task():
            try:
                # Re-instantiate agents
                image_agent = ImageAgent()
                brand_dna = db.collection('users').document(uid).collection('brand_profile').document('current').get().to_dict()
                
                # Construct Prompt
                # We use the original visual prompt if available, or fall back to a generic one
                visual_prompt = data.get("visualPrompt") or f"A creative asset for {channel} campaign: {data.get('campaignGoal')}"
                
                dna_str = f"Style {brand_dna.get('visual_styles', [])}. Colors {brand_dna.get('color_palette', {})}"
                
                logger.info(f"🎨 Remixing draft {draft_id} -> {new_draft_id} for channel {channel}")
                
                # Generate
                result = image_agent.generate_image(
                    prompt=visual_prompt,
                    brand_dna=dna_str,
                    folder=f"campaigns/{channel}/remix"
                )
                
                new_url = result.get('url') if isinstance(result, dict) else result
                
                # Update the new draft with the image
                if new_url:
                    new_draft_ref.update({
                        "thumbnailUrl": new_url,
                        "status": "DRAFT" # It remains DRAFT until published
                    })
                    logger.info(f"✅ Remix complete: {new_draft_id}")
                else:
                    new_draft_ref.update({"status": "ERROR", "error": "Generation failed"})
                    
            except Exception as e:
                logger.error(f"❌ Remix Generation Failed: {e}")
                new_draft_ref.update({"status": "ERROR", "error": str(e)})

        background_tasks.add_task(generate_remix_task)
        
        return {"new_draft_id": new_draft_id, "status": "remix_started"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Remix Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

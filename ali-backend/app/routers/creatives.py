"""
Creative drafts endpoints for authenticated users.
"""
import base64
import io
import zipfile
import logging
from typing import List, Optional, Tuple
from urllib.parse import unquote, urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import requests
from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.security import db, get_current_user_id
from app.services.gcs_service import GCSService

router = APIRouter()
logger = logging.getLogger(__name__)
KNOWN_CHANNELS = [
    "linkedin",
    "instagram",
    "facebook",
    "tiktok",
    "google_display",
    "pinterest",
    "threads",
    "email",
    "blog"
]


def _extract_gcs_blob(asset_url: str) -> Optional[Tuple[str, str]]:
    parsed = urlparse(asset_url)
    if parsed.scheme == "gs":
        bucket, _, blob_path = parsed.path.lstrip("/").partition("/")
        blob_path = unquote(blob_path)
        if bucket and blob_path:
            return bucket, blob_path
        return None

    if "storage.googleapis.com" not in parsed.netloc:
        return None

    if parsed.netloc == "storage.googleapis.com":
        bucket, _, blob_path = parsed.path.lstrip("/").partition("/")
    elif parsed.netloc.endswith(".storage.googleapis.com"):
        bucket = parsed.netloc.split(".storage.googleapis.com")[0]
        blob_path = parsed.path.lstrip("/")
    else:
        return None

    blob_path = unquote(blob_path)
    if bucket and blob_path:
        return bucket, blob_path
    return None


def _parse_draft_id(draft_id: str) -> Optional[Tuple[str, str, str]]:
    if not draft_id.startswith("draft_"):
        return None
    remainder = draft_id[len("draft_"):]
    for channel in KNOWN_CHANNELS:
        channel_token = f"_{channel}_"
        if channel_token in remainder:
            campaign_id, format_label = remainder.split(channel_token, 1)
            return campaign_id, channel, format_label or "primary"
        if remainder.endswith(f"_{channel}"):
            campaign_id = remainder[:-(len(channel) + 1)]
            return campaign_id, channel, "primary"
    return None


def _cleanup_campaign_asset(user_id: str, campaign_id: str, channel: str, format_label: str) -> None:
    asset_key = channel if format_label in ["primary", "feed"] else f"{channel}_{format_label}"
    campaign_ref = db.collection("users").document(user_id).collection("campaigns").document(campaign_id)
    campaign_doc = campaign_ref.get()
    if not campaign_doc.exists:
        return
    campaign_data = campaign_doc.to_dict()
    assets = dict(campaign_data.get("assets", {}))
    assets_metadata = dict(campaign_data.get("assets_metadata", {}))
    blueprint = dict(campaign_data.get("blueprint", {}))

    asset_removed = False
    if asset_key in assets:
        assets.pop(asset_key, None)
        asset_removed = True

    remaining_channel_assets = [
        key for key in assets.keys()
        if key == channel or key.startswith(f"{channel}_")
    ]

    update_data = {}
    if asset_removed:
        update_data["assets"] = assets
    if not remaining_channel_assets:
        if channel in blueprint:
            blueprint.pop(channel, None)
            update_data["blueprint"] = blueprint
        if channel in assets_metadata:
            assets_metadata.pop(channel, None)
            update_data["assets_metadata"] = assets_metadata
    if update_data:
        campaign_ref.set(update_data, merge=True)


@router.get("/my-drafts")
def get_my_drafts(user_id: str = Depends(get_current_user_id)) -> List[dict]:
    """
    Fetch current user's draft creatives (status IN [DRAFT, PENDING] or missing).
    Returns only creatives owned by the authenticated user.
    
    Note: Filtering and sorting done in Python to avoid Firestore compound index requirements.
    V4.0: Auto-flags stale PENDING drafts as TIMED_OUT after 30 minutes.
    """
    from datetime import datetime, timedelta, timezone
    
    try:
        # Query only by user_id to avoid compound index requirement
        docs = list(db.collection("creative_drafts").where(filter=FieldFilter("userId", "==", user_id)).stream())
        
        # Convert to list of dicts - V4.0 FIX: Include document ID!
        all_docs = [{**doc.to_dict(), "id": doc.id, "_doc_ref": doc.reference} for doc in docs]
        
        # V4.0: Auto-flag stale PENDING drafts as TIMED_OUT (30 min timeout)
        now = datetime.now(timezone.utc)
        timeout_threshold = timedelta(minutes=30)
        
        for draft in all_docs:
            if draft.get("status") == "PENDING":
                created_at = draft.get("createdAt")
                # Firestore timestamps need conversion
                if created_at and hasattr(created_at, 'timestamp'):
                    created_time = datetime.fromtimestamp(created_at.timestamp(), tz=timezone.utc)
                    if now - created_time > timeout_threshold:
                        # Auto-flag as TIMED_OUT
                        draft["status"] = "TIMED_OUT"
                        draft["_original_status"] = "PENDING"
                        draft["_timeout_reason"] = "Generation exceeded 30 minute timeout"
                        
                        # Update Firestore so this persists
                        try:
                            draft["_doc_ref"].update({
                                "status": "TIMED_OUT",
                                "timeoutAt": now
                            })
                            logger.info(f"⏰ Auto-flagged stale PENDING draft as TIMED_OUT: {draft['id']}")
                        except Exception as update_err:
                            logger.warning(f"Could not update stale draft status: {update_err}")
        
        # Remove internal reference from response
        drafts = [{k: v for k, v in d.items() if not k.startswith('_')} for d in all_docs]
        
        # Sort in Python by createdAt descending (use 0 for missing values for proper sorting)
        drafts.sort(key=lambda x: x.get("createdAt") or 0, reverse=True)
        
        # Return limited results
        return drafts[:50]
    except Exception as e:
        logger.error(f"Error fetching drafts: {e}")
        return []


@router.get("/my-published")
def get_my_published(user_id: str = Depends(get_current_user_id)) -> List[dict]:
    """
    Fetch current user's published creatives (status = PUBLISHED).
    Returns only creatives owned by the authenticated user.
    
    Note: Filtering and sorting done in Python to avoid Firestore compound index requirements.
    """
    try:
        # Query only by user_id to avoid compound index requirement
        docs = db.collection("creative_drafts").where(filter=FieldFilter("userId", "==", user_id)).stream()
        
        # Convert to list of dicts - V4.0 FIX: Include document ID!
        all_docs = [{**doc.to_dict(), "id": doc.id} for doc in docs]
        
        # Filter in Python: keep only PUBLISHED items
        published = [d for d in all_docs if d.get("status") == "PUBLISHED"]
        
        # Sort in Python by publishedAt descending (handle missing values safely)
        published.sort(key=lambda x: x.get("publishedAt", ""), reverse=True)
        
        # Return limited results
        return published[:50]
    except Exception as e:
        logger.error(f"Error fetching published: {e}")
        return []


# --- PUBLISH & EXPORT ENDPOINTS (v4.0) ---

@router.post("/{draft_id}/publish")
def publish_creative(draft_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Approve and publish a draft creative.
    Updates status from DRAFT to PUBLISHED.
    """
    try:
        from firebase_admin import firestore as fs
        
        doc_ref = db.collection("creative_drafts").document(draft_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            parsed = _parse_draft_id(draft_id)
            if parsed:
                campaign_id, channel, format_label = parsed
                _cleanup_campaign_asset(user_id, campaign_id, channel, format_label)
                logger.info(f"🧹 Cleaned campaign asset for missing draft {draft_id}")
                return {"status": "deleted", "draft_id": draft_id, "campaign_cleanup": True}
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
        
        data = doc.to_dict()
        
        # Verify ownership
        if data.get("userId") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to publish this creative")
        
        # Update status to PUBLISHED
        doc_ref.update({
            "status": "PUBLISHED",
            "publishedAt": fs.SERVER_TIMESTAMP
        })
        
        logger.info(f"✅ Published creative {draft_id} for user {user_id}")
        return {"status": "published", "draft_id": draft_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Publish failed for {draft_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{draft_id}/download")
def download_asset(draft_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Download an individual creative asset.
    Returns the asset as a file download.
    """
    try:
        doc = db.collection("creative_drafts").document(draft_id).get()
        
        if not doc.exists:
            parsed = _parse_draft_id(draft_id)
            if parsed:
                campaign_id, channel, format_label = parsed
                _cleanup_campaign_asset(user_id, campaign_id, channel, format_label)
                logger.info(f"🧹 Cleaned campaign asset for missing draft {draft_id}")
                return {"status": "deleted", "draft_id": draft_id, "campaign_cleanup": True}
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
        
        data = doc.to_dict()
        
        # Verify ownership
        if data.get("userId") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to download this creative")
        
        asset_url = data.get("asset_url") or data.get("url")
        if not asset_url:
            raise HTTPException(status_code=404, detail="No asset URL found")

        gcs_blob = _extract_gcs_blob(asset_url)
        if gcs_blob:
            bucket_name, blob_path = gcs_blob
            gcs_service = GCSService()
            refreshed_url = gcs_service.generate_signed_url(bucket_name, blob_path)
            if refreshed_url:
                asset_url = refreshed_url
        
        if asset_url.startswith("data:"):
            header, data_payload = asset_url.split(",", 1)
            header_meta = header[5:]
            parts = header_meta.split(";")
            content_type = parts[0] if parts[0] else "text/plain"
            if "base64" in parts:
                raw_bytes = base64.b64decode(data_payload)
            else:
                raw_bytes = unquote(data_payload).encode("utf-8")
            ext = "html" if "html" in content_type else "png"
            channel = data.get("channel", "asset")
            filename = f"{channel}_{draft_id}.{ext}"
            return StreamingResponse(
                io.BytesIO(raw_bytes),
                media_type=content_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

        # Fetch the asset
        response = requests.get(asset_url, timeout=30)
        response.raise_for_status()
        
        # Determine file extension
        content_type = response.headers.get("Content-Type", "image/png")
        ext = "png" if "png" in content_type else "jpg" if "jpeg" in content_type or "jpg" in content_type else "html"
        
        channel = data.get("channel", "asset")
        filename = f"{channel}_{draft_id}.{ext}"
        
        return StreamingResponse(
            io.BytesIO(response.content),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed for {draft_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{campaign_id}/export-zip")
def export_campaign_zip(
    campaign_id: str,
    user_id: str = Depends(get_current_user_id),
    channel: Optional[str] = Query(None)
):
    """
    Export all PUBLISHED assets from a campaign as a ZIP file.
    Only includes approved (published) assets.
    """
    try:
        # Fetch all creative drafts for this campaign
        docs = db.collection("creative_drafts").where(filter=FieldFilter("userId", "==", user_id)).stream()
        all_docs = [doc.to_dict() for doc in docs]
        
        # Filter to this campaign and PUBLISHED status
        campaign_assets = [
            d for d in all_docs 
            if d.get("campaignId") == campaign_id and d.get("status") == "PUBLISHED"
        ]

        if channel:
            campaign_assets = [
                d for d in campaign_assets if d.get("channel") == channel
            ]
        
        if not campaign_assets:
            detail = "No approved assets found for this campaign"
            if channel:
                detail = f"No approved assets found for channel {channel}"
            raise HTTPException(status_code=404, detail=detail)
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for asset in campaign_assets:
                asset_url = asset.get("asset_url") or asset.get("url")
                if not asset_url:
                    continue
                
                try:
                    # Fetch asset
                    response = requests.get(asset_url, timeout=30)
                    response.raise_for_status()
                    
                    # Determine filename
                    channel = asset.get("channel", "asset")
                    content_type = response.headers.get("Content-Type", "image/png")
                    
                    if "html" in content_type or asset_url.endswith(".html"):
                        ext = "html"
                    elif "png" in content_type:
                        ext = "png"
                    else:
                        ext = "jpg"
                    
                    filename = f"{channel}.{ext}"
                    
                    # Handle duplicates
                    base_name = filename
                    counter = 1
                    while filename in [a.filename for a in zip_file.infolist()]:
                        name, extension = base_name.rsplit('.', 1)
                        filename = f"{name}_{counter}.{extension}"
                        counter += 1
                    
                    zip_file.writestr(filename, response.content)
                    logger.info(f"📦 Added {filename} to ZIP")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Could not fetch asset {asset_url}: {e}")
                    continue
        
        zip_buffer.seek(0)
        
        logger.info(f"✅ Created ZIP with {len(campaign_assets)} assets for campaign {campaign_id}")

        filename = f"campaign_{campaign_id}_assets.zip"
        if channel:
            filename = f"campaign_{campaign_id}_{channel}_assets.zip"
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ZIP export failed for {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{draft_id}")
def delete_creative(draft_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Delete a creative draft permanently.
    """
    try:
        doc_ref = db.collection("creative_drafts").document(draft_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            parsed = _parse_draft_id(draft_id)
            if parsed:
                campaign_id, channel, format_label = parsed
                _cleanup_campaign_asset(user_id, campaign_id, channel, format_label)
                logger.info(f"🧹 Cleaned campaign asset for missing draft {draft_id}")
                return {"status": "deleted", "draft_id": draft_id, "campaign_cleanup": True}
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
        
        data = doc.to_dict()
        
        # Verify ownership
        if data.get("userId") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this creative")

        campaign_id = data.get("campaignId")
        channel = data.get("channel")
        if campaign_id and channel:
            base_id = f"draft_{campaign_id}_{channel}"
            format_label = "primary"
            if draft_id.startswith(base_id):
                suffix = draft_id[len(base_id):]
                if suffix.startswith("_"):
                    format_label = suffix.lstrip("_") or "primary"
            _cleanup_campaign_asset(user_id, campaign_id, channel, format_label)
        
        doc_ref.delete()
        logger.info(f"🗑️ Deleted creative {draft_id} for user {user_id}")
        return {"status": "deleted", "draft_id": draft_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed for {draft_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{draft_id}/regenerate")
async def regenerate_failed_creative(draft_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Regenerate a failed creative asset.
    Only works for drafts with status='FAILED'.
    """
    from fastapi import BackgroundTasks
    
    try:
        doc_ref = db.collection("creative_drafts").document(draft_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
        
        data = doc.to_dict()
        
        # Verify ownership
        if data.get("userId") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to regenerate this creative")
        
        # V4.0: Allow regeneration for FAILED/TIMED_OUT OR DRAFT with missing asset URL
        status = data.get("status")
        asset_url = data.get("asset_url") or data.get("assetPayload")
        
        # Can regenerate if: FAILED/TIMED_OUT status, OR DRAFT/PENDING with no valid URL
        can_regenerate = (
            status in ["FAILED", "TIMED_OUT"] or 
            (status in ["DRAFT", "PENDING", None] and not asset_url)
        )
        
        if not can_regenerate:
            raise HTTPException(status_code=400, detail="Only failed or incomplete assets can be regenerated")
        
        # Update status to PENDING
        from firebase_admin import firestore as fs
        doc_ref.update({
            "status": "PENDING",
            "updatedAt": fs.SERVER_TIMESTAMP
        })
        
        # Trigger regeneration in background
        campaign_id = data.get("campaignId")
        channel = data.get("channel")
        goal = data.get("campaignGoal") or data.get("title", "Brand Campaign")
        
        # Import and run regeneration
        from app.agents.orchestrator_agent import OrchestratorAgent
        from app.services.image_agent import ImageAgent
        import asyncio
        
        async def regenerate_task():
            try:
                image_agent = ImageAgent()
                # Simple regeneration with the goal as prompt
                result = image_agent.generate_image(
                    f"{goal}. Professional brand visual for {channel}.",
                    brand_dna="",
                    folder=f"campaigns/{channel}"
                )
                
                if result and isinstance(result, dict) and result.get('url'):
                    doc_ref.update({
                        "status": "DRAFT",
                        "asset_url": result['url'],
                        "thumbnailUrl": result['url'],
                        "updatedAt": fs.SERVER_TIMESTAMP
                    })
                    logger.info(f"✅ Regenerated {draft_id} successfully")
                else:
                    doc_ref.update({
                        "status": "FAILED",
                        "updatedAt": fs.SERVER_TIMESTAMP
                    })
                    logger.warning(f"⚠️ Regeneration returned no URL for {draft_id}")
            except Exception as e:
                logger.error(f"❌ Regeneration failed for {draft_id}: {e}")
                doc_ref.update({
                    "status": "FAILED",
                    "updatedAt": fs.SERVER_TIMESTAMP
                })
        
        # Run in background
        asyncio.create_task(regenerate_task())
        
        logger.info(f"🔄 Started regeneration for {draft_id}")
        return {"status": "regenerating", "draft_id": draft_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Regeneration start failed for {draft_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
Creative drafts endpoints for authenticated users.
"""
import io
import zipfile
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import requests

from app.core.security import db, get_current_user_id

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/my-drafts")
def get_my_drafts(user_id: str = Depends(get_current_user_id)) -> List[dict]:
    """
    Fetch current user's draft creatives (status IN [DRAFT, PENDING] or missing).
    Returns only creatives owned by the authenticated user.
    
    Note: Filtering and sorting done in Python to avoid Firestore compound index requirements.
    """
    try:
        # Query only by user_id to avoid compound index requirement
        docs = db.collection("creative_drafts").where("userId", "==", user_id).stream()
        
        # Convert to list of dicts
        all_docs = [doc.to_dict() for doc in docs]
        
        # V3.1 FIX: Return ALL drafts (including FAILED) so users can see failed generations
        # No status filtering - users need to see what failed to debug issues
        drafts = all_docs
        
        # Sort in Python by createdAt descending (use 0 for missing values for proper sorting)
        drafts.sort(key=lambda x: x.get("createdAt") or 0, reverse=True)
        
        # Return limited results
        return drafts[:50]
    except Exception as e:
        print(f"Error fetching drafts: {e}")
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
        docs = db.collection("creative_drafts").where("userId", "==", user_id).stream()
        
        # Convert to list of dicts
        all_docs = [doc.to_dict() for doc in docs]
        
        # Filter in Python: keep only PUBLISHED items
        published = [d for d in all_docs if d.get("status") == "PUBLISHED"]
        
        # Sort in Python by publishedAt descending (handle missing values safely)
        published.sort(key=lambda x: x.get("publishedAt", ""), reverse=True)
        
        # Return limited results
        return published[:50]
    except Exception as e:
        print(f"Error fetching published: {e}")
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
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
        
        data = doc.to_dict()
        
        # Verify ownership
        if data.get("userId") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to download this creative")
        
        asset_url = data.get("asset_url") or data.get("url")
        if not asset_url:
            raise HTTPException(status_code=404, detail="No asset URL found")
        
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
def export_campaign_zip(campaign_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Export all PUBLISHED assets from a campaign as a ZIP file.
    Only includes approved (published) assets.
    """
    try:
        # Fetch all creative drafts for this campaign
        docs = db.collection("creative_drafts").where("userId", "==", user_id).stream()
        all_docs = [doc.to_dict() for doc in docs]
        
        # Filter to this campaign and PUBLISHED status
        campaign_assets = [
            d for d in all_docs 
            if d.get("campaignId") == campaign_id and d.get("status") == "PUBLISHED"
        ]
        
        if not campaign_assets:
            raise HTTPException(status_code=404, detail="No approved assets found for this campaign")
        
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
        logger.error(f"ZIP export failed for {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


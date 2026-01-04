from fastapi import APIRouter, Depends, HTTPException, Body
from app.core.security import verify_token, db
from app.services.metricool_client import MetricoolClient
from app.services.gcs_service import GCSService
import logging
from typing import Dict, Any
import base64

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/publish/content")
async def publish_video(payload: Dict[str, Any] = Body(...), user: dict = Depends(verify_token)):
    """
    Publishing Flow: VEO -> GCS -> Metricool
    Constraint: Requires 'metricool_blog_id' to be set by Admin.
    """
    user_id = user['uid']
    
    # 1. Check Integration Status
    doc = db.collection("user_integrations").document(f"{user_id}_metricool").get()
    
    if not doc.exists:
        raise HTTPException(status_code=400, detail="Social integration not requested.")
        
    data = doc.to_dict()
    blog_id = data.get("metricool_blog_id")
    
    # Critical Check: Is the ID populated?
    if not blog_id:
        raise HTTPException(status_code=403, detail="Social accounts are not linked yet. Please check your email for the Metricool invitation.")
    
    # 2. Upload to GCS (VEO Handoff)
    public_video_url = ""
    gcs_service = GCSService()
    try:
        video_bytes = base64.b64decode(payload['video_bytes'])
        filename = payload.get('filename', f"veo_gen_{user_id}.mp4")
        
        public_video_url = gcs_service.upload_video(
            file_obj=video_bytes, 
            filename=filename, 
            content_type="video/mp4"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GCS Upload Failed: {e}")

    # 3. Publish via Metricool
    try:
        client = MetricoolClient()
        res = client.publish_post(
            blog_id=str(blog_id),
            text=payload.get("post_text"),
            media_url=public_video_url, # From GCS
            platforms=payload.get("platforms")
        )
        
        return {
            "status": "success", 
            "message": "Scheduled via Metricool", 
            "metricool_id": result.get('postId')
        }

    except Exception as e:
        logger.error(f"❌ Metricool Publish Failed: {e}")
        raise HTTPException(status_code=500, detail=f"Publishing failed: {e}")
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import verify_token
from app.services.ai_studio import CreativeService

router = APIRouter()

class VideoRequest(BaseModel):
    prompt: str
    style: str = "cinematic"

@router.post("/generate/video")
def generate_video_endpoint(body: VideoRequest, user: dict = Depends(verify_token)):
    """
    Triggers the Creative Engine.
    """
    try:
        service = CreativeService()
        # This will block for 10-20 seconds while generating
        asset_url = service.generate_video(body.prompt, body.style)
        
        return {
            "status": "completed",
            "video_url": asset_url,
            "message": "Asset generated successfully."
        }

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Studio Error: {error_msg}")
        
        # Friendly error if quota is hit
        if "429" in error_msg:
            raise HTTPException(status_code=429, detail="Daily AI quota exceeded.")
        if "404" in error_msg:
            raise HTTPException(status_code=404, detail="AI Model not found (Check Vertex AI Model Garden).")
            
        raise HTTPException(status_code=500, detail=error_msg)
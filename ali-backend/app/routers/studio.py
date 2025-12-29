from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from app.core.security import verify_token
from app.services.ai_studio import CreativeService
import json
import os
import google.generativeai as genai

router = APIRouter()

class VideoRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=1000)
    style: str = Field("cinematic", min_length=2, max_length=100)

@router.post("/generate/video")
async def generate_video_endpoint(body: VideoRequest, user: dict = Depends(verify_token)):
    """
    Triggers the Creative Engine with a streaming response to keep Cloud Run connections alive.
    """
    # Validate GENAI_PROJECT_ID as integer for downstream clients
    project_raw = os.getenv("GENAI_PROJECT_ID") or os.getenv("PROJECT_ID")
    try:
        _ = int(project_raw) if project_raw is not None else None
    except (TypeError, ValueError):
        raise HTTPException(status_code=500, detail="GENAI_PROJECT_ID must be a valid integer")

    # Ensure module import is exercised (configuration handled in CreativeService)
    _ = genai  # touch to satisfy linter and surface ImportError early

    async def stream():
        # Initial tiny chunk keeps the connection warm during cold starts
        yield b" "
        try:
            service = CreativeService()
            asset_url = await run_in_threadpool(service.generate_video, body.prompt, body.style)
            payload = {
                "status": "completed",
                "video_url": asset_url,
                "message": "Asset generated successfully."
            }
            yield json.dumps(payload).encode()
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Studio Error: {error_msg}")
            if "429" in error_msg:
                yield json.dumps({"status": "error", "detail": "Daily AI quota exceeded."}).encode()
            elif "404" in error_msg:
                yield json.dumps({"status": "error", "detail": "AI Model not found (Check Vertex AI Model Garden)."}).encode()
            else:
                yield json.dumps({"status": "error", "detail": error_msg}).encode()

    return StreamingResponse(stream(), media_type="application/json")
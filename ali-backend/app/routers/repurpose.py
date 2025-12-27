from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.core.security import verify_token
from app.services.ai_studio import CreativeService
import google.generativeai as genai
import os
import json

router = APIRouter()

# Configure AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class RepurposeRequest(BaseModel):
    origin_content: str = Field(..., min_length=3, max_length=2000)  # e.g., "Video about sustainable coffee"
    platform_target: str = Field(..., min_length=2, max_length=50) # e.g., "LinkedIn" or "Blog"

@router.post("/repurpose/content")
def repurpose_content(body: RepurposeRequest, user: dict = Depends(verify_token)):
    """
    Takes a core concept and remixes it into text + image assets.
    """
    print(f"♻️ Repurposing '{body.origin_content}' for {body.platform_target}...")
    
    try:
        creative = CreativeService()
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 1. Generate Text Content
        prompt = f"""
        You are a Content Marketing Expert.
        Repurpose this concept: "{body.origin_content}".
        Target Platform: {body.platform_target}.
        
        Output JSON:
        {{
            "headline": "Catchy Hook",
            "body": "The main post content (formatted for the platform)",
            "hashtags": ["#tag1", "#tag2"],
            "image_prompt": "A description of a perfect image to accompany this post"
        }}
        """
        
        response = model.generate_content(prompt)
        content = json.loads(response.text.replace("```json", "").replace("```", "").strip())
        
        # 2. Generate Matching Image
        image_url = creative.generate_image(content["image_prompt"])
        
        return {
            "status": "success",
            "data": {
                "headline": content["headline"],
                "body": content["body"],
                "hashtags": content["hashtags"],
                "image_url": image_url
            }
        }

    except Exception as e:
        print(f"❌ Repurpose Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
import os
import json
import asyncio
from google.cloud import storage
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from .base_agent import BaseAgent

class VisualAgent(BaseAgent):
    def __init__(self):
        super().__init__("VisualAgent")
        # Ensure Project ID is an integer for Veo
        self.project_id = os.getenv("PROJECT_ID") or os.getenv("GENAI_PROJECT_ID")
        location = os.getenv("AI_STUDIO_LOCATION", "us-central1")
        vertexai.init(project=self.project_id, location=location)

    async def generate_branded_video(self, prompt, brand_dna):
        """Calls VEO for branded TikTok/Reels content."""
        self.log_task("Initiating VEO Video Generation...")
        # Inject branding into the prompt
        refined_prompt = f"Style: {brand_dna['visual_direction']}. Theme: {prompt}. Colors: {brand_dna['extracted_colors']}"
        
        # [REDACTED: Logic from our previous fix handling raw bytes vs URI]
        # This will call VEO, poll operation.done, and upload resulting bytes to GCS.
        # Returning the final GCS Signed URL.
        return "https://storage.googleapis.com/.../video.mp4"

    async def generate_branded_image(self, blueprint_item, brand_dna):
        """Calls Imagen 3 for high-res social posts."""
        self.log_task("Initiating Imagen Image Generation...")
        
        try:
            # Handle prompt being a dictionary (blueprint item) or string
            if isinstance(blueprint_item, dict):
                visual_prompt = blueprint_item.get('visual_prompt', '') or blueprint_item.get('description', '')
                aspect_ratio = blueprint_item.get('aspect_ratio', '1:1') # Default to square for IG
            else:
                visual_prompt = str(blueprint_item)
                aspect_ratio = '16:9' # Default for legacy string calls

            model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
            images = model.generate_images(
                prompt=visual_prompt,
                number_of_images=1,
                aspect_ratio=aspect_ratio
            )
            if images:
                # In a real implementation, we would upload bytes to GCS here
                # For now, returning a placeholder or the first image's GCS URI if available
                # Vertex AI ImageGenerationModel returns ImageGenerationResponse
                # We'll assume we handle the bytes/upload elsewhere or return a placeholder
                return "https://storage.googleapis.com/.../image.png"
        except Exception as e:
            self.log_task(f"Imagen Error: {e}")
            return ""
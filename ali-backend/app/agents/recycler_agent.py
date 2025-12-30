from app.services.llm_factory import get_gemini_model
import os
import json
from .base_agent import BaseAgent
from app.agents.visual_agent import VisualAgent

class RecyclerAgent(BaseAgent):
    def __init__(self):
        super().__init__("RecyclerAgent")
        self.model = get_gemini_model('gemini-1.5-flash')

    async def recycle_asset(self, uid: str, campaign_id: str, original_asset_url: str, user_instruction: str, brand_dna: dict):
        self.log_task(f"Recycling asset: {original_asset_url} with instruction: {user_instruction}")
        
        # 1. Classification Step: What does the user want?
        classification_prompt = f"""
        User wants to transform this existing asset: {original_asset_url}
        Instruction: "{user_instruction}"
        
        Categorize this transformation into one of these: 
        'resize_image', 'image_to_video', 'text_to_image', 'reformat_text'.
        Return ONLY the category name.
        """
        category = self.model.generate_content(classification_prompt).text.strip()

        # 2. Execution Step
        visualizer = VisualAgent()
        
        if category == 'resize_image':
            # Logic for Imagen 3 Inpainting/Outpainting to new dimensions
            return await visualizer.generate_branded_image(f"Resize and extend background: {user_instruction}", brand_dna)
        
        elif category == 'image_to_video':
            # Logic for VEO (Image-to-Video)
            return await visualizer.generate_branded_video(f"Animate this image: {user_instruction}", brand_dna)
            
        elif category == 'reformat_text':
            # Logic for Gemini to rewrite copy
            return await self.rewrite_copy(original_asset_url, user_instruction, brand_dna)

        return None
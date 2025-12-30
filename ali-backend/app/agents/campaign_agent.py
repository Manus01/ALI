import os
import json
import logging
from .base_agent import BaseAgent
from app.services.llm_factory import get_model

class CampaignAgent(BaseAgent):
    def __init__(self):
        super().__init__("CampaignAgent")
        # Using Pro for complex strategic reasoning
        self.model = get_model(intent='complex')

    async def generate_clarifying_questions(self, goal: str, brand_dna: dict):
        """Analyze goal vs Brand DNA and ask 3-4 strategic questions."""
        self.log_task(f"Generating strategic questions for goal: {goal}")
        
        prompt = f"""
        You are a Senior Marketing Consultant. 
        BRAND DNA: {json.dumps(brand_dna)}
        USER GOAL: "{goal}"
        TARGET COUNTRIES: {brand_dna.get('target_countries', 'Global')}

        Your task:
        Before generating assets, you must ask 3-4 surgical questions to the user.
        These questions should help you decide:
        1. The specific aesthetic sub-style (within their brand guidelines).
        2. The cultural hook for their target market (e.g., if Germany, focus on data; if Cyprus, focus on community).
        3. The primary call to action.

        Return ONLY a JSON array of strings. Example: ["Question 1", "Question 2"]
        """
        
        try:
            response = self.model.generate_content(prompt)
            # Cleanup JSON formatting from AI response
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(raw_text)
        except Exception as e:
            self.handle_error(e)

    async def create_campaign_blueprint(self, goal: str, brand_dna: dict, answers: dict):
        """Create the full multi-channel plan once questions are answered."""
        self.log_task("Formulating final campaign blueprint...")
        
        prompt = f"""
        Based on:
        Brand DNA: {json.dumps(brand_dna)}
        Goal: {goal}
        User Clarifications: {json.dumps(answers)}

        Create a Campaign Blueprint. 
        Include:
        1. 'theme': A 1-sentence title for the campaign.
        2. 'instagram': A 'caption' and a 'visual_prompt'.
        3. 'tiktok': A 'video_script' and 'audio_style'.
        4. 'email': A 'subject' and 'body_copy'.

        Ensure the tone strictly follows the Brand DNA and respects the cultural target.
        Return ONLY a JSON object.
        """
        
        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(raw_text)
        except Exception as e:
            self.handle_error(e)
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

    async def generate_clarifying_questions(self, goal: str, brand_dna: dict, connected_platforms: list = None, selected_channels: list = None):
        """Analyze goal vs Brand DNA and ask 3-4 strategic questions."""
        self.log_task(f"Generating strategic questions for goal: {goal}")
        
        # Contextual Instructions based on integrations
        platform_instruction = ""
        if selected_channels and len(selected_channels) > 0:
             platform_instruction = f"""
            CONTEXT: The user has ALREADY selected these channels: {', '.join(selected_channels)}. 
            DO NOT ask questions about which channels to use. Focus only on content strategy.
            """
        elif connected_platforms and len(connected_platforms) > 0:
            platform_instruction = f"""
            DETECTED INTEGRATIONS: {', '.join(connected_platforms)}.
            CRITICAL: Do NOT ask which platforms to use. We MUST use the detected ones. 
            Instead, ask specific strategic questions about the content *for* these platforms (e.g. "For TikTok, do you want X or Y?").
            """
        else:
            platform_instruction = "3. The primary channels for this campaign (Ask if they want TikTok, Instagram, etc)."

        prompt = f"""
        You are a Senior Marketing Consultant. 
        BRAND DNA: {json.dumps(brand_dna)}
        USER GOAL: "{goal}"
        TARGET COUNTRIES: {brand_dna.get('target_countries', 'Global')}

        Your task:
        Before generating assets, you must ask 3-4 surgical questions to the user.
        {platform_instruction}
        
        These questions should help you decide:
        1. The specific aesthetic sub-style (within their brand guidelines).
        2. The cultural hook for their target market (e.g., if Germany, focus on data; if Cyprus, focus on community).
        3. The primary call to action.

        Return ONLY a JSON array of strings. Example: ["Question 1", "Question 2"]
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            # Cleanup JSON formatting from AI response
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(raw_text)
        except Exception as e:
            self.handle_error(e)

    async def create_campaign_blueprint(self, goal: str, brand_dna: dict, answers: dict, selected_channels: list = None):
        """Create the full multi-channel plan once questions are answered."""
        self.log_task("Formulating final campaign blueprint...")
        
        # Build channel-specific instructions
        channels = selected_channels if selected_channels else ["instagram", "linkedin"]
        channel_instructions = self._build_channel_instructions(channels)
        
        prompt = f"""
        Based on:
        Brand DNA: {json.dumps(brand_dna)}
        Goal: {goal}
        User Clarifications: {json.dumps(answers)}
        Target Channels: {', '.join(channels)}

        Create a Campaign Blueprint. 
        
        CRITICAL: You MUST create content for EACH of these channels: {', '.join(channels)}
        
        {channel_instructions}
        
        For EVERY channel, include at minimum:
        - 'visual_prompt': A detailed image generation prompt
        - 'format_type': REQUIRED. Choose "video" or "image" based on these rules:
            * TikTok: MUST ALWAYS be "video" (no exceptions)
            * Instagram/Facebook: Choose "video" if content implies motion, storytelling, demos, or reveals. Choose "image" if it's a static announcement, quote, or infographic.
            * LinkedIn/Others: Default to "image" unless content specifically benefits from motion
        - 'caption' or 'body' or 'headlines': Platform-appropriate text copy
        
        Also include a general 'theme': A 1-sentence title for the campaign.
        
        Ensure the tone strictly follows the Brand DNA and respects the cultural target.
        Return ONLY a JSON object with keys for 'theme' and each channel.
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(raw_text)
        except Exception as e:
            self.handle_error(e)
    
    def _build_channel_instructions(self, channels: list) -> str:
        """Build channel-specific prompting instructions based on platform tones."""
        instructions = []
        
        channel_tones = {
            "linkedin": "Professional, thought-leadership tone. Target 150-300 characters. Include industry insights.",
            "instagram": "Visual-heavy with strategic hashtags. Engaging, lifestyle-focused caption.",
            "facebook": "Conversational and community-focused. Encourage engagement and sharing.",
            "tiktok": "Trendy, short, punchy. Script format with hook in first 3 seconds.",
            "google_display": "Direct response focused. Headlines max 30 chars, descriptions max 90 chars. Include keywords.",
            "pinterest": "Aspirational, visual. Focus on inspiration and lifestyle outcomes.",
            "threads": "Minimal, conversational. Think Twitter-style brevity with personality.",
            "email": "Persuasive with clear CTA. Subject line + body format.",
            "blog": "Informative, SEO-friendly. Include meta description and key points."
        }
        
        for channel in channels:
            tone_guide = channel_tones.get(channel, "Professional and on-brand.")
            instructions.append(f"'{channel}': {tone_guide}")
        
        return "TONE GUIDELINES PER CHANNEL:\n" + "\n".join(instructions)
import json
import logging
from typing import Optional
from .base_agent import BaseAgent
from app.services.llm_factory import get_model
from app.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

class CampaignAgent(BaseAgent):
    def __init__(self):
        super().__init__("CampaignAgent")
        # Using Pro for complex strategic reasoning
        self.model = get_model(intent='complex')
        self.knowledge_service = KnowledgeService()

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

    async def create_campaign_blueprint(
        self,
        goal: str,
        brand_dna: dict,
        answers: dict,
        selected_channels: list = None,
        memory_hooks: list = None,
        competitor_insights: dict = None
    ):
        """Create the full multi-channel plan once questions are answered."""
        self.log_task("Formulating final campaign blueprint...")

        user_id = (
            brand_dna.get("user_id")
            or brand_dna.get("userId")
            or brand_dna.get("uid")
            or brand_dna.get("brand_id")
            or brand_dna.get("brandId")
            or brand_dna.get("id")
        )
        try:
            rag_facts = self.knowledge_service.query_knowledge_base(user_id, query=goal)
            if not rag_facts:
                logger.warning("⚠️ No brand knowledge found for user %s", user_id)
                rag_facts = []
        except Exception as exc:
            logger.warning("⚠️ Knowledge query failed for user %s: %s", user_id, exc)
            rag_facts = []

        knowledge_lines = ["[REAL-TIME BRAND KNOWLEDGE]"]
        if rag_facts:
            for fact in rag_facts:
                if isinstance(fact, dict):
                    alert = fact.get("alert") or fact.get("monitoring_alert")
                    fact_text = (
                        fact.get("text")
                        or fact.get("fact")
                        or fact.get("summary")
                        or fact.get("title")
                    )
                    citation = fact.get("citation")
                    if alert:
                        knowledge_lines.append(f"- Alert: {alert}")
                        continue
                    if fact_text:
                        citation_text = ""
                        if citation:
                            if isinstance(citation, dict):
                                citation_value = (
                                    citation.get("url")
                                    or citation.get("source")
                                    or citation.get("title")
                                    or citation.get("text")
                                )
                            else:
                                citation_value = str(citation)
                            if citation_value:
                                citation_text = f" (Source: {citation_value})"
                        knowledge_lines.append(f"- Fact: {fact_text}{citation_text}")
                        continue
                if isinstance(fact, str):
                    knowledge_lines.append(f"- Fact: {fact}")
        else:
            knowledge_lines.append("- Fact: No relevant brand knowledge available.")

        knowledge_block = "\n".join(knowledge_lines)

        # Build channel-specific instructions
        channels = selected_channels if selected_channels else ["instagram", "linkedin"]
        channel_instructions = self._build_channel_instructions(channels)
        
        # Phase 1: Extract voice and constraints for enforcement
        brand_voice = brand_dna.get('voice', {})
        voice_personality = brand_voice.get('personality', 'Professional and approachable')
        voice_dos = brand_voice.get('do', [])
        voice_donts = brand_voice.get('dont', [])
        constraints = brand_dna.get('constraints', {})
        banned_phrases = constraints.get('banned_phrases', [])
        
        prompt = f"""
        Based on:
        Brand DNA: {json.dumps(brand_dna)}
        Goal: {goal}
        User Clarifications: {json.dumps(answers)}
        {knowledge_block}
        Target Channels: {', '.join(channels)}
        Reusable Hooks (same brand only): {json.dumps(memory_hooks or [])}
        Competitor Insights (themes only, do not copy): {json.dumps(competitor_insights or {})}

        Create a Campaign Blueprint. 

        Use the provided [REAL-TIME BRAND KNOWLEDGE] to ensure the campaign copy and visual direction align with the latest brand facts and monitoring alerts.
        
        CRITICAL: You MUST create content for EACH of these channels: {', '.join(channels)}
        
        {channel_instructions}
        
        ================================================================================
        PHASE 1: FORMAT DECISION MATRIX (The Strategist)
        ================================================================================
        For EVERY channel, you MUST determine the recommended_format by analyzing the goal:
        
        DECISION RULES:
        - If the message is emotional, complex, story-driven, demonstrates a process, or reveals something → "video"
        - If the message is urgent, promotional, simple announcement, quote-based, or infographic → "image"
        - If the message benefits from multiple frames (tutorials, step-by-step, comparisons) → "carousel"
        
        HARD OVERRIDES:
        - TikTok: MUST ALWAYS be "video" (no exceptions)
        - YouTube Shorts: MUST ALWAYS be "video"
        - Google Display: MUST ALWAYS be "image" (static ads)
        - Email/Blog: MUST ALWAYS be "image"
        
        ================================================================================
        PHASE 1: VOICE ENFORCEMENT (The Editor Pre-Check)
        ================================================================================
        BRAND VOICE PERSONALITY: {voice_personality}
        
        VOICE DO's (MUST FOLLOW):
        {chr(10).join(['- ' + item for item in voice_dos]) if voice_dos else '- Be professional and approachable'}
        
        VOICE DON'Ts (STRICTLY AVOID):
        {chr(10).join(['- ' + item for item in voice_donts]) if voice_donts else '- Avoid jargon without explanation'}
        
        BANNED PHRASES (NEVER USE):
        {chr(10).join(['- "' + phrase + '"' for phrase in banned_phrases]) if banned_phrases else '- None specified'}
        
        All generated copy MUST:
        1. Match the brand voice personality exactly
        2. Apply all items from the DO's list
        3. STRICTLY AVOID all items from the DON'Ts list
        4. NEVER use any banned phrases
        ================================================================================
        
        For EVERY channel, include at minimum:
        - 'visual_prompt': A detailed image generation prompt
        - 'recommended_format': REQUIRED. One of "video", "image", or "carousel" based on the rules above
        - 'headline': Primary attention-grabbing text
        - 'caption' or 'body': Platform-appropriate text copy (following voice enforcement rules)
        
        Also include a general 'theme': A 1-sentence title for the campaign.
        
        Return ONLY a JSON object with keys for 'theme' and each channel.
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(raw_text)
        except Exception as e:
            self.handle_error(e)

    async def generate_creative_intent(
        self,
        goal: str,
        brand_dna: dict,
        answers: dict,
        selected_channels: list = None,
        memory_hooks: list = None,
        competitor_insights: dict = None
    ):
        """Generate a structured Creative Intent Object for governance and auditability."""
        self.log_task("Generating creative intent object...")

        channels = selected_channels if selected_channels else ["instagram", "linkedin"]
        prompt = f"""
        You are a senior creative strategist.
        Brand DNA: {json.dumps(brand_dna)}
        Goal: {goal}
        User Clarifications: {json.dumps(answers)}
        Target Channels: {', '.join(channels)}
        Reusable Hooks (same brand only): {json.dumps(memory_hooks or [])}
        Competitor Insights (themes only, do not copy): {json.dumps(competitor_insights or {})}

        Return a JSON object with:
        - objective: short user-facing objective statement
        - angle: the primary positioning angle
        - hook_type: e.g., "social proof", "curiosity", "authority", "benefit-led"
        - hypothesis: a measurable hypothesis for testing

        Return ONLY JSON.
        """

        try:
            response = await self.model.generate_content_async(prompt)
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(raw_text)
        except Exception as e:
            self.handle_error(e)
            return {
                "objective": goal,
                "angle": "brand-led",
                "hook_type": "benefit-led",
                "hypothesis": "On-brand creative will improve engagement."
            }
    
    async def _analyze_goal_for_format(self, goal: str, channel: str) -> str:
        """
        Phase 1: Format Decision Matrix
        
        Analyze campaign goal complexity and sentiment to determine format.
        
        Rules:
        - Emotional/complex/story-driven → "video"
        - Urgent/promotional/simple → "image" or "carousel"
        - TikTok → Always "video" (hard override)
        
        Returns: "video", "image", or "carousel"
        """
        # Hard override for TikTok
        if channel.lower() in ['tiktok', 'youtube_shorts']:
            logger.info(f"📹 Format Matrix: {channel} hardcoded to 'video'")
            return "video"
        
        prompt = f"""
        Analyze this marketing campaign goal and determine the best visual format.
        
        Goal: "{goal}"
        Target Channel: {channel}
        
        DECISION RULES:
        1. If the message is emotional, complex, story-driven, or involves demonstrations → "video"
        2. If the message is urgent, promotional, simple announcements, or quote-based → "image"
        3. If the message benefits from multiple frames (tutorials, step-by-step, comparisons) → "carousel"
        
        CHANNEL CONSIDERATIONS:
        - Instagram/Facebook Stories → prefer "video" for engagement
        - LinkedIn → prefer "image" unless content is educational or story-based
        - Google Display → always "image" (static ads)
        - Email/Blog → always "image" (static content)
        
        Return ONLY one word: "video", "image", or "carousel"
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            format_result = response.text.strip().lower().replace('"', '').replace("'", "")
            
            # Validate response
            if format_result not in ["video", "image", "carousel"]:
                logger.warning(f"⚠️ Invalid format response '{format_result}', defaulting to 'image'")
                format_result = "image"
            
            logger.info(f"📊 Format Matrix for {channel}: '{format_result}' (goal: {goal[:50]}...)")
            return format_result
        except Exception as e:
            logger.error(f"❌ Format analysis failed: {e}, defaulting to 'image'")
            return "image"
    
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

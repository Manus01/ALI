"""
PR Opportunity Agent
AI-powered detection of PR opportunities and content generation.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent
from app.services.llm_factory import get_model

logger = logging.getLogger(__name__)


class PRAgent(BaseAgent):
    """
    Agent responsible for:
    1. Detecting PR opportunities from mentions
    2. Categorizing opportunities by type and urgency
    3. Generating press releases and social media content
    """
    
    # Supported output channels
    SUPPORTED_CHANNELS = [
        "press_release",
        "linkedin",
        "instagram",
        "facebook",
        "tiktok",
        "twitter",  # X
        "threads",
        "email",
        "blog"
    ]
    
    def __init__(self):
        super().__init__("PRAgent")
        self.model = get_model(intent='fast')
        self.creative_model = get_model(intent='creative')  # For content generation
    
    async def detect_opportunities(
        self,
        mentions: List[Dict[str, Any]],
        competitor_insights: List[Dict[str, Any]] = [],
        brand_profile: Dict[str, Any] = {}
    ) -> List[Dict[str, Any]]:
        """
        Analyze mentions and competitor insights to detect PR opportunities.
        
        Args:
            mentions: List of brand mentions with sentiment data
            competitor_insights: Analyzed competitor mentions
            brand_profile: Our brand DNA
            
        Returns:
            List of PR opportunities with:
            - type: "amplify" | "engage" | "respond" | "capitalize" | "trend"
            - source_mention: The originating mention
            - urgency: "critical" | "high" | "medium" | "low"
            - suggested_channels: Recommended output channels
            - action_summary: What to do
        """
        self.log_task(f"Detecting PR opportunities from {len(mentions)} mentions")
        
        brand_name = brand_profile.get('brand_name', 'Our Brand')
        
        # Prepare mentions summary for analysis
        mentions_summary = []
        for m in mentions[:20]:  # Limit for context window
            mentions_summary.append({
                "id": m.get('id', m.get('url', '')),
                "title": m.get('title', ''),
                "sentiment": m.get('sentiment', 'neutral'),
                "severity": m.get('severity'),
                "source": m.get('source_name', m.get('source', '')),
                "summary": m.get('ai_summary', m.get('description', ''))[:200]
            })
        
        # Include competitor opportunities
        competitor_opps = [
            {
                "competitor": c.get('competitor_name'),
                "type": c.get('opportunity_type'),
                "angle": c.get('our_angle')
            }
            for c in competitor_insights
            if c.get('opportunity_type') in ['capitalize', 'defend']
        ]
        
        prompt = f"""You are a PR strategist for {brand_name}. Analyze these mentions and identify PR opportunities.

BRAND MENTIONS:
{json.dumps(mentions_summary, indent=2)}

COMPETITOR INSIGHTS:
{json.dumps(competitor_opps, indent=2)}

Identify up to 10 PR opportunities. Categorize each as:
- AMPLIFY: Positive mention worth sharing/celebrating
- ENGAGE: Neutral mention to convert into advocacy
- RESPOND: Negative mention requiring response
- CAPITALIZE: Competitor weakness we can exploit
- TREND: Industry trend we can ride

Return ONLY valid JSON array:
[
    {{
        "type": "amplify|engage|respond|capitalize|trend",
        "source_mention_id": "ID of the originating mention or null",
        "title": "Short title for this opportunity",
        "description": "What the opportunity is about",
        "urgency": "critical|high|medium|low",
        "suggested_channels": ["linkedin", "press_release"],
        "action_summary": "Specific action to take",
        "key_message": "Core message to communicate",
        "hashtags": ["#relevant", "#hashtags"]
    }}
]
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            opportunities = json.loads(clean_json)
            
            # Attach source mention data
            mentions_by_id = {m.get('id', m.get('url', '')): m for m in mentions}
            for opp in opportunities:
                source_id = opp.get('source_mention_id')
                if source_id and source_id in mentions_by_id:
                    opp['source_mention'] = mentions_by_id[source_id]
            
            self.log_task(f"Detected {len(opportunities)} PR opportunities")
            return opportunities
            
        except Exception as e:
            logger.error(f"❌ Opportunity detection failed: {e}")
            return []
    
    async def generate_content(
        self,
        opportunity: Dict[str, Any],
        channels: List[str],
        brand_profile: Dict[str, Any],
        strategic_agenda: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate content for specified channels based on a PR opportunity.
        
        Args:
            opportunity: The PR opportunity to address
            channels: List of channels to generate for
            brand_profile: Brand DNA for tone/style alignment
            strategic_agenda: User's strategic goal (attract_clients, competitive_advantage, sustainability, etc.)
            
        Returns:
            Dictionary with channel-specific content:
            {
                "linkedin": {"content": "...", "hashtags": [...], "media_suggestion": "..."},
                "press_release": {"headline": "...", "body": "...", "boilerplate": "..."},
                ...
            }
        """
        self.log_task(f"Generating content for {len(channels)} channels with agenda: {strategic_agenda}")
        
        # Validate channels
        valid_channels = [c for c in channels if c in self.SUPPORTED_CHANNELS]
        if not valid_channels:
            return {"error": "No valid channels specified"}
        
        brand_name = brand_profile.get('brand_name', 'Our Brand')
        brand_tone = brand_profile.get('tone', 'Professional')
        brand_values = brand_profile.get('values', [])
        brand_description = brand_profile.get('description', '')
        
        opp_type = opportunity.get('type', 'engage')
        opp_title = opportunity.get('title', '')
        opp_description = opportunity.get('description', '')
        key_message = opportunity.get('key_message', '')
        hashtags = opportunity.get('hashtags', [])
        
        # Build strategic agenda context
        agenda_context = ""
        if strategic_agenda:
            agenda_guidance = {
                "attract_clients": """
STRATEGIC FOCUS: ATTRACT NEW CLIENTS
- Emphasize success stories, testimonials, and proven results
- Include calls-to-action that drive leads (contact us, learn more, book a demo)
- Highlight unique value propositions and competitive advantages
- Use social proof and credibility markers""",
                "competitive_advantage": """
STRATEGIC FOCUS: COMPETITIVE ADVANTAGE
- Subtly position against competitors without naming them directly
- Emphasize "unlike others" or "better alternative" messaging
- Highlight unique differentiators and innovations
- Address common pain points competitors fail to solve""",
                "sustainability": """
STRATEGIC FOCUS: ENVIRONMENTAL & SUSTAINABILITY
- Lead with green/eco-friendly messaging
- Include sustainability metrics, certifications, or commitments
- Use nature-inspired language and imagery suggestions
- Connect to ESG initiatives and climate consciousness""",
                "thought_leadership": """
STRATEGIC FOCUS: THOUGHT LEADERSHIP
- Position the brand/person as an industry authority
- Include insights, predictions, and forward-thinking perspectives
- Reference research, data, or expertise
- Use language that establishes credibility and innovation""",
                "crisis_recovery": """
STRATEGIC FOCUS: CRISIS RECOVERY
- Acknowledge past challenges transparently (without dwelling)
- Focus on concrete improvements and changes made
- Rebuild trust through actions and commitments
- Express genuine accountability and forward momentum""",
                "market_expansion": """
STRATEGIC FOCUS: MARKET EXPANSION
- Announce or signal entry into new markets/segments
- Highlight partnerships, launches, or growth milestones
- Use inclusive language welcoming new audiences
- Emphasize scalability and broad applicability"""
            }
            agenda_context = agenda_guidance.get(strategic_agenda, "")
        
        prompt = f"""You are a PR and content specialist for {brand_name}. Generate content for multiple channels based on this PR opportunity.

BRAND PROFILE:
- Name: {brand_name}
- Tone: {brand_tone}
- Values: {brand_values}
- Description: {brand_description}
{agenda_context}

PR OPPORTUNITY:
- Type: {opp_type.upper()}
- Title: {opp_title}
- Description: {opp_description}
- Key Message: {key_message}
- Suggested Hashtags: {hashtags}

Generate content for these channels: {valid_channels}

CHANNEL REQUIREMENTS:
- linkedin: Professional tone, 1300 char max, include relevant hashtags
- instagram: Visual-first, 2200 char max, emoji-friendly, hashtag block at end
- facebook: Conversational, 500 char ideal, question to drive engagement
- twitter: 280 char max, punchy, hashtags inline
- tiktok: Script format, casual/trendy, hook in first 3 seconds
- threads: Conversational thread format, 500 char per post
- email: Subject line + body, professional, clear CTA
- blog: Full article 500-800 words, SEO-friendly headline
- press_release: Formal structure with headline, dateline, body, quotes, boilerplate

Return ONLY valid JSON:
{{
    "linkedin": {{
        "content": "Full post text",
        "hashtags": ["#tag1", "#tag2"],
        "media_suggestion": "Suggested image/video type",
        "best_time": "Suggested posting time"
    }},
    "press_release": {{
        "headline": "Press release headline",
        "subheadline": "Optional subheadline",
        "dateline": "CITY, DATE —",
        "body": "Full press release body",
        "quote": "Executive quote",
        "quote_attribution": "Name, Title",
        "boilerplate": "About the company paragraph",
        "contact": "Media contact info placeholder"
    }},
    // ... other requested channels
}}
"""
        
        try:
            # Use creative model for better content
            response = await self.creative_model.generate_content_async(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            content = json.loads(clean_json)
            
            # Only return requested channels
            result = {ch: content.get(ch, {"error": "Generation failed"}) for ch in valid_channels}
            
            self.log_task(f"Generated content for {len(result)} channels")
            return result
            
        except Exception as e:
            logger.error(f"❌ Content generation failed: {e}")
            return {ch: {"error": str(e)} for ch in valid_channels}
    
    async def generate_crisis_content(
        self,
        crisis_mention: Dict[str, Any],
        crisis_response: Dict[str, Any],
        channels: List[str],
        brand_profile: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate crisis response content based on BrandMonitoringAgent's crisis analysis.
        
        This bridges the existing crisis response system with content generation.
        """
        self.log_task("Generating crisis response content")
        
        brand_name = brand_profile.get('brand_name', 'Our Brand')
        brand_tone = brand_profile.get('tone', 'Professional')
        
        executive_summary = crisis_response.get('executive_summary', '')
        key_messages = crisis_response.get('key_messages', [])
        do_not_say = crisis_response.get('do_not_say', [])
        escalation = crisis_response.get('escalation_level', 'medium')
        
        valid_channels = [c for c in channels if c in self.SUPPORTED_CHANNELS]
        
        prompt = f"""You are a crisis communications specialist for {brand_name}. Generate response content for multiple channels.

BRAND: {brand_name} (Tone: {brand_tone})

CRISIS SITUATION:
{executive_summary}

KEY MESSAGES TO CONVEY:
{json.dumps(key_messages, indent=2)}

DO NOT SAY:
{json.dumps(do_not_say, indent=2)}

ESCALATION LEVEL: {escalation.upper()}

Generate crisis response content for: {valid_channels}

CRITICAL RULES:
1. Acknowledge the situation appropriately
2. Express empathy where relevant
3. Focus on actions being taken
4. Avoid defensive or dismissive language
5. Never include phrases from the "DO NOT SAY" list
6. Match urgency to escalation level

Return ONLY valid JSON with content for each channel (same format as regular content generation).
"""
        
        try:
            response = await self.creative_model.generate_content_async(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            content = json.loads(clean_json)
            
            result = {ch: content.get(ch, {"error": "Generation failed"}) for ch in valid_channels}
            
            self.log_task(f"Generated crisis content for {len(result)} channels")
            return result
            
        except Exception as e:
            logger.error(f"❌ Crisis content generation failed: {e}")
            return {ch: {"error": str(e)} for ch in valid_channels}
    
    async def suggest_response_angle(
        self,
        mention: Dict[str, Any],
        brand_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Quick analysis to suggest the best response angle for a mention.
        Useful for UI to show recommended action before full content generation.
        """
        sentiment = mention.get('sentiment', 'neutral')
        severity = mention.get('severity', 0)
        
        # Quick heuristics first
        if sentiment == 'positive':
            return {
                "recommendation": "amplify",
                "reason": "Positive mention worth sharing",
                "suggested_channels": ["linkedin", "instagram"],
                "urgency": "medium"
            }
        elif sentiment == 'negative' and severity and severity >= 7:
            return {
                "recommendation": "respond_urgently",
                "reason": "High-severity negative mention requires immediate response",
                "suggested_channels": ["press_release", "linkedin", "twitter"],
                "urgency": "critical"
            }
        elif sentiment == 'negative':
            return {
                "recommendation": "respond",
                "reason": "Negative mention should be addressed",
                "suggested_channels": ["linkedin", "twitter"],
                "urgency": "high"
            }
        else:
            return {
                "recommendation": "engage",
                "reason": "Neutral mention is an opportunity for engagement",
                "suggested_channels": ["twitter", "linkedin"],
                "urgency": "low"
            }

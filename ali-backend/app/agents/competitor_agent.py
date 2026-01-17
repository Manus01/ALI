"""
Competitor Intelligence Agent
AI-powered competitor discovery, analysis, and insight generation.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent
from app.services.llm_factory import get_model

logger = logging.getLogger(__name__)


class CompetitorAgent(BaseAgent):
    """
    Agent responsible for:
    1. Suggesting relevant competitors based on brand profile
    2. Analyzing competitor mentions for opportunities/threats
    3. Identifying market gaps and positioning opportunities
    """
    
    def __init__(self):
        super().__init__("CompetitorAgent")
        self.model = get_model(intent='fast')  # Gemini 1.5 Flash for speed
    
    async def suggest_competitors(
        self,
        brand_profile: Dict[str, Any],
        entity_type: str,  # "company" or "person"
        existing_competitors: List[str] = [],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate AI-powered competitor suggestions based on brand profile.
        
        Args:
            brand_profile: The user's brand DNA / profile data
            entity_type: "company" or "person"
            existing_competitors: Already tracked competitors to exclude
            limit: Number of suggestions to return
            
        Returns:
            List of competitor suggestions with:
            - name: Competitor name
            - type: "direct" | "aspirational" | "emerging"
            - reason: Why this competitor is relevant
            - industry: Their primary industry
            - region: Geographic focus
        """
        self.log_task(f"Generating {limit} competitor suggestions for {entity_type}")
        
        brand_name = brand_profile.get('brand_name', 'Unknown')
        industry = brand_profile.get('industry', brand_profile.get('offerings', []))
        description = brand_profile.get('description', '')
        countries = brand_profile.get('countries', [])
        
        exclude_list = ", ".join(existing_competitors) if existing_competitors else "None"
        
        prompt = f"""You are a competitive intelligence analyst. Analyze this brand profile and suggest competitors to monitor.

BRAND PROFILE:
- Name: {brand_name}
- Type: {entity_type.upper()}
- Industry/Offerings: {industry}
- Description: {description}
- Target Countries: {countries}

ALREADY TRACKING (exclude these): {exclude_list}

Generate {limit} competitor suggestions. Include a MIX of:
1. DIRECT competitors (same industry, same region, similar size)
2. ASPIRATIONAL examples (global leaders to learn from, even if different region)
3. EMERGING threats (new entrants, disruptors, or adjacent players)

For PERSON type: Focus on individuals in similar roles, thought leaders, and public figures in the same space.

Return ONLY valid JSON array:
[
    {{
        "name": "Competitor Name",
        "type": "direct",
        "reason": "Why monitor this competitor (1 sentence)",
        "industry": "Their primary industry",
        "region": "Their geographic focus",
        "website": "https://example.com (if known, or null)"
    }}
]
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            suggestions = json.loads(clean_json)
            
            self.log_task(f"Generated {len(suggestions)} competitor suggestions")
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"❌ Competitor suggestion failed: {e}")
            # Return fallback suggestions
            return [
                {
                    "name": f"{brand_name} Competitor 1",
                    "type": "direct",
                    "reason": "AI suggestion unavailable - please add competitors manually",
                    "industry": str(industry)[:50] if industry else "Unknown",
                    "region": countries[0] if countries else "Global",
                    "website": None
                }
            ]
    
    async def analyze_competitor_mention(
        self,
        competitor_name: str,
        mention: Dict[str, Any],
        our_brand_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a competitor mention and extract actionable insights.
        
        Args:
            competitor_name: The competitor being mentioned
            mention: The article/post data
            our_brand_profile: Our brand DNA for comparison
            
        Returns:
            Dictionary containing:
            - opportunity_type: "capitalize" | "defend" | "learn" | "ignore"
            - summary: What the mention is about
            - our_angle: How we can use this information
            - urgency: "high" | "medium" | "low"
            - suggested_action: Recommended next step
        """
        self.log_task(f"Analyzing mention of competitor: {competitor_name}")
        
        our_brand = our_brand_profile.get('brand_name', 'Our Brand')
        our_offerings = our_brand_profile.get('offerings', [])
        
        mention_title = mention.get('title', '')
        mention_content = mention.get('content', mention.get('description', ''))[:1500]
        
        prompt = f"""You are a competitive intelligence analyst. Analyze this mention of a competitor and identify opportunities for our brand.

COMPETITOR: {competitor_name}
OUR BRAND: {our_brand}
OUR OFFERINGS: {our_offerings}

MENTION:
Title: {mention_title}
Content: {mention_content}

Analyze this mention and determine:
1. What is being said about the competitor?
2. Is this an opportunity or threat for us?
3. What action should we take?

Return ONLY valid JSON:
{{
    "opportunity_type": "capitalize|defend|learn|ignore",
    "summary": "1-2 sentence summary of what's being said",
    "sentiment_toward_competitor": "positive|neutral|negative",
    "our_angle": "How we can use this (or null if ignore)",
    "urgency": "high|medium|low",
    "suggested_action": "Specific recommended next step",
    "pr_opportunity": true/false,
    "key_quotes": ["Notable quotes from the mention if any"]
}}

OPPORTUNITY TYPES:
- capitalize: Competitor weakness we can exploit
- defend: Competitor strength threatening us
- learn: Best practice we should adopt
- ignore: Not relevant to our strategy
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            analysis = json.loads(clean_json)
            
            analysis['competitor_name'] = competitor_name
            analysis['mention_id'] = mention.get('id', mention.get('url', ''))
            
            self.log_task(f"Competitor analysis complete: {analysis.get('opportunity_type')}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Competitor mention analysis failed: {e}")
            return {
                "competitor_name": competitor_name,
                "opportunity_type": "ignore",
                "summary": "Analysis unavailable",
                "sentiment_toward_competitor": "neutral",
                "our_angle": None,
                "urgency": "low",
                "suggested_action": "Review manually",
                "pr_opportunity": False,
                "key_quotes": []
            }
    
    async def compare_with_competitor(
        self,
        our_brand_profile: Dict[str, Any],
        competitor_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a strategic comparison between our brand and a competitor.
        
        Returns:
            Dictionary with:
            - strengths: Where we outperform
            - weaknesses: Where they outperform us
            - opportunities: Market gaps we can fill
            - messaging_angles: How to position against them
        """
        self.log_task(f"Comparing with competitor: {competitor_profile.get('name', 'Unknown')}")
        
        prompt = f"""You are a brand strategist. Compare these two brands and identify strategic positioning opportunities.

OUR BRAND:
{json.dumps(our_brand_profile, indent=2)}

COMPETITOR:
{json.dumps(competitor_profile, indent=2)}

Provide a strategic comparison. Return ONLY valid JSON:
{{
    "strengths": ["Where we outperform them (3-5 points)"],
    "weaknesses": ["Where they outperform us (3-5 points)"],
    "opportunities": ["Market gaps or positioning opportunities (3-5 points)"],
    "messaging_angles": [
        {{
            "angle": "Positioning message",
            "context": "When to use this message"
        }}
    ],
    "differentiation_summary": "One paragraph summary of how we differ"
}}
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(clean_json)
            
        except Exception as e:
            logger.error(f"❌ Competitor comparison failed: {e}")
            return {
                "strengths": ["Analysis unavailable"],
                "weaknesses": ["Analysis unavailable"],
                "opportunities": ["Analysis unavailable"],
                "messaging_angles": [],
                "differentiation_summary": "Comparison could not be generated."
            }

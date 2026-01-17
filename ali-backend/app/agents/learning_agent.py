"""
Learning Agent
Uses historical data from BigQuery to power AI recommendations.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent
from app.services.llm_factory import get_model
from app.services.bigquery_service import get_bigquery_service

logger = logging.getLogger(__name__)


class LearningAgent(BaseAgent):
    """
    Agent that learns from historical data to improve recommendations.
    
    Key capabilities:
    1. Find similar past situations
    2. Recommend actions based on outcomes
    3. Summarize competitor playbooks
    4. Aggregate patterns for GDPR-safe retention
    """
    
    def __init__(self):
        super().__init__("LearningAgent")
        self.model = get_model(intent='fast')
        self.bq = get_bigquery_service()
    
    async def find_similar_situations(
        self,
        user_id: str,
        current_mention: Dict[str, Any],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find past mentions similar to the current one.
        Used to show: "Last time you faced something similar..."
        """
        self.log_task(f"Finding similar situations for {current_mention.get('sentiment')} mention")
        
        sentiment = current_mention.get('sentiment', 'neutral')
        
        # Query BigQuery for similar past mentions
        similar = self.bq.query_similar_mentions(
            user_id=user_id,
            sentiment=sentiment,
            entity_type="brand",
            limit=limit
        )
        
        return similar
    
    async def recommend_action(
        self,
        user_id: str,
        mention: Dict[str, Any],
        brand_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recommend the best action based on what worked before.
        
        Returns:
            {
                "recommended_action": "amplify|respond|engage|escalate",
                "confidence": 0.0-1.0,
                "reasoning": "Based on 5 similar situations...",
                "past_examples": [{...}, {...}]
            }
        """
        self.log_task("Generating action recommendation based on history")
        
        # Get similar past situations
        similar = await self.find_similar_situations(user_id, mention)
        
        if not similar:
            # No history - return default recommendation
            sentiment = mention.get('sentiment', 'neutral')
            severity = mention.get('severity', 0)
            
            if sentiment == 'positive':
                return {
                    "recommended_action": "amplify",
                    "confidence": 0.5,
                    "reasoning": "No historical data. Default: amplify positive mentions.",
                    "past_examples": []
                }
            elif sentiment == 'negative' and severity and severity >= 7:
                return {
                    "recommended_action": "escalate",
                    "confidence": 0.5,
                    "reasoning": "No historical data. Default: escalate high-severity issues.",
                    "past_examples": []
                }
            else:
                return {
                    "recommended_action": "engage",
                    "confidence": 0.5,
                    "reasoning": "No historical data. Default: engage with neutral mentions.",
                    "past_examples": []
                }
        
        # Use AI to analyze past outcomes and recommend
        prompt = f"""Based on historical data, recommend the best action for this mention.

CURRENT MENTION:
- Sentiment: {mention.get('sentiment')}
- Severity: {mention.get('severity', 'N/A')}
- Title: {mention.get('title', 'N/A')}
- Source: {mention.get('source_type', 'N/A')}

SIMILAR PAST SITUATIONS:
{json.dumps(similar[:3], indent=2, default=str)}

Based on what typically works, recommend an action:
- AMPLIFY: Share/celebrate positive mentions
- RESPOND: Address negative mentions
- ENGAGE: Convert neutral mentions to advocacy
- ESCALATE: Urgent crisis response needed
- IGNORE: Not worth responding

Return ONLY valid JSON:
{{
    "recommended_action": "action_type",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation"
}}
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            result = json.loads(clean_json)
            result['past_examples'] = similar[:3]
            return result
        except Exception as e:
            logger.error(f"❌ Recommendation failed: {e}")
            return {
                "recommended_action": "engage",
                "confidence": 0.3,
                "reasoning": f"Fallback recommendation (error: {str(e)[:50]})",
                "past_examples": similar[:3] if similar else []
            }
    
    async def get_competitor_playbook(
        self,
        user_id: str,
        competitor_name: str
    ) -> Dict[str, Any]:
        """
        Summarize what a competitor has done historically.
        
        Returns:
            {
                "competitor": "CompanyX",
                "total_actions": 15,
                "patterns": ["Frequent product launches", "Strong sustainability messaging"],
                "recent_actions": [{...}]
            }
        """
        self.log_task(f"Building playbook for competitor: {competitor_name}")
        
        # This would query competitor_actions_log
        # For now, return placeholder as we need data first
        return {
            "competitor": competitor_name,
            "total_actions": 0,
            "patterns": [],
            "recent_actions": [],
            "note": "Playbook builds as more competitor data is collected"
        }
    
    async def get_brand_health_score(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate current brand health score (0-100).
        
        Score Components:
        - Sentiment Score (40%): Average sentiment over period
        - Visibility Score (25%): Mention volume vs baseline
        - Response Score (20%): Actions taken vs needed
        - Competitive Position (15%): Your sentiment vs competitors
        """
        self.log_task(f"Calculating brand health score for {days} days")
        
        # Get health trend data
        trend = self.bq.get_brand_health_trend(user_id, days)
        
        if trend:
            # Return most recent score
            latest = trend[-1]
            return {
                "overall_score": latest.get('overall_score', 50),
                "sentiment_score": latest.get('sentiment_score', 50),
                "visibility_score": latest.get('visibility_score', 50),
                "response_score": latest.get('response_score', 50),
                "trend": trend,
                "status": self._get_health_status(latest.get('overall_score', 50))
            }
        
        # No data - return baseline
        return {
            "overall_score": 50,
            "sentiment_score": 50,
            "visibility_score": 50,
            "response_score": 50,
            "trend": [],
            "status": "unknown",
            "note": "Insufficient data. Score will improve as more mentions are tracked."
        }
    
    def _get_health_status(self, score: float) -> str:
        """Convert score to status label."""
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "needs_attention"
        else:
            return "critical"
    
    async def get_geographic_insights(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get sentiment breakdown by country.
        Returns top 5 positive and negative countries.
        """
        self.log_task(f"Getting geographic insights for {days} days")
        
        return self.bq.get_geographic_sentiment_breakdown(user_id, days, "brand")

"""
Brand Monitoring Agent
AI-powered sentiment analysis and crisis response for brand mentions.
"""
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent
from app.services.llm_factory import get_model

logger = logging.getLogger(__name__)


class BrandMonitoringAgent(BaseAgent):
    """
    Agent responsible for:
    1. Analyzing sentiment of brand mentions
    2. Scoring severity of negative mentions
    3. Generating crisis response suggestions
    """
    
    def __init__(self):
        super().__init__("BrandMonitoringAgent")
        self.model = get_model(intent='fast')  # Gemini 1.5 Flash for speed
    
    async def analyze_mentions(
        self, 
        brand_name: str, 
        articles: List[Dict[str, Any]],
        negative_examples: List[Dict[str, str]] = []
    ) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for each article mentioning the brand.
        
        Args:
            brand_name: The brand being monitored
            articles: List of article dictionaries from news client
            negative_examples: List of articles previously marked as irrelevant
            
        Returns:
            List of articles with added sentiment analysis fields:
            - sentiment: "positive" | "neutral" | "negative"
            - sentiment_score: float (-1.0 to 1.0)
            - severity: int (1-10, only for negative)
            - key_concerns: list of concerning phrases (only for negative)
        """
        self.log_task(f"Analyzing {len(articles)} mentions for brand: {brand_name}")
        
        if not articles:
            return []
        
        analyzed_articles = []
        
        # Process articles in batches for efficiency
        batch_size = 5
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            batch_results = await self._analyze_batch(brand_name, batch, negative_examples)
            analyzed_articles.extend(batch_results)
            
        # Filter out irrelevant articles
        relevant_articles = [a for a in analyzed_articles if a.get("is_relevant", True)]
        
        # Sort by severity (negative first) then by date
        relevant_articles.sort(
            key=lambda x: (
                0 if x.get("sentiment") == "negative" else 1,
                -(x.get("severity") or 0),
                x.get("published_at", "")
            ),
            reverse=False
        )
        
        self.log_task(f"Analysis complete. Found {sum(1 for a in relevant_articles if a.get('sentiment') == 'negative')} negative mentions out of {len(relevant_articles)} relevant articles.")
        return relevant_articles
    
    async def _analyze_batch(
        self, 
        brand_name: str, 
        articles: List[Dict[str, Any]],
        negative_examples: List[Dict[str, str]] = []
    ) -> List[Dict[str, Any]]:
        """Analyze a batch of articles for sentiment."""
        
        # Prepare articles for analysis
        articles_text = []
        for idx, article in enumerate(articles):
            articles_text.append(f"""
Article {idx + 1}:
Title: {article.get('title', 'N/A')}
Source: {article.get('source_name', 'Unknown')}
Content: {article.get('content', article.get('description', 'N/A'))[:1000]}
""")

        # Prepare negative examples context
        negative_context = ""
        if negative_examples:
            examples_list = "\n".join([f"- {ex.get('title', '')}: {ex.get('snippet', '')[:100]}" for ex in negative_examples])
            negative_context = f"""
IMPORTANT - RELEVANCE FILTERING:
The following are examples of articles the user has marked as IRRELEVANT (wrong brand, wrong context). 
If any of the articles below are similar to these or discuss a clearly different entity with the same name, mark "is_relevant": false.

IRRELEVANT EXAMPLES:
{examples_list}
"""
        
        prompt = f"""You are a brand reputation analyst. Analyze the following articles about "{brand_name}" for sentiment.

{negative_context}

For EACH article, determine:
1. is_relevant: boolean (true/false) - Is this article actually about the brand "{brand_name}"?
2. sentiment: "positive", "neutral", or "negative"
3. sentiment_score: float from -1.0 (very negative) to 1.0 (very positive)
4. severity: integer 1-10 (only for negative sentiment, how damaging to brand reputation)
5. key_concerns: list of 1-3 concerning phrases/issues (only for negative sentiment)
6. summary: one-sentence summary of the article's stance on the brand

ARTICLES TO ANALYZE:
{"".join(articles_text)}

Return ONLY a valid JSON array with {len(articles)} objects in the same order as the articles:
[
  {{
    "article_index": 0,
    "is_relevant": true,
    "sentiment": "positive",
    "sentiment_score": 0.8,
    "severity": null,
    "key_concerns": [],
    "summary": "Brief summary..."
  }},
  ...
]
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            results = json.loads(clean_json)
            
            # Merge results with original articles
            analyzed = []
            for idx, article in enumerate(articles):
                result = next((r for r in results if r.get("article_index") == idx), {})
                analyzed.append({
                    **article,
                    "is_relevant": result.get("is_relevant", True),
                    "sentiment": result.get("sentiment", "neutral"),
                    "sentiment_score": result.get("sentiment_score", 0.0),
                    "severity": result.get("severity"),
                    "key_concerns": result.get("key_concerns", []),
                    "ai_summary": result.get("summary", "")
                })
            
            return analyzed
            
        except Exception as e:
            logger.error(f"❌ Sentiment analysis failed: {e}")
            # Return articles with default neutral sentiment
            return [{
                **article,
                "is_relevant": True,
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "severity": None,
                "key_concerns": [],
                "ai_summary": "Analysis unavailable"
            } for article in articles]
    
    async def get_crisis_response(
        self, 
        negative_mention: Dict[str, Any],
        brand_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate AI-powered crisis response suggestions for a negative mention.
        
        Args:
            negative_mention: The article data with sentiment analysis
            brand_context: Optional brand DNA/profile for personalized responses
            
        Returns:
            Dictionary containing:
            - executive_summary: Brief overview of the issue
            - recommended_actions: List of prioritized action items
            - response_templates: Draft responses for different channels
            - escalation_level: "low" | "medium" | "high" | "critical"
            - timeline: Suggested response timeline
        """
        self.log_task(f"Generating crisis response for: {negative_mention.get('title', 'Unknown')}")
        
        brand_info = ""
        if brand_context:
            brand_info = f"""
Brand Profile:
- Name: {brand_context.get('brand_name', 'Unknown')}
- Tone: {brand_context.get('tone', 'Professional')}
- Values: {brand_context.get('offerings', [])}
"""
        
        prompt = f"""You are a senior PR crisis management expert. A brand is facing a negative mention that requires a response strategy.

{brand_info}

NEGATIVE MENTION DETAILS:
- Title: {negative_mention.get('title', 'N/A')}
- Source: {negative_mention.get('source_name', 'Unknown')} 
- Severity: {negative_mention.get('severity', 'N/A')}/10
- Key Concerns: {negative_mention.get('key_concerns', [])}
- Content: {negative_mention.get('content', negative_mention.get('description', 'N/A'))[:1500]}
- AI Summary: {negative_mention.get('ai_summary', 'N/A')}

Generate a comprehensive crisis response plan. Return ONLY valid JSON:
{{
    "executive_summary": "2-3 sentence overview of the situation and stakes",
    "escalation_level": "low|medium|high|critical",
    "recommended_actions": [
        {{
            "priority": 1,
            "action": "Specific action to take",
            "rationale": "Why this matters",
            "owner": "Who should handle this (e.g., PR Team, Legal, CEO)"
        }}
    ],
    "response_templates": {{
        "press_statement": "Draft press statement (2-3 sentences)",
        "social_media": "Draft social media response (under 280 chars)",
        "internal_memo": "Key points for internal communication"
    }},
    "timeline": {{
        "immediate": "Actions for next 1-2 hours",
        "short_term": "Actions for next 24 hours",
        "long_term": "Actions for next week"
    }},
    "do_not_say": ["List of phrases or topics to avoid"],
    "key_messages": ["3-5 key messages to emphasize"]
}}
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            crisis_response = json.loads(clean_json)
            
            self.log_task("Crisis response generated successfully")
            return {
                "status": "success",
                "article_id": negative_mention.get("id", ""),
                "article_title": negative_mention.get("title", ""),
                **crisis_response
            }
            
        except Exception as e:
            logger.error(f"❌ Crisis response generation failed: {e}")
            return {
                "status": "error",
                "article_id": negative_mention.get("id", ""),
                "error": str(e),
                "executive_summary": "Unable to generate automated response. Please consult your PR team.",
                "escalation_level": "high",
                "recommended_actions": [
                    {
                        "priority": 1,
                        "action": "Contact your PR or communications team immediately",
                        "rationale": "Automated analysis failed - human review required",
                        "owner": "PR Team"
                    }
                ]
            }

    async def suggest_keywords(
        self,
        brand_name: str,
        description: str = ""
    ) -> List[str]:
        """
        Generate distinct keyword suggestions for brand monitoring.
        """
        prompt = f"""You are a brand monitoring expert.
Brand: {brand_name}
Description: {description}

Suggest 5-8 distinct, high-value keywords or phrases to monitor for this brand to catch reputation issues or trends.
Exclude the brand name itself. Focus on products, key executives (if known), industry terms specific to them, or common misspellings if relevant.
Return ONLY a valid JSON array of strings: ["keyword1", "keyword2"]"""

        try:
            response = await self.model.generate_content_async(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"❌ Keyword suggestion failed: {e}")
            return [f"{brand_name} reviews", f"{brand_name} scam", f"{brand_name} support"]

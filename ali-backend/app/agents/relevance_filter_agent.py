"""
Relevance Filter Agent
AI-powered entity disambiguation for brand monitoring.
Filters out articles that mention the brand name but are about a different entity.
"""
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from .base_agent import BaseAgent
from app.services.llm_factory import get_model

logger = logging.getLogger(__name__)


class RelevanceFilterAgent(BaseAgent):
    """
    Agent responsible for:
    1. Determining if articles are about the user's SPECIFIC brand (not a different entity with the same name)
    2. Using rich brand context (industry, offerings, location) for disambiguation
    3. Learning from user feedback to identify common false positives
    """
    
    def __init__(self):
        super().__init__("RelevanceFilterAgent")
        self.model = get_model(intent='fast')  # Gemini 1.5 Flash for speed
    
    async def filter_articles(
        self,
        brand_profile: Dict[str, Any],
        articles: List[Dict[str, Any]],
        feedback_patterns: Optional[List[Dict[str, str]]] = None,
        monitoring_topic: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Filter articles to keep only those that are about the user's specific brand OR monitored topic.
        
        Args:
            brand_profile: Rich brand context (used if monitoring_topic is None or matches brand)
            articles: List of article dictionaries
            feedback_patterns: User-flagged false positives
            monitoring_topic: Specific topic/keyword being monitored (overrides brand_name context)
        """
        target_name = monitoring_topic if monitoring_topic else brand_profile.get('brand_name', 'Unknown')
        self.log_task(f"Filtering {len(articles)} articles for target: {target_name}")
        
        if not articles:
            return [], {"total": 0, "relevant": 0, "filtered_out": 0}
        
        relevant_articles = []
        filtered_count = 0
        
        # Process articles in batches
        batch_size = 8
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            batch_results = await self._filter_batch(brand_profile, batch, feedback_patterns, monitoring_topic)
            
            for article, filter_result in zip(batch, batch_results):
                article_with_filter = {
                    **article,
                    "relevance_confidence": filter_result.get("confidence", 0.5),
                    "relevance_reasoning": filter_result.get("reasoning", ""),
                    "detected_entity": filter_result.get("entity_detected", "")
                }
                
                if filter_result.get("is_relevant", True):
                    relevant_articles.append(article_with_filter)
                else:
                    filtered_count += 1
                    self.log_task(f"Filtered out: '{article.get('title', 'Unknown')[:50]}...' - Entity: {filter_result.get('entity_detected', 'Unknown')}")
        
        filter_stats = {
            "total": len(articles),
            "relevant": len(relevant_articles),
            "filtered_out": filtered_count,
            "filter_rate": round(filtered_count / len(articles) * 100, 1) if articles else 0
        }
        
        return relevant_articles, filter_stats
    
    async def _filter_batch(
        self,
        brand_profile: Dict[str, Any],
        articles: List[Dict[str, Any]],
        feedback_patterns: Optional[List[Dict[str, str]]] = None,
        monitoring_topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filter a batch of articles using LLM disambiguation."""
        
        # Determine context based on whether we are monitoring the brand or a generic topic
        brand_name = brand_profile.get('brand_name', 'Unknown')
        is_generic_topic = monitoring_topic and monitoring_topic != brand_name
        
        if is_generic_topic:
            # We are monitoring a topic/competitor, so strict brand profile details (like my website) 
            # might NOT apply to the relevant articles.
            target_name = monitoring_topic
            industry = brand_profile.get('industry', 'Business') # Keep industry as loose context
            context_desc = f"Topic/Keyword being monitored: {monitoring_topic}"
        else:
            # We are monitoring the user's specific brand
            target_name = brand_name
            industry = brand_profile.get('industry', brand_profile.get('offerings', ['Unknown'])[0] if brand_profile.get('offerings') else 'Unknown')
            offerings = brand_profile.get('offerings', [])
            description = brand_profile.get('description', '')
            location = brand_profile.get('location', brand_profile.get('cultural_nuance', ''))
            website = brand_profile.get('website', '')
            tone = brand_profile.get('tone', '')
            
            context_desc = f"""• Name: {target_name}
• Industry/Sector: {industry}
• Products/Services: {', '.join(offerings[:5]) if offerings else 'Not specified'}
• Description: {description[:200] if description else 'Not specified'}
• Location/Markets: {location if location else 'Not specified'}
• Website: {website if website else 'Not specified'}"""

        # Build articles text for analysis
        articles_text = []
        for idx, article in enumerate(articles):
            articles_text.append(f"""
Article {idx + 1}:
Title: {article.get('title', 'N/A')}
Source: {article.get('source_name', 'Unknown')}
Content: {article.get('content', article.get('description', 'N/A'))[:800]}
URL: {article.get('url', 'N/A')}
""")

        # Build false positive examples from feedback
        feedback_context = ""
        if feedback_patterns:
            examples_list = "\n".join([
                f"- \"{ex.get('title', '')[:60]}...\" → Actually about: {ex.get('detected_entity', ex.get('snippet', '')[:40])}"
                for ex in feedback_patterns[:10]
            ])
            feedback_context = f"""
KNOWN FALSE POSITIVES (user flagged as irrelevant):
{examples_list}
"""

        prompt = f"""You are a relevance filter expert.
Target ID: {target_name}
Context: {context_desc}
{feedback_context}

Task: Identify articles RELEVANT to "{target_name}".
1. IGNORE articles clearly about a completely different entity with a similar name.
2. KEEP articles that discuss "{target_name}" or are relevant to this topic.

═══════════════════════════════════════════════════════════════════════════════
DISAMBIGUATION GUIDELINES:
═══════════════════════════════════════════════════════════════════════════════
1. An article is RELEVANT if it's actually about the business/brand described above
2. An article is NOT RELEVANT if:
   - It's about a PERSON with the same name (e.g., celebrity, athlete)
   - It's about a DIFFERENT COMPANY with a similar name/ticker
   - It's about an acronym that expands to something else
   - The brand name appears coincidentally but the article is about something else
3. Look for contextual clues: industry terms, location, products mentioned
4. When uncertain, lean towards RELEVANT (false negatives are worse than false positives for now)

═══════════════════════════════════════════════════════════════════════════════
ARTICLES TO ANALYZE:
═══════════════════════════════════════════════════════════════════════════════
{"".join(articles_text)}

═══════════════════════════════════════════════════════════════════════════════
Return ONLY a valid JSON array with {len(articles)} objects in EXACT order:
[
  {{
    "article_index": 0,
    "is_relevant": true,
    "confidence": 0.95,
    "reasoning": "One sentence explaining why this is/isn't about the brand",
    "entity_detected": "The actual entity this article is about"
  }},
  ...
]
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            results = json.loads(clean_json)
            
            # Map results to articles by index
            results_by_index = {r.get("article_index"): r for r in results}
            
            # Return results in order, with defaults for missing
            return [
                results_by_index.get(idx, {
                    "is_relevant": True,  # Default to relevant if parsing fails
                    "confidence": 0.5,
                    "reasoning": "Could not determine",
                    "entity_detected": "Unknown"
                })
                for idx in range(len(articles))
            ]
            
        except Exception as e:
            logger.error(f"❌ Relevance filtering failed: {e}")
            # Return default relevant for all if LLM fails (don't lose articles)
            return [{
                "is_relevant": True,
                "confidence": 0.5,
                "reasoning": "Filter unavailable - defaulting to relevant",
                "entity_detected": "Unknown"
            } for _ in articles]
    
    def extract_feedback_pattern(
        self,
        article_title: str,
        article_snippet: str,
        brand_name: str
    ) -> Dict[str, str]:
        """
        Extract a disambiguation pattern from user feedback.
        Called when user marks an article as irrelevant.
        
        Returns a pattern dict to store for future filtering.
        """
        # Simple pattern extraction - could be enhanced with LLM later
        return {
            "title": article_title,
            "snippet": article_snippet[:200],
            "brand_searched": brand_name,
            "detected_entity": "Unknown - user flagged as irrelevant"
        }

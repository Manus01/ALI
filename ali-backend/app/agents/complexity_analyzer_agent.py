"""
Complexity Analyzer Agent
Analyzes topic complexity for the Adaptive Tutorial Engine (ATE).

Factors considered:
1. Prerequisite concepts required
2. Abstraction level (concrete vs abstract)
3. Historical failure rates from similar topics
4. Estimated cognitive load
5. Domain-specific difficulty markers
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ComplexityAnalyzerAgent:
    """
    Analyzes topic complexity to inform tutorial generation.
    Uses LLM reasoning combined with historical data.
    """

    # Complexity factor weights
    WEIGHTS = {
        "prerequisite_count": 0.25,      # More prerequisites = higher complexity
        "abstraction_level": 0.25,       # Abstract concepts are harder
        "historical_failure_rate": 0.20, # Past user struggles indicate difficulty
        "cognitive_load": 0.15,          # Estimated mental effort required
        "domain_depth": 0.15             # How specialized the topic is
    }

    # Domain categories and their base complexity
    DOMAIN_COMPLEXITY = {
        "fundamentals": 2.0,
        "strategy": 5.0,
        "analytics": 6.0,
        "automation": 7.0,
        "advanced_optimization": 8.0,
        "enterprise": 9.0
    }

    # Marketing topic prerequisites map
    PREREQUISITE_MAP = {
        "facebook_ads_basics": [],
        "audience_targeting": ["facebook_ads_basics"],
        "lookalike_audiences": ["audience_targeting", "custom_audiences"],
        "custom_audiences": ["audience_targeting"],
        "conversion_tracking": ["facebook_ads_basics"],
        "retargeting": ["conversion_tracking", "custom_audiences"],
        "campaign_optimization": ["conversion_tracking", "audience_targeting"],
        "a_b_testing": ["facebook_ads_basics", "conversion_tracking"],
        "attribution_modeling": ["conversion_tracking", "campaign_optimization"],
        "budget_optimization": ["campaign_optimization"],
        "creative_strategy": ["facebook_ads_basics"],
        "video_ads": ["creative_strategy"],
        "dynamic_ads": ["retargeting", "product_catalog"],
        "product_catalog": ["facebook_ads_basics"],
    }

    def __init__(self, db=None, bq_service=None):
        """Initialize with optional Firestore and BigQuery clients."""
        self._db = db
        self._bq_service = bq_service

    @property
    def db(self):
        if self._db is None:
            try:
                from app.core.security import db
                self._db = db
            except Exception:
                pass
        return self._db

    @property
    def bq(self):
        if self._bq_service is None:
            try:
                from app.services.bigquery_service import get_bigquery_service
                self._bq_service = get_bigquery_service()
            except Exception:
                pass
        return self._bq_service

    def analyze_topic_complexity(
        self, 
        topic: str,
        user_skill_level: str = "INTERMEDIATE",
        include_llm_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze the complexity of a given topic.
        
        Args:
            topic: The topic to analyze
            user_skill_level: User's current skill level (NOVICE, INTERMEDIATE, EXPERT)
            include_llm_analysis: Whether to use LLM for deeper analysis
            
        Returns:
            ComplexityAnalysis dict with scores and recommendations
        """
        try:
            # 1. Count prerequisites
            prerequisite_count = self._count_prerequisites(topic)
            prerequisite_score = min(prerequisite_count / 5, 1.0) * 10  # Normalize to 1-10

            # 2. Estimate abstraction level
            abstraction_score = self._estimate_abstraction_level(topic)

            # 3. Get historical failure rate
            failure_rate = self._get_historical_failure_rate(topic)
            failure_score = failure_rate * 10 if failure_rate else 5.0  # Default to medium

            # 4. Estimate cognitive load
            cognitive_score = self._estimate_cognitive_load(topic, user_skill_level)

            # 5. Determine domain depth
            domain_score = self._get_domain_depth(topic)

            # Calculate weighted complexity score
            complexity_score = (
                prerequisite_score * self.WEIGHTS["prerequisite_count"] +
                abstraction_score * self.WEIGHTS["abstraction_level"] +
                failure_score * self.WEIGHTS["historical_failure_rate"] +
                cognitive_score * self.WEIGHTS["cognitive_load"] +
                domain_score * self.WEIGHTS["domain_depth"]
            )

            # LLM enhancement if enabled
            llm_analysis = None
            if include_llm_analysis:
                llm_analysis = self._get_llm_complexity_analysis(topic)
                if llm_analysis:
                    # Blend LLM score with calculated score (70% calculated, 30% LLM)
                    llm_score = llm_analysis.get("complexity_score", complexity_score)
                    complexity_score = complexity_score * 0.7 + llm_score * 0.3

            # Determine recommended skill level based on complexity
            if complexity_score <= 3:
                recommended_level = "NOVICE"
            elif complexity_score <= 6:
                recommended_level = "INTERMEDIATE"
            else:
                recommended_level = "EXPERT"

            # Estimate duration based on complexity
            base_duration = 15  # minutes
            estimated_duration = int(base_duration * (1 + complexity_score / 10))

            return {
                "topic": topic,
                "complexity_score": round(complexity_score, 2),
                "prerequisite_count": prerequisite_count,
                "prerequisites": self._get_prerequisites(topic),
                "abstraction_level": round(abstraction_score, 2),
                "historical_failure_rate": failure_rate,
                "estimated_duration_minutes": estimated_duration,
                "recommended_skill_level": recommended_level,
                "analysis_confidence": 0.8 if llm_analysis else 0.6,
                "component_scores": {
                    "prerequisites": round(prerequisite_score, 2),
                    "abstraction": round(abstraction_score, 2),
                    "failure_history": round(failure_score, 2),
                    "cognitive_load": round(cognitive_score, 2),
                    "domain_depth": round(domain_score, 2)
                },
                "llm_insights": llm_analysis.get("insights") if llm_analysis else None,
                "analyzed_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Complexity analysis failed: {e}")
            # Return safe defaults
            return {
                "topic": topic,
                "complexity_score": 5.0,
                "prerequisite_count": 0,
                "prerequisites": [],
                "abstraction_level": 5.0,
                "historical_failure_rate": None,
                "estimated_duration_minutes": 20,
                "recommended_skill_level": "INTERMEDIATE",
                "analysis_confidence": 0.3,
                "error": str(e),
                "analyzed_at": datetime.utcnow().isoformat()
            }

    def _count_prerequisites(self, topic: str) -> int:
        """Count direct and transitive prerequisites for a topic."""
        normalized_topic = topic.lower().replace(" ", "_").replace("-", "_")
        
        # Check direct match
        if normalized_topic in self.PREREQUISITE_MAP:
            direct = self.PREREQUISITE_MAP[normalized_topic]
            # Count transitive prerequisites too
            all_prereqs = set(direct)
            for prereq in direct:
                if prereq in self.PREREQUISITE_MAP:
                    all_prereqs.update(self.PREREQUISITE_MAP[prereq])
            return len(all_prereqs)
        
        # Fuzzy match
        for key in self.PREREQUISITE_MAP:
            if normalized_topic in key or key in normalized_topic:
                return len(self.PREREQUISITE_MAP[key])
        
        # Default based on topic length/words (more words = likely more complex)
        word_count = len(topic.split())
        return min(word_count - 1, 3) if word_count > 1 else 0

    def _get_prerequisites(self, topic: str) -> List[str]:
        """Get list of prerequisite topics."""
        normalized_topic = topic.lower().replace(" ", "_").replace("-", "_")
        
        if normalized_topic in self.PREREQUISITE_MAP:
            return self.PREREQUISITE_MAP[normalized_topic]
        
        for key in self.PREREQUISITE_MAP:
            if normalized_topic in key or key in normalized_topic:
                return self.PREREQUISITE_MAP[key]
        
        return []

    def _estimate_abstraction_level(self, topic: str) -> float:
        """Estimate how abstract vs concrete the topic is."""
        topic_lower = topic.lower()
        
        # Concrete topics (low abstraction)
        concrete_markers = ["setup", "create", "build", "install", "configure", "basic", "step"]
        # Abstract topics (high abstraction)
        abstract_markers = ["strategy", "theory", "framework", "optimization", "analysis", 
                          "attribution", "modeling", "psychology", "principles"]
        
        concrete_count = sum(1 for m in concrete_markers if m in topic_lower)
        abstract_count = sum(1 for m in abstract_markers if m in topic_lower)
        
        if concrete_count > abstract_count:
            return 3.0 + abstract_count
        elif abstract_count > concrete_count:
            return 7.0 + min(abstract_count, 3)
        else:
            return 5.0

    def _get_historical_failure_rate(self, topic: str) -> Optional[float]:
        """Get average failure rate from BigQuery for similar topics."""
        if not self.bq or not self.bq.client:
            return None
        
        try:
            # Query learning analytics for similar topics
            query = f"""
            SELECT 
                AVG(CASE WHEN quiz_pass = false THEN 1 ELSE 0 END) as failure_rate
            FROM `{self.bq._get_table_ref('learning_analytics_log')}`
            WHERE LOWER(tutorial_topic) LIKE LOWER(@topic_pattern)
              AND event_type IN ('quiz_pass', 'quiz_fail')
              AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
            """
            
            from google.cloud import bigquery
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("topic_pattern", "STRING", f"%{topic}%"),
                ]
            )
            
            results = list(self.bq.client.query(query, job_config=job_config))
            if results and results[0]["failure_rate"] is not None:
                return round(results[0]["failure_rate"], 2)
        except Exception as e:
            logger.debug(f"Historical failure rate query failed: {e}")
        
        return None

    def _estimate_cognitive_load(self, topic: str, user_skill_level: str) -> float:
        """Estimate cognitive load based on topic and user level."""
        base_load = 5.0
        
        # Adjust for user level
        level_adjustment = {
            "NOVICE": 2.0,       # Everything is harder for novices
            "INTERMEDIATE": 0.0,
            "EXPERT": -2.0       # Experts find things easier
        }
        
        # Adjust for topic complexity markers
        high_load_markers = ["multi", "complex", "advanced", "integration", "automated"]
        low_load_markers = ["simple", "basic", "intro", "beginner", "quick"]
        
        topic_lower = topic.lower()
        for marker in high_load_markers:
            if marker in topic_lower:
                base_load += 1.0
        for marker in low_load_markers:
            if marker in topic_lower:
                base_load -= 1.0
        
        return max(1.0, min(10.0, base_load + level_adjustment.get(user_skill_level, 0)))

    def _get_domain_depth(self, topic: str) -> float:
        """Determine the domain depth/specialization of the topic."""
        topic_lower = topic.lower()
        
        for domain, base_complexity in self.DOMAIN_COMPLEXITY.items():
            if domain.replace("_", " ") in topic_lower or domain in topic_lower:
                return base_complexity
        
        # Default to mid-range
        return 5.0

    def _get_llm_complexity_analysis(self, topic: str) -> Optional[Dict[str, Any]]:
        """Use LLM to analyze topic complexity (optional enhancement)."""
        try:
            from google import genai
            import os
            import json
            
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            
            prompt = f"""Analyze the complexity of this marketing education topic for a learner:

Topic: {topic}

Rate on a scale of 1-10 (1=very easy, 10=very difficult) considering:
1. How many prerequisite concepts are needed
2. How abstract vs practical the topic is
3. How much domain expertise is required

Return ONLY valid JSON:
{{"complexity_score": <number 1-10>, "insights": "<1-2 sentence explanation>"}}
"""
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            # Parse JSON from response
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            return json.loads(text)
            
        except Exception as e:
            logger.debug(f"LLM complexity analysis failed: {e}")
            return None


# Singleton instance
_complexity_agent: Optional[ComplexityAnalyzerAgent] = None


def get_complexity_analyzer() -> ComplexityAnalyzerAgent:
    """Get or create singleton ComplexityAnalyzerAgent."""
    global _complexity_agent
    if _complexity_agent is None:
        _complexity_agent = ComplexityAnalyzerAgent()
    return _complexity_agent

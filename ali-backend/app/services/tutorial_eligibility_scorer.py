"""
Tutorial Eligibility Scorer
Scores and prioritizes tutorial generation recommendations.

Factors considered:
1. Gap severity (from GapAnalyzerAgent)
2. User performance level
3. Topic complexity
4. Prerequisite completion status
5. Time since last tutorial completion
6. Campaign performance correlation
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class EligibilityScore(float, Enum):
    """Named eligibility score ranges for clarity."""
    CRITICAL = 95      # Must generate immediately
    HIGH = 80          # Should generate soon
    MEDIUM = 60        # Normal priority
    LOW = 40           # Can wait
    SKIP = 20          # Don't generate


class TutorialEligibilityScorer:
    """
    Scores tutorial generation eligibility based on multiple factors.
    Used to prioritize which tutorials should be generated first.
    """

    # Scoring weights (must sum to 1.0)
    WEIGHTS = {
        "gap_severity": 0.30,          # How critical is the knowledge gap
        "performance_level": 0.20,     # User's current performance status
        "topic_complexity": 0.15,      # How complex is the topic
        "prerequisite_status": 0.15,   # Are prerequisites completed
        "recency": 0.10,               # Time since last tutorial
        "campaign_correlation": 0.10   # Campaign performance impact
    }

    # Performance level score mappings
    PERFORMANCE_SCORES = {
        "struggling": 100,      # Highest priority
        "below_average": 80,
        "average": 50,
        "above_average": 30,
        "excelling": 20         # Lowest priority (already doing well)
    }

    def __init__(self, db=None):
        """Initialize with optional Firestore client."""
        self._db = db
        self._complexity_analyzer = None
        self._performance_analyzer = None
        self._gap_analyzer = None

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
    def complexity_analyzer(self):
        if self._complexity_analyzer is None:
            try:
                from app.agents.complexity_analyzer_agent import get_complexity_analyzer
                self._complexity_analyzer = get_complexity_analyzer()
            except Exception:
                pass
        return self._complexity_analyzer

    @property
    def performance_analyzer(self):
        if self._performance_analyzer is None:
            try:
                from app.agents.performance_analyzer_agent import get_performance_analyzer
                self._performance_analyzer = get_performance_analyzer()
            except Exception:
                pass
        return self._performance_analyzer

    @property
    def gap_analyzer(self):
        if self._gap_analyzer is None:
            try:
                from app.agents.gap_analyzer_agent import get_gap_analyzer
                self._gap_analyzer = get_gap_analyzer()
            except Exception:
                pass
        return self._gap_analyzer

    def score_recommendation(
        self,
        user_id: str,
        topic: str,
        gap_data: Optional[Dict] = None,
        performance_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Calculate eligibility score for a tutorial recommendation.
        
        Args:
            user_id: User to generate tutorial for
            topic: Topic of the proposed tutorial
            gap_data: Pre-computed gap data (optional)
            performance_data: Pre-computed performance data (optional)
            
        Returns:
            {
                "total_score": float (0-100),
                "eligibility": str (CRITICAL, HIGH, MEDIUM, LOW, SKIP),
                "component_scores": dict,
                "should_auto_approve": bool,
                "reasoning": list[str]
            }
        """
        try:
            component_scores = {}
            reasoning = []

            # 1. Gap Severity Score
            gap_score = self._score_gap_severity(gap_data, topic)
            component_scores["gap_severity"] = gap_score
            if gap_score >= 80:
                reasoning.append(f"Critical knowledge gap detected (score: {gap_score})")

            # 2. Performance Level Score
            perf_score = self._score_performance_level(user_id, performance_data)
            component_scores["performance_level"] = perf_score
            if perf_score >= 80:
                reasoning.append("User is struggling and needs intervention")

            # 3. Topic Complexity Score
            complexity_score = self._score_topic_complexity(topic)
            component_scores["topic_complexity"] = complexity_score

            # 4. Prerequisite Completion Score
            prereq_score = self._score_prerequisites(user_id, topic)
            component_scores["prerequisite_status"] = prereq_score
            if prereq_score < 50:
                reasoning.append("Prerequisites not yet completed")

            # 5. Recency Score
            recency_score = self._score_recency(user_id)
            component_scores["recency"] = recency_score

            # 6. Campaign Correlation Score
            campaign_score = self._score_campaign_correlation(user_id, topic)
            component_scores["campaign_correlation"] = campaign_score
            if campaign_score >= 70:
                reasoning.append("Topic directly relates to campaign performance issues")

            # Calculate weighted total
            total_score = sum(
                component_scores[key] * self.WEIGHTS[key]
                for key in self.WEIGHTS
            )

            # Determine eligibility level
            if total_score >= 90:
                eligibility = "CRITICAL"
            elif total_score >= 70:
                eligibility = "HIGH"
            elif total_score >= 50:
                eligibility = "MEDIUM"
            elif total_score >= 30:
                eligibility = "LOW"
            else:
                eligibility = "SKIP"

            # Determine auto-approval
            # Auto-approve only for quiz failures with high scores
            trigger_type = gap_data.get("trigger_type") if gap_data else None
            should_auto_approve = (
                trigger_type == "quiz_failure_remediation" and
                total_score >= 70
            )

            return {
                "user_id": user_id,
                "topic": topic,
                "total_score": round(total_score, 2),
                "eligibility": eligibility,
                "component_scores": component_scores,
                "should_auto_approve": should_auto_approve,
                "reasoning": reasoning,
                "scored_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Eligibility scoring failed: {e}")
            return {
                "user_id": user_id,
                "topic": topic,
                "total_score": 50,
                "eligibility": "MEDIUM",
                "error": str(e)
            }

    def _score_gap_severity(self, gap_data: Optional[Dict], topic: str) -> float:
        """Score based on gap severity."""
        if not gap_data:
            return 50  # Default medium score
        
        severity = gap_data.get("severity", 5)
        # Convert 1-10 severity to 0-100 score
        return min(severity * 10, 100)

    def _score_performance_level(
        self, 
        user_id: str, 
        performance_data: Optional[Dict]
    ) -> float:
        """Score based on user's overall performance level."""
        if performance_data:
            level = performance_data.get("performance_level", "average")
        elif self.performance_analyzer:
            analysis = self.performance_analyzer.analyze_user_performance(user_id)
            level = analysis.get("performance_level", "average")
        else:
            level = "average"
        
        return self.PERFORMANCE_SCORES.get(level, 50)

    def _score_topic_complexity(self, topic: str) -> float:
        """Score based on topic complexity - higher complexity = higher priority."""
        if self.complexity_analyzer:
            analysis = self.complexity_analyzer.analyze_topic_complexity(topic)
            complexity = analysis.get("complexity_score", 5)
            # Higher complexity means higher need for structured learning
            return min(complexity * 10, 100)
        return 50

    def _score_prerequisites(self, user_id: str, topic: str) -> float:
        """Score based on prerequisite completion status."""
        if not self.complexity_analyzer:
            return 80  # Default: assume prerequisites are mostly met
        
        # Get prerequisites for topic
        analysis = self.complexity_analyzer.analyze_topic_complexity(topic)
        prerequisites = analysis.get("prerequisites", [])
        
        if not prerequisites:
            return 100  # No prerequisites needed
        
        if not self.db:
            return 60
        
        try:
            # Check how many prerequisites are in completed tutorials
            tutorials = list(
                self.db.collection('users').document(user_id)
                .collection('tutorials')
                .where('is_completed', '==', True)
                .stream()
            )
            
            completed_topics = set()
            for t in tutorials:
                t_data = t.to_dict()
                topic_lower = t_data.get('topic', '').lower()
                completed_topics.add(topic_lower)
            
            # Count completed prerequisites
            completed_prereqs = sum(
                1 for p in prerequisites 
                if any(p.lower() in ct or ct in p.lower() for ct in completed_topics)
            )
            
            return (completed_prereqs / len(prerequisites)) * 100
            
        except Exception:
            return 60

    def _score_recency(self, user_id: str) -> float:
        """Score based on time since last tutorial completion."""
        if not self.db:
            return 50
        
        try:
            # Get most recent completed tutorial
            tutorials = list(
                self.db.collection('users').document(user_id)
                .collection('tutorials')
                .where('is_completed', '==', True)
                .order_by('completedAt', direction='DESCENDING')
                .limit(1)
                .stream()
            )
            
            if not tutorials:
                return 80  # No tutorials = high priority to start learning
            
            last_tutorial = tutorials[0].to_dict()
            completed_at = last_tutorial.get('completedAt')
            
            if not completed_at:
                return 60
            
            # Calculate days since completion
            if hasattr(completed_at, 'timestamp'):
                completed_datetime = datetime.fromtimestamp(completed_at.timestamp())
            else:
                completed_datetime = datetime.fromisoformat(str(completed_at))
            
            days_since = (datetime.utcnow() - completed_datetime).days
            
            # More days = higher priority (user hasn't learned recently)
            if days_since >= 14:
                return 90
            elif days_since >= 7:
                return 70
            elif days_since >= 3:
                return 50
            else:
                return 30  # Low priority - recently active
                
        except Exception:
            return 50

    def _score_campaign_correlation(self, user_id: str, topic: str) -> float:
        """Score based on campaign performance correlation to topic."""
        if not self.db:
            return 50
        
        try:
            # Get recent campaign performance
            campaigns = list(
                self.db.collection('users').document(user_id)
                .collection('campaign_performance')
                .limit(5)
                .stream()
            )
            
            if not campaigns:
                return 40  # No campaigns = lower priority for campaign-related tutorials
            
            # Check for performance issues
            low_performance = False
            topic_lower = topic.lower()
            
            for c in campaigns:
                c_data = c.to_dict()
                ctr = c_data.get('ctr', 0)
                
                # If CTR is low and topic is related to optimization/creative
                if ctr < 1.0:
                    if any(t in topic_lower for t in ['optimization', 'creative', 'ctr', 'engagement']):
                        return 90  # High correlation
                    low_performance = True
            
            if low_performance:
                return 70  # General performance issues
            
            return 50  # Normal
            
        except Exception:
            return 50

    def batch_score_recommendations(
        self, 
        user_id: str,
        recommendations: List[Dict]
    ) -> List[Dict]:
        """
        Score multiple recommendations and return sorted by priority.
        """
        # Pre-fetch performance data once
        performance_data = None
        if self.performance_analyzer:
            performance_data = self.performance_analyzer.analyze_user_performance(user_id)
        
        scored = []
        for rec in recommendations:
            score_result = self.score_recommendation(
                user_id=user_id,
                topic=rec.get("topic", ""),
                gap_data=rec,
                performance_data=performance_data
            )
            rec["eligibility_score"] = score_result
            scored.append(rec)
        
        # Sort by total score descending
        scored.sort(key=lambda x: x["eligibility_score"]["total_score"], reverse=True)
        
        return scored


# Singleton instance
_eligibility_scorer: Optional[TutorialEligibilityScorer] = None


def get_eligibility_scorer() -> TutorialEligibilityScorer:
    """Get or create singleton TutorialEligibilityScorer."""
    global _eligibility_scorer
    if _eligibility_scorer is None:
        _eligibility_scorer = TutorialEligibilityScorer()
    return _eligibility_scorer

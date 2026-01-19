"""
Gap Analyzer Agent
Identifies and prioritizes learning gaps for the Adaptive Tutorial Engine (ATE).

Combines data from:
1. Quiz results and section struggles
2. Skill matrix analysis
3. Campaign performance correlation
4. Time-based learning patterns
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class GapAnalyzerAgent:
    """
    Identifies learning gaps by analyzing multiple data sources.
    Produces prioritized recommendations for tutorial generation.
    """

    # Gap severity levels
    SEVERITY = {
        "CRITICAL": 9,    # Immediate intervention needed
        "HIGH": 7,        # Should be addressed soon
        "MEDIUM": 5,      # Normal priority
        "LOW": 3          # Optional enhancement
    }

    # Trigger type mapping
    TRIGGER_TYPES = {
        "quiz_failure": "quiz_failure_remediation",
        "skill_gap": "skill_gap_detected",
        "performance_decline": "performance_decline",
        "excellence": "performance_excellence",
        "channel": "new_channel_onboarding"
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

    def analyze_user_gaps(self, user_id: str) -> Dict[str, Any]:
        """
        Comprehensive gap analysis for a user.
        
        Returns:
        - gaps: List of identified learning gaps
        - recommendations: Suggested tutorials to generate
        - priority_actions: Immediate actions to take
        """
        try:
            gaps = []
            recommendations = []
            
            # 1. Analyze quiz failures
            quiz_gaps = self._analyze_quiz_failures(user_id)
            gaps.extend(quiz_gaps)
            
            # 2. Analyze skill matrix
            skill_gaps = self._analyze_skill_matrix(user_id)
            gaps.extend(skill_gaps)
            
            # 3. Analyze campaign performance (if available)
            campaign_gaps = self._analyze_campaign_correlation(user_id)
            gaps.extend(campaign_gaps)
            
            # 4. Deduplicate and prioritize
            prioritized_gaps = self._prioritize_gaps(gaps)
            
            # 5. Generate recommendations
            for gap in prioritized_gaps[:5]:  # Top 5 gaps
                rec = self._create_recommendation(gap, user_id)
                if rec:
                    recommendations.append(rec)
            
            # 6. Determine priority actions
            priority_actions = self._determine_priority_actions(prioritized_gaps)
            
            return {
                "user_id": user_id,
                "gaps": prioritized_gaps,
                "gap_count": len(prioritized_gaps),
                "recommendations": recommendations,
                "priority_actions": priority_actions,
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Gap analysis failed for {user_id}: {e}")
            return {"error": str(e), "user_id": user_id}

    def _analyze_quiz_failures(self, user_id: str) -> List[Dict]:
        """Analyze quiz results to find failure patterns."""
        gaps = []
        
        if not self.db:
            return gaps
        
        try:
            tutorials = self.db.collection('users').document(user_id).collection('tutorials').stream()
            
            for t_doc in tutorials:
                t_data = t_doc.to_dict()
                if not t_data.get('is_completed'):
                    continue
                
                quiz_results = t_data.get('quiz_results', [])
                for qr in quiz_results:
                    score = qr.get('score', 100)
                    
                    if score < 60:
                        # Critical failure
                        gaps.append({
                            "gap_id": str(uuid.uuid4()),
                            "type": "quiz_failure",
                            "topic": qr.get('section_title', t_data.get('title', 'Unknown')),
                            "source_tutorial_id": t_doc.id,
                            "source_tutorial_title": t_data.get('title'),
                            "severity": self.SEVERITY["CRITICAL"] if score < 40 else self.SEVERITY["HIGH"],
                            "evidence": f"Score: {score}% (below 60% threshold)",
                            "score": score,
                            "trigger_type": self.TRIGGER_TYPES["quiz_failure"],
                            "auto_approve": True  # Remediation is auto-approved
                        })
                    elif score < 75:
                        # Below passing
                        gaps.append({
                            "gap_id": str(uuid.uuid4()),
                            "type": "quiz_failure",
                            "topic": qr.get('section_title', t_data.get('title', 'Unknown')),
                            "source_tutorial_id": t_doc.id,
                            "source_tutorial_title": t_data.get('title'),
                            "severity": self.SEVERITY["MEDIUM"],
                            "evidence": f"Score: {score}% (below 75% passing threshold)",
                            "score": score,
                            "trigger_type": self.TRIGGER_TYPES["quiz_failure"],
                            "auto_approve": True
                        })
        except Exception as e:
            logger.warning(f"Quiz failure analysis error: {e}")
        
        return gaps

    def _analyze_skill_matrix(self, user_id: str) -> List[Dict]:
        """Analyze skill matrix to find underdeveloped areas."""
        gaps = []
        
        if not self.db:
            return gaps
        
        try:
            user_doc = self.db.collection('users').document(user_id).get()
            if not user_doc.exists:
                return gaps
            
            user_data = user_doc.to_dict()
            profile = user_data.get('profile', {})
            skills = profile.get('marketing_skills', {})
            
            # Check for NOVICE skills that should be developed
            for category, level in skills.items():
                if level == "NOVICE":
                    gaps.append({
                        "gap_id": str(uuid.uuid4()),
                        "type": "skill_gap",
                        "topic": f"{category.replace('_', ' ').title()} Fundamentals",
                        "source_tutorial_id": None,
                        "source_tutorial_title": None,
                        "severity": self.SEVERITY["MEDIUM"],
                        "evidence": f"Skill level: NOVICE in {category}",
                        "current_level": level,
                        "trigger_type": self.TRIGGER_TYPES["skill_gap"],
                        "auto_approve": False  # Skill gaps need admin approval
                    })
                    
        except Exception as e:
            logger.warning(f"Skill matrix analysis error: {e}")
        
        return gaps

    def _analyze_campaign_correlation(self, user_id: str) -> List[Dict]:
        """Analyze campaign performance to suggest relevant tutorials."""
        gaps = []
        
        if not self.db:
            return gaps
        
        try:
            # Get recent campaign performance
            campaigns = list(
                self.db.collection('users').document(user_id)
                .collection('campaign_performance')
                .order_by('date', direction='DESCENDING')
                .limit(10)
                .stream()
            )
            
            if not campaigns:
                return gaps
            
            # Analyze for poor performance patterns
            low_ctr_count = 0
            high_cpc_count = 0
            
            for c_doc in campaigns:
                c_data = c_doc.to_dict()
                ctr = c_data.get('ctr', 0)
                cpc = c_data.get('cpc', 0)
                
                if ctr < 1.0:  # Low CTR
                    low_ctr_count += 1
                if cpc > 2.0:  # High CPC
                    high_cpc_count += 1
            
            # Suggest tutorials based on patterns
            if low_ctr_count >= 3:
                gaps.append({
                    "gap_id": str(uuid.uuid4()),
                    "type": "performance_decline",
                    "topic": "Creative Optimization for Higher CTR",
                    "source_tutorial_id": None,
                    "source_tutorial_title": None,
                    "severity": self.SEVERITY["HIGH"],
                    "evidence": f"Low CTR detected in {low_ctr_count} of last 10 campaigns",
                    "trigger_type": self.TRIGGER_TYPES["performance_decline"],
                    "auto_approve": False
                })
            
            if high_cpc_count >= 3:
                gaps.append({
                    "gap_id": str(uuid.uuid4()),
                    "type": "performance_decline",
                    "topic": "Budget Optimization and Bid Strategy",
                    "source_tutorial_id": None,
                    "source_tutorial_title": None,
                    "severity": self.SEVERITY["HIGH"],
                    "evidence": f"High CPC detected in {high_cpc_count} of last 10 campaigns",
                    "trigger_type": self.TRIGGER_TYPES["performance_decline"],
                    "auto_approve": False
                })
                
        except Exception as e:
            logger.warning(f"Campaign correlation analysis error: {e}")
        
        return gaps

    def _prioritize_gaps(self, gaps: List[Dict]) -> List[Dict]:
        """Deduplicate and prioritize gaps by severity."""
        # Deduplicate by topic (keep highest severity)
        topic_map = {}
        for gap in gaps:
            topic = gap.get("topic", "")
            if topic not in topic_map or gap.get("severity", 0) > topic_map[topic].get("severity", 0):
                topic_map[topic] = gap
        
        # Sort by severity (highest first)
        prioritized = sorted(topic_map.values(), key=lambda x: x.get("severity", 0), reverse=True)
        
        # Add priority rank
        for i, gap in enumerate(prioritized):
            gap["priority_rank"] = i + 1
        
        return prioritized

    def _create_recommendation(self, gap: Dict, user_id: str) -> Optional[Dict]:
        """Create a tutorial recommendation from a gap."""
        try:
            return {
                "recommendation_id": str(uuid.uuid4()),
                "user_id": user_id,
                "topic": gap.get("topic"),
                "trigger_reason": gap.get("trigger_type"),
                "priority": gap.get("severity", 5),
                "source_gap_id": gap.get("gap_id"),
                "source_tutorial_id": gap.get("source_tutorial_id"),
                "source_quiz_score": gap.get("score"),
                "evidence": gap.get("evidence"),
                "auto_approve": gap.get("auto_approve", False),
                "approval_status": "auto_approved" if gap.get("auto_approve") else "pending",
                "created_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.warning(f"Failed to create recommendation: {e}")
            return None

    def _determine_priority_actions(self, gaps: List[Dict]) -> List[str]:
        """Determine priority actions based on gaps."""
        actions = []
        
        critical_count = len([g for g in gaps if g.get("severity", 0) >= self.SEVERITY["CRITICAL"]])
        high_count = len([g for g in gaps if g.get("severity", 0) >= self.SEVERITY["HIGH"]])
        
        if critical_count > 0:
            actions.append(f"🚨 {critical_count} critical gap(s) require immediate remediation")
        
        if high_count > 2:
            actions.append(f"⚠️ Multiple high-priority gaps detected - consider structured learning path")
        
        # Check for quiz failure patterns
        quiz_failures = [g for g in gaps if g.get("type") == "quiz_failure"]
        if len(quiz_failures) >= 3:
            actions.append("📚 Pattern of quiz failures suggests need for foundational review")
        
        # Check for campaign performance issues
        campaign_gaps = [g for g in gaps if g.get("type") == "performance_decline"]
        if campaign_gaps:
            actions.append("📈 Campaign performance issues correlate with knowledge gaps")
        
        return actions


# Singleton instance
_gap_agent: Optional[GapAnalyzerAgent] = None


def get_gap_analyzer() -> GapAnalyzerAgent:
    """Get or create singleton GapAnalyzerAgent."""
    global _gap_agent
    if _gap_agent is None:
        _gap_agent = GapAnalyzerAgent()
    return _gap_agent

"""
Performance Analyzer Agent
Analyzes user learning performance for the Adaptive Tutorial Engine (ATE).

Provides:
1. Comprehensive user performance metrics
2. Trend analysis (improving/declining)
3. Comparison with cohort averages
4. Academic performance scoring
5. Audit trail for admin visibility
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class PerformanceLevel(str, Enum):
    """User performance classification levels."""
    STRUGGLING = "struggling"      # Needs immediate intervention
    BELOW_AVERAGE = "below_average"
    AVERAGE = "average"
    ABOVE_AVERAGE = "above_average"
    EXCELLING = "excelling"        # May benefit from advanced content


class TutorialTriggerType(str, Enum):
    """Reasons for tutorial generation - used for audit trail."""
    USER_REQUESTED = "user_requested"
    QUIZ_FAILURE_REMEDIATION = "quiz_failure_remediation"
    SKILL_GAP_DETECTED = "skill_gap_detected"
    PERFORMANCE_DECLINE = "performance_decline"
    PERFORMANCE_EXCELLENCE = "performance_excellence"
    NEW_CHANNEL_ONBOARDING = "new_channel_onboarding"
    ADMIN_ASSIGNED = "admin_assigned"
    SCHEDULED_CURRICULUM = "scheduled_curriculum"


class PerformanceAnalyzerAgent:
    """
    Analyzes user learning performance and generates actionable insights.
    Provides data for both user-facing recommendations and admin dashboards.
    """

    # Performance thresholds
    THRESHOLDS = {
        "struggling": 50,           # Score below this = struggling
        "below_average": 65,        # Score below this = below average
        "average": 80,              # Score below this = average
        "above_average": 90,        # Score below this = above average
        # Above 90 = excelling
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

    def analyze_user_performance(
        self, 
        user_id: str,
        include_trend: bool = True,
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive user performance analysis.
        
        Returns detailed metrics for both user and admin dashboards.
        """
        try:
            if not self.db:
                return {"error": "Database not available"}

            # Fetch user data
            user_doc = self.db.collection('users').document(user_id).get()
            user_data = user_doc.to_dict() if user_doc.exists else {}
            profile = user_data.get('profile', {})

            # Get all tutorials
            tutorials_ref = self.db.collection('users').document(user_id).collection('tutorials')
            tutorials = list(tutorials_ref.stream())

            # Calculate metrics
            metrics = self._calculate_metrics(tutorials)
            
            # Determine performance level
            performance_level = self._classify_performance(metrics["overall_score"])
            
            # Calculate trend if requested
            trend = None
            if include_trend:
                trend = self._calculate_trend(tutorials)

            # Generate recommendations if requested
            recommendations = None
            triggers = []
            if include_recommendations:
                recommendations, triggers = self._generate_recommendations(
                    metrics, performance_level, profile
                )

            return {
                "user_id": user_id,
                "email": user_data.get("email"),
                "display_name": profile.get("displayName", user_data.get("displayName")),
                
                # Academic Performance
                "performance_level": performance_level,
                "overall_score": metrics["overall_score"],
                "quiz_pass_rate": metrics["quiz_pass_rate"],
                "average_quiz_score": metrics["average_score"],
                
                # Tutorial Progress
                "tutorials_completed": metrics["completed_count"],
                "tutorials_in_progress": metrics["in_progress_count"],
                "total_time_spent_minutes": metrics["total_time_spent"],
                
                # Skill Levels
                "skill_levels": profile.get("marketing_skills", {}),
                "learning_style": profile.get("learning_style", "VISUAL"),
                
                # Detailed Breakdown
                "section_struggles": metrics["struggles"][:10],
                "remediation_count": metrics["remediation_count"],
                "weak_areas": metrics["weak_areas"],
                "strong_areas": metrics["strong_areas"],
                
                # Trend
                "trend": trend,
                
                # Recommendations (for automatic tutorial generation)
                "recommendations": recommendations,
                "triggered_actions": triggers,
                
                # Audit Info
                "analyzed_at": datetime.utcnow().isoformat(),
                "analysis_version": "1.0"
            }

        except Exception as e:
            logger.error(f"❌ Performance analysis failed for {user_id}: {e}")
            return {"error": str(e), "user_id": user_id}

    def _calculate_metrics(self, tutorials: List) -> Dict[str, Any]:
        """Calculate performance metrics from tutorial data."""
        completed = []
        in_progress = []
        all_scores = []
        struggles = []
        topic_scores = {}
        remediation_count = 0
        total_time = 0

        for t_doc in tutorials:
            t_data = t_doc.to_dict()
            
            if t_data.get('is_completed'):
                completed.append(t_data)
                score = t_data.get('completion_score', 0)
                all_scores.append(score)
                
                # Track by category
                category = t_data.get('category', 'general')
                if category not in topic_scores:
                    topic_scores[category] = []
                topic_scores[category].append(score)
                
                # Track time spent
                total_time += t_data.get('time_spent_minutes', 0)
                
                # Analyze quiz results for struggles
                for qr in t_data.get('quiz_results', []):
                    qr_score = qr.get('score', 100)
                    if qr_score < 60:
                        struggles.append({
                            "tutorial_id": t_doc.id,
                            "tutorial_title": t_data.get('title'),
                            "section": qr.get('section_title', 'Unknown'),
                            "score": qr_score,
                            "failed_at": t_data.get('completedAt')
                        })
            else:
                in_progress.append(t_data)
            
            remediation_count += t_data.get('remediation_count', 0)

        # Calculate aggregates
        quiz_pass_rate = len([s for s in all_scores if s >= 75]) / max(len(all_scores), 1)
        average_score = sum(all_scores) / max(len(all_scores), 1)

        # Identify weak/strong areas
        weak_areas = []
        strong_areas = []
        for topic, scores in topic_scores.items():
            avg = sum(scores) / len(scores) if scores else 0
            if avg < 70:
                weak_areas.append({"category": topic, "average_score": round(avg, 1)})
            elif avg >= 85:
                strong_areas.append({"category": topic, "average_score": round(avg, 1)})

        # Calculate overall score
        overall = (
            quiz_pass_rate * 40 +
            (average_score / 100) * 40 +
            min(len(completed) / 10, 1) * 10 +
            (1 - min(remediation_count / 10, 1)) * 10
        ) * 100

        return {
            "completed_count": len(completed),
            "in_progress_count": len(in_progress),
            "quiz_pass_rate": round(quiz_pass_rate, 2),
            "average_score": round(average_score, 1),
            "overall_score": round(overall, 1),
            "struggles": struggles,
            "weak_areas": weak_areas,
            "strong_areas": strong_areas,
            "remediation_count": remediation_count,
            "total_time_spent": total_time
        }

    def _classify_performance(self, overall_score: float) -> str:
        """Classify user performance level."""
        if overall_score < self.THRESHOLDS["struggling"]:
            return PerformanceLevel.STRUGGLING
        elif overall_score < self.THRESHOLDS["below_average"]:
            return PerformanceLevel.BELOW_AVERAGE
        elif overall_score < self.THRESHOLDS["average"]:
            return PerformanceLevel.AVERAGE
        elif overall_score < self.THRESHOLDS["above_average"]:
            return PerformanceLevel.ABOVE_AVERAGE
        else:
            return PerformanceLevel.EXCELLING

    def _calculate_trend(self, tutorials: List) -> Dict[str, Any]:
        """Calculate performance trend over time."""
        completed = [t.to_dict() for t in tutorials if t.to_dict().get('is_completed')]
        
        if len(completed) < 3:
            return {"direction": "insufficient_data", "change": 0}

        # Sort by completion date
        try:
            sorted_tutorials = sorted(
                completed,
                key=lambda x: x.get('completedAt', datetime.min) if x.get('completedAt') else datetime.min
            )
        except:
            sorted_tutorials = completed

        # Compare first half vs second half
        mid = len(sorted_tutorials) // 2
        first_half_scores = [t.get('completion_score', 0) for t in sorted_tutorials[:mid]]
        second_half_scores = [t.get('completion_score', 0) for t in sorted_tutorials[mid:]]

        first_avg = sum(first_half_scores) / len(first_half_scores) if first_half_scores else 0
        second_avg = sum(second_half_scores) / len(second_half_scores) if second_half_scores else 0

        change = second_avg - first_avg

        if change > 5:
            direction = "improving"
        elif change < -5:
            direction = "declining"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "change": round(change, 1),
            "early_average": round(first_avg, 1),
            "recent_average": round(second_avg, 1)
        }

    def _generate_recommendations(
        self, 
        metrics: Dict[str, Any],
        performance_level: str,
        profile: Dict[str, Any]
    ) -> tuple:
        """Generate recommendations and identify tutorial triggers."""
        recommendations = []
        triggers = []

        # Struggling user - needs remediation
        if performance_level == PerformanceLevel.STRUGGLING:
            for struggle in metrics["struggles"][:3]:
                triggers.append({
                    "type": TutorialTriggerType.QUIZ_FAILURE_REMEDIATION,
                    "topic": struggle["section"],
                    "reason": f"Score {struggle['score']}% on quiz",
                    "priority": 9,
                    "auto_approve": True
                })
            recommendations.append("Generate remedial tutorials for failed sections")

        # Below average - skill gaps
        elif performance_level == PerformanceLevel.BELOW_AVERAGE:
            for weak in metrics["weak_areas"][:2]:
                triggers.append({
                    "type": TutorialTriggerType.SKILL_GAP_DETECTED,
                    "topic": weak["category"],
                    "reason": f"Low average ({weak['average_score']}%) in category",
                    "priority": 7,
                    "auto_approve": False
                })
            recommendations.append("Consider additional practice tutorials for weak areas")

        # Excelling - advanced content
        elif performance_level == PerformanceLevel.EXCELLING:
            for strong in metrics["strong_areas"][:2]:
                triggers.append({
                    "type": TutorialTriggerType.PERFORMANCE_EXCELLENCE,
                    "topic": f"Advanced {strong['category']}",
                    "reason": f"Excelling ({strong['average_score']}%) - ready for advanced content",
                    "priority": 5,
                    "auto_approve": False
                })
            recommendations.append("User ready for advanced tutorials")

        return recommendations, triggers

    def get_all_users_summary(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        ADMIN: Get performance summary for all users.
        Used for admin dashboard overview.
        """
        if not self.db:
            return []

        try:
            users = list(self.db.collection('users').limit(limit).stream())
            summaries = []

            for user_doc in users:
                user_id = user_doc.id
                user_data = user_doc.to_dict()
                
                # Quick tutorial count
                tutorials = list(
                    self.db.collection('users').document(user_id)
                    .collection('tutorials').limit(100).stream()
                )
                
                completed = len([t for t in tutorials if t.to_dict().get('is_completed')])
                in_progress = len(tutorials) - completed
                
                # Get last activity
                profile = user_data.get('profile', {})
                
                summaries.append({
                    "user_id": user_id,
                    "email": user_data.get("email", ""),
                    "display_name": profile.get("displayName", user_data.get("displayName", "Unknown")),
                    "tutorials_completed": completed,
                    "tutorials_in_progress": in_progress,
                    "skill_level": profile.get("marketing_knowledge", "NOVICE"),
                    "last_updated": user_data.get("last_updated")
                })

            return summaries

        except Exception as e:
            logger.error(f"❌ Failed to get users summary: {e}")
            return []

    def get_tutorial_generation_audit(
        self, 
        user_id: Optional[str] = None, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        ADMIN: Get audit trail of tutorial generations.
        Shows who generated what, why, and when.
        """
        if not self.db:
            return []

        try:
            query = self.db.collection('tutorial_requests')
            
            if user_id:
                query = query.where('userId', '==', user_id)
            
            requests = list(query.order_by('createdAt', direction='DESCENDING').limit(100).stream())
            
            audit_trail = []
            for req in requests:
                req_data = req.to_dict()
                
                # Determine trigger type
                source = req_data.get('source', 'user_requested')
                if source == 'adaptive_tutorial_engine':
                    trigger_type = TutorialTriggerType.SKILL_GAP_DETECTED
                elif source == 'remediation':
                    trigger_type = TutorialTriggerType.QUIZ_FAILURE_REMEDIATION
                elif source == 'admin':
                    trigger_type = TutorialTriggerType.ADMIN_ASSIGNED
                else:
                    trigger_type = TutorialTriggerType.USER_REQUESTED

                audit_trail.append({
                    "request_id": req.id,
                    "user_id": req_data.get('userId'),
                    "topic": req_data.get('topic'),
                    "trigger_type": trigger_type,
                    "source": source,
                    "status": req_data.get('status'),
                    "context": req_data.get('context', ''),
                    "recommendation_id": req_data.get('recommendation_id'),
                    "created_at": req_data.get('createdAt'),
                    "approved_by": req_data.get('approvedBy'),
                    "generated_tutorial_id": req_data.get('generatedTutorialId')
                })

            return audit_trail

        except Exception as e:
            logger.error(f"❌ Failed to get audit trail: {e}")
            return []


# Singleton instance
_performance_agent: Optional[PerformanceAnalyzerAgent] = None


def get_performance_analyzer() -> PerformanceAnalyzerAgent:
    """Get or create singleton PerformanceAnalyzerAgent."""
    global _performance_agent
    if _performance_agent is None:
        _performance_agent = PerformanceAnalyzerAgent()
    return _performance_agent

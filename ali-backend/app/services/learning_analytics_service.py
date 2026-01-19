"""
Learning Analytics Service
Provides analytics collection, analysis, and recommendation generation
for the Adaptive Tutorial Engine (ATE).

Features:
1. Event collection from frontend interactions
2. Performance analysis across tutorials and sections
3. Learning gap detection and prioritization
4. Tutorial recommendation generation with approval workflow
"""
import logging
import uuid
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LearningAnalyticsService:
    """
    Service for learning analytics and adaptive tutorial recommendations.
    Integrates with BigQuery for storage and Firestore for real-time data.
    """

    def __init__(self, db=None, bq_service=None):
        """
        Initialize with Firestore and BigQuery clients.
        Both are lazy-loaded if not provided.
        """
        self._db = db
        self._bq_service = bq_service

    @property
    def db(self):
        """Lazy-load Firestore client."""
        if self._db is None:
            try:
                from app.core.security import db
                self._db = db
            except Exception as e:
                logger.error(f"❌ Failed to load Firestore: {e}")
        return self._db

    @property
    def bq(self):
        """Lazy-load BigQuery service."""
        if self._bq_service is None:
            try:
                from app.services.bigquery_service import get_bigquery_service
                self._bq_service = get_bigquery_service()
            except Exception as e:
                logger.error(f"❌ Failed to load BigQuery service: {e}")
        return self._bq_service

    # --- EVENT LOGGING ---

    def log_learning_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Log a learning event to BigQuery.
        
        Args:
            event_data: Dictionary containing event details
                - user_id: Required
                - event_type: Required (section_start, quiz_attempt, etc.)
                - tutorial_id: Optional
                - section_index: Optional
                - Additional metrics...
        
        Returns:
            True if logged successfully
        """
        if not event_data.get("user_id") or not event_data.get("event_type"):
            logger.warning("⚠️ Missing required fields for learning event")
            return False

        # Generate event ID if not provided
        event_data.setdefault("event_id", str(uuid.uuid4()))
        event_data.setdefault("created_at", datetime.utcnow().isoformat())

        # Log to BigQuery
        if self.bq:
            return self.bq._insert_to_table("learning_analytics_log", event_data, "created_at")

        logger.warning("⚠️ BigQuery not available, event not logged")
        return False

    def log_learning_events_batch(self, events: List[Dict[str, Any]]) -> int:
        """Log multiple learning events. Returns count of successful inserts."""
        if not self.bq or not self.bq.client:
            return 0

        # Prepare events
        for event in events:
            event.setdefault("event_id", str(uuid.uuid4()))
            event.setdefault("created_at", datetime.utcnow().isoformat())

        try:
            table_ref = self.bq._get_table_ref("learning_analytics_log")
            errors = self.bq.client.insert_rows_json(table_ref, events)
            if errors:
                logger.error(f"❌ Batch insert errors: {errors}")
                return len(events) - len(errors)
            return len(events)
        except Exception as e:
            logger.error(f"❌ Failed to batch insert learning events: {e}")
            return 0

    # --- PERFORMANCE ANALYSIS ---

    def get_user_performance_summary(
        self, 
        user_id: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive performance summary for a user.
        
        Returns:
            {
                "quiz_pass_rate": float,
                "average_score": float,
                "tutorials_completed": int,
                "tutorials_in_progress": int,
                "section_struggle_count": int,
                "remediation_count": int,
                "weak_areas": List[str],
                "strong_areas": List[str],
                "skill_levels": Dict[str, str],
                "overall_score": float
            }
        """
        if not self.db:
            return {"error": "Database not available"}

        try:
            # Fetch user's tutorials from private collection
            tutorials_ref = self.db.collection('users').document(user_id).collection('tutorials')
            tutorials = list(tutorials_ref.stream())

            # Analyze performance
            completed = []
            in_progress = []
            all_quiz_scores = []
            section_struggles = []
            remediation_count = 0
            topic_scores = {}  # topic -> list of scores

            for t_doc in tutorials:
                t_data = t_doc.to_dict()
                
                if t_data.get('is_completed'):
                    completed.append(t_data)
                    score = t_data.get('completion_score', 0)
                    all_quiz_scores.append(score)
                    
                    # Track by topic/category
                    category = t_data.get('category', 'general')
                    if category not in topic_scores:
                        topic_scores[category] = []
                    topic_scores[category].append(score)
                    
                    # Check quiz results for struggles
                    for qr in t_data.get('quiz_results', []):
                        qr_score = qr.get('score', 100)
                        if qr_score < 60:
                            section_struggles.append({
                                "tutorial": t_data.get('title'),
                                "section": qr.get('section_title', 'Unknown'),
                                "score": qr_score
                            })
                else:
                    in_progress.append(t_data)
                
                # Count remediations
                remediation_count += t_data.get('remediation_count', 0)

            # Calculate aggregates
            quiz_pass_rate = len([s for s in all_quiz_scores if s >= 75]) / max(len(all_quiz_scores), 1)
            average_score = sum(all_quiz_scores) / max(len(all_quiz_scores), 1)

            # Identify weak/strong areas by category
            weak_areas = []
            strong_areas = []
            for topic, scores in topic_scores.items():
                avg = sum(scores) / len(scores) if scores else 0
                if avg < 70:
                    weak_areas.append(topic)
                elif avg >= 85:
                    strong_areas.append(topic)

            # Get skill levels from profile
            user_doc = self.db.collection('users').document(user_id).get()
            user_data = user_doc.to_dict() if user_doc.exists else {}
            skill_levels = user_data.get('profile', {}).get('marketing_skills', {})

            # Calculate overall performance score (0-100)
            overall = (
                quiz_pass_rate * 30 +           # 30% weight on pass rate
                (average_score / 100) * 30 +    # 30% weight on average score
                min(len(completed) / 10, 1) * 20 +  # 20% on completion count (cap at 10)
                (1 - min(len(section_struggles) / 10, 1)) * 20  # 20% inverse of struggles
            ) * 100

            return {
                "quiz_pass_rate": round(quiz_pass_rate, 2),
                "average_score": round(average_score, 1),
                "tutorials_completed": len(completed),
                "tutorials_in_progress": len(in_progress),
                "section_struggle_count": len(section_struggles),
                "section_struggles": section_struggles[:10],  # Top 10
                "remediation_count": remediation_count,
                "weak_areas": weak_areas,
                "strong_areas": strong_areas,
                "skill_levels": skill_levels,
                "overall_score": round(overall, 1)
            }

        except Exception as e:
            logger.error(f"❌ Performance analysis failed: {e}")
            return {"error": str(e)}

    # --- LEARNING GAP DETECTION ---

    def detect_learning_gaps(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Analyze user performance to detect learning gaps.
        
        Returns list of gaps with priority and suggested actions.
        """
        performance = self.get_user_performance_summary(user_id)
        
        if "error" in performance:
            return []

        gaps = []

        # Gap 1: Section struggles (score < 60%)
        for struggle in performance.get("section_struggles", []):
            gap = {
                "gap_id": str(uuid.uuid4()),
                "user_id": user_id,
                "topic": struggle.get("section", "Unknown"),
                "source_tutorial": struggle.get("tutorial"),
                "severity": 10 - (struggle.get("score", 0) / 10),  # Lower score = higher severity
                "evidence": [f"Score {struggle.get('score')}% in quiz"],
                "suggested_tutorial_type": "deep_dive",
                "priority": 8 if struggle.get("score", 0) < 50 else 6,
                "trigger_reason": "quiz_failure_remediation",
                "created_at": datetime.utcnow().isoformat()
            }
            gaps.append(gap)

        # Gap 2: Weak skill areas
        for weak_area in performance.get("weak_areas", []):
            gap = {
                "gap_id": str(uuid.uuid4()),
                "user_id": user_id,
                "topic": weak_area,
                "source_tutorial": None,
                "severity": 7,
                "evidence": ["Low average score in category"],
                "suggested_tutorial_type": "practice",
                "priority": 5,
                "trigger_reason": "skill_gap_detected",
                "created_at": datetime.utcnow().isoformat()
            }
            gaps.append(gap)

        # Gap 3: High remediation count indicates persistent issues
        if performance.get("remediation_count", 0) >= 3:
            # Find common topic from struggles
            topics = [s.get("section", "") for s in performance.get("section_struggles", [])]
            common_topic = max(set(topics), key=topics.count) if topics else "Core Concepts"
            
            gap = {
                "gap_id": str(uuid.uuid4()),
                "user_id": user_id,
                "topic": f"Fundamentals: {common_topic}",
                "source_tutorial": None,
                "severity": 8,
                "evidence": [f"{performance.get('remediation_count')} remediation requests"],
                "suggested_tutorial_type": "review",
                "priority": 7,
                "trigger_reason": "quiz_failure_remediation",
                "created_at": datetime.utcnow().isoformat()
            }
            gaps.append(gap)

        # Sort by priority
        gaps.sort(key=lambda x: x["priority"], reverse=True)

        # Log gaps to BigQuery
        for gap in gaps:
            gap["status"] = "open"
            if self.bq:
                self.bq._insert_to_table("learning_gaps", gap, "created_at")

        return gaps

    # --- TUTORIAL RECOMMENDATIONS ---

    def generate_recommendations(
        self, 
        user_id: str, 
        max_count: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate tutorial recommendations based on detected gaps.
        
        Remediation-triggered recommendations are auto-approved.
        New topic recommendations require admin approval.
        """
        gaps = self.detect_learning_gaps(user_id)
        recommendations = []

        for gap in gaps[:max_count]:
            trigger = gap.get("trigger_reason", "skill_gap_detected")
            
            # Auto-approve remediation, require approval for others
            auto_approve = trigger == "quiz_failure_remediation"
            
            rec = {
                "recommendation_id": str(uuid.uuid4()),
                "user_id": user_id,
                "topic": gap.get("topic"),
                "trigger_reason": trigger,
                "priority": gap.get("priority", 5),
                "source_gap_id": gap.get("gap_id"),
                "source_tutorial_id": gap.get("source_tutorial"),
                "source_quiz_score": None,
                "suggested_complexity": gap.get("severity", 5),
                "suggested_duration_minutes": 15 if gap.get("suggested_tutorial_type") == "review" else 30,
                "prerequisites": [],
                "approval_status": "auto_approved" if auto_approve else "pending",
                "requires_admin_approval": not auto_approve,
                "created_at": datetime.utcnow().isoformat()
            }
            recommendations.append(rec)

            # Log to BigQuery
            if self.bq:
                self.bq._insert_to_table("tutorial_recommendations", rec, "created_at")

            # Create admin task for non-auto-approved
            if not auto_approve and self.db:
                try:
                    from google.cloud import firestore
                    self.db.collection('admin_tasks').add({
                        "type": "tutorial_recommendation_review",
                        "recommendation_id": rec["recommendation_id"],
                        "user_id": user_id,
                        "topic": rec["topic"],
                        "trigger_reason": trigger,
                        "priority": rec["priority"],
                        "status": "pending",
                        "created_at": firestore.SERVER_TIMESTAMP
                    })
                except Exception as e:
                    logger.warning(f"Failed to create admin task: {e}")

        return recommendations

    def get_pending_recommendations(self, user_id: str = None) -> List[Dict[str, Any]]:
        """
        Get pending tutorial recommendations.
        
        Args:
            user_id: If provided, filter by user. Otherwise get all pending.
        """
        if not self.bq or not self.bq.client:
            return []

        query = f"""
        SELECT *
        FROM `{self.bq._get_table_ref('tutorial_recommendations')}`
        WHERE approval_status = 'pending'
        {'AND user_id = @user_id' if user_id else ''}
        ORDER BY priority DESC, created_at DESC
        LIMIT 50
        """

        params = []
        if user_id:
            from google.cloud import bigquery
            params.append(bigquery.ScalarQueryParameter("user_id", "STRING", user_id))

        try:
            job_config = None
            if params:
                from google.cloud import bigquery
                job_config = bigquery.QueryJobConfig(query_parameters=params)
            
            results = self.bq.client.query(query, job_config=job_config)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"❌ Failed to query recommendations: {e}")
            return []


# --- SINGLETON INSTANCE ---

_learning_analytics_service: Optional[LearningAnalyticsService] = None


def get_learning_analytics_service() -> LearningAnalyticsService:
    """Get or create singleton LearningAnalyticsService instance."""
    global _learning_analytics_service
    if _learning_analytics_service is None:
        _learning_analytics_service = LearningAnalyticsService()
    return _learning_analytics_service

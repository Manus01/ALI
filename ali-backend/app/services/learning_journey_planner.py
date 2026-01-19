"""
Learning Journey Planner
Plans and manages progressive learning journeys for users.

Features:
1. Dynamic path generation based on gaps and goals
2. Prerequisite-aware sequencing
3. Progress tracking
4. Adaptive recalculation as user completes tutorials
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class LearningJourneyPlanner:
    """
    Plans and manages learning journeys for users.
    Creates personalized learning paths based on gaps, goals, and prerequisites.
    """

    # Journey types
    JOURNEY_TYPES = {
        "remediation": "gap-based",      # Fixing identified gaps
        "skill_building": "progressive",  # Building new skills
        "certification": "structured",    # Following a defined path
        "exploration": "flexible"         # User-directed learning
    }

    # Maximum nodes in a single journey
    MAX_JOURNEY_NODES = 10

    def __init__(self, db=None):
        """Initialize with optional Firestore client."""
        self._db = db
        self._gap_analyzer = None
        self._complexity_analyzer = None

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
    def gap_analyzer(self):
        if self._gap_analyzer is None:
            try:
                from app.agents.gap_analyzer_agent import get_gap_analyzer
                self._gap_analyzer = get_gap_analyzer()
            except Exception:
                pass
        return self._gap_analyzer

    @property
    def complexity_analyzer(self):
        if self._complexity_analyzer is None:
            try:
                from app.agents.complexity_analyzer_agent import get_complexity_analyzer
                self._complexity_analyzer = get_complexity_analyzer()
            except Exception:
                pass
        return self._complexity_analyzer

    def generate_journey(
        self,
        user_id: str,
        journey_type: str = "remediation",
        target_skill: Optional[str] = None,
        max_nodes: int = 5
    ) -> Dict[str, Any]:
        """
        Generate a personalized learning journey for the user.
        
        Args:
            user_id: User to create journey for
            journey_type: Type of journey (remediation, skill_building, etc)
            target_skill: Target skill area (for skill_building)
            max_nodes: Maximum number of nodes in journey
            
        Returns:
            Journey object with ordered nodes
        """
        try:
            journey_id = str(uuid.uuid4())
            nodes = []

            if journey_type == "remediation":
                nodes = self._generate_remediation_journey(user_id, max_nodes)
            elif journey_type == "skill_building":
                nodes = self._generate_skill_journey(user_id, target_skill, max_nodes)
            else:
                nodes = self._generate_general_journey(user_id, max_nodes)

            # Build journey object
            journey = {
                "journey_id": journey_id,
                "user_id": user_id,
                "journey_type": journey_type,
                "target_skill": target_skill,
                "status": "active",
                "nodes": nodes,
                "total_nodes": len(nodes),
                "completed_nodes": 0,
                "current_node_index": 0,
                "created_at": datetime.utcnow().isoformat(),
                "estimated_completion_hours": self._estimate_completion_time(nodes)
            }

            # Persist to Firestore
            if self.db:
                self.db.collection("users").document(user_id).collection(
                    "learning_journeys"
                ).document(journey_id).set(journey)
                
                logger.info(f"🗺️ Created journey {journey_id} for {user_id} ({len(nodes)} nodes)")

            return journey

        except Exception as e:
            logger.error(f"❌ Journey generation failed: {e}")
            return {"error": str(e), "user_id": user_id}

    def _generate_remediation_journey(self, user_id: str, max_nodes: int) -> List[Dict]:
        """Generate journey based on identified learning gaps."""
        nodes = []

        if not self.gap_analyzer:
            return nodes

        try:
            # Get gaps from analyzer
            gap_analysis = self.gap_analyzer.analyze_user_gaps(user_id)
            gaps = gap_analysis.get("gaps", [])

            # Convert gaps to journey nodes
            for i, gap in enumerate(gaps[:max_nodes]):
                node = {
                    "node_id": str(uuid.uuid4()),
                    "order": i + 1,
                    "topic": gap.get("topic"),
                    "type": "tutorial",
                    "source": "gap_analysis",
                    "gap_id": gap.get("gap_id"),
                    "priority": gap.get("severity", 5),
                    "status": "pending",
                    "prerequisites": [],
                    "estimated_duration_minutes": 30
                }
                
                # Add prerequisites based on complexity analysis
                if self.complexity_analyzer:
                    analysis = self.complexity_analyzer.analyze_topic_complexity(gap.get("topic", ""))
                    node["prerequisites"] = analysis.get("prerequisites", [])[:3]
                    node["complexity"] = analysis.get("complexity_score", 5)
                
                nodes.append(node)

            # Sort by priority (highest first) and add ordering
            nodes.sort(key=lambda x: x.get("priority", 0), reverse=True)
            for i, node in enumerate(nodes):
                node["order"] = i + 1

            return nodes

        except Exception as e:
            logger.warning(f"Remediation journey generation error: {e}")
            return []

    def _generate_skill_journey(
        self, 
        user_id: str, 
        target_skill: Optional[str], 
        max_nodes: int
    ) -> List[Dict]:
        """Generate journey to build a specific skill."""
        nodes = []

        if not target_skill:
            return []

        # Skill progression paths (simplified)
        SKILL_PATHS = {
            "content_creation": [
                "Content Strategy Fundamentals",
                "Writing Compelling Copy",
                "Visual Content Basics",
                "Content Calendar Management",
                "Advanced Content Optimization"
            ],
            "paid_advertising": [
                "Introduction to Paid Ads",
                "Audience Targeting Strategies",
                "Ad Creative Best Practices",
                "Budget Optimization",
                "Advanced Campaign Analytics"
            ],
            "social_media": [
                "Social Media Fundamentals",
                "Platform-Specific Strategies",
                "Community Building",
                "Social Media Analytics",
                "Influencer Collaboration"
            ],
            "analytics": [
                "Marketing Analytics Basics",
                "Understanding Key Metrics",
                "Data-Driven Decision Making",
                "Attribution Modeling",
                "Advanced Analytics Tools"
            ]
        }

        path = SKILL_PATHS.get(target_skill.lower(), [])
        
        # Get user's completed tutorials to skip already-covered topics
        completed_topics = self._get_completed_topics(user_id)

        for i, topic in enumerate(path[:max_nodes]):
            # Skip if already completed
            if any(topic.lower() in ct.lower() or ct.lower() in topic.lower() 
                   for ct in completed_topics):
                continue

            nodes.append({
                "node_id": str(uuid.uuid4()),
                "order": len(nodes) + 1,
                "topic": topic,
                "type": "tutorial",
                "source": "skill_path",
                "skill_area": target_skill,
                "status": "pending",
                "prerequisites": [path[i-1]] if i > 0 else [],
                "estimated_duration_minutes": 30 + (i * 5)  # Progressive difficulty
            })

        return nodes

    def _generate_general_journey(self, user_id: str, max_nodes: int) -> List[Dict]:
        """Generate a general learning journey based on user profile."""
        nodes = []

        if not self.db:
            return nodes

        try:
            # Get user profile for skill gaps
            user_doc = self.db.collection("users").document(user_id).get()
            if not user_doc.exists:
                return []

            user_data = user_doc.to_dict()
            profile = user_data.get("profile", {})
            skills = profile.get("marketing_skills", {})

            # Find weakest skill areas
            weak_skills = [
                skill for skill, level in skills.items()
                if level in ["NOVICE", "BEGINNER"]
            ]

            # Generate a node for each weak skill
            for i, skill in enumerate(weak_skills[:max_nodes]):
                nodes.append({
                    "node_id": str(uuid.uuid4()),
                    "order": i + 1,
                    "topic": f"{skill.replace('_', ' ').title()} Fundamentals",
                    "type": "tutorial",
                    "source": "profile_analysis",
                    "skill_area": skill,
                    "status": "pending",
                    "prerequisites": [],
                    "estimated_duration_minutes": 30
                })

            return nodes

        except Exception as e:
            logger.warning(f"General journey generation error: {e}")
            return []

    def _get_completed_topics(self, user_id: str) -> List[str]:
        """Get list of topics user has completed tutorials for."""
        if not self.db:
            return []

        try:
            tutorials = self.db.collection("users").document(user_id).collection(
                "tutorials"
            ).where("is_completed", "==", True).stream()

            topics = []
            for t in tutorials:
                t_data = t.to_dict()
                if t_data.get("topic"):
                    topics.append(t_data["topic"])
                if t_data.get("title"):
                    topics.append(t_data["title"])

            return topics

        except Exception:
            return []

    def _estimate_completion_time(self, nodes: List[Dict]) -> float:
        """Estimate total hours to complete journey."""
        total_minutes = sum(
            node.get("estimated_duration_minutes", 30) 
            for node in nodes
        )
        return round(total_minutes / 60, 1)

    def get_active_journey(self, user_id: str) -> Optional[Dict]:
        """Get user's current active journey."""
        if not self.db:
            return None

        try:
            journeys = list(
                self.db.collection("users").document(user_id).collection(
                    "learning_journeys"
                ).where("status", "==", "active").limit(1).stream()
            )

            if journeys:
                journey = journeys[0].to_dict()
                journey["journey_id"] = journeys[0].id
                return journey

            return None

        except Exception as e:
            logger.error(f"❌ Get active journey failed: {e}")
            return None

    def get_next_node(self, user_id: str) -> Optional[Dict]:
        """Get the next node in the user's active journey."""
        journey = self.get_active_journey(user_id)
        if not journey:
            return None

        nodes = journey.get("nodes", [])
        current_index = journey.get("current_node_index", 0)

        if current_index < len(nodes):
            return nodes[current_index]

        return None

    def complete_node(
        self, 
        user_id: str, 
        journey_id: str, 
        node_id: str,
        score: Optional[float] = None
    ) -> Dict[str, Any]:
        """Mark a journey node as completed."""
        if not self.db:
            return {"error": "Database not available"}

        try:
            ref = self.db.collection("users").document(user_id).collection(
                "learning_journeys"
            ).document(journey_id)

            doc = ref.get()
            if not doc.exists:
                return {"error": "Journey not found"}

            journey = doc.to_dict()
            nodes = journey.get("nodes", [])

            # Find and update the node
            node_found = False
            for node in nodes:
                if node.get("node_id") == node_id:
                    node["status"] = "completed"
                    node["completed_at"] = datetime.utcnow().isoformat()
                    node["score"] = score
                    node_found = True
                    break

            if not node_found:
                return {"error": "Node not found in journey"}

            # Update journey progress
            completed_count = sum(1 for n in nodes if n.get("status") == "completed")
            current_index = min(completed_count, len(nodes) - 1)

            # Check if journey is complete
            journey_complete = completed_count >= len(nodes)

            ref.update({
                "nodes": nodes,
                "completed_nodes": completed_count,
                "current_node_index": current_index,
                "status": "completed" if journey_complete else "active",
                "completed_at": datetime.utcnow().isoformat() if journey_complete else None
            })

            # Get next node if available
            next_node = None
            if not journey_complete and current_index < len(nodes):
                next_node = nodes[current_index]

            return {
                "status": "success",
                "journey_complete": journey_complete,
                "progress": f"{completed_count}/{len(nodes)}",
                "next_node": next_node
            }

        except Exception as e:
            logger.error(f"❌ Complete node failed: {e}")
            return {"error": str(e)}

    def recalculate_journey(self, user_id: str, journey_id: str) -> Dict[str, Any]:
        """Recalculate journey based on updated user performance."""
        if not self.db:
            return {"error": "Database not available"}

        try:
            ref = self.db.collection("users").document(user_id).collection(
                "learning_journeys"
            ).document(journey_id)

            doc = ref.get()
            if not doc.exists:
                return {"error": "Journey not found"}

            journey = doc.to_dict()
            journey_type = journey.get("journey_type", "remediation")

            # Only recalculate for remediation journeys
            if journey_type == "remediation" and self.gap_analyzer:
                # Get fresh gaps
                gap_analysis = self.gap_analyzer.analyze_user_gaps(user_id)
                new_gaps = gap_analysis.get("gaps", [])

                # Keep completed nodes, replace pending with new gaps
                nodes = journey.get("nodes", [])
                completed = [n for n in nodes if n.get("status") == "completed"]
                
                # Generate new nodes from gaps
                new_nodes = []
                for gap in new_gaps[:self.MAX_JOURNEY_NODES - len(completed)]:
                    # Skip if already in completed
                    if any(c.get("topic") == gap.get("topic") for c in completed):
                        continue
                    
                    new_nodes.append({
                        "node_id": str(uuid.uuid4()),
                        "order": len(completed) + len(new_nodes) + 1,
                        "topic": gap.get("topic"),
                        "type": "tutorial",
                        "source": "gap_recalculation",
                        "gap_id": gap.get("gap_id"),
                        "priority": gap.get("severity", 5),
                        "status": "pending",
                        "prerequisites": [],
                        "estimated_duration_minutes": 30
                    })

                # Combine completed + new
                updated_nodes = completed + new_nodes

                # Update journey
                ref.update({
                    "nodes": updated_nodes,
                    "total_nodes": len(updated_nodes),
                    "recalculated_at": datetime.utcnow().isoformat()
                })

                return {
                    "status": "success",
                    "message": f"Journey updated with {len(new_nodes)} new nodes",
                    "total_nodes": len(updated_nodes)
                }

            return {"status": "no_change", "message": "Journey type does not support recalculation"}

        except Exception as e:
            logger.error(f"❌ Recalculate journey failed: {e}")
            return {"error": str(e)}


# Singleton instance
_journey_planner: Optional[LearningJourneyPlanner] = None


def get_journey_planner() -> LearningJourneyPlanner:
    """Get or create singleton LearningJourneyPlanner."""
    global _journey_planner
    if _journey_planner is None:
        _journey_planner = LearningJourneyPlanner()
    return _journey_planner

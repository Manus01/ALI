"""
Saga Map Service
Spec v2.2 §4.3: CourseManifest hierarchy for structured learning paths.

Provides:
1. CRUD operations for Courses and Modules
2. Progress calculation and tracking
3. Unlock condition evaluation
4. Default Course/Module management for migration
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SagaMapService:
    """
    Service for managing Course/Module hierarchy (Saga Map).
    Spec v2.2 §4.3: Enables structured learning paths with prerequisites.
    """
    
    def __init__(self, db=None):
        """
        Initialize with Firestore client.
        
        Args:
            db: Firestore client instance. If None, will be imported at runtime.
        """
        self._db = db
    
    @property
    def db(self):
        """Lazy-load Firestore client."""
        if self._db is None:
            try:
                from app.core.security import db as firestore_db
                self._db = firestore_db
            except ImportError:
                logger.error("❌ Failed to import Firestore client")
                raise RuntimeError("Database not available")
        return self._db
    
    # --- COURSE OPERATIONS ---
    
    def create_course(
        self,
        tenant_id: str,
        title: str,
        description: str = "",
        created_by: str = "system",
        course_id: Optional[str] = None,
        status: str = "DRAFT"
    ) -> Dict[str, Any]:
        """
        Create a new course.
        
        Args:
            tenant_id: Tenant identifier for multi-tenant support
            title: Course title
            description: Course description
            created_by: UID of the admin creating the course
            course_id: Optional explicit ID (for default course)
            status: Initial status (DRAFT, PUBLISHED)
            
        Returns:
            Created course document as dict
        """
        from app.types.course_manifest import Course, CourseStatus
        
        now = datetime.utcnow()
        
        # Generate ID if not provided
        if course_id:
            doc_ref = self.db.collection("courses").document(course_id)
        else:
            doc_ref = self.db.collection("courses").document()
        
        course = Course(
            id=doc_ref.id,
            tenant_id=tenant_id,
            title=title,
            description=description,
            status=CourseStatus(status),
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        
        doc_ref.set(course.to_dict())
        logger.info(f"📚 Created course: {course.id} - '{title}'")
        
        return course.to_dict()
    
    def get_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get a course by ID."""
        doc = self.db.collection("courses").document(course_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    
    def list_courses(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List courses, optionally filtered by tenant and status.
        """
        query = self.db.collection("courses")
        
        if tenant_id:
            query = query.where("tenantId", "==", tenant_id)
        if status:
            query = query.where("status", "==", status)
        
        courses = []
        for doc in query.stream():
            data = doc.to_dict() or {}
            data.setdefault("id", doc.id)
            courses.append(data)
        return courses
    
    def update_course(self, course_id: str, updates: Dict[str, Any]) -> bool:
        """Update a course with the given fields."""
        updates["updatedAt"] = datetime.utcnow().isoformat()
        self.db.collection("courses").document(course_id).update(updates)
        logger.info(f"📚 Updated course: {course_id}")
        return True
    
    # --- MODULE OPERATIONS ---
    
    def create_module(
        self,
        course_id: str,
        title: str,
        description: str = "",
        sequence: int = 1,
        module_id: Optional[str] = None,
        unlock_conditions: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Create a new module within a course.
        
        Args:
            course_id: Parent course ID
            title: Module title
            description: Module description
            sequence: Order within course (1, 2, 3...)
            module_id: Optional explicit ID (for default module)
            unlock_conditions: List of unlock condition dicts
            
        Returns:
            Created module document as dict
        """
        from app.types.course_manifest import Module, UnlockConditionType
        
        now = datetime.utcnow()
        
        # Generate ID if not provided
        if module_id:
            doc_ref = self.db.collection("modules").document(module_id)
        else:
            doc_ref = self.db.collection("modules").document()
        
        # Default to ALWAYS_UNLOCKED if no conditions specified
        if unlock_conditions is None:
            unlock_conditions = [{
                "type": UnlockConditionType.ALWAYS_UNLOCKED.value,
                "prerequisiteModuleIds": None,
                "minimumScore": None,
                "unlockedBy": None,
                "unlockedAt": None,
            }]
        
        module = Module(
            id=doc_ref.id,
            course_id=course_id,
            title=title,
            description=description,
            sequence=sequence,
            unlock_conditions=unlock_conditions,
            created_at=now,
            updated_at=now,
        )
        
        doc_ref.set(module.to_dict())
        
        # Add module to course's moduleIds array
        self.db.collection("courses").document(course_id).update({
            "moduleIds": firestore_array_union([doc_ref.id]),
            "updatedAt": datetime.utcnow().isoformat(),
        })
        
        logger.info(f"📦 Created module: {module.id} - '{title}' in course {course_id}")
        
        return module.to_dict()
    
    def get_module(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Get a module by ID."""
        doc = self.db.collection("modules").document(module_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    
    def list_modules_for_course(self, course_id: str) -> List[Dict[str, Any]]:
        """List all modules in a course, ordered by sequence."""
        query = self.db.collection("modules").where("courseId", "==", course_id).order_by("sequence")
        modules = []
        for doc in query.stream():
            data = doc.to_dict() or {}
            data.setdefault("id", doc.id)
            modules.append(data)
        return modules
    
    def add_tutorial_to_module(self, module_id: str, tutorial_id: str) -> bool:
        """Add a tutorial to a module's tutorialIds array."""
        self.db.collection("modules").document(module_id).update({
            "tutorialIds": firestore_array_union([tutorial_id]),
            "updatedAt": datetime.utcnow().isoformat(),
        })
        logger.info(f"📝 Added tutorial {tutorial_id} to module {module_id}")
        return True
    
    def reorder_modules(self, course_id: str, module_ids: List[str]) -> bool:
        """
        Reorder modules in a course.
        
        Args:
            course_id: Course to update
            module_ids: List of module IDs in desired order
        """
        batch = self.db.batch()
        
        for seq, module_id in enumerate(module_ids, start=1):
            ref = self.db.collection("modules").document(module_id)
            batch.update(ref, {"sequence": seq, "updatedAt": datetime.utcnow().isoformat()})
        
        # Update course's moduleIds to match
        course_ref = self.db.collection("courses").document(course_id)
        batch.update(course_ref, {"moduleIds": module_ids, "updatedAt": datetime.utcnow().isoformat()})
        
        batch.commit()
        logger.info(f"🔄 Reordered {len(module_ids)} modules in course {course_id}")
        return True
    
    # --- PROGRESS TRACKING ---
    
    def calculate_module_progress(self, user_id: str, module_id: str) -> Dict[str, Any]:
        """
        Calculate a user's progress through a module.
        
        Returns:
            ProgressRecord dict with completion percentage
        """
        module = self.get_module(module_id)
        if not module:
            return {"error": "Module not found"}
        
        tutorial_ids = module.get("tutorialIds", [])
        if not tutorial_ids:
            return {
                "userId": user_id,
                "moduleId": module_id,
                "courseId": module.get("courseId"),
                "completedTutorialIds": [],
                "totalTutorials": 0,
                "percentComplete": 100.0,  # Empty module = complete
            }
        
        # Get user's completed tutorials
        user_doc = self.db.collection("users").document(user_id).get()
        completed_all = user_doc.to_dict().get("completed_tutorials", []) if user_doc.exists else []
        
        # Find which module tutorials are completed
        completed_in_module = [tid for tid in tutorial_ids if tid in completed_all]
        
        percent = (len(completed_in_module) / len(tutorial_ids)) * 100 if tutorial_ids else 100.0
        
        return {
            "userId": user_id,
            "moduleId": module_id,
            "courseId": module.get("courseId"),
            "completedTutorialIds": completed_in_module,
            "totalTutorials": len(tutorial_ids),
            "percentComplete": round(percent, 1),
            "lastActivityAt": datetime.utcnow().isoformat(),
        }
    
    def calculate_course_progress(self, user_id: str, course_id: str) -> Dict[str, Any]:
        """
        Calculate a user's overall progress through a course.
        """
        course = self.get_course(course_id)
        if not course:
            return {"error": "Course not found"}
        
        module_ids = course.get("moduleIds", [])
        if not module_ids:
            return {
                "userId": user_id,
                "courseId": course_id,
                "moduleId": None,
                "completedTutorialIds": [],
                "totalTutorials": 0,
                "percentComplete": 100.0,
            }
        
        # Aggregate progress across all modules
        all_completed = []
        total_tutorials = 0
        
        for mid in module_ids:
            module_progress = self.calculate_module_progress(user_id, mid)
            all_completed.extend(module_progress.get("completedTutorialIds", []))
            total_tutorials += module_progress.get("totalTutorials", 0)
        
        percent = (len(all_completed) / total_tutorials) * 100 if total_tutorials else 100.0
        
        return {
            "userId": user_id,
            "courseId": course_id,
            "moduleId": None,
            "completedTutorialIds": all_completed,
            "totalTutorials": total_tutorials,
            "percentComplete": round(percent, 1),
        }
    
    # --- UNLOCK CONDITION EVALUATION ---
    
    def check_unlock_conditions(self, user_id: str, module_id: str) -> Dict[str, Any]:
        """
        Check if a module is unlocked for a user.
        
        Returns:
            UnlockStatus dict with isUnlocked and reason
        """
        from app.types.course_manifest import UnlockConditionType
        
        module = self.get_module(module_id)
        if not module:
            return {
                "moduleId": module_id,
                "isUnlocked": False,
                "reason": "Module not found",
                "unmetConditions": [],
            }
        
        conditions = module.get("unlockConditions", [])
        
        # If no conditions, it's unlocked
        if not conditions:
            return {
                "moduleId": module_id,
                "isUnlocked": True,
                "reason": "No unlock conditions",
                "unmetConditions": [],
            }
        
        unmet = []
        
        for cond in conditions:
            cond_type = cond.get("type", "")
            
            if cond_type == UnlockConditionType.ALWAYS_UNLOCKED.value:
                # Always passes
                continue
            
            elif cond_type == UnlockConditionType.PREREQUISITE_COMPLETE.value:
                prereq_ids = cond.get("prerequisiteModuleIds", [])
                for prereq_id in prereq_ids:
                    progress = self.calculate_module_progress(user_id, prereq_id)
                    if progress.get("percentComplete", 0) < 100:
                        prereq_module = self.get_module(prereq_id)
                        prereq_title = prereq_module.get("title", prereq_id) if prereq_module else prereq_id
                        unmet.append(f"Complete module '{prereq_title}' first")
            
            elif cond_type == UnlockConditionType.SCORE_THRESHOLD.value:
                min_score = cond.get("minimumScore", 0)
                # Get user's average score across prerequisite modules
                # For now, check if user has achieved the score on any related module
                prereq_ids = cond.get("prerequisiteModuleIds", [])
                passed = False
                for prereq_id in prereq_ids:
                    progress = self.calculate_module_progress(user_id, prereq_id)
                    avg_score = progress.get("averageScore")
                    if avg_score and avg_score >= min_score:
                        passed = True
                        break
                if not passed and prereq_ids:
                    unmet.append(f"Achieve {min_score}% average score on prerequisites")
            
            elif cond_type == UnlockConditionType.MANUAL_UNLOCK.value:
                # Check if admin has unlocked for this user
                unlocked_by = cond.get("unlockedBy")
                if not unlocked_by:
                    unmet.append("Awaiting admin unlock")
        
        is_unlocked = len(unmet) == 0
        reason = "All conditions met" if is_unlocked else "; ".join(unmet)
        
        return {
            "moduleId": module_id,
            "isUnlocked": is_unlocked,
            "reason": reason,
            "unmetConditions": unmet,
        }
    
    def is_module_unlocked(self, user_id: str, module_id: str) -> bool:
        """Simple boolean check for module unlock status."""
        status = self.check_unlock_conditions(user_id, module_id)
        return status.get("isUnlocked", False)
    
    # --- DEFAULT COURSE/MODULE MANAGEMENT ---
    
    def get_or_create_default_course(self, tenant_id: str = "default") -> Dict[str, Any]:
        """
        Get or create the default "General" course for orphan tutorials.
        Used by migration script.
        """
        from app.types.course_manifest import (
            DEFAULT_COURSE_ID, 
            DEFAULT_COURSE_TITLE, 
            DEFAULT_COURSE_DESCRIPTION
        )
        
        existing = self.get_course(DEFAULT_COURSE_ID)
        if existing:
            return existing
        
        return self.create_course(
            tenant_id=tenant_id,
            title=DEFAULT_COURSE_TITLE,
            description=DEFAULT_COURSE_DESCRIPTION,
            created_by="migration_script",
            course_id=DEFAULT_COURSE_ID,
            status="PUBLISHED"
        )
    
    def get_or_create_default_module(self, course_id: str = None) -> Dict[str, Any]:
        """
        Get or create the default "Uncategorized" module.
        Used by migration script.
        """
        from app.types.course_manifest import (
            DEFAULT_COURSE_ID,
            DEFAULT_MODULE_ID,
            DEFAULT_MODULE_TITLE,
            DEFAULT_MODULE_DESCRIPTION
        )
        
        if course_id is None:
            course_id = DEFAULT_COURSE_ID
        
        existing = self.get_module(DEFAULT_MODULE_ID)
        if existing:
            return existing
        
        return self.create_module(
            course_id=course_id,
            title=DEFAULT_MODULE_TITLE,
            description=DEFAULT_MODULE_DESCRIPTION,
            sequence=1,
            module_id=DEFAULT_MODULE_ID,
            unlock_conditions=None  # Always unlocked
        )


# Helper function for Firestore array operations
def firestore_array_union(values: List[Any]):
    """Wrapper for Firestore ArrayUnion."""
    try:
        from firebase_admin import firestore
        return firestore.ArrayUnion(values)
    except ImportError:
        # Fallback for testing
        return values


# --- SINGLETON INSTANCE ---
_saga_map_service: Optional[SagaMapService] = None


def get_saga_map_service() -> SagaMapService:
    """Get or create singleton SagaMapService instance."""
    global _saga_map_service
    if _saga_map_service is None:
        _saga_map_service = SagaMapService()
    return _saga_map_service

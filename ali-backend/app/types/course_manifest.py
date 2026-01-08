"""
ALI Enterprise Application - Course Manifest Types
Implements Saga Map / CourseManifest hierarchy per Spec v2.2 §4.3

Provides:
1. CourseManifest - Top-level learning path container
2. ModuleManifest - Ordered sequence of tutorials with unlock conditions
3. UnlockCondition - Prerequisites and gating logic
4. ProgressRecord - User progress tracking
"""
from enum import Enum
from typing import TypedDict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime


class CourseStatus(str, Enum):
    """Lifecycle states for courses."""
    DRAFT = "DRAFT"           # Being built, not visible to users
    PUBLISHED = "PUBLISHED"   # Active and available
    ARCHIVED = "ARCHIVED"     # No longer active, retained for history


class UnlockConditionType(str, Enum):
    """Types of conditions that gate module access."""
    ALWAYS_UNLOCKED = "ALWAYS_UNLOCKED"          # No prerequisites
    PREREQUISITE_COMPLETE = "PREREQUISITE_COMPLETE"  # Must complete specified module(s)
    SCORE_THRESHOLD = "SCORE_THRESHOLD"          # Must achieve minimum score
    MANUAL_UNLOCK = "MANUAL_UNLOCK"              # Admin manually unlocks


class UnlockCondition(TypedDict):
    """
    A single unlock condition for a module.
    Spec v2.2 §4.3: Modules can have prerequisites and unlock conditions.
    """
    type: str  # UnlockConditionType value
    prerequisiteModuleIds: Optional[List[str]]  # For PREREQUISITE_COMPLETE
    minimumScore: Optional[int]  # For SCORE_THRESHOLD (0-100)
    unlockedBy: Optional[str]  # Admin UID for MANUAL_UNLOCK
    unlockedAt: Optional[str]  # ISO timestamp for MANUAL_UNLOCK


class ModuleManifest(TypedDict):
    """
    A module is an ordered sequence of tutorials within a course.
    Spec v2.2 §4.3: Saga Map structure with sequence and prerequisites.
    """
    id: str
    courseId: str
    title: str
    description: Optional[str]
    sequence: int  # Order within course (1, 2, 3...)
    tutorialIds: List[str]  # Ordered list of tutorial IDs in this module
    unlockConditions: List[UnlockCondition]
    estimatedMinutes: Optional[int]  # Total time estimate
    createdAt: str  # ISO timestamp
    updatedAt: str  # ISO timestamp


class CourseManifest(TypedDict):
    """
    A course is a collection of modules forming a complete learning path.
    Spec v2.2 §4.3: Top-level container in the Saga Map hierarchy.
    """
    id: str
    tenantId: str  # Multi-tenant support
    title: str
    description: Optional[str]
    status: str  # CourseStatus value
    moduleIds: List[str]  # Ordered list of module IDs
    coverImageUrl: Optional[str]
    category: Optional[str]  # e.g., "paid_ads", "content", "analytics"
    difficulty: Optional[str]  # NOVICE, INTERMEDIATE, EXPERT
    estimatedHours: Optional[float]
    prerequisites: List[str]  # Other courseIds that should be completed first
    createdBy: str  # Admin UID
    createdAt: str  # ISO timestamp
    updatedAt: str  # ISO timestamp
    publishedAt: Optional[str]  # When it went live


class ProgressRecord(TypedDict):
    """
    Tracks a user's progress through a module or course.
    Stored per-user for granular progress tracking.
    """
    userId: str
    courseId: str
    moduleId: Optional[str]  # None for course-level progress
    completedTutorialIds: List[str]
    totalTutorials: int
    percentComplete: float  # 0.0 - 100.0
    averageScore: Optional[float]  # Weighted average of quiz scores
    startedAt: str  # ISO timestamp
    lastActivityAt: str  # ISO timestamp
    completedAt: Optional[str]  # Set when 100% complete


class UnlockStatus(TypedDict):
    """Result of evaluating unlock conditions for a module."""
    moduleId: str
    isUnlocked: bool
    reason: str  # Human-readable explanation
    unmetConditions: List[str]  # List of condition descriptions not yet met
    progressToUnlock: Optional[float]  # 0.0-100.0 progress toward unlock


# --- DEFAULT COURSE/MODULE CONSTANTS ---
# Used by migration script to assign orphan tutorials

DEFAULT_COURSE_ID = "course_general"
DEFAULT_COURSE_TITLE = "General"
DEFAULT_COURSE_DESCRIPTION = "General learning content not assigned to a specific course."

DEFAULT_MODULE_ID = "module_uncategorized"
DEFAULT_MODULE_TITLE = "Uncategorized"
DEFAULT_MODULE_DESCRIPTION = "Tutorials not yet assigned to a specific module."


# --- DATACLASS VERSIONS FOR INTERNAL USE ---
# These provide rich behavior for the service layer

@dataclass
class Course:
    """Mutable Course object for service-layer operations."""
    id: str
    tenant_id: str
    title: str
    status: CourseStatus = CourseStatus.DRAFT
    description: str = ""
    module_ids: List[str] = field(default_factory=list)
    cover_image_url: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    estimated_hours: Optional[float] = None
    prerequisites: List[str] = field(default_factory=list)
    created_by: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to Firestore-compatible dict."""
        return {
            "id": self.id,
            "tenantId": self.tenant_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "moduleIds": self.module_ids,
            "coverImageUrl": self.cover_image_url,
            "category": self.category,
            "difficulty": self.difficulty,
            "estimatedHours": self.estimated_hours,
            "prerequisites": self.prerequisites,
            "createdBy": self.created_by,
            "createdAt": self.created_at.isoformat() if self.created_at else datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat(),
            "publishedAt": self.published_at.isoformat() if self.published_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Course":
        """Create Course from Firestore dict."""
        return cls(
            id=data.get("id", ""),
            tenant_id=data.get("tenantId", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=CourseStatus(data.get("status", "DRAFT")),
            module_ids=data.get("moduleIds", []),
            cover_image_url=data.get("coverImageUrl"),
            category=data.get("category"),
            difficulty=data.get("difficulty"),
            estimated_hours=data.get("estimatedHours"),
            prerequisites=data.get("prerequisites", []),
            created_by=data.get("createdBy", ""),
        )


@dataclass
class Module:
    """Mutable Module object for service-layer operations."""
    id: str
    course_id: str
    title: str
    sequence: int = 1
    description: str = ""
    tutorial_ids: List[str] = field(default_factory=list)
    unlock_conditions: List[dict] = field(default_factory=list)
    estimated_minutes: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to Firestore-compatible dict."""
        return {
            "id": self.id,
            "courseId": self.course_id,
            "title": self.title,
            "description": self.description,
            "sequence": self.sequence,
            "tutorialIds": self.tutorial_ids,
            "unlockConditions": self.unlock_conditions,
            "estimatedMinutes": self.estimated_minutes,
            "createdAt": self.created_at.isoformat() if self.created_at else datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Module":
        """Create Module from Firestore dict."""
        return cls(
            id=data.get("id", ""),
            course_id=data.get("courseId", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            sequence=data.get("sequence", 1),
            tutorial_ids=data.get("tutorialIds", []),
            unlock_conditions=data.get("unlockConditions", []),
            estimated_minutes=data.get("estimatedMinutes"),
        )

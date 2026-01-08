"""ALI Types Package - Enterprise Architecture Type Definitions"""
from .tutorial_lifecycle import (
    TutorialStatus,
    TutorialRequestStatus,
    TutorialVersion,
    RubricScore,
    RubricReport,
    EvidenceBundle,
    TutorialMetadata,
    TutorialRequest
)

from .course_manifest import (
    CourseStatus,
    UnlockConditionType,
    UnlockCondition,
    ModuleManifest,
    CourseManifest,
    ProgressRecord,
    UnlockStatus,
    Course,
    Module,
    DEFAULT_COURSE_ID,
    DEFAULT_COURSE_TITLE,
    DEFAULT_MODULE_ID,
    DEFAULT_MODULE_TITLE,
)

__all__ = [
    # Tutorial Lifecycle
    "TutorialStatus",
    "TutorialRequestStatus", 
    "TutorialVersion",
    "RubricScore",
    "RubricReport",
    "EvidenceBundle",
    "TutorialMetadata",
    "TutorialRequest",
    # Course Manifest (Saga Map)
    "CourseStatus",
    "UnlockConditionType",
    "UnlockCondition",
    "ModuleManifest",
    "CourseManifest",
    "ProgressRecord",
    "UnlockStatus",
    "Course",
    "Module",
    "DEFAULT_COURSE_ID",
    "DEFAULT_COURSE_TITLE",
    "DEFAULT_MODULE_ID",
    "DEFAULT_MODULE_TITLE",
]

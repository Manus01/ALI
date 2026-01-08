"""
ALI Enterprise Application - Tutorial Lifecycle Types
Implements DRAFT → IN_REVIEW → PUBLISHED → ARCHIVED workflow per Spec v2.2 §7
"""
from enum import Enum
from typing import TypedDict, Optional, List, Any
from datetime import datetime


class TutorialStatus(str, Enum):
    """Lifecycle states for tutorial content."""
    DRAFT = "DRAFT"           # Generated + QC complete, not user-facing
    IN_REVIEW = "IN_REVIEW"   # Admin reviewing; may request regeneration
    PUBLISHED = "PUBLISHED"   # Available to learners; immutable version
    ARCHIVED = "ARCHIVED"     # Retained for audit/rollback; not active


class TutorialRequestStatus(str, Enum):
    """States for user tutorial requests."""
    PENDING = "PENDING"         # User submitted, awaiting admin
    APPROVED = "APPROVED"       # Admin approved, ready for generation
    DENIED = "DENIED"           # Admin denied the request
    GENERATING = "GENERATING"   # Generation in progress
    COMPLETED = "COMPLETED"     # Generation complete, tutorial created
    FAILED = "FAILED"           # Generation failed


class TutorialVersion(TypedDict):
    """Immutable version snapshot for rollback support."""
    versionId: str
    hash: str
    timestamp: str  # ISO format
    modelVersion: str
    publishedBy: Optional[str]


class RubricScore(TypedDict):
    """Individual rubric dimension score."""
    dimension: str
    score: int  # 0-100
    passed: bool
    issues: List[str]


class RubricReport(TypedDict):
    """Critic Agent rubric validation report."""
    verdict: str  # PASS or FAIL
    overallScore: int  # 0-100
    scores: List[RubricScore]
    citationCoverage: float  # 0.0-1.0
    cardWordCountViolations: int
    syntaxErrors: List[str]
    fixList: List[str]
    validatedAt: str


class EvidenceBundle(TypedDict):
    """Citation and source evidence for grounded content."""
    sources: List[dict]
    citations: List[dict]
    truthSourceJson: Optional[str]  # GCS path
    createdAt: str


class TutorialMetadata(TypedDict):
    """Full tutorial metadata with lifecycle support."""
    id: str
    title: str
    topic: str
    userId: str
    status: str  # TutorialStatus value
    versions: List[TutorialVersion]
    currentVersion: str
    rubricReport: Optional[RubricReport]
    evidenceBundle: Optional[EvidenceBundle]
    createdAt: str
    updatedAt: str
    publishedAt: Optional[str]


class TutorialRequest(TypedDict):
    """User's request for tutorial generation."""
    requestId: str
    userId: str
    userEmail: str
    topic: str
    context: Optional[str]
    status: str  # TutorialRequestStatus value
    createdAt: Any  # Firestore timestamp
    adminDecision: Optional[dict]
    tutorialId: Optional[str]  # Set after generation completes

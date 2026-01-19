"""
ALI Enterprise Application - Learning Analytics Types
Data models for the Adaptive Tutorial Engine (ATE) system.
Spec: AI-Driven Adaptive Tutorial Generation System v1.0
"""
from enum import Enum
from typing import TypedDict, Optional, List, Any, Dict
from datetime import datetime


class LearningEventType(str, Enum):
    """Types of learning events tracked for analytics."""
    SECTION_START = "section_start"
    SECTION_COMPLETE = "section_complete"
    QUIZ_ATTEMPT = "quiz_attempt"
    QUIZ_PASS = "quiz_pass"
    QUIZ_FAIL = "quiz_fail"
    REMEDIATION_REQUEST = "remediation_request"
    REMEDIATION_COMPLETE = "remediation_complete"
    TUTORIAL_START = "tutorial_start"
    TUTORIAL_COMPLETE = "tutorial_complete"
    AUDIO_PLAY = "audio_play"
    VIDEO_PLAY = "video_play"
    HELP_CLICK = "help_click"


class TutorialTriggerReason(str, Enum):
    """Reasons for auto-generating tutorials."""
    QUIZ_FAILURE_REMEDIATION = "quiz_failure_remediation"
    LOW_SCORE_DEEP_DIVE = "low_score_deep_dive"
    SKILL_GAP_DETECTED = "skill_gap_detected"
    NEW_CHANNEL_ONBOARDING = "new_channel_onboarding"
    PERFORMANCE_DECLINE = "performance_decline"
    COMPETITOR_ALERT = "competitor_alert"
    USER_REQUEST = "user_request"
    ADMIN_SCHEDULED = "admin_scheduled"


class ApprovalStatus(str, Enum):
    """Status for admin-gated tutorial generation."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"  # For remediation triggers


class LearningEvent(TypedDict):
    """A single learning analytics event."""
    event_id: str
    user_id: str
    tutorial_id: Optional[str]
    section_index: Optional[int]
    section_title: Optional[str]
    event_type: str  # LearningEventType value
    
    # Performance metrics
    time_spent_seconds: Optional[int]
    scroll_depth_percent: Optional[float]
    replay_count: Optional[int]
    quiz_score: Optional[float]
    
    # Context
    device_type: Optional[str]
    session_id: Optional[str]
    
    # Timestamps
    created_at: str  # ISO format


class ComplexityAnalysis(TypedDict):
    """Topic complexity assessment."""
    topic: str
    complexity_score: float  # 1-10
    prerequisite_count: int
    abstraction_level: float  # 1.0 = concrete, 10.0 = abstract
    estimated_duration_minutes: int
    failure_rate: Optional[float]  # Historical failure rate
    recommended_skill_level: str  # NOVICE, INTERMEDIATE, EXPERT
    analysis_confidence: float  # 0.0-1.0


class PerformanceAnalysis(TypedDict):
    """User performance assessment."""
    user_id: str
    analysis_period_days: int
    quiz_pass_rate: float
    average_score: float
    section_struggle_count: int
    remediation_requests: int
    completion_velocity: float  # Relative to average (1.0 = average)
    skill_progression: Dict[str, str]  # category -> level
    weak_areas: List[str]
    strong_areas: List[str]
    overall_performance_score: float  # 0-100


class LearningGap(TypedDict):
    """Identified gap in user's knowledge."""
    gap_id: str
    user_id: str
    topic: str
    severity: float  # 1-10 (10 = critical gap)
    evidence: List[str]  # Quiz IDs, section titles showing weakness
    suggested_tutorial_type: str  # "deep_dive", "practice", "review"
    priority: int  # 1-10
    created_at: str


class TutorialRecommendation(TypedDict):
    """Recommendation for tutorial generation."""
    recommendation_id: str
    user_id: str
    topic: str
    trigger_reason: str  # TutorialTriggerReason value
    priority: int  # 1-10 (10 = highest)
    
    # Source data
    source_gap_id: Optional[str]
    source_tutorial_id: Optional[str]
    source_quiz_score: Optional[float]
    
    # Generation config
    suggested_complexity: float
    suggested_duration_minutes: int
    prerequisites: List[str]
    
    # Approval
    approval_status: str  # ApprovalStatus value
    requires_admin_approval: bool
    
    # Timestamps
    created_at: str
    approved_at: Optional[str]
    generated_at: Optional[str]


class LearningJourneyNode(TypedDict):
    """A node in the learning journey map."""
    node_id: str
    tutorial_id: Optional[str]  # None if not yet generated
    title: str
    node_type: str  # "required", "optional", "remediation", "advanced"
    status: str  # "locked", "available", "in_progress", "completed"
    
    # Positioning
    sequence: int
    parent_node_id: Optional[str]
    
    # Requirements
    prerequisite_node_ids: List[str]
    unlock_conditions: List[Dict[str, Any]]
    
    # Progress
    completion_score: Optional[float]
    completed_at: Optional[str]


class LearningJourney(TypedDict):
    """Complete learning journey for a user."""
    journey_id: str
    user_id: str
    title: str
    description: str
    journey_type: str  # "remediation", "mastery", "quick_start", "channel_specific"
    
    # Structure
    nodes: List[LearningJourneyNode]
    total_nodes: int
    completed_nodes: int
    
    # Progress
    progress_percent: float
    estimated_completion_hours: float
    
    # Metadata
    created_at: str
    updated_at: str
    completed_at: Optional[str]

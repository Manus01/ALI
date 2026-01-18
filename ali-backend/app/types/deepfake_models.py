"""
Deepfake Analysis Models
Data models for async deepfake detection jobs and results.

Provides schemas for:
- DeepfakeAnalysis: Complete job record with lifecycle
- DeepfakeSignal: Individual detection indicators
- Request/Response models for API endpoints
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# =============================================================================
# ENUMS
# =============================================================================

class DeepfakeJobStatus(str, Enum):
    """Job lifecycle states."""
    QUEUED = "queued"        # Job accepted, waiting to process
    RUNNING = "running"      # Analysis in progress
    COMPLETED = "completed"  # Analysis finished successfully
    FAILED = "failed"        # Analysis failed (retryable or permanent)


class DeepfakeVerdict(str, Enum):
    """Human-readable verdict categories for non-technical users."""
    LIKELY_AUTHENTIC = "likely_authentic"      # Low manipulation probability
    INCONCLUSIVE = "inconclusive"              # Cannot determine with confidence
    LIKELY_MANIPULATED = "likely_manipulated"  # High manipulation probability
    CONFIRMED_SYNTHETIC = "confirmed_synthetic" # Definitive synthetic media


class MediaType(str, Enum):
    """Type of media analyzed."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"  # AI-generated text detection
    UNKNOWN = "unknown"


class SignalSeverity(str, Enum):
    """Severity levels for detection signals."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# SIGNAL SCHEMA
# =============================================================================

class DeepfakeSignal(BaseModel):
    """Individual signal/indicator from analysis."""
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    signal_type: str = Field(..., description="Type: 'keyword_match', 'face_swap', 'voice_clone', etc.")
    severity: SignalSeverity = Field(default=SignalSeverity.MEDIUM)
    description: str = Field(..., description="Human-readable explanation")
    technical_detail: Optional[str] = Field(None, description="Technical details for experts")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    class Config:
        use_enum_values = True


# =============================================================================
# MAIN ANALYSIS MODEL
# =============================================================================

class DeepfakeAnalysis(BaseModel):
    """
    Complete deepfake analysis job record.
    Linked to EvidenceItem and EvidenceSource for chain integration.
    """
    # === Identification ===
    id: str = Field(..., description="Unique job ID (e.g., DFA-XXXXXX)")
    user_id: str = Field(..., description="User who initiated the analysis")
    
    # === Media Reference ===
    media_ref: str = Field(..., description="URL or GCS path to analyzed media")
    media_type: MediaType = Field(default=MediaType.UNKNOWN)
    source_mention_id: Optional[str] = Field(None, description="Source mention ID if from mentions")
    
    # === Job Lifecycle ===
    status: DeepfakeJobStatus = Field(default=DeepfakeJobStatus.QUEUED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    priority: str = Field(default="normal", description="normal or high")
    
    # === Results (populated on completion) ===
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall confidence 0-1")
    verdict: Optional[DeepfakeVerdict] = None
    verdict_label: Optional[str] = Field(None, description="Human-readable verdict label")
    signals: List[DeepfakeSignal] = Field(default_factory=list)
    
    # === User-Facing Explanation ===
    user_explanation: Optional[str] = Field(None, description="Plain English explanation")
    recommended_action: Optional[str] = Field(None, description="What user should do next")
    
    # === Raw Output ===
    raw_output: Optional[Dict[str, Any]] = Field(None, description="Raw API response (for debugging)")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    
    # === Evidence Chain Integration ===
    attach_to_evidence: bool = Field(default=True, description="Auto-attach to evidence chain")
    report_item_id: Optional[str] = Field(None, description="Linked EvidenceItem ID if attached to report")
    evidence_source_id: Optional[str] = Field(None, description="Linked EvidenceSource ID")
    
    class Config:
        use_enum_values = True


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class DeepfakeCheckEnqueueRequest(BaseModel):
    """Request to enqueue deepfake analysis."""
    media_url: str = Field(..., description="URL of media to analyze")
    media_type: Optional[str] = Field(None, description="image/video/audio/text")
    mention_id: Optional[str] = Field(None, description="Source mention ID for linking")
    attach_to_evidence: bool = Field(default=True, description="Auto-attach to evidence chain")
    priority: str = Field(default="normal", description="normal or high (affects queue position)")


class DeepfakeCheckEnqueueResponse(BaseModel):
    """Response from enqueueing analysis job."""
    status: str = Field(default="success")
    job_id: str
    job_status: str = Field(default="queued")
    estimated_wait_seconds: int = Field(default=30)
    poll_url: str
    message: str = Field(default="Deepfake analysis job enqueued successfully")


class DeepfakeCheckStatusResponse(BaseModel):
    """Response from status polling."""
    status: str = Field(default="success")
    job_id: str
    job_status: str  # queued/running/completed/failed
    progress_pct: Optional[int] = Field(None, description="0-100 during running")
    
    # Populated on completion
    confidence: Optional[float] = None
    verdict: Optional[str] = None
    verdict_label: Optional[str] = None
    signals: Optional[List[Dict[str, Any]]] = None
    user_explanation: Optional[str] = None
    recommended_action: Optional[str] = None
    
    # Evidence linkage
    evidence_source_id: Optional[str] = None
    
    # Error info if failed
    error: Optional[str] = None
    retry_allowed: bool = Field(default=False)
    
    # Timestamps
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# =============================================================================
# VERDICT HELPERS
# =============================================================================

VERDICT_LABELS = {
    DeepfakeVerdict.LIKELY_AUTHENTIC: "✅ Likely Authentic",
    DeepfakeVerdict.INCONCLUSIVE: "⚪ Inconclusive",
    DeepfakeVerdict.LIKELY_MANIPULATED: "⚠️ Likely Manipulated",
    DeepfakeVerdict.CONFIRMED_SYNTHETIC: "🚨 Confirmed Synthetic"
}

VERDICT_EXPLANATIONS = {
    DeepfakeVerdict.LIKELY_AUTHENTIC: "No obvious manipulation indicators were detected in this media.",
    DeepfakeVerdict.INCONCLUSIVE: "We could not definitively determine if this media has been manipulated.",
    DeepfakeVerdict.LIKELY_MANIPULATED: "This media shows indicators of potential manipulation.",
    DeepfakeVerdict.CONFIRMED_SYNTHETIC: "This media appears to be AI-generated or heavily manipulated."
}

VERDICT_ACTIONS = {
    DeepfakeVerdict.LIKELY_AUTHENTIC: "No immediate action required, but continue monitoring.",
    DeepfakeVerdict.INCONCLUSIVE: "Use manual verification tools if this content is critical to your case.",
    DeepfakeVerdict.LIKELY_MANIPULATED: "Review the indicators and consider adding this to your evidence report.",
    DeepfakeVerdict.CONFIRMED_SYNTHETIC: "Flag this content immediately and include in your evidence report for legal action."
}


def get_verdict_from_score(risk_score: float) -> DeepfakeVerdict:
    """Map a risk score (0-10) to a verdict category."""
    if risk_score >= 8:
        return DeepfakeVerdict.CONFIRMED_SYNTHETIC
    elif risk_score >= 5:
        return DeepfakeVerdict.LIKELY_MANIPULATED
    elif risk_score >= 2:
        return DeepfakeVerdict.INCONCLUSIVE
    else:
        return DeepfakeVerdict.LIKELY_AUTHENTIC


def get_verdict_label(verdict: DeepfakeVerdict) -> str:
    """Get human-readable label for a verdict."""
    return VERDICT_LABELS.get(verdict, "⚪ Unknown")


def get_verdict_explanation(verdict: DeepfakeVerdict) -> str:
    """Get plain English explanation for a verdict."""
    return VERDICT_EXPLANATIONS.get(verdict, "Analysis complete.")


def get_verdict_action(verdict: DeepfakeVerdict) -> str:
    """Get recommended action for a verdict."""
    return VERDICT_ACTIONS.get(verdict, "Review the analysis results.")

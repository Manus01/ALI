"""
Adaptive Scanning Service
Threat scoring, policy engine, and adaptive scheduling for Brand Monitoring.
"""
import asyncio
import hashlib
import logging
import random
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

class ThreatLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


class ScanMode(str, Enum):
    ADAPTIVE = "adaptive"
    FIXED = "fixed"


class TriggerReason(str, Enum):
    ADAPTIVE_CRITICAL = "adaptive_critical"
    ADAPTIVE_HIGH = "adaptive_high"
    ADAPTIVE_MODERATE = "adaptive_moderate"
    ADAPTIVE_LOW = "adaptive_low"
    MANUAL = "manual"
    SCHEDULED_FIXED = "scheduled_fixed"
    QUIET_HOURS = "quiet_hours"


@dataclass
class ThresholdRule:
    """A single threshold rule for adaptive scanning."""
    min_score: int
    max_score: int
    interval_min: int  # minutes
    interval_max: int  # minutes
    label: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThresholdRule":
        return cls(**data)


@dataclass
class QuietHoursConfig:
    """Quiet hours configuration."""
    enabled: bool = False
    start: str = "22:00"  # HH:MM local time
    end: str = "07:00"
    interval_minutes: int = 360  # 6 hours
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuietHoursConfig":
        return cls(**data)


@dataclass
class ThreatBreakdown:
    """Breakdown of threat score components."""
    volume_delta: float = 0.0
    severity_mix: float = 0.0
    platform_risk: float = 0.0
    deepfake_flag: float = 0.0
    trend_24h: float = 0.0
    trend_7d: float = 0.0
    manual_priority: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "volumeDelta": self.volume_delta,
            "severityMix": self.severity_mix,
            "platformRisk": self.platform_risk,
            "deepfakeFlag": self.deepfake_flag,
            "trend24h": self.trend_24h,
            "trend7d": self.trend_7d,
            "manualPriority": self.manual_priority
        }


@dataclass
class ThreatAssessment:
    """Result of threat score calculation."""
    score: int
    label: ThreatLevel
    interval_ms: int
    reason: str
    breakdown: ThreatBreakdown
    calculated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "label": self.label.value,
            "interval_ms": self.interval_ms,
            "reason": self.reason,
            "breakdown": self.breakdown.to_dict(),
            "calculated_at": self.calculated_at.isoformat()
        }


@dataclass
class ScanPolicy:
    """Configuration for adaptive scanning behavior."""
    brand_id: str
    user_id: str
    mode: ScanMode = ScanMode.ADAPTIVE
    fixed_interval_ms: int = 3600000  # 1 hour default
    
    # Adaptive thresholds
    thresholds: List[ThresholdRule] = field(default_factory=lambda: [
        ThresholdRule(min_score=80, max_score=100, interval_min=5, interval_max=10, label="CRITICAL"),
        ThresholdRule(min_score=50, max_score=79, interval_min=30, interval_max=30, label="HIGH"),
        ThresholdRule(min_score=20, max_score=49, interval_min=60, interval_max=60, label="MODERATE"),
        ThresholdRule(min_score=0, max_score=19, interval_min=180, interval_max=360, label="LOW"),
    ])
    
    # Constraints
    min_interval_ms: int = 5 * 60 * 1000      # 5 minutes floor
    max_interval_ms: int = 6 * 60 * 60 * 1000  # 6 hours ceiling
    backoff_multiplier: float = 1.5
    backoff_max_consecutive: int = 3
    
    # Quiet hours
    quiet_hours: QuietHoursConfig = field(default_factory=QuietHoursConfig)
    
    # Manual priority
    manual_priority: str = "normal"  # "urgent" | "watch" | "normal"
    user_timezone: str = "UTC"
    
    # Current state (updated after each scan)
    last_scan_at: Optional[datetime] = None
    next_scan_at: Optional[datetime] = None
    current_threat_score: int = 0
    current_threat_label: str = "LOW"
    consecutive_low_scans: int = 0
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand_id": self.brand_id,
            "user_id": self.user_id,
            "mode": self.mode.value,
            "fixed_interval_ms": self.fixed_interval_ms,
            "thresholds": [t.to_dict() for t in self.thresholds],
            "min_interval_ms": self.min_interval_ms,
            "max_interval_ms": self.max_interval_ms,
            "backoff_multiplier": self.backoff_multiplier,
            "backoff_max_consecutive": self.backoff_max_consecutive,
            "quiet_hours": self.quiet_hours.to_dict(),
            "manual_priority": self.manual_priority,
            "user_timezone": self.user_timezone,
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
            "next_scan_at": self.next_scan_at.isoformat() if self.next_scan_at else None,
            "current_threat_score": self.current_threat_score,
            "current_threat_label": self.current_threat_label,
            "consecutive_low_scans": self.consecutive_low_scans,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanPolicy":
        """Create ScanPolicy from dictionary (e.g., Firestore document)."""
        thresholds = [ThresholdRule.from_dict(t) for t in data.get("thresholds", [])]
        quiet_hours = QuietHoursConfig.from_dict(data.get("quiet_hours", {}))
        
        return cls(
            brand_id=data.get("brand_id", ""),
            user_id=data.get("user_id", ""),
            mode=ScanMode(data.get("mode", "adaptive")),
            fixed_interval_ms=data.get("fixed_interval_ms", 3600000),
            thresholds=thresholds if thresholds else None,
            min_interval_ms=data.get("min_interval_ms", 5 * 60 * 1000),
            max_interval_ms=data.get("max_interval_ms", 6 * 60 * 60 * 1000),
            backoff_multiplier=data.get("backoff_multiplier", 1.5),
            backoff_max_consecutive=data.get("backoff_max_consecutive", 3),
            quiet_hours=quiet_hours,
            manual_priority=data.get("manual_priority", "normal"),
            user_timezone=data.get("user_timezone", "UTC"),
            last_scan_at=datetime.fromisoformat(data["last_scan_at"]) if data.get("last_scan_at") else None,
            next_scan_at=datetime.fromisoformat(data["next_scan_at"]) if data.get("next_scan_at") else None,
            current_threat_score=data.get("current_threat_score", 0),
            current_threat_label=data.get("current_threat_label", "LOW"),
            consecutive_low_scans=data.get("consecutive_low_scans", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow()
        )


@dataclass
class ScanJob:
    """Represents a scheduled scan job."""
    job_id: str
    brand_id: str
    user_id: str
    scheduled_for: datetime
    
    # Idempotency
    idempotency_key: str
    
    # "Why am I scanning now?" metadata
    trigger_reason: TriggerReason
    threat_assessment: Dict[str, Any]
    policy_snapshot: Dict[str, Any]
    
    # Execution tracking
    status: str = "pending"  # "pending" | "running" | "completed" | "failed"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "brand_id": self.brand_id,
            "user_id": self.user_id,
            "scheduled_for": self.scheduled_for.isoformat(),
            "idempotency_key": self.idempotency_key,
            "trigger_reason": self.trigger_reason.value,
            "threat_assessment": self.threat_assessment,
            "policy_snapshot": self.policy_snapshot,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_summary": self.result_summary,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ScanLog:
    """Detailed log of a scan execution."""
    log_id: str
    brand_id: str
    user_id: str
    
    # Job metadata
    job_id: str
    trigger_reason: str
    threat_score_at_schedule: int
    policy_mode: str
    
    # Execution metrics
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    status: str = "running"  # "running" | "success" | "failed"
    error_message: Optional[str] = None
    
    # Results
    mentions_found: int = 0
    new_mentions_logged: int = 0
    duplicates_skipped: int = 0
    opportunities_detected: int = 0
    competitor_mentions: int = 0
    
    # Post-scan assessment
    threat_score_post: Optional[int] = None
    threat_breakdown_post: Optional[Dict[str, float]] = None
    
    # Scheduling
    next_scan_scheduled_for: Optional[datetime] = None
    scan_interval_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "brand_id": self.brand_id,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "trigger_reason": self.trigger_reason,
            "threat_score_at_schedule": self.threat_score_at_schedule,
            "policy_mode": self.policy_mode,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_message": self.error_message,
            "mentions_found": self.mentions_found,
            "new_mentions_logged": self.new_mentions_logged,
            "duplicates_skipped": self.duplicates_skipped,
            "opportunities_detected": self.opportunities_detected,
            "competitor_mentions": self.competitor_mentions,
            "threat_score_post": self.threat_score_post,
            "threat_breakdown_post": self.threat_breakdown_post,
            "next_scan_scheduled_for": self.next_scan_scheduled_for.isoformat() if self.next_scan_scheduled_for else None,
            "scan_interval_ms": self.scan_interval_ms
        }


# =============================================================================
# THREAT SCORING ENGINE
# =============================================================================

class ThreatScoringEngine:
    """
    Calculates threat scores based on multiple signals.
    
    Weights:
    - mentionVolumeDelta: 20%
    - severityMix: 25%
    - platformRiskWeight: 10%
    - deepfakeFlag: 15%
    - trend24h: 10%
    - trend7d: 10%
    - manualPriority: 10%
    """
    
    PLATFORM_WEIGHTS = {
        "twitter": 1.5,
        "x": 1.5,
        "news": 1.2,
        "facebook": 1.1,
        "linkedin": 1.1,
        "instagram": 1.0,
        "blog": 1.0,
        "forum": 0.9,
        "other": 0.8
    }
    
    PRIORITY_SCORES = {
        "urgent": 10,
        "watch": 5,
        "normal": 0
    }
    
    async def calculate_threat_score(
        self,
        brand_id: str,
        user_id: str,
        policy: ScanPolicy,
        recent_mentions: Optional[List[Dict[str, Any]]] = None
    ) -> ThreatAssessment:
        """
        Calculate a 0-100 threat score and recommended scan interval.
        
        Args:
            brand_id: The brand to assess
            user_id: The user ID
            policy: Current scan policy
            recent_mentions: Optional list of recent mentions (if already fetched)
        
        Returns:
            ThreatAssessment with score, interval, and reason breakdown
        """
        # Fetch metrics if not provided
        if recent_mentions is None:
            recent_mentions = await self._fetch_recent_mentions(brand_id, user_id, hours=24)
        
        weekly_stats = await self._fetch_weekly_stats(brand_id, user_id)
        
        breakdown = ThreatBreakdown()
        
        # 1. Mention Volume Delta (0-20 points)
        current_count = len(recent_mentions)
        weekly_avg = weekly_stats.get("avg_daily_mentions", 0)
        
        if weekly_avg > 0:
            volume_delta = (current_count - weekly_avg) / weekly_avg
            breakdown.volume_delta = min(20, max(0, volume_delta * 50))
        else:
            # No baseline - use current count directly
            breakdown.volume_delta = min(20, current_count * 2)
        
        # 2. Severity Mix (0-25 points)
        if recent_mentions:
            avg_severity = sum(
                m.get("severity", 1) for m in recent_mentions if m.get("sentiment") == "negative"
            ) / max(len([m for m in recent_mentions if m.get("sentiment") == "negative"]), 1)
            breakdown.severity_mix = (avg_severity / 10) * 25
        
        # 3. Platform Risk (0-10 points)
        if recent_mentions:
            platform_scores = [
                self.PLATFORM_WEIGHTS.get(
                    m.get("source_type", "").lower(),
                    self.PLATFORM_WEIGHTS.get(m.get("source_platform", "").lower(), 1.0)
                )
                for m in recent_mentions
            ]
            avg_platform_weight = sum(platform_scores) / len(platform_scores)
            breakdown.platform_risk = min(10, (avg_platform_weight - 1.0) * 20)
        
        # 4. Deepfake Flag (0-15 points)
        has_deepfake = any(m.get("deepfake_detected", False) for m in recent_mentions)
        breakdown.deepfake_flag = 15 if has_deepfake else 0
        
        # 5. 24h Trend (0-10 points)
        trend_24h = await self._calculate_24h_trend(brand_id, user_id)
        breakdown.trend_24h = min(10, max(0, trend_24h * 20))
        
        # 6. 7-day Sentiment Trend (0-10 points)
        sentiment_trajectory = weekly_stats.get("sentiment_trajectory", 0)
        # Negative trajectory = worsening sentiment = higher risk
        breakdown.trend_7d = min(10, max(0, -sentiment_trajectory * 10))
        
        # 7. Manual Priority Boost (0-10 points)
        breakdown.manual_priority = self.PRIORITY_SCORES.get(policy.manual_priority, 0)
        
        # Aggregate score
        raw_score = (
            breakdown.volume_delta +
            breakdown.severity_mix +
            breakdown.platform_risk +
            breakdown.deepfake_flag +
            breakdown.trend_24h +
            breakdown.trend_7d +
            breakdown.manual_priority
        )
        threat_score = min(100, max(0, int(raw_score)))
        
        # Determine threat level
        threat_label = self._get_threat_label(threat_score)
        
        # Apply rules engine to get interval
        interval_ms, reason = self._apply_rules_engine(threat_score, policy)
        
        return ThreatAssessment(
            score=threat_score,
            label=threat_label,
            interval_ms=interval_ms,
            reason=reason,
            breakdown=breakdown,
            calculated_at=datetime.utcnow()
        )
    
    def _get_threat_label(self, score: int) -> ThreatLevel:
        """Map score to threat level."""
        if score >= 80:
            return ThreatLevel.CRITICAL
        elif score >= 50:
            return ThreatLevel.HIGH
        elif score >= 20:
            return ThreatLevel.MODERATE
        else:
            return ThreatLevel.LOW
    
    def _apply_rules_engine(self, threat_score: int, policy: ScanPolicy) -> Tuple[int, str]:
        """
        Apply policy rules to determine next scan interval.
        
        Returns:
            (interval_ms, reason_string)
        """
        # 1. Check for fixed mode
        if policy.mode == ScanMode.FIXED:
            return (policy.fixed_interval_ms, "Fixed schedule policy")
        
        # 2. Check quiet hours
        if policy.quiet_hours.enabled and self._is_quiet_hours(policy):
            return (
                policy.quiet_hours.interval_minutes * 60 * 1000,
                f"Quiet hours active ({policy.quiet_hours.start}-{policy.quiet_hours.end})"
            )
        
        # 3. Match threshold rules
        for rule in policy.thresholds:
            if rule.min_score <= threat_score <= rule.max_score:
                # Randomize within range for natural distribution
                interval_min_ms = rule.interval_min * 60 * 1000
                interval_max_ms = rule.interval_max * 60 * 1000
                interval = random.randint(interval_min_ms, interval_max_ms)
                
                # Apply backoff if consecutive low-threat scans
                if rule.label == "LOW" and policy.consecutive_low_scans > 0:
                    interval = self._apply_backoff(interval, policy)
                
                # Enforce global min/max
                interval = max(policy.min_interval_ms, min(interval, policy.max_interval_ms))
                
                return (interval, f"Threat level: {rule.label} (score: {threat_score})")
        
        # Fallback
        return (60 * 60 * 1000, "Default hourly (no matching rule)")
    
    def _apply_backoff(self, base_interval: int, policy: ScanPolicy) -> int:
        """Apply exponential backoff for consecutive calm periods."""
        consecutive = min(policy.consecutive_low_scans, policy.backoff_max_consecutive)
        
        if consecutive >= policy.backoff_max_consecutive:
            # Reset backoff after max consecutive
            return base_interval
        
        multiplier = policy.backoff_multiplier ** consecutive
        return int(base_interval * multiplier)
    
    def _is_quiet_hours(self, policy: ScanPolicy) -> bool:
        """Check if current time falls within quiet hours."""
        try:
            # Get current time in user's timezone (simplified - using UTC offset)
            now = datetime.utcnow()
            
            # Parse start and end times
            start_parts = policy.quiet_hours.start.split(":")
            end_parts = policy.quiet_hours.end.split(":")
            
            start_time = time(int(start_parts[0]), int(start_parts[1]))
            end_time = time(int(end_parts[0]), int(end_parts[1]))
            current_time = now.time()
            
            # Handle overnight ranges (22:00 - 07:00)
            if start_time > end_time:
                return current_time >= start_time or current_time < end_time
            else:
                return start_time <= current_time < end_time
        except Exception as e:
            logger.warning(f"Error checking quiet hours: {e}")
            return False
    
    async def _fetch_recent_mentions(
        self, 
        brand_id: str, 
        user_id: str, 
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Fetch recent mentions from BigQuery or Firestore."""
        try:
            from app.services.bigquery_service import get_bigquery_service
            
            bq = get_bigquery_service()
            if not bq.client:
                return []
            
            # Query recent mentions
            query = f"""
            SELECT 
                mention_id, sentiment, sentiment_score, severity,
                source_type, source_platform, detected_at
            FROM `{bq._get_table_ref('brand_mentions_log')}`
            WHERE user_id = @user_id
              AND detected_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @hours HOUR)
            ORDER BY detected_at DESC
            LIMIT 100
            """
            
            from google.cloud import bigquery
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                    bigquery.ScalarQueryParameter("hours", "INT64", hours),
                ]
            )
            
            results = bq.client.query(query, job_config=job_config)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.warning(f"Error fetching recent mentions: {e}")
            return []
    
    async def _fetch_weekly_stats(self, brand_id: str, user_id: str) -> Dict[str, Any]:
        """Fetch weekly statistics for baseline comparison."""
        try:
            from app.services.bigquery_service import get_bigquery_service
            
            bq = get_bigquery_service()
            if not bq.client:
                return {"avg_daily_mentions": 0, "sentiment_trajectory": 0}
            
            query = f"""
            WITH daily_stats AS (
                SELECT 
                    DATE(detected_at) as date,
                    COUNT(*) as mention_count,
                    AVG(sentiment_score) as avg_sentiment
                FROM `{bq._get_table_ref('brand_mentions_log')}`
                WHERE user_id = @user_id
                  AND detected_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
                GROUP BY DATE(detected_at)
            )
            SELECT 
                AVG(mention_count) as avg_daily_mentions,
                -- Sentiment trajectory: difference between recent 2 days and earlier 5 days
                (SELECT AVG(avg_sentiment) FROM daily_stats WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY))
                - (SELECT AVG(avg_sentiment) FROM daily_stats WHERE date < DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY))
                as sentiment_trajectory
            FROM daily_stats
            """
            
            from google.cloud import bigquery
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                ]
            )
            
            results = list(bq.client.query(query, job_config=job_config))
            if results:
                row = results[0]
                return {
                    "avg_daily_mentions": float(row.get("avg_daily_mentions") or 0),
                    "sentiment_trajectory": float(row.get("sentiment_trajectory") or 0)
                }
            
            return {"avg_daily_mentions": 0, "sentiment_trajectory": 0}
            
        except Exception as e:
            logger.warning(f"Error fetching weekly stats: {e}")
            return {"avg_daily_mentions": 0, "sentiment_trajectory": 0}
    
    async def _calculate_24h_trend(self, brand_id: str, user_id: str) -> float:
        """Calculate the 24h mention volume trend (slope)."""
        try:
            from app.services.bigquery_service import get_bigquery_service
            
            bq = get_bigquery_service()
            if not bq.client:
                return 0.0
            
            query = f"""
            WITH hourly_counts AS (
                SELECT 
                    TIMESTAMP_TRUNC(detected_at, HOUR) as hour,
                    COUNT(*) as mention_count
                FROM `{bq._get_table_ref('brand_mentions_log')}`
                WHERE user_id = @user_id
                  AND detected_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
                GROUP BY hour
            )
            SELECT 
                -- Simple trend: compare last 6 hours to previous 18 hours
                (SELECT AVG(mention_count) FROM hourly_counts 
                 WHERE hour >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 HOUR))
                / NULLIF(
                    (SELECT AVG(mention_count) FROM hourly_counts 
                     WHERE hour < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 HOUR)), 0
                ) - 1 as trend_ratio
            """
            
            from google.cloud import bigquery
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                ]
            )
            
            results = list(bq.client.query(query, job_config=job_config))
            if results and results[0].get("trend_ratio") is not None:
                return float(results[0]["trend_ratio"])
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating 24h trend: {e}")
            return 0.0


# =============================================================================
# POLICY SERVICE
# =============================================================================

class AdaptiveScanPolicyService:
    """
    Service for managing scan policies and job scheduling.
    """
    
    def __init__(self):
        self.threat_engine = ThreatScoringEngine()
        self._jobs: Dict[str, ScanJob] = {}  # In-memory for MVP, move to Firestore
        self._logs: Dict[str, ScanLog] = {}  # In-memory for MVP, move to Firestore
    
    async def get_policy(self, brand_id: str, user_id: str) -> ScanPolicy:
        """Get or create scan policy for a brand."""
        from app.core.security import db
        
        try:
            doc_ref = db.collection("scan_policies").document(brand_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return ScanPolicy.from_dict(doc.to_dict())
            else:
                # Create default policy
                policy = ScanPolicy(brand_id=brand_id, user_id=user_id)
                doc_ref.set(policy.to_dict())
                return policy
                
        except Exception as e:
            logger.error(f"Error getting policy for {brand_id}: {e}")
            return ScanPolicy(brand_id=brand_id, user_id=user_id)
    
    async def update_policy(
        self, 
        brand_id: str, 
        user_id: str, 
        updates: Dict[str, Any]
    ) -> ScanPolicy:
        """Update scan policy configuration."""
        from app.core.security import db
        
        policy = await self.get_policy(brand_id, user_id)
        
        # Apply updates
        if "mode" in updates:
            policy.mode = ScanMode(updates["mode"])
        if "fixed_interval_minutes" in updates:
            policy.fixed_interval_ms = updates["fixed_interval_minutes"] * 60 * 1000
        if "thresholds" in updates:
            policy.thresholds = [ThresholdRule.from_dict(t) for t in updates["thresholds"]]
        if "min_interval_minutes" in updates:
            policy.min_interval_ms = updates["min_interval_minutes"] * 60 * 1000
        if "max_interval_minutes" in updates:
            policy.max_interval_ms = updates["max_interval_minutes"] * 60 * 1000
        if "backoff_multiplier" in updates:
            policy.backoff_multiplier = updates["backoff_multiplier"]
        if "quiet_hours" in updates:
            policy.quiet_hours = QuietHoursConfig.from_dict(updates["quiet_hours"])
        if "manual_priority" in updates:
            policy.manual_priority = updates["manual_priority"]
        
        policy.updated_at = datetime.utcnow()
        
        # Save to Firestore
        try:
            db.collection("scan_policies").document(brand_id).set(policy.to_dict())
        except Exception as e:
            logger.error(f"Error saving policy: {e}")
        
        # Recalculate next scan
        assessment = await self.threat_engine.calculate_threat_score(
            brand_id, user_id, policy
        )
        await self.schedule_next_scan(brand_id, user_id, assessment, policy)
        
        return policy
    
    async def calculate_current_threat(
        self, 
        brand_id: str, 
        user_id: str
    ) -> ThreatAssessment:
        """Calculate current threat score."""
        policy = await self.get_policy(brand_id, user_id)
        return await self.threat_engine.calculate_threat_score(brand_id, user_id, policy)
    
    async def schedule_next_scan(
        self,
        brand_id: str,
        user_id: str,
        assessment: ThreatAssessment,
        policy: ScanPolicy
    ) -> ScanJob:
        """
        Schedule the next scan job with deduplication.
        """
        scheduled_for = datetime.utcnow() + timedelta(milliseconds=assessment.interval_ms)
        
        # Idempotency key: prevent duplicate jobs in same time window
        time_bucket = scheduled_for.strftime("%Y-%m-%d-%H")
        idempotency_key = hashlib.sha256(f"{brand_id}:{time_bucket}".encode()).hexdigest()[:16]
        
        # Check for existing job
        existing = self._find_job_by_idempotency_key(idempotency_key)
        if existing and existing.status in ["pending", "running"]:
            logger.info(f"Dedup: Job already exists for {brand_id} at {time_bucket}")
            return existing
        
        # Determine trigger reason
        trigger_reason = self._get_trigger_reason(assessment.label, policy)
        
        job = ScanJob(
            job_id=str(uuid.uuid4()),
            brand_id=brand_id,
            user_id=user_id,
            scheduled_for=scheduled_for,
            idempotency_key=idempotency_key,
            trigger_reason=trigger_reason,
            threat_assessment=assessment.to_dict(),
            policy_snapshot=policy.to_dict(),
            status="pending"
        )
        
        self._jobs[job.job_id] = job
        
        # Update policy with next scan time
        policy.next_scan_at = scheduled_for
        policy.current_threat_score = assessment.score
        policy.current_threat_label = assessment.label.value
        
        from app.core.security import db
        try:
            db.collection("scan_policies").document(brand_id).update({
                "next_scan_at": scheduled_for.isoformat(),
                "current_threat_score": assessment.score,
                "current_threat_label": assessment.label.value,
                "updated_at": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error updating policy next_scan_at: {e}")
        
        logger.info(
            f"📅 Scheduled scan for {brand_id}: {scheduled_for.isoformat()} "
            f"(threat: {assessment.score}, reason: {trigger_reason.value})"
        )
        
        return job
    
    def _find_job_by_idempotency_key(self, key: str) -> Optional[ScanJob]:
        """Find job by idempotency key."""
        for job in self._jobs.values():
            if job.idempotency_key == key:
                return job
        return None
    
    def _get_trigger_reason(self, label: ThreatLevel, policy: ScanPolicy) -> TriggerReason:
        """Map threat level to trigger reason."""
        if policy.mode == ScanMode.FIXED:
            return TriggerReason.SCHEDULED_FIXED
        
        if policy.quiet_hours.enabled and self.threat_engine._is_quiet_hours(policy):
            return TriggerReason.QUIET_HOURS
        
        reason_map = {
            ThreatLevel.CRITICAL: TriggerReason.ADAPTIVE_CRITICAL,
            ThreatLevel.HIGH: TriggerReason.ADAPTIVE_HIGH,
            ThreatLevel.MODERATE: TriggerReason.ADAPTIVE_MODERATE,
            ThreatLevel.LOW: TriggerReason.ADAPTIVE_LOW
        }
        return reason_map.get(label, TriggerReason.ADAPTIVE_MODERATE)
    
    async def execute_scan(self, job: ScanJob) -> ScanLog:
        """
        Execute a scan job with idempotency.
        """
        log = ScanLog(
            log_id=str(uuid.uuid4()),
            brand_id=job.brand_id,
            user_id=job.user_id,
            job_id=job.job_id,
            trigger_reason=job.trigger_reason.value,
            threat_score_at_schedule=job.threat_assessment.get("score", 0),
            policy_mode=job.policy_snapshot.get("mode", "adaptive"),
            started_at=datetime.utcnow()
        )
        
        # Mark job as running
        job.status = "running"
        job.started_at = datetime.utcnow()
        
        try:
            # Execute actual scan
            from app.services.brand_monitoring_scanner import get_scanner
            
            scanner = get_scanner()
            config = await self._get_brand_config(job.brand_id, job.user_id)
            result = await scanner.scan_user(job.user_id, config)
            
            # Update log with results
            log.status = "success"
            log.completed_at = datetime.utcnow()
            log.duration_ms = int((log.completed_at - log.started_at).total_seconds() * 1000)
            log.mentions_found = result.get("brand_mentions", 0)
            log.new_mentions_logged = result.get("new_items_logged", 0)
            log.duplicates_skipped = result.get("duplicates_skipped", 0)
            log.opportunities_detected = result.get("opportunities", 0)
            log.competitor_mentions = result.get("competitor_mentions", 0)
            
            # Mark job as completed
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.result_summary = result
            
            # Update policy last_scan_at
            policy = await self.get_policy(job.brand_id, job.user_id)
            policy.last_scan_at = datetime.utcnow()
            
            # Update consecutive low scans counter
            current_threat = await self.calculate_current_threat(job.brand_id, job.user_id)
            if current_threat.label == ThreatLevel.LOW:
                policy.consecutive_low_scans += 1
            else:
                policy.consecutive_low_scans = 0
            
            # Log post-scan assessment
            log.threat_score_post = current_threat.score
            log.threat_breakdown_post = current_threat.breakdown.to_dict()
            
            # Schedule next scan
            next_job = await self.schedule_next_scan(
                job.brand_id, job.user_id, current_threat, policy
            )
            log.next_scan_scheduled_for = next_job.scheduled_for
            log.scan_interval_ms = current_threat.interval_ms
            
            logger.info(
                f"✅ Scan complete for {job.brand_id}: "
                f"{log.mentions_found} mentions, {log.new_mentions_logged} logged, "
                f"next scan in {current_threat.interval_ms // 60000} min"
            )
            
        except Exception as e:
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            log.duration_ms = int((log.completed_at - log.started_at).total_seconds() * 1000)
            
            job.status = "failed"
            job.error_message = str(e)
            
            logger.error(f"❌ Scan failed for {job.brand_id}: {e}")
        
        # Store log
        self._logs[log.log_id] = log
        await self._persist_scan_log(log)
        
        return log
    
    async def _get_brand_config(self, brand_id: str, user_id: str) -> Dict[str, Any]:
        """Get brand monitoring config for scanner."""
        from app.core.security import db
        
        try:
            doc = db.collection("user_integrations").document(f"{user_id}_brand_monitoring").get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            logger.warning(f"Error getting brand config: {e}")
        
        return {}
    
    async def _persist_scan_log(self, log: ScanLog) -> None:
        """Persist scan log to Firestore and BigQuery."""
        from app.core.security import db
        
        # Firestore
        try:
            db.collection("scan_logs").document(log.log_id).set(log.to_dict())
        except Exception as e:
            logger.error(f"Error saving scan log to Firestore: {e}")
        
        # BigQuery
        try:
            from app.services.bigquery_service import get_bigquery_service
            bq = get_bigquery_service()
            
            if bq.client:
                bq._insert_to_table("scan_logs", {
                    "log_id": log.log_id,
                    "brand_id": log.brand_id,
                    "user_id": log.user_id,
                    "job_id": log.job_id,
                    "trigger_reason": log.trigger_reason,
                    "threat_score_at_schedule": log.threat_score_at_schedule,
                    "policy_mode": log.policy_mode,
                    "started_at": log.started_at.isoformat(),
                    "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                    "duration_ms": log.duration_ms,
                    "status": log.status,
                    "error_message": log.error_message,
                    "mentions_found": log.mentions_found,
                    "new_mentions_logged": log.new_mentions_logged,
                    "opportunities_detected": log.opportunities_detected,
                    "threat_score_post": log.threat_score_post,
                    "threat_breakdown": log.threat_breakdown_post,
                    "next_scan_scheduled_for": log.next_scan_scheduled_for.isoformat() if log.next_scan_scheduled_for else None,
                    "scan_interval_ms": log.scan_interval_ms
                }, timestamp_field="started_at")
        except Exception as e:
            logger.error(f"Error saving scan log to BigQuery: {e}")
    
    async def get_scan_history(
        self, 
        brand_id: str, 
        user_id: str, 
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get scan history for telemetry."""
        from app.core.security import db
        
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            query = (
                db.collection("scan_logs")
                .where("brand_id", "==", brand_id)
                .where("started_at", ">=", since.isoformat())
                .order_by("started_at", direction="DESCENDING")
                .limit(100)
            )
            
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
            
        except Exception as e:
            logger.error(f"Error getting scan history: {e}")
            # Fallback to in-memory logs
            return [
                log.to_dict() for log in self._logs.values()
                if log.brand_id == brand_id
            ]
    
    async def get_pending_jobs_count(self, brand_id: str) -> int:
        """Get count of pending jobs."""
        return len([j for j in self._jobs.values() 
                   if j.brand_id == brand_id and j.status == "pending"])
    
    async def trigger_manual_scan(self, brand_id: str, user_id: str) -> ScanJob:
        """Trigger an immediate manual scan."""
        policy = await self.get_policy(brand_id, user_id)
        
        # Create manual scan job
        job = ScanJob(
            job_id=str(uuid.uuid4()),
            brand_id=brand_id,
            user_id=user_id,
            scheduled_for=datetime.utcnow(),
            idempotency_key=f"manual_{datetime.utcnow().isoformat()}",
            trigger_reason=TriggerReason.MANUAL,
            threat_assessment={},
            policy_snapshot=policy.to_dict(),
            status="pending"
        )
        
        self._jobs[job.job_id] = job
        
        # Execute immediately
        await self.execute_scan(job)
        
        return job


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_policy_service: Optional[AdaptiveScanPolicyService] = None


def get_adaptive_scan_service() -> AdaptiveScanPolicyService:
    """Get or create singleton adaptive scan service."""
    global _policy_service
    if _policy_service is None:
        _policy_service = AdaptiveScanPolicyService()
    return _policy_service

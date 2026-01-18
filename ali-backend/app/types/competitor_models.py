"""
Market Radar: Competitor Intelligence Models
Data models for the competitor tracking and event monitoring system.

Provides schemas for:
- Competitor: A tracked competitor entity
- CompetitorEvent: A detected change/activity from a competitor
- ThemeCluster: Grouped events with actionable insights
- WeeklyDigest: Summary report for competitor activity
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import hashlib


# =============================================================================
# ENUMS
# =============================================================================

class EventType(str, Enum):
    """Categories of competitor events."""
    PRICING = "pricing"           # Price changes, discounts, new tiers
    PRODUCT = "product"           # New features, launches, deprecations
    MESSAGING = "messaging"       # Positioning shifts, rebrand, tagline changes
    PARTNERSHIP = "partnership"   # Integrations, alliances, acquisitions
    INCIDENT = "incident"         # Outages, data breaches, PR crises
    HIRING = "hiring"             # Key hires, layoffs, team changes
    FUNDING = "funding"           # Investment rounds, valuations
    LEGAL = "legal"               # Lawsuits, regulatory actions


class SourceType(str, Enum):
    """How the event was detected."""
    NEWS = "news"                 # News articles via NewsData.io / DuckDuckGo
    RSS = "rss"                   # RSS feed monitoring
    SOCIAL = "social"             # Social media posts
    WEBSITE_DIFF = "website_diff" # Website change detection
    MANUAL = "manual"             # User-submitted event


# =============================================================================
# HASHING UTILITIES
# =============================================================================

def compute_event_hash(title: str, source_url: str, detected_at: str) -> str:
    """
    Compute tamper-evident hash for a competitor event.
    
    Hash = SHA-256(title + "|" + source_url + "|" + detected_at_iso)
    
    Args:
        title: Event headline/summary
        source_url: The source URL
        detected_at: ISO format timestamp of detection
    
    Returns:
        64-character hex string (SHA-256)
    """
    payload = f"{title}|{source_url}|{detected_at}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def compute_cluster_hash(theme_name: str, event_hashes: List[str]) -> str:
    """
    Compute hash for a theme cluster.
    
    Hash = SHA-256(theme_name + "|" + sorted_event_hashes_joined)
    
    Args:
        theme_name: The cluster theme name
        event_hashes: List of event hashes (will be sorted for determinism)
    
    Returns:
        64-character hex string (SHA-256)
    """
    sorted_hashes = sorted(event_hashes)
    payload = f"{theme_name}|{'|'.join(sorted_hashes)}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


# =============================================================================
# THEME CONFIGURATION (Rule-based MVP)
# =============================================================================

THEME_KEYWORDS = {
    "Pricing Moves": ["pricing", "price", "discount", "tier", "plan", "subscription", "cost", "fee"],
    "AI & ML Expansion": ["ai", "artificial intelligence", "machine learning", "llm", "gpt", "copilot", "genai"],
    "Product Launches": ["launch", "release", "new feature", "beta", "ga", "announce", "introduce", "unveil"],
    "Partnerships & Integrations": ["partner", "integration", "alliance", "collaborate", "api", "ecosystem"],
    "Security & Compliance": ["security", "breach", "compliance", "gdpr", "soc2", "vulnerability", "audit"],
    "Market Expansion": ["expand", "new market", "region", "country", "international", "global"],
    "Leadership Changes": ["ceo", "cto", "cfo", "hire", "appoint", "resign", "layoff", "restructure"],
    "Funding & Valuation": ["funding", "series", "valuation", "ipo", "acquisition", "merge", "investor"],
}

INSIGHT_TEMPLATES = {
    "Pricing Moves": {
        "why": "{count} competitor(s) adjusted pricing in the past {days} days. This may signal market pressure or repositioning strategies.",
        "actions": [
            "Review your pricing against new competitor tiers",
            "Update sales battlecards with competitive pricing data",
            "Consider a value-focused campaign if competitors are undercutting"
        ]
    },
    "AI & ML Expansion": {
        "why": "AI investment is accelerating in your space. {count} competitor(s) announced AI-related updates.",
        "actions": [
            "Assess your AI roadmap against competitor capabilities",
            "Highlight your AI differentiators in messaging",
            "Monitor customer reactions to competitor AI launches"
        ]
    },
    "Product Launches": {
        "why": "{count} competitor(s) launched new products or features. Market expectations may be shifting.",
        "actions": [
            "Analyze feature gaps in your offering",
            "Prepare competitive positioning statements",
            "Brief sales team on new competitor capabilities"
        ]
    },
    "Partnerships & Integrations": {
        "why": "{count} competitor(s) announced partnerships or integrations. Ecosystem plays are intensifying.",
        "actions": [
            "Identify potential partner opportunities for your brand",
            "Monitor for exclusivity arrangements that may limit your reach",
            "Consider API/integration expansion to match ecosystem depth"
        ]
    },
    "Security & Compliance": {
        "why": "{count} competitor(s) had security or compliance-related events. This may affect customer trust dynamics.",
        "actions": [
            "Highlight your security credentials in marketing",
            "Prepare messaging for concerned prospects",
            "Review your own security posture proactively"
        ]
    },
    "Market Expansion": {
        "why": "{count} competitor(s) expanded into new markets or regions. Geographic competition is intensifying.",
        "actions": [
            "Assess your own expansion readiness for those markets",
            "Strengthen positioning in your current stronghold regions",
            "Monitor for localized pricing or feature variations"
        ]
    },
    "Leadership Changes": {
        "why": "{count} competitor(s) announced leadership changes. This may signal strategic shifts.",
        "actions": [
            "Research incoming leaders' backgrounds and priorities",
            "Monitor for strategy announcements following leadership changes",
            "Update competitive intelligence profiles"
        ]
    },
    "Funding & Valuation": {
        "why": "{count} competitor(s) announced funding, acquisition, or valuation news. Capital allocation may change competitive dynamics.",
        "actions": [
            "Anticipate increased competitor marketing spend",
            "Monitor for aggressive pricing or expansion moves",
            "Consider your own positioning around sustainability and profitability"
        ]
    },
}


# =============================================================================
# COMPETITOR - A tracked entity
# =============================================================================

class Competitor(BaseModel):
    """
    A tracked competitor entity.
    
    Represents a company or individual to monitor in the competitive landscape.
    """
    id: str = Field(..., description="Unique competitor ID (uuid)")
    user_id: str = Field(..., description="Owning user/brand ID")
    name: str = Field(..., description="Competitor name")
    domains: List[str] = Field(default_factory=list, description="Official domains to monitor")
    regions: List[str] = Field(default_factory=list, description="Geographic regions (ISO country codes)")
    tags: List[str] = Field(default_factory=list, description="User-defined classification tags")
    entity_type: str = Field(default="company", description="company | person")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    # Optional enrichment
    logo_url: Optional[str] = Field(None, description="Logo image URL")
    website: Optional[str] = Field(None, description="Primary website URL")
    industry: Optional[str] = Field(None, description="Industry classification")
    
    class Config:
        use_enum_values = True


# =============================================================================
# COMPETITOR EVENT - A detected change
# =============================================================================

class CompetitorEvent(BaseModel):
    """
    A detected competitor change/event.
    
    Represents a significant activity from a competitor detected via
    news monitoring, website diffs, or social listening.
    """
    id: str = Field(..., description="Unique event ID (uuid)")
    competitor_id: str = Field(..., description="Parent Competitor ID")
    competitor_name: str = Field(default="", description="Denormalized competitor name for queries")
    user_id: str = Field(..., description="Owning user/brand ID")
    
    # Event Classification
    type: EventType = Field(...)
    themes: List[str] = Field(default_factory=list, description="Extracted themes (AI-generated)")
    
    # Detection Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    source_url: str = Field(..., description="Original source URL")
    source_type: SourceType = Field(default=SourceType.NEWS)
    
    # Content
    title: str = Field(..., description="Event headline/summary")
    summary: str = Field(default="", description="AI-generated event summary")
    raw_snippet: str = Field(default="", description="Original text snippet")
    
    # Scoring
    impact_score: int = Field(default=5, ge=1, le=10, description="Estimated business impact (1-10)")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Detection confidence")
    
    # Evidence Chain Integration
    evidence_links: List[str] = Field(default_factory=list, description="Screenshot/archive URLs")
    event_hash: str = Field(default="", description="SHA-256(title + source_url + detected_at)")
    
    # Region (optional, for filtering)
    region: Optional[str] = Field(None, description="ISO country code if region-specific")
    
    # Processing status
    is_processed: bool = Field(default=True, description="Whether clustering has been applied")
    cluster_id: Optional[str] = Field(None, description="Assigned ThemeCluster ID")
    
    class Config:
        use_enum_values = True


# =============================================================================
# THEME CLUSTER - Grouped events with insights
# =============================================================================

class ThemeCluster(BaseModel):
    """
    A cluster of related competitor events by theme.
    
    Groups events under a strategic theme and provides actionable
    insights via rule-based templates or AI generation.
    """
    id: str = Field(..., description="Unique cluster ID (uuid)")
    user_id: str = Field(..., description="Owning user/brand ID")
    theme_name: str = Field(..., description="Cluster label (e.g., 'Pricing Moves')")
    
    # Aggregated Events
    event_ids: List[str] = Field(default_factory=list, description="Event IDs in this cluster")
    event_count: int = Field(default=0)
    competitors_involved: List[str] = Field(default_factory=list, description="Competitor names")
    
    # Insights (Rule-based or AI-generated)
    why_it_matters: str = Field(default="", description="Strategic impact explanation")
    suggested_actions: List[str] = Field(default_factory=list, description="Recommended responses")
    
    # Metadata
    time_range_start: datetime = Field(...)
    time_range_end: datetime = Field(...)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    priority: int = Field(default=5, ge=1, le=10, description="Cluster urgency")
    
    # Integrity
    cluster_hash: str = Field(default="", description="SHA-256(theme_name + sorted(event_hashes))")
    
    class Config:
        use_enum_values = True


# =============================================================================
# WEEKLY DIGEST - Summary report
# =============================================================================

class DigestMetrics(BaseModel):
    """Key metrics for a digest period."""
    total_events: int = Field(default=0)
    competitors_active: int = Field(default=0)
    high_impact_events: int = Field(default=0, description="Events with impact_score >= 7")
    dominant_theme: Optional[str] = Field(None)
    
    class Config:
        use_enum_values = True


class WeeklyDigest(BaseModel):
    """
    Summary report for competitor activity.
    
    Aggregates events and clusters over a time period with
    executive summary and actionable takeaways.
    """
    id: str = Field(..., description="Unique digest ID (uuid)")
    user_id: str = Field(..., description="Owning user/brand ID")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Time Range
    time_range_start: datetime = Field(...)
    time_range_end: datetime = Field(...)
    time_range_label: str = Field(default="7d", description="7d, 30d, etc.")
    
    # Summary
    executive_summary: str = Field(default="", description="AI or template-generated summary")
    metrics: DigestMetrics = Field(default_factory=DigestMetrics)
    
    # Content
    top_clusters: List[str] = Field(default_factory=list, description="ThemeCluster IDs")
    notable_events: List[str] = Field(default_factory=list, description="Top event IDs by impact")
    
    # Recommendations
    recommended_responses: List[str] = Field(default_factory=list)
    
    # Export
    export_url: Optional[str] = Field(None, description="URL to exported HTML/PDF")
    export_format: Optional[str] = Field(None, description="html or pdf")
    
    class Config:
        use_enum_values = True


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreateCompetitorRequest(BaseModel):
    """Request body for adding a new competitor."""
    name: str = Field(..., description="Competitor name")
    domains: List[str] = Field(default_factory=list)
    regions: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    entity_type: str = Field(default="company")
    website: Optional[str] = Field(None)
    industry: Optional[str] = Field(None)


class UpdateCompetitorRequest(BaseModel):
    """Request body for updating a competitor."""
    name: Optional[str] = Field(None)
    domains: Optional[List[str]] = Field(None)
    regions: Optional[List[str]] = Field(None)
    tags: Optional[List[str]] = Field(None)
    is_active: Optional[bool] = Field(None)
    website: Optional[str] = Field(None)
    industry: Optional[str] = Field(None)


class ListEventsRequest(BaseModel):
    """Query parameters for listing events."""
    competitor_id: Optional[str] = Field(None)
    event_type: Optional[str] = Field(None)
    theme: Optional[str] = Field(None)
    region: Optional[str] = Field(None)
    start_date: Optional[datetime] = Field(None)
    end_date: Optional[datetime] = Field(None)
    min_impact: Optional[int] = Field(None, ge=1, le=10)
    limit: int = Field(default=50, le=200)
    offset: int = Field(default=0)


class GenerateDigestRequest(BaseModel):
    """Request body for generating a digest."""
    time_range: str = Field(default="7d", description="7d, 30d, 90d")
    include_clusters: bool = Field(default=True)
    include_events: bool = Field(default=True)
    format: str = Field(default="html", description="html or pdf")


class ListEventsResponse(BaseModel):
    """Response for event listing."""
    events: List[CompetitorEvent] = Field(default_factory=list)
    total_count: int = Field(default=0)
    clusters_summary: Dict[str, int] = Field(default_factory=dict)


class ListClustersResponse(BaseModel):
    """Response for cluster listing."""
    clusters: List[ThemeCluster] = Field(default_factory=list)
    time_range: Dict[str, str] = Field(default_factory=dict)


class DigestResponse(BaseModel):
    """Response for digest generation."""
    digest: WeeklyDigest
    export_url: Optional[str] = Field(None)

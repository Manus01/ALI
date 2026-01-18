"""
Market Radar: Intelligence Agent
AI-powered competitor event classification, theme extraction, and insight generation.
"""
import uuid
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

from .base_agent import BaseAgent
from app.services.llm_factory import get_model
from app.services.firestore_service import get_firestore_client
from app.services.bigquery_service import get_bigquery_service
from app.types.competitor_models import (
    Competitor,
    CompetitorEvent,
    EventType,
    SourceType,
    THEME_KEYWORDS,
    INSIGHT_TEMPLATES,
    compute_event_hash,
)

logger = logging.getLogger(__name__)


class RadarAgent(BaseAgent):
    """
    AI Agent for Market Radar competitor intelligence.
    
    Responsibilities:
    1. Classify raw news/mentions into structured CompetitorEvents
    2. Extract themes and compute impact scores
    3. Generate insights and suggested actions
    4. Orchestrate the change detection pipeline
    """
    
    CLASSIFICATION_PROMPT = """You are a competitive intelligence analyst. Analyze this news about competitor "{competitor_name}":

**Title:** {title}

**Content:** {content}

**Source URL:** {source_url}

**Instructions:**
1. Classify the event type from: pricing, product, messaging, partnership, incident, hiring, funding, legal
2. Extract 1-3 relevant themes/keywords (e.g., "AI features", "enterprise pricing", "security breach")
3. Rate the business impact (1-10): How significant is this for the market?
4. Rate your confidence (0.0-1.0): How certain is this classification?
5. Write a 1-2 sentence summary of the event's significance

**Return JSON only:**
{{
  "type": "product",
  "themes": ["AI copilot", "enterprise features"],
  "impact_score": 8,
  "confidence": 0.9,
  "summary": "Competitor launched an AI copilot feature targeting enterprise customers, signaling a major product strategy shift."
}}
"""

    AI_INSIGHT_PROMPT = """You are a strategic advisor analyzing competitor activity for a brand.

**Theme:** {theme_name}
**Event Count:** {event_count} events in the past {days} days
**Competitors Involved:** {competitors}

**Sample Events:**
{sample_events}

**Instructions:**
1. Write a 2-3 sentence "Why It Matters" analysis explaining the strategic implications
2. Suggest 3 specific, actionable responses the brand should consider

**Return JSON only:**
{{
  "why_it_matters": "Your analysis here...",
  "suggested_actions": [
    "Action 1",
    "Action 2", 
    "Action 3"
  ]
}}
"""

    def __init__(self):
        super().__init__("RadarAgent")
        self.model = None
    
    def _ensure_model(self):
        """Lazy-load the LLM model."""
        if self.model is None:
            self.model = get_model("gemini-2.0-flash")
    
    async def classify_event(
        self, 
        raw_mention: Dict[str, Any], 
        competitor: Competitor
    ) -> Optional[CompetitorEvent]:
        """
        Classify a raw news mention into a structured CompetitorEvent.
        
        Args:
            raw_mention: Dictionary with title, content, source_url, detected_at
            competitor: The Competitor this mention is about
        
        Returns:
            CompetitorEvent if classification succeeds, None otherwise
        """
        self._ensure_model()
        
        title = raw_mention.get("title", "")
        content = raw_mention.get("content", raw_mention.get("snippet", ""))
        source_url = raw_mention.get("source_url", raw_mention.get("url", ""))
        detected_at = raw_mention.get("detected_at", datetime.utcnow())
        
        if isinstance(detected_at, str):
            try:
                detected_at = datetime.fromisoformat(detected_at.replace("Z", "+00:00"))
            except:
                detected_at = datetime.utcnow()
        
        prompt = self.CLASSIFICATION_PROMPT.format(
            competitor_name=competitor.name,
            title=title,
            content=content[:2000],  # Limit content length
            source_url=source_url
        )
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Parse JSON from response
            result = self._parse_json_response(result_text)
            
            if not result:
                self.log_task(f"⚠️ Failed to parse classification for: {title[:50]}")
                return None
            
            # Validate and normalize event type
            event_type_str = result.get("type", "product").lower()
            try:
                event_type = EventType(event_type_str)
            except ValueError:
                event_type = EventType.PRODUCT  # Default fallback
            
            # Compute hash
            detected_at_str = detected_at.isoformat() if isinstance(detected_at, datetime) else str(detected_at)
            event_hash = compute_event_hash(title, source_url, detected_at_str)
            
            # Create event
            event = CompetitorEvent(
                id=str(uuid.uuid4()),
                competitor_id=competitor.id,
                competitor_name=competitor.name,
                user_id=competitor.user_id,
                type=event_type,
                themes=result.get("themes", []),
                detected_at=detected_at,
                source_url=source_url,
                source_type=SourceType(raw_mention.get("source_type", "news")),
                title=title,
                summary=result.get("summary", ""),
                raw_snippet=content[:500],
                impact_score=min(10, max(1, result.get("impact_score", 5))),
                confidence=min(1.0, max(0.0, result.get("confidence", 0.7))),
                event_hash=event_hash,
                region=raw_mention.get("country"),
                is_processed=True
            )
            
            self.log_task(f"✅ Classified event: {title[:40]}... (type={event_type}, impact={event.impact_score})")
            return event
        
        except Exception as e:
            self.log_task(f"❌ Classification error: {e}")
            return None
    
    async def classify_events_batch(
        self, 
        raw_mentions: List[Dict[str, Any]], 
        competitor: Competitor
    ) -> List[CompetitorEvent]:
        """
        Classify multiple mentions in sequence.
        
        Args:
            raw_mentions: List of raw mention dictionaries
            competitor: The Competitor these mentions are about
        
        Returns:
            List of successfully classified CompetitorEvents
        """
        events = []
        for mention in raw_mentions:
            event = await self.classify_event(mention, competitor)
            if event:
                events.append(event)
        return events
    
    async def generate_ai_insight(
        self, 
        theme_name: str, 
        events: List[CompetitorEvent], 
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Generate AI-powered insights for a theme cluster.
        
        Uses LLM for richer analysis when event count is significant.
        Falls back to rule-based templates for smaller clusters.
        
        Args:
            theme_name: The theme to analyze
            events: List of events in this theme cluster
            days: Time range for the analysis
        
        Returns:
            Dict with "why_it_matters" and "suggested_actions"
        """
        # For small clusters, use rule-based templates
        if len(events) < 3:
            return {
                "why_it_matters": INSIGHT_TEMPLATES.get(theme_name, {}).get(
                    "why", 
                    f"{len(events)} competitor event(s) detected in '{theme_name}'."
                ).format(count=len(events), days=days, details=""),
                "suggested_actions": INSIGHT_TEMPLATES.get(theme_name, {}).get(
                    "actions", 
                    ["Review events for strategic implications", "Update competitive positioning"]
                )
            }
        
        # For larger clusters, use AI
        self._ensure_model()
        
        competitors = list(set(e.competitor_name for e in events))
        sample_events = "\n".join([
            f"- {e.title} ({e.competitor_name}, impact: {e.impact_score})"
            for e in sorted(events, key=lambda x: x.impact_score, reverse=True)[:5]
        ])
        
        prompt = self.AI_INSIGHT_PROMPT.format(
            theme_name=theme_name,
            event_count=len(events),
            days=days,
            competitors=", ".join(competitors[:5]),
            sample_events=sample_events
        )
        
        try:
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text.strip())
            
            if result:
                return {
                    "why_it_matters": result.get("why_it_matters", ""),
                    "suggested_actions": result.get("suggested_actions", [])
                }
        except Exception as e:
            self.log_task(f"⚠️ AI insight generation failed: {e}")
        
        # Fallback to templates
        return {
            "why_it_matters": f"{len(events)} events detected in '{theme_name}' across {len(competitors)} competitor(s).",
            "suggested_actions": INSIGHT_TEMPLATES.get(theme_name, {}).get("actions", [
                "Review the events for strategic implications",
                "Update your competitive positioning",
                "Brief relevant stakeholders"
            ])
        }
    
    def match_event_to_theme(self, event: CompetitorEvent) -> str:
        """
        Match an event to a predefined theme using keyword matching.
        
        Args:
            event: The CompetitorEvent to match
        
        Returns:
            Theme name (string)
        """
        event_text = f"{event.title} {' '.join(event.themes)}".lower()
        
        for theme_name, keywords in THEME_KEYWORDS.items():
            if any(kw in event_text for kw in keywords):
                return theme_name
        
        return "Other"
    
    def group_events_by_theme(self, events: List[CompetitorEvent]) -> Dict[str, List[CompetitorEvent]]:
        """
        Group events by theme using keyword matching.
        
        Args:
            events: List of CompetitorEvents
        
        Returns:
            Dictionary mapping theme names to lists of events
        """
        theme_groups = defaultdict(list)
        
        for event in events:
            theme = self.match_event_to_theme(event)
            theme_groups[theme].append(event)
        
        return dict(theme_groups)
    
    def calculate_cluster_priority(self, events: List[CompetitorEvent]) -> int:
        """
        Calculate priority score for a cluster.
        
        Formula: (event_count / 3) + (avg_impact / 2)
        Clamped to 1-10 range.
        
        Args:
            events: Events in the cluster
        
        Returns:
            Priority score (1-10)
        """
        if not events:
            return 1
        
        avg_impact = sum(e.impact_score for e in events) / len(events)
        priority = (len(events) / 3) + (avg_impact / 2)
        return min(10, max(1, int(priority)))
    
    async def process_raw_mentions(
        self, 
        mentions: List[Dict[str, Any]], 
        competitor: Competitor,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Full pipeline: classify mentions -> save events -> return summary.
        
        Args:
            mentions: Raw news/social mentions
            competitor: The Competitor being monitored
            save_to_db: Whether to persist to Firestore/BigQuery
        
        Returns:
            Summary dict with event counts and theme breakdown
        """
        self.log_task(f"📡 Processing {len(mentions)} mentions for {competitor.name}")
        
        # Classify
        events = await self.classify_events_batch(mentions, competitor)
        
        if not events:
            return {"events_processed": 0, "events_created": 0, "themes": {}}
        
        # Group by theme
        theme_groups = self.group_events_by_theme(events)
        theme_counts = {theme: len(evts) for theme, evts in theme_groups.items()}
        
        # Save to database
        if save_to_db:
            db = get_firestore_client()
            bq = get_bigquery_service()
            
            for event in events:
                # Firestore
                db.collection("competitor_events").document(event.id).set(event.dict())
                
                # BigQuery
                bq.insert_competitor_event({
                    "event_id": event.id,
                    "competitor_id": event.competitor_id,
                    "competitor_name": event.competitor_name,
                    "user_id": event.user_id,
                    "event_type": event.type.value,
                    "themes": event.themes,
                    "detected_at": event.detected_at.isoformat(),
                    "source_url": event.source_url,
                    "source_type": event.source_type.value,
                    "title": event.title,
                    "summary": event.summary,
                    "impact_score": event.impact_score,
                    "confidence": event.confidence,
                    "region": event.region,
                    "event_hash": event.event_hash,
                })
            
            self.log_task(f"✅ Saved {len(events)} events to database")
        
        return {
            "events_processed": len(mentions),
            "events_created": len(events),
            "themes": theme_counts,
            "high_impact_count": sum(1 for e in events if e.impact_score >= 7)
        }
    
    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON from LLM response, handling markdown code blocks.
        
        Args:
            text: Raw LLM response text
        
        Returns:
            Parsed dictionary or None if parsing fails
        """
        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            import re
            match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            return None

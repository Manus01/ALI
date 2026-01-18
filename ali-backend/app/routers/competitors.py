"""
Market Radar: Competitor Intelligence Router
API endpoints for competitor tracking, event monitoring, and insight generation.
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import verify_token, db
from app.services.bigquery_service import get_bigquery_service
from app.types.competitor_models import (
    Competitor,
    CompetitorEvent,
    ThemeCluster,
    WeeklyDigest,
    DigestMetrics,
    EventType,
    SourceType,
    CreateCompetitorRequest,
    UpdateCompetitorRequest,
    ListEventsRequest,
    ListEventsResponse,
    ListClustersResponse,
    GenerateDigestRequest,
    DigestResponse,
    THEME_KEYWORDS,
    INSIGHT_TEMPLATES,
    compute_event_hash,
    compute_cluster_hash,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST/RESPONSE MODELS (API-specific)
# =============================================================================

class CompetitorListResponse(BaseModel):
    """Response for listing competitors."""
    competitors: List[Competitor] = Field(default_factory=list)
    total_count: int = Field(default=0)


class CompetitorResponse(BaseModel):
    """Response for a single competitor."""
    competitor: Competitor
    event_count: int = Field(default=0)
    last_event_at: Optional[datetime] = Field(None)


class ScanNowRequest(BaseModel):
    """Request to trigger an immediate competitor scan."""
    competitor_ids: Optional[List[str]] = Field(None, description="Specific competitors to scan, or all if empty")


class ScanNowResponse(BaseModel):
    """Response for scan trigger."""
    job_id: str
    status: str = "queued"
    message: str


# =============================================================================
# COMPETITOR CRUD ENDPOINTS
# =============================================================================

@router.get("/competitors", response_model=CompetitorListResponse)
async def list_competitors(
    include_inactive: bool = Query(False, description="Include inactive competitors"),
    user: dict = Depends(verify_token)
):
    """
    Get list of tracked competitors.
    """
    try:
        user_id = user.get("uid")
        
        query = db.collection("competitors").where("user_id", "==", user_id)
        if not include_inactive:
            query = query.where("is_active", "==", True)
        
        docs = list(query.stream())
        competitors = []
        
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            competitors.append(Competitor(**data))
        
        return CompetitorListResponse(
            competitors=competitors,
            total_count=len(competitors)
        )
    except Exception as e:
        logger.error(f"❌ Failed to list competitors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/competitors", response_model=CompetitorResponse)
async def create_competitor(
    request: CreateCompetitorRequest,
    user: dict = Depends(verify_token)
):
    """
    Add a new competitor to track.
    """
    try:
        user_id = user.get("uid")
        
        # Check for duplicates
        existing = db.collection("competitors")\
            .where("user_id", "==", user_id)\
            .where("name", "==", request.name)\
            .limit(1)\
            .stream()
        
        if list(existing):
            raise HTTPException(status_code=400, detail=f"Competitor '{request.name}' already exists")
        
        # Create competitor
        competitor_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        competitor = Competitor(
            id=competitor_id,
            user_id=user_id,
            name=request.name,
            domains=request.domains,
            regions=request.regions,
            tags=request.tags,
            entity_type=request.entity_type,
            website=request.website,
            industry=request.industry,
            created_at=now,
            updated_at=now,
            is_active=True
        )
        
        db.collection("competitors").document(competitor_id).set(competitor.dict())
        
        logger.info(f"✅ Created competitor: {request.name} for user {user_id}")
        
        return CompetitorResponse(competitor=competitor, event_count=0)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create competitor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/competitors/{competitor_id}", response_model=CompetitorResponse)
async def get_competitor(
    competitor_id: str,
    user: dict = Depends(verify_token)
):
    """
    Get a single competitor by ID.
    """
    try:
        user_id = user.get("uid")
        
        doc = db.collection("competitors").document(competitor_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        data = doc.to_dict()
        if data.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        data["id"] = doc.id
        competitor = Competitor(**data)
        
        # Get event count
        events = db.collection("competitor_events")\
            .where("competitor_id", "==", competitor_id)\
            .order_by("detected_at", direction="DESCENDING")\
            .limit(1)\
            .stream()
        
        events_list = list(events)
        event_count = len(list(db.collection("competitor_events").where("competitor_id", "==", competitor_id).stream()))
        last_event_at = events_list[0].to_dict().get("detected_at") if events_list else None
        
        return CompetitorResponse(
            competitor=competitor,
            event_count=event_count,
            last_event_at=last_event_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get competitor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/competitors/{competitor_id}", response_model=CompetitorResponse)
async def update_competitor(
    competitor_id: str,
    request: UpdateCompetitorRequest,
    user: dict = Depends(verify_token)
):
    """
    Update a competitor.
    """
    try:
        user_id = user.get("uid")
        
        doc_ref = db.collection("competitors").document(competitor_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        data = doc.to_dict()
        if data.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Build update dict
        updates = {"updated_at": datetime.utcnow()}
        if request.name is not None:
            updates["name"] = request.name
        if request.domains is not None:
            updates["domains"] = request.domains
        if request.regions is not None:
            updates["regions"] = request.regions
        if request.tags is not None:
            updates["tags"] = request.tags
        if request.is_active is not None:
            updates["is_active"] = request.is_active
        if request.website is not None:
            updates["website"] = request.website
        if request.industry is not None:
            updates["industry"] = request.industry
        
        doc_ref.update(updates)
        
        # Fetch updated doc
        updated_doc = doc_ref.get()
        updated_data = updated_doc.to_dict()
        updated_data["id"] = competitor_id
        
        return CompetitorResponse(competitor=Competitor(**updated_data))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update competitor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/competitors/{competitor_id}")
async def delete_competitor(
    competitor_id: str,
    user: dict = Depends(verify_token)
):
    """
    Remove a competitor from tracking (soft delete).
    """
    try:
        user_id = user.get("uid")
        
        doc_ref = db.collection("competitors").document(competitor_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        data = doc.to_dict()
        if data.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Soft delete
        doc_ref.update({
            "is_active": False,
            "updated_at": datetime.utcnow()
        })
        
        return {"status": "deleted", "competitor_id": competitor_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete competitor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# COMPETITOR EVENTS ENDPOINTS
# =============================================================================

@router.get("/competitors/events", response_model=ListEventsResponse)
async def list_competitor_events(
    competitor_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    theme: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    min_impact: Optional[int] = Query(None, ge=1, le=10),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    user: dict = Depends(verify_token)
):
    """
    List competitor events with optional filters.
    """
    try:
        user_id = user.get("uid")
        
        # Build query
        query = db.collection("competitor_events").where("user_id", "==", user_id)
        
        if competitor_id:
            query = query.where("competitor_id", "==", competitor_id)
        if event_type:
            query = query.where("type", "==", event_type)
        if min_impact:
            query = query.where("impact_score", ">=", min_impact)
        
        # Order and limit
        query = query.order_by("detected_at", direction="DESCENDING")
        
        # Fetch all matching for count
        all_docs = list(query.stream())
        total_count = len(all_docs)
        
        # Apply pagination
        paginated = all_docs[offset:offset + limit]
        
        events = []
        theme_counts = defaultdict(int)
        
        for doc in paginated:
            data = doc.to_dict()
            data["id"] = doc.id
            
            # Apply additional filters that Firestore can't handle
            if start_date and data.get("detected_at") and data["detected_at"] < start_date:
                continue
            if end_date and data.get("detected_at") and data["detected_at"] > end_date:
                continue
            if theme and theme.lower() not in [t.lower() for t in data.get("themes", [])]:
                continue
            if region and data.get("region") != region:
                continue
            
            events.append(CompetitorEvent(**data))
            
            # Count themes
            for t in data.get("themes", []):
                theme_counts[t] += 1
        
        # Build clusters summary
        clusters_summary = dict(theme_counts)
        
        return ListEventsResponse(
            events=events,
            total_count=total_count,
            clusters_summary=clusters_summary
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to list competitor events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/competitors/events/{event_id}")
async def get_competitor_event(
    event_id: str,
    user: dict = Depends(verify_token)
):
    """
    Get a single competitor event by ID.
    """
    try:
        user_id = user.get("uid")
        
        doc = db.collection("competitor_events").document(event_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Event not found")
        
        data = doc.to_dict()
        if data.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        data["id"] = doc.id
        return {"event": CompetitorEvent(**data)}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# THEME CLUSTERS ENDPOINTS
# =============================================================================

@router.get("/competitors/clusters", response_model=ListClustersResponse)
async def list_theme_clusters(
    time_range: str = Query("7d", description="7d, 30d, 90d"),
    min_priority: Optional[int] = Query(None, ge=1, le=10),
    regenerate: bool = Query(False, description="Force regenerate clusters"),
    user: dict = Depends(verify_token)
):
    """
    Get theme clusters for competitor events.
    
    Clusters group related events by theme and provide actionable insights.
    """
    try:
        user_id = user.get("uid")
        
        # Parse time range
        days = {"7d": 7, "30d": 30, "90d": 90}.get(time_range, 7)
        start_date = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()
        
        if regenerate:
            # Regenerate clusters from events
            clusters = await _generate_clusters(db, user_id, start_date, end_date)
        else:
            # Try to fetch existing clusters
            query = db.collection("theme_clusters")\
                .where("user_id", "==", user_id)\
                .where("time_range_start", ">=", start_date)
            
            if min_priority:
                query = query.where("priority", ">=", min_priority)
            
            docs = list(query.stream())
            
            if not docs:
                # No cached clusters, generate
                clusters = await _generate_clusters(db, user_id, start_date, end_date)
            else:
                clusters = [ThemeCluster(**{**doc.to_dict(), "id": doc.id}) for doc in docs]
        
        # Filter by priority if specified
        if min_priority:
            clusters = [c for c in clusters if c.priority >= min_priority]
        
        # Sort by priority
        clusters.sort(key=lambda c: c.priority, reverse=True)
        
        return ListClustersResponse(
            clusters=clusters,
            time_range={"start": start_date.isoformat(), "end": end_date.isoformat()}
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to list theme clusters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/competitors/clusters/{cluster_id}")
async def get_theme_cluster(
    cluster_id: str,
    include_events: bool = Query(True),
    user: dict = Depends(verify_token)
):
    """
    Get a single theme cluster with optionally embedded events.
    """
    try:
        user_id = user.get("uid")
        
        doc = db.collection("theme_clusters").document(cluster_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        data = doc.to_dict()
        if data.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        data["id"] = doc.id
        cluster = ThemeCluster(**data)
        
        events = []
        if include_events and cluster.event_ids:
            for event_id in cluster.event_ids[:20]:  # Limit embedded events
                event_doc = db.collection("competitor_events").document(event_id).get()
                if event_doc.exists:
                    event_data = event_doc.to_dict()
                    event_data["id"] = event_doc.id
                    events.append(CompetitorEvent(**event_data))
        
        return {"cluster": cluster, "events": events}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get cluster: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DIGEST GENERATION ENDPOINTS
# =============================================================================

@router.post("/competitors/digest", response_model=DigestResponse)
async def generate_weekly_digest(
    request: GenerateDigestRequest,
    user: dict = Depends(verify_token)
):
    """
    Generate a weekly digest of competitor activity.
    
    Manual trigger only - produces a summary report with top clusters and notable events.
    """
    try:
        user_id = user.get("uid")
        
        # Parse time range
        days = {"7d": 7, "30d": 30, "90d": 90}.get(request.time_range, 7)
        start_date = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()
        
        # Fetch events
        events_query = db.collection("competitor_events")\
            .where("user_id", "==", user_id)\
            .where("detected_at", ">=", start_date)\
            .order_by("detected_at", direction="DESCENDING")
        
        events_docs = list(events_query.stream())
        events = [CompetitorEvent(**{**doc.to_dict(), "id": doc.id}) for doc in events_docs]
        
        # Generate or fetch clusters
        clusters = await _generate_clusters(db, user_id, start_date, end_date)
        
        # Calculate metrics
        competitors_involved = set()
        high_impact_count = 0
        theme_counts = defaultdict(int)
        
        for event in events:
            competitors_involved.add(event.competitor_id)
            if event.impact_score >= 7:
                high_impact_count += 1
            for theme in event.themes:
                theme_counts[theme] += 1
        
        dominant_theme = max(theme_counts.keys(), key=lambda t: theme_counts[t]) if theme_counts else None
        
        metrics = DigestMetrics(
            total_events=len(events),
            competitors_active=len(competitors_involved),
            high_impact_events=high_impact_count,
            dominant_theme=dominant_theme
        )
        
        # Build executive summary
        summary = _generate_executive_summary(metrics, clusters, request.time_range)
        
        # Create digest
        digest_id = str(uuid.uuid4())
        digest = WeeklyDigest(
            id=digest_id,
            user_id=user_id,
            generated_at=datetime.utcnow(),
            time_range_start=start_date,
            time_range_end=end_date,
            time_range_label=request.time_range,
            executive_summary=summary,
            metrics=metrics,
            top_clusters=[c.id for c in clusters[:5]],
            notable_events=[e.id for e in sorted(events, key=lambda x: x.impact_score, reverse=True)[:5]],
            recommended_responses=_generate_recommended_responses(clusters)
        )
        
        # Save digest
        db.collection("weekly_digests").document(digest_id).set(digest.dict())
        
        # Log to BigQuery
        bq = get_bigquery_service()
        bq.insert_weekly_digest({
            "digest_id": digest_id,
            "user_id": user_id,
            "generated_at": datetime.utcnow().isoformat(),
            "time_range_start": start_date.isoformat(),
            "time_range_end": end_date.isoformat(),
            "time_range_label": request.time_range,
            "total_events": metrics.total_events,
            "competitors_active": metrics.competitors_active,
            "high_impact_events": metrics.high_impact_events,
            "dominant_theme": metrics.dominant_theme,
            "top_cluster_ids": [c.id for c in clusters[:5]],
            "notable_event_ids": [e.id for e in sorted(events, key=lambda x: x.impact_score, reverse=True)[:5]],
        })
        
        return DigestResponse(
            digest=digest,
            export_url=f"/competitors/digest/{digest_id}/export"
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to generate digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/competitors/digest/{digest_id}/export")
async def export_digest(
    digest_id: str,
    format: str = Query("html", description="html or pdf"),
    user: dict = Depends(verify_token)
):
    """
    Export a digest as HTML (or PDF if available).
    """
    try:
        user_id = user.get("uid")
        
        doc = db.collection("weekly_digests").document(digest_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Digest not found")
        
        data = doc.to_dict()
        if data.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        data["id"] = doc.id
        digest = WeeklyDigest(**data)
        
        # Generate HTML export
        html = _generate_html_export(digest, db)
        
        return {
            "digest_id": digest_id,
            "format": format,
            "content": html,
            "content_type": "text/html"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to export digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SCAN TRIGGER ENDPOINT
# =============================================================================

@router.post("/competitors/scan-now", response_model=ScanNowResponse)
async def trigger_competitor_scan(
    request: ScanNowRequest,
    user: dict = Depends(verify_token)
):
    """
    Trigger an immediate competitor scan.
    
    Queues a background job to fetch latest news/events for specified competitors.
    """
    try:
        user_id = user.get("uid")
        
        job_id = str(uuid.uuid4())
        
        # Create scan job
        job_data = {
            "job_id": job_id,
            "user_id": user_id,
            "competitor_ids": request.competitor_ids,
            "status": "queued",
            "created_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "events_found": 0,
            "error": None
        }
        
        db.collection("competitor_scan_jobs").document(job_id).set(job_data)
        
        # TODO: Trigger background worker (Cloud Tasks or async)
        # For now, return queued status
        
        logger.info(f"✅ Queued competitor scan job: {job_id}")
        
        return ScanNowResponse(
            job_id=job_id,
            status="queued",
            message="Competitor scan queued. Events will appear in the feed shortly."
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to trigger scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _generate_clusters(db, user_id: str, start_date: datetime, end_date: datetime) -> List[ThemeCluster]:
    """
    Generate theme clusters from events using keyword-based MVP algorithm.
    """
    # Fetch events
    events_query = db.collection("competitor_events")\
        .where("user_id", "==", user_id)\
        .where("detected_at", ">=", start_date)
    
    events_docs = list(events_query.stream())
    events = []
    for doc in events_docs:
        data = doc.to_dict()
        data["id"] = doc.id
        events.append(data)
    
    if not events:
        return []
    
    # Group events by theme
    theme_events = defaultdict(list)
    
    for event in events:
        event_text = f"{event.get('title', '')} {' '.join(event.get('themes', []))}".lower()
        
        matched = False
        for theme_name, keywords in THEME_KEYWORDS.items():
            if any(kw in event_text for kw in keywords):
                theme_events[theme_name].append(event)
                matched = True
                break
        
        if not matched:
            theme_events["Other"].append(event)
    
    # Create clusters
    clusters = []
    days = (end_date - start_date).days
    
    for theme_name, theme_event_list in theme_events.items():
        if not theme_event_list:
            continue
        
        cluster_id = str(uuid.uuid4())
        event_ids = [e["id"] for e in theme_event_list]
        competitors = list(set(e.get("competitor_name", e.get("competitor_id", "Unknown")) for e in theme_event_list))
        
        # Calculate priority based on event count and impact scores
        avg_impact = sum(e.get("impact_score", 5) for e in theme_event_list) / len(theme_event_list)
        priority = min(10, max(1, int((len(theme_event_list) / 3) + (avg_impact / 2))))
        
        # Generate insights
        why_it_matters = _generate_why_it_matters(theme_name, len(theme_event_list), days)
        suggested_actions = _generate_suggested_actions(theme_name)
        
        # Compute hash
        event_hashes = [e.get("event_hash", "") for e in theme_event_list]
        cluster_hash = compute_cluster_hash(theme_name, event_hashes)
        
        cluster = ThemeCluster(
            id=cluster_id,
            user_id=user_id,
            theme_name=theme_name,
            event_ids=event_ids,
            event_count=len(theme_event_list),
            competitors_involved=competitors,
            why_it_matters=why_it_matters,
            suggested_actions=suggested_actions,
            time_range_start=start_date,
            time_range_end=end_date,
            created_at=datetime.utcnow(),
            priority=priority,
            cluster_hash=cluster_hash
        )
        
        # Save cluster
        db.collection("theme_clusters").document(cluster_id).set(cluster.dict())
        
        clusters.append(cluster)
    
    return clusters


def _generate_why_it_matters(theme_name: str, count: int, days: int) -> str:
    """Generate 'why it matters' insight using templates."""
    template = INSIGHT_TEMPLATES.get(theme_name, {}).get("why", 
        f"{count} competitor event(s) detected in the '{theme_name}' category over the past {days} days.")
    
    return template.format(count=count, days=days, details="")


def _generate_suggested_actions(theme_name: str) -> List[str]:
    """Generate suggested actions using templates."""
    return INSIGHT_TEMPLATES.get(theme_name, {}).get("actions", [
        "Review the events for strategic implications",
        "Update your competitive positioning",
        "Brief relevant stakeholders"
    ])


def _generate_executive_summary(metrics: DigestMetrics, clusters: List[ThemeCluster], time_range: str) -> str:
    """Generate an executive summary for the digest."""
    summary_parts = [
        f"Over the past {time_range}, we detected {metrics.total_events} competitor event(s) "
        f"across {metrics.competitors_active} active competitor(s)."
    ]
    
    if metrics.high_impact_events > 0:
        summary_parts.append(f"{metrics.high_impact_events} event(s) were classified as high-impact (score ≥ 7).")
    
    if metrics.dominant_theme:
        summary_parts.append(f"The dominant theme was '{metrics.dominant_theme}'.")
    
    if clusters:
        top_cluster = max(clusters, key=lambda c: c.priority)
        summary_parts.append(f"Top priority: {top_cluster.theme_name} ({top_cluster.event_count} events).")
    
    return " ".join(summary_parts)


def _generate_recommended_responses(clusters: List[ThemeCluster]) -> List[str]:
    """Aggregate recommended responses from top clusters."""
    responses = []
    for cluster in sorted(clusters, key=lambda c: c.priority, reverse=True)[:3]:
        responses.extend(cluster.suggested_actions[:2])
    return list(dict.fromkeys(responses))[:5]  # Dedupe and limit


def _generate_html_export(digest: WeeklyDigest, db) -> str:
    """Generate an HTML export of the digest."""
    # Fetch clusters
    clusters_html = ""
    for cluster_id in digest.top_clusters[:5]:
        doc = db.collection("theme_clusters").document(cluster_id).get()
        if doc.exists:
            c = doc.to_dict()
            clusters_html += f"""
            <div style="border: 1px solid #ddd; padding: 16px; margin: 8px 0; border-radius: 8px;">
                <h3 style="margin: 0 0 8px 0;">{c.get('theme_name', 'Unknown')}</h3>
                <p style="color: #666;">{c.get('event_count', 0)} events • Priority: {c.get('priority', 5)}/10</p>
                <p><strong>Why it matters:</strong> {c.get('why_it_matters', '')}</p>
            </div>
            """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Market Radar Digest - {digest.time_range_label}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 24px; }}
            h1 {{ color: #1a1a1a; }}
            .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin: 24px 0; }}
            .metric {{ background: #f8f9fa; padding: 16px; border-radius: 8px; text-align: center; }}
            .metric-value {{ font-size: 2rem; font-weight: bold; color: #2563eb; }}
            .metric-label {{ color: #666; font-size: 0.9rem; }}
        </style>
    </head>
    <body>
        <h1>🎯 Market Radar Digest</h1>
        <p style="color: #666;">Generated: {digest.generated_at.strftime('%B %d, %Y')} • Period: {digest.time_range_label}</p>
        
        <h2>Executive Summary</h2>
        <p>{digest.executive_summary}</p>
        
        <h2>Key Metrics</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{digest.metrics.total_events}</div>
                <div class="metric-label">Total Events</div>
            </div>
            <div class="metric">
                <div class="metric-value">{digest.metrics.competitors_active}</div>
                <div class="metric-label">Active Competitors</div>
            </div>
            <div class="metric">
                <div class="metric-value">{digest.metrics.high_impact_events}</div>
                <div class="metric-label">High Impact</div>
            </div>
        </div>
        
        <h2>Top Theme Clusters</h2>
        {clusters_html if clusters_html else "<p>No clusters available.</p>"}
        
        <h2>Recommended Responses</h2>
        <ul>
            {"".join(f"<li>{r}</li>" for r in digest.recommended_responses)}
        </ul>
        
        <hr style="margin: 32px 0;">
        <p style="color: #999; font-size: 0.8rem;">Generated by ALI Market Radar • {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
    </body>
    </html>
    """
    
    return html

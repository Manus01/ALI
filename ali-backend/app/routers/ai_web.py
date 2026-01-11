from fastapi import APIRouter, Depends, Body, HTTPException, Query
from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import urlparse
import logging

from app.core.security import verify_token, db
from app.services.knowledge_packs_service import get_knowledge_packs_service
from app.services.web_search_client import WebSearchClient

logger = logging.getLogger(__name__)
router = APIRouter()


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


@router.post("/search")
async def web_search(payload: Dict = Body(...), user: dict = Depends(verify_token)):
    """
    Controlled web search endpoint.
    Input: { queryText: string, topicTags?: string[], maxResults?: int }
    """
    query_text = payload.get("queryText") or ""
    topic_tags = payload.get("topicTags") or []
    max_results = int(payload.get("maxResults", 20))

    if not query_text:
        raise HTTPException(status_code=400, detail="queryText is required")

    client = WebSearchClient()
    results = await client.search_web_mentions(
        brand_name=query_text,
        keywords=topic_tags,
        max_results=max_results
    )

    kp_service = get_knowledge_packs_service()
    for item in results:
        domain = _extract_domain(item.get("url", ""))
        tier = kp_service.get_credibility_tier(domain)
        item["domain"] = domain
        item["credibilityTier"] = tier.value
        item["credibilityScore"] = kp_service.calculate_credibility_score(domain, tier)

    return {"results": results}


@router.post("/extract")
async def web_extract(payload: Dict = Body(...), user: dict = Depends(verify_token)):
    """
    Create Knowledge Packs from extracted facts.
    Input: { topicTags: string[], facts: [{text, citation?}], sources?: [] }
    """
    topic_tags = payload.get("topicTags") or []
    facts_payload = payload.get("facts") or []
    sources = payload.get("sources") or []

    if not topic_tags:
        raise HTTPException(status_code=400, detail="topicTags is required")

    kp_service = get_knowledge_packs_service()
    facts = []

    for fact in facts_payload:
        text = fact.get("text")
        citation_data = fact.get("citation") or {}
        if not text or not citation_data:
            continue

        citation = kp_service.create_citation(
            url=citation_data.get("url", ""),
            domain=citation_data.get("domain") or _extract_domain(citation_data.get("url", "")),
            title=citation_data.get("title", ""),
            supporting_quote=citation_data.get("supporting_quote", ""),
            quote_context=citation_data.get("quote_context", ""),
            author=citation_data.get("author"),
            published_at=citation_data.get("published_at")
        )
        facts.append(kp_service.create_fact(text=text, citation=citation, topic_tags=topic_tags))

    if not facts:
        raise HTTPException(status_code=400, detail="facts are required to build a Knowledge Pack")

    pack = kp_service.create_knowledge_pack(
        user_id=user["uid"],
        topic_tags=topic_tags,
        facts=facts,
        sources=sources
    )

    return {"pack": pack.to_dict()}


@router.post("/monitor")
async def schedule_monitoring(payload: Dict = Body(...), user: dict = Depends(verify_token)):
    """
    Schedule monitoring jobs for topics or sources.
    Input: { topicTags?: string[], sources?: string[] }
    """
    topic_tags = payload.get("topicTags") or []
    sources = payload.get("sources") or []

    if not topic_tags and not sources:
        raise HTTPException(status_code=400, detail="topicTags or sources are required")

    job = {
        "userId": user["uid"],
        "topicTags": topic_tags,
        "sources": sources,
        "status": "scheduled",
        "createdAt": datetime.utcnow().isoformat()
    }

    if db:
        db.collection("ai_web_monitoring_jobs").add(job)

    return {"status": "scheduled", "job": job}


@router.post("/knowledge/query")
async def knowledge_query(payload: Dict = Body(...), user: dict = Depends(verify_token)):
    """
    Vector retrieval endpoint for Knowledge Packs.
    Input: { queryText: string, topK?: int, threshold?: float }
    """
    query_text = payload.get("queryText") or ""
    top_k = int(payload.get("topK", 10))
    threshold = float(payload.get("threshold", 0.78))

    if not query_text:
        raise HTTPException(status_code=400, detail="queryText is required")

    kp_service = get_knowledge_packs_service()
    results = kp_service.semantic_search(user_id=user["uid"], query=query_text, top_k=top_k)

    filtered = []
    for item in results:
        if item.get("similarity", 0) < threshold:
            continue
        citation = item.get("citation") or {}
        filtered.append({
            "chunkId": item.get("fact_id"),
            "factId": item.get("fact_id"),
            "packId": item.get("packId"),
            "textSnippet": item.get("text"),
            "topicTags": [],
            "confidenceScore": citation.get("confidence_score"),
            "similarityScore": item.get("similarity"),
            "citationObject": citation,
            "sourceCredibilityScore": citation.get("credibility_score")
        })

    return {"results": filtered}


@router.get("/packs/{pack_id}")
async def get_pack(pack_id: str, user: dict = Depends(verify_token)):
    kp_service = get_knowledge_packs_service()
    pack = kp_service.get_knowledge_pack(pack_id)

    if not pack or pack.user_id != user["uid"]:
        raise HTTPException(status_code=404, detail="Knowledge Pack not found")

    return {"pack": pack.to_dict()}


@router.get("/packs")
async def list_packs(
    topic_tags: Optional[str] = Query(default=None),
    user: dict = Depends(verify_token)
):
    kp_service = get_knowledge_packs_service()
    tags = [tag.strip() for tag in topic_tags.split(",")] if topic_tags else []

    if tags:
        packs = kp_service.search_packs_by_topic(user_id=user["uid"], topic_tags=tags, include_expired=True)
    elif kp_service.db:
        packs = []
        for doc in kp_service.db.collection("knowledge_packs").where("userId", "==", user["uid"]).stream():
            packs.append(doc.to_dict())
    else:
        packs = []

    return {"packs": packs}


@router.get("/monitor/alerts")
async def get_monitor_alerts(
    severity: Optional[str] = Query(default=None),
    user: dict = Depends(verify_token)
):
    if not db:
        return {"alerts": []}

    severity_filter = [s.strip().upper() for s in severity.split(",")] if severity else ["CRITICAL", "IMPORTANT"]
    alerts = []

    packs_query = db.collection("knowledge_packs").where("userId", "==", user["uid"]).stream()

    for pack_doc in packs_query:
        pack_data = pack_doc.to_dict()
        change_log = pack_data.get("changeLog", [])

        for change in change_log:
            change_severity = change.get("severity", "INFORMATIONAL")
            if change_severity not in severity_filter:
                continue

            detected_at = change.get("detectedAt") or ""
            alerts.append({
                "id": f"{pack_doc.id}_{detected_at}",
                "packId": pack_doc.id,
                "topicTags": pack_data.get("topicTags", []),
                "severity": change_severity,
                "summary": change.get("summary") or "Monitoring update detected.",
                "description": change.get("summary") or change.get("notes") or "Monitoring update detected.",
                "detectedAt": detected_at,
                "status": change.get("status", "NEW")
            })

    alerts.sort(key=lambda x: x.get("detectedAt") or "", reverse=True)
    return {"alerts": alerts[:50]}

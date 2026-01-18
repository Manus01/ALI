"""
Brand Monitoring Router
API endpoints for brand reputation monitoring, crisis management,
competitor tracking, and PR content generation.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import uuid
import asyncio
from datetime import datetime, timedelta
from urllib.parse import urlparse

from app.core.security import verify_token, db
from app.services.news_client import NewsClient
from app.services.web_search_client import WebSearchClient
from app.agents.brand_monitoring_agent import BrandMonitoringAgent
from app.agents.relevance_filter_agent import RelevanceFilterAgent
from app.agents.competitor_agent import CompetitorAgent
from app.agents.pr_agent import PRAgent
from app.agents.learning_agent import LearningAgent
from app.agents.protection_agent import ProtectionAgent
from app.types.deepfake_models import (
    DeepfakeAnalysis, DeepfakeJobStatus, DeepfakeVerdict, MediaType,
    DeepfakeSignal, DeepfakeCheckEnqueueRequest, DeepfakeCheckEnqueueResponse,
    DeepfakeCheckStatusResponse, get_verdict_from_score, get_verdict_label,
    get_verdict_explanation, get_verdict_action
)

router = APIRouter()
logger = logging.getLogger(__name__)


# --- Request/Response Models ---

class MentionRequest(BaseModel):
    brand_name: Optional[str] = None
    keywords: Optional[List[str]] = None
    max_results: Optional[int] = 10


class CrisisResponseRequest(BaseModel):
    article: Dict[str, Any]


class MonitoringSettingsRequest(BaseModel):
    brand_name: str
    keywords: Optional[List[str]] = []
    auto_monitor: Optional[bool] = True
    alert_threshold: Optional[int] = 5  # Severity threshold for alerts
    language: Optional[str] = "en"
    country: Optional[str] = None


class EntityConfigRequest(BaseModel):
    """Configuration for what entities to monitor."""
    monitoring_mode: str  # "company" | "personal" | "both"
    company_name: Optional[str] = None
    personal_name: Optional[str] = None
    strategic_agendas: Optional[List[str]] = []  # User's strategic goals


# Predefined strategic agenda options
STRATEGIC_AGENDA_OPTIONS = [
    {
        "id": "attract_clients",
        "label": "Attract New Clients",
        "description": "Focus on lead generation, testimonials, and success stories",
        "keywords": ["testimonial", "case study", "success", "recommendation", "referral"]
    },
    {
        "id": "competitive_advantage",
        "label": "Competitive Advantage",
        "description": "Highlight competitor weaknesses and your strengths",
        "keywords": ["better than", "alternative to", "vs", "comparison", "switch"]
    },
    {
        "id": "sustainability",
        "label": "Environmental & Sustainability",
        "description": "Showcase green initiatives and environmental consciousness",
        "keywords": ["sustainable", "eco-friendly", "green", "carbon", "environment", "ESG"]
    },
    {
        "id": "thought_leadership",
        "label": "Thought Leadership",
        "description": "Position as industry expert and innovator",
        "keywords": ["innovation", "expert", "pioneer", "future", "insights", "trends"]
    },
    {
        "id": "crisis_recovery",
        "label": "Crisis Recovery",
        "description": "Rebuild reputation and restore trust",
        "keywords": ["apology", "improvement", "commitment", "change", "transparency"]
    },
    {
        "id": "market_expansion",
        "label": "Market Expansion",
        "description": "Enter new markets or segments",
        "keywords": ["launch", "expansion", "new market", "growth", "partnership"]
    }
]


class CompetitorRequest(BaseModel):
    """Add a competitor to track."""
    name: str
    entity_type: Optional[str] = "company"  # "company" | "person"


class ContentGenerationRequest(BaseModel):
    """Request content generation for specified channels."""
    opportunity_id: Optional[str] = None
    mention: Optional[Dict[str, Any]] = None
    channels: List[str]  # e.g., ["linkedin", "press_release", "instagram"]
    agenda: Optional[str] = None  # Strategic agenda to guide content tone


# --- Endpoints ---

@router.post("/feedback")
async def submit_feedback(
    request: dict,  # generic dict to avoid strict validation issues for now, or define model
    user: dict = Depends(verify_token)
):
    """
    Submit user feedback (thumbs up/down) for a mention.
    This helps fine-tune future monitoring results.
    """
    user_id = user['uid']
    
    try:
        feedback_data = {
            "user_id": user_id,
            "mention_id": request.get("mention_id"), # URL or unique ID
            "title": request.get("title"),
            "snippet": request.get("snippet", ""),
            "feedback_type": request.get("feedback_type"), # 'positive' (relevant) or 'negative' (irrelevant)
            "timestamp": db.transaction().id  # Use transaction ID or server server_timestamp if available, or just ignore for now
        }
        
        # Store in a subcolumn for easy retrieval
        # Using URL hash or similar as ID would be better to avoid duplicates, but auto-id is fine for log
        import hashlib
        doc_id = hashlib.md5(f"{request.get('mention_id')}".encode()).hexdigest()
        
        db.collection('user_integrations').document(f"{user_id}_brand_monitoring")\
          .collection('feedback').document(doc_id).set(feedback_data)
        
        logger.info(f"✅ Feedback received from {user_id}: {request.get('feedback_type')}")
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"❌ Feedback submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mentions")
async def get_brand_mentions(
    brand_name: Optional[str] = None,
    topic: Optional[str] = None,  # NEW: Specific topic/keyword to search for
    max_results: int = 10,
    user: dict = Depends(verify_token)
):
    """
    Fetch and analyze brand mentions from news sources.
    Uses brand name from user profile if not provided.
    If 'topic' is provided, it searches for that specific topic instead of the brand name,
    but still applies global relevance filters.
    """
    user_id = user['uid']
    
    try:
        # Fetch full brand profile for disambiguation context
        brand_profile = {}
        brand_doc = db.collection('users').document(user_id).collection('brand_profile').document('current').get()
        if brand_doc.exists:
            brand_profile = brand_doc.to_dict()
        
        # Get brand name from request, profile, or fallback
        if not brand_name:
            brand_name = brand_profile.get('brand_name')
            
            # Fallback to user profile
            if not brand_name:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    brand_name = user_data.get('profile', {}).get('company_name', '')
        
        if not brand_name:
            return {
                "status": "no_brand",
                "message": "No brand name configured. Please complete onboarding or provide a brand name.",
                "mentions": []
            }
        
        # Determine the primary search query
        # If 'topic' is set (e.g. a specific keyword tab), we use it as the main search term.
        # Otherwise we use the brand_name.
        search_query = topic if topic else brand_name
        
        # Fetch stored settings for additional keywords and filters
        keywords = []
        language = "en"
        country = None
        
        settings_doc = db.collection('user_integrations').document(f"{user_id}_brand_monitoring").get()
        if settings_doc.exists:
            settings = settings_doc.to_dict()
            keywords = settings.get('keywords', [])
            language = settings.get('language', 'en')
            country = settings.get('country', None)

        # If we are searching for a specific topic, we don't need to append the other keywords to the query,
        # as that would muddy the specific tab's results.
        # However, we might want to keep them for context or relevance filtering if needed.
        # For now, if topic is present, we pass EMPTY keywords to NewsClient so it focuses on the topic.
        search_keywords = [] if topic else keywords

        # Fetch negative feedback (irrelevant articles) to filter out similar ones
        negative_examples = []
        feedback_docs = db.collection('user_integrations').document(f"{user_id}_brand_monitoring")\
                          .collection('feedback').where('feedback_type', '==', 'negative').limit(20).get()
        
        for doc in feedback_docs:
            data = doc.to_dict()
            negative_examples.append({
                "title": data.get("title"),
                "snippet": data.get("snippet")
            })

        # Fetch news mentions
        news_client = NewsClient()
        news_coroutine = news_client.search_brand_mentions(
            brand_name=search_query,  # Use search_query (topic or brand_name)
            keywords=search_keywords, # Use adjusted keywords list
            language=language,
            country=country,
            max_results=max_results
        )
        
        # Fetch broad web mentions (if enabled or just always for now)
        # We can perform these in parallel
        web_client = WebSearchClient()
        web_coroutine = web_client.search_web_mentions(
            brand_name=search_query,
            keywords=search_keywords,
            max_results=max_results
        )
        
        # Execute parallel fetches
        import asyncio
        news_results, web_results = await asyncio.gather(news_coroutine, web_coroutine, return_exceptions=True)
        
        # Handle potential errors in results
        articles = []
        if isinstance(news_results, list):
            articles.extend(news_results)
        else:
            logger.error(f"News fetch failed: {news_results}")
            
        if isinstance(web_results, list):
            articles.extend(web_results)
        else:
            logger.error(f"Web fetch failed: {web_results}")
        
        # Deduplicate by URL
        seen_urls = set()
        unique_articles = []
        for a in articles:
            if a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                unique_articles.append(a)
        
        # === AI RELEVANCE FILTERING (Entity Disambiguation) ===
        # Filter out articles that mention brand name/topic but are about different entities
        filter_agent = RelevanceFilterAgent()
        relevant_articles, filter_stats = await filter_agent.filter_articles(
            brand_profile=brand_profile,
            articles=unique_articles,
            feedback_patterns=negative_examples,  # Use negative feedback as disambiguation patterns
            monitoring_topic=search_query        # NEW: Specifically filter for the topic we searched for
        )
        
        logger.info(f"📊 Relevance filter: {filter_stats['relevant']}/{filter_stats['total']} articles kept ({filter_stats['filter_rate']}% filtered)")
        
        # Analyze sentiment only on relevant (filtered) articles
        monitoring_agent = BrandMonitoringAgent()
        analyzed_mentions = await monitoring_agent.analyze_mentions(
            brand_name=search_query,   # Analyze relevance to the specific topic if set
            articles=relevant_articles,
            negative_examples=[]  # Already filtered, no need to pass again
        )
        
        # Calculate summary stats
        negative_count = sum(1 for m in analyzed_mentions if m.get('sentiment') == 'negative')
        positive_count = sum(1 for m in analyzed_mentions if m.get('sentiment') == 'positive')
        
        # Check if there are critical alerts (severity >= 7)
        critical_alerts = [m for m in analyzed_mentions if (m.get('severity') or 0) >= 7]
        
        summary = {
            "total": len(analyzed_mentions),
            "positive": positive_count,
            "neutral": len(analyzed_mentions) - positive_count - negative_count,
            "negative": negative_count,
            "critical_alerts": len(critical_alerts)
        }
        
        return {
            "brand_name": brand_name,
            "keywords": keywords,
            "total_mentions": len(analyzed_mentions),
            "summary": summary,
            "mentions": analyzed_mentions,
            "has_critical": any((a.get("severity") or 0) >= 8 for a in analyzed_mentions),
            "filter_stats": filter_stats  # NEW: Show how many were filtered out
        }
        
    except Exception as e:
        logger.error(f"❌ Brand monitoring error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crisis-response")
async def get_crisis_response(
    request: CrisisResponseRequest,
    user: dict = Depends(verify_token)
):
    """
    Generate AI-powered crisis response suggestions for a negative mention.
    """
    user_id = user['uid']
    
    try:
        # Get brand context for personalized response
        brand_context = None
        brand_doc = db.collection('users').document(user_id).collection('brand_profile').document('current').get()
        if brand_doc.exists:
            brand_context = brand_doc.to_dict()
        
        # Generate crisis response
        monitoring_agent = BrandMonitoringAgent()
        response = await monitoring_agent.get_crisis_response(
            negative_mention=request.article,
            brand_context=brand_context
        )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Crisis response error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings")
async def get_monitoring_settings(user: dict = Depends(verify_token)):
    """
    Get current brand monitoring settings.
    """
    user_id = user['uid']
    
    try:
        settings_doc = db.collection('user_integrations').document(f"{user_id}_brand_monitoring").get()
        
        if settings_doc.exists:
            return {"status": "success", "settings": settings_doc.to_dict()}
        
        # Return defaults if no settings exist
        return {
            "status": "success",
            "settings": {
                "brand_name": "",
                "keywords": [],
                "auto_monitor": True,
                "alert_threshold": 5,
                "language": "en",
                "country": None
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Settings fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings")
async def update_monitoring_settings(
    request: MonitoringSettingsRequest,
    user: dict = Depends(verify_token)
):
    """
    Update brand monitoring settings.
    """
    user_id = user['uid']
    
    try:
        settings_data = {
            "brand_name": request.brand_name,
            "keywords": request.keywords or [],
            "auto_monitor": request.auto_monitor,
            "alert_threshold": request.alert_threshold,
            "language": request.language,
            "country": request.country,
            "user_id": user_id
        }
        
        db.collection('user_integrations').document(f"{user_id}_brand_monitoring").set(settings_data)
        
        logger.info(f"✅ Updated monitoring settings for user: {user_id}")
        return {"status": "success", "settings": settings_data}
        
    except Exception as e:
        logger.error(f"❌ Settings update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keywords/suggest")
async def suggest_keywords(
    user: dict = Depends(verify_token)
):
    """
    Generate AI suggestions for monitoring keywords.
    """
    user_id = user['uid']
    
    try:
        # Get brand profile
        brand_name = ""
        description = ""
        
        brand_doc = db.collection('users').document(user_id).collection('brand_profile').document('current').get()
        if brand_doc.exists:
            data = brand_doc.to_dict()
            brand_name = data.get('brand_name', '')
            description = data.get('description', '')
        
        if not brand_name:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                brand_name = user_doc.to_dict().get('profile', {}).get('company_name', '')

        if not brand_name:
            raise HTTPException(status_code=400, detail="Brand name required for suggestions")
        
        agent = BrandMonitoringAgent()
        suggestions = await agent.suggest_keywords(brand_name, description)
        
        return {"status": "success", "suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"❌ Keyword suggestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENTITY CONFIGURATION ENDPOINTS
# ============================================================================

@router.get("/entity-config")
async def get_entity_config(user: dict = Depends(verify_token)):
    """
    Get current entity monitoring configuration (company/personal/both).
    """
    user_id = user['uid']
    
    try:
        settings_doc = db.collection('user_integrations').document(f"{user_id}_brand_monitoring").get()
        
        if settings_doc.exists:
            data = settings_doc.to_dict()
            return {
                "status": "success",
                "config": {
                    "monitoring_mode": data.get('monitoring_mode', 'company'),
                    "company_name": data.get('company_name', data.get('brand_name', '')),
                    "personal_name": data.get('personal_name', ''),
                    "competitors": data.get('competitors', []),
                    "strategic_agendas": data.get('strategic_agendas', [])
                }
            }
        
        return {
            "status": "success",
            "config": {
                "monitoring_mode": "company",
                "company_name": "",
                "personal_name": "",
                "competitors": [],
                "strategic_agendas": []
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Entity config fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/entity-config")
async def update_entity_config(
    request: EntityConfigRequest,
    user: dict = Depends(verify_token)
):
    """
    Update entity monitoring configuration.
    """
    user_id = user['uid']
    
    try:
        doc_ref = db.collection('user_integrations').document(f"{user_id}_brand_monitoring")
        
        doc_ref.set({
            "monitoring_mode": request.monitoring_mode,
            "company_name": request.company_name,
            "personal_name": request.personal_name,
            "strategic_agendas": request.strategic_agendas or [],
            "user_id": user_id
        }, merge=True)
        
        logger.info(f"✅ Updated entity config for user: {user_id}")
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"❌ Entity config update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategic-agendas")
async def get_strategic_agendas():
    """
    Get available strategic agenda options.
    Users select from these to guide monitoring focus and content generation.
    """
    return {
        "status": "success",
        "agendas": STRATEGIC_AGENDA_OPTIONS
    }


# ============================================================================
# COMPETITOR MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/competitors")
async def get_competitors(user: dict = Depends(verify_token)):
    """
    Get list of tracked competitors.
    """
    user_id = user['uid']
    
    try:
        settings_doc = db.collection('user_integrations').document(f"{user_id}_brand_monitoring").get()
        
        competitors = []
        if settings_doc.exists:
            competitors = settings_doc.to_dict().get('competitors', [])
        
        return {"status": "success", "competitors": competitors}
        
    except Exception as e:
        logger.error(f"❌ Competitors fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/competitors")
async def add_competitor(
    request: CompetitorRequest,
    user: dict = Depends(verify_token)
):
    """
    Add a competitor to track.
    """
    user_id = user['uid']
    
    try:
        doc_ref = db.collection('user_integrations').document(f"{user_id}_brand_monitoring")
        doc = doc_ref.get()
        
        competitors = []
        if doc.exists:
            competitors = doc.to_dict().get('competitors', [])
        
        # Check limit (5 max)
        if len(competitors) >= 5:
            raise HTTPException(status_code=400, detail="Maximum 5 competitors allowed")
        
        # Check for duplicate
        if any(c.get('name', '').lower() == request.name.lower() for c in competitors):
            raise HTTPException(status_code=400, detail="Competitor already exists")
        
        competitors.append({
            "name": request.name,
            "type": request.entity_type,
            "added_by": "user"
        })
        
        doc_ref.set({"competitors": competitors, "user_id": user_id}, merge=True)
        
        logger.info(f"✅ Added competitor '{request.name}' for user: {user_id}")
        return {"status": "success", "competitors": competitors}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Add competitor error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/competitors/{name}")
async def remove_competitor(name: str, user: dict = Depends(verify_token)):
    """
    Remove a competitor from tracking.
    """
    user_id = user['uid']
    
    try:
        doc_ref = db.collection('user_integrations').document(f"{user_id}_brand_monitoring")
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="No competitors found")
        
        competitors = doc.to_dict().get('competitors', [])
        updated = [c for c in competitors if c.get('name', '').lower() != name.lower()]
        
        if len(updated) == len(competitors):
            raise HTTPException(status_code=404, detail="Competitor not found")
        
        doc_ref.set({"competitors": updated}, merge=True)
        
        logger.info(f"✅ Removed competitor '{name}' for user: {user_id}")
        return {"status": "success", "competitors": updated}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Remove competitor error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/competitors/suggest")
async def suggest_competitors(user: dict = Depends(verify_token)):
    """
    Get AI-powered competitor suggestions based on brand profile.
    """
    user_id = user['uid']
    
    try:
        # Get brand profile
        brand_profile = {}
        brand_doc = db.collection('users').document(user_id).collection('brand_profile').document('current').get()
        if brand_doc.exists:
            brand_profile = brand_doc.to_dict()
        
        if not brand_profile.get('brand_name'):
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                brand_profile['brand_name'] = user_data.get('profile', {}).get('company_name', '')
        
        if not brand_profile.get('brand_name'):
            raise HTTPException(status_code=400, detail="Brand profile required for suggestions")
        
        # Get existing competitors to exclude
        settings_doc = db.collection('user_integrations').document(f"{user_id}_brand_monitoring").get()
        existing = []
        entity_type = "company"
        if settings_doc.exists:
            data = settings_doc.to_dict()
            existing = [c.get('name') for c in data.get('competitors', [])]
            entity_type = data.get('monitoring_mode', 'company')
            if entity_type == 'both':
                entity_type = 'company'  # Default for suggestions
        
        agent = CompetitorAgent()
        suggestions = await agent.suggest_competitors(
            brand_profile=brand_profile,
            entity_type=entity_type,
            existing_competitors=existing,
            limit=5
        )
        
        return {"status": "success", "suggestions": suggestions}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Competitor suggestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PR OPPORTUNITY ENDPOINTS
# ============================================================================

@router.get("/opportunities")
async def get_pr_opportunities(user: dict = Depends(verify_token)):
    """
    Detect PR opportunities from recent mentions and competitor insights.
    """
    user_id = user['uid']
    
    try:
        # Get brand profile
        brand_profile = {}
        brand_doc = db.collection('users').document(user_id).collection('brand_profile').document('current').get()
        if brand_doc.exists:
            brand_profile = brand_doc.to_dict()
        
        # Fetch recent mentions (reuse existing logic)
        settings_doc = db.collection('user_integrations').document(f"{user_id}_brand_monitoring").get()
        settings = settings_doc.to_dict() if settings_doc.exists else {}
        
        brand_name = settings.get('company_name') or settings.get('brand_name') or brand_profile.get('brand_name', '')
        
        if not brand_name:
            return {"status": "success", "opportunities": [], "message": "Configure brand monitoring first"}
        
        # Fetch mentions
        news_client = NewsClient()
        web_client = WebSearchClient()
        
        import asyncio
        news_results, web_results = await asyncio.gather(
            news_client.search_brand_mentions(brand_name=brand_name, max_results=10),
            web_client.search_web_mentions(brand_name=brand_name, max_results=10),
            return_exceptions=True
        )
        
        mentions = []
        if isinstance(news_results, list):
            mentions.extend(news_results)
        if isinstance(web_results, list):
            mentions.extend(web_results)
        
        # Analyze sentiment
        monitoring_agent = BrandMonitoringAgent()
        analyzed = await monitoring_agent.analyze_mentions(brand_name, mentions[:20])
        
        # Detect opportunities
        pr_agent = PRAgent()
        opportunities = await pr_agent.detect_opportunities(
            mentions=analyzed,
            competitor_insights=[],  # TODO: Add competitor insights
            brand_profile=brand_profile
        )
        
        return {"status": "success", "opportunities": opportunities}
        
    except Exception as e:
        logger.error(f"❌ Opportunity detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CONTENT GENERATION ENDPOINTS
# ============================================================================

@router.post("/generate-content")
async def generate_pr_content(
    request: ContentGenerationRequest,
    user: dict = Depends(verify_token)
):
    """
    Generate PR content for specified channels based on a mention or opportunity.
    """
    user_id = user['uid']
    
    try:
        if not request.channels:
            raise HTTPException(status_code=400, detail="At least one channel required")
        
        # Get brand profile
        brand_profile = {}
        brand_doc = db.collection('users').document(user_id).collection('brand_profile').document('current').get()
        if brand_doc.exists:
            brand_profile = brand_doc.to_dict()
        
        pr_agent = PRAgent()
        
        # Build opportunity from request
        if request.mention:
            # Quick suggestion first
            angle = await pr_agent.suggest_response_angle(request.mention, brand_profile)
            
            opportunity = {
                "type": angle.get("recommendation", "engage"),
                "title": request.mention.get("title", "Brand Mention"),
                "description": request.mention.get("ai_summary", request.mention.get("description", "")),
                "key_message": "",
                "hashtags": []
            }
        else:
            opportunity = {
                "type": "engage",
                "title": "General PR Content",
                "description": "Content generation request",
                "key_message": "",
                "hashtags": []
            }
        
        content = await pr_agent.generate_content(
            opportunity=opportunity,
            channels=request.channels,
            brand_profile=brand_profile,
            strategic_agenda=request.agenda
        )
        
        return {"status": "success", "content": content, "agenda_applied": request.agenda}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Content generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-crisis-content")
async def generate_crisis_content(
    request: ContentGenerationRequest,
    user: dict = Depends(verify_token)
):
    """
    Generate crisis response content for specified channels.
    Integrates with existing crisis response system.
    """
    user_id = user['uid']
    
    try:
        if not request.mention:
            raise HTTPException(status_code=400, detail="Mention data required for crisis content")
        
        if not request.channels:
            raise HTTPException(status_code=400, detail="At least one channel required")
        
        # Get brand profile
        brand_profile = {}
        brand_doc = db.collection('users').document(user_id).collection('brand_profile').document('current').get()
        if brand_doc.exists:
            brand_profile = brand_doc.to_dict()
        
        # Get crisis response from existing agent
        monitoring_agent = BrandMonitoringAgent()
        crisis_response = await monitoring_agent.get_crisis_response(
            negative_mention=request.mention,
            brand_context=brand_profile
        )
        
        # Generate content
        pr_agent = PRAgent()
        content = await pr_agent.generate_crisis_content(
            crisis_mention=request.mention,
            crisis_response=crisis_response,
            channels=request.channels,
            brand_profile=brand_profile
        )
        
        return {
            "status": "success",
            "crisis_analysis": crisis_response,
            "content": content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Crisis content generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BRAND INTELLIGENCE ENDPOINTS
# ============================================================================

@router.get("/health-score")
async def get_brand_health_score(
    days: int = 30,
    user: dict = Depends(verify_token)
):
    """
    Get current brand health score (0-100) with trend data.
    
    Score Components:
    - Sentiment (40%): Average sentiment over period
    - Visibility (25%): Mention volume vs baseline
    - Response (20%): Actions taken effectiveness
    - Competitive (15%): Position vs competitors
    """
    user_id = user['uid']
    
    try:
        learning_agent = LearningAgent()
        result = await learning_agent.get_brand_health_score(user_id, days)
        
        return {
            "status": "success",
            **result
        }
        
    except Exception as e:
        logger.error(f"❌ Health score error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/geographic-insights")
async def get_geographic_insights(
    days: int = 30,
    user: dict = Depends(verify_token)
):
    """
    Get sentiment breakdown by country.
    
    Returns:
    - top_positive: Top 5 countries with positive sentiment
    - top_negative: Top 5 countries with negative sentiment
    - all_countries: Full country list for detailed report
    - total_countries: Count of countries with mentions
    """
    user_id = user['uid']
    
    try:
        learning_agent = LearningAgent()
        result = await learning_agent.get_geographic_insights(user_id, days)
        
        return {
            "status": "success",
            **result
        }
        
    except Exception as e:
        logger.error(f"❌ Geographic insights error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend-action")
async def recommend_action(
    request: Dict[str, Any],
    user: dict = Depends(verify_token)
):
    """
    Get AI-powered action recommendation based on historical data.
    
    Request body:
        mention: Dict - The mention to analyze
    
    Returns recommendation with confidence and reasoning based on past outcomes.
    """
    user_id = user['uid']
    mention = request.get('mention', {})
    
    if not mention:
        raise HTTPException(status_code=400, detail="Mention data required")
    
    try:
        # Get brand profile
        brand_profile = {}
        brand_doc = db.collection('users').document(user_id).collection('brand_profile').document('current').get()
        if brand_doc.exists:
            brand_profile = brand_doc.to_dict()
        
        learning_agent = LearningAgent()
        result = await learning_agent.recommend_action(user_id, mention, brand_profile)
        
        return {
            "status": "success",
            **result
        }
        
    except Exception as e:
        logger.error(f"❌ Action recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADVANCED PROTECTION ENDPOINTS
# ============================================================================

@router.post("/priority-actions")
async def get_priority_actions(
    request: Dict[str, Any],
    user: dict = Depends(verify_token)
):
    """
    Get prioritized list of mentions requiring action.
    
    Request body:
        mentions: List[Dict] - Mentions to score and prioritize
        max_items: int (optional) - Max items to return (default 10)
    
    Returns urgency-scored list with recommended actions.
    """
    mentions = request.get('mentions', [])
    max_items = request.get('max_items', 10)
    
    if not mentions:
        raise HTTPException(status_code=400, detail="Mentions list required")
    
    try:
        protection_agent = ProtectionAgent()
        priorities = await protection_agent.get_priority_actions(mentions, max_items)
        
        return {
            "status": "success",
            "total_analyzed": len(mentions),
            "priority_items": len(priorities),
            "actions": priorities
        }
        
    except Exception as e:
        logger.error(f"❌ Priority actions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deepfake-check")
async def enqueue_deepfake_check(
    request: DeepfakeCheckEnqueueRequest,
    user: dict = Depends(verify_token)
):
    """
    Enqueue media for deepfake analysis (async job).
    
    Rate Limits:
    - 10 requests per user per hour (normal priority)
    - 3 requests per user per hour (high priority)
    
    Returns job_id for polling status via GET /deepfake-check/{job_id}
    """
    user_id = user['uid']
    
    try:
        # === Rate Limit Check ===
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        jobs_ref = db.collection('users').document(user_id).collection('deepfake_jobs')
        
        # Count recent jobs
        recent_jobs = list(jobs_ref.where('created_at', '>=', one_hour_ago).stream())
        recent_count = len(recent_jobs)
        
        # Apply rate limits
        max_jobs = 3 if request.priority == "high" else 10
        if recent_count >= max_jobs:
            raise HTTPException(
                status_code=429, 
                detail=f"Rate limit exceeded. Maximum {max_jobs} {'high priority ' if request.priority == 'high' else ''}jobs per hour."
            )
        
        # === URL Validation ===
        parsed_url = urlparse(request.media_url)
        if parsed_url.scheme not in ('http', 'https'):
            raise HTTPException(status_code=400, detail="Only HTTP/HTTPS URLs are allowed")
        
        if not parsed_url.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        # Block internal IPs (basic check)
        hostname = parsed_url.hostname or ""
        if hostname in ('localhost', '127.0.0.1', '0.0.0.0') or hostname.startswith('192.168.') or hostname.startswith('10.'):
            raise HTTPException(status_code=400, detail="Internal URLs are not allowed")
        
        # === Create Job ===
        job_id = f"DFA-{uuid.uuid4().hex[:10].upper()}"
        now = datetime.utcnow()
        
        # Determine media type from URL if not provided
        media_type = request.media_type or "unknown"
        if media_type == "unknown":
            url_lower = request.media_url.lower()
            if any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                media_type = "image"
            elif any(ext in url_lower for ext in ['.mp4', '.webm', '.mov', '.avi']):
                media_type = "video"
            elif any(ext in url_lower for ext in ['.mp3', '.wav', '.ogg', '.m4a']):
                media_type = "audio"
        
        job_doc = {
            "id": job_id,
            "user_id": user_id,
            "media_ref": request.media_url,
            "media_type": media_type,
            "source_mention_id": request.mention_id,
            "status": "queued",
            "created_at": now,
            "priority": request.priority,
            "attach_to_evidence": request.attach_to_evidence,
            "confidence": None,
            "verdict": None,
            "verdict_label": None,
            "signals": [],
            "user_explanation": None,
            "recommended_action": None,
            "raw_output": None,
            "error_message": None,
            "started_at": None,
            "completed_at": None
        }
        
        jobs_ref.document(job_id).set(job_doc)
        logger.info(f"✅ Deepfake job {job_id} enqueued for user {user_id}")
        
        # === Trigger Background Processing ===
        # Use asyncio.create_task for fire-and-forget processing
        asyncio.create_task(_process_deepfake_job(user_id, job_id))
        
        return DeepfakeCheckEnqueueResponse(
            status="success",
            job_id=job_id,
            job_status="queued",
            estimated_wait_seconds=30,
            poll_url=f"/api/brand-monitoring/deepfake-check/{job_id}",
            message="Deepfake analysis job enqueued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Deepfake enqueue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deepfake-check/{job_id}")
async def get_deepfake_check_status(
    job_id: str,
    user: dict = Depends(verify_token)
):
    """
    Get current status and results of a deepfake analysis job.
    
    Status values:
    - queued: Waiting in queue
    - running: Analysis in progress
    - completed: Results available
    - failed: Analysis failed (check error field)
    
    Poll every 2-5 seconds while queued/running.
    """
    user_id = user['uid']
    
    try:
        job_ref = db.collection('users').document(user_id).collection('deepfake_jobs').document(job_id)
        doc = job_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job = doc.to_dict()
        
        # Verify ownership
        if job.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Calculate progress estimate for running jobs
        progress_pct = None
        if job.get('status') == 'running':
            started = job.get('started_at')
            if started:
                elapsed = (datetime.utcnow() - started).total_seconds()
                # Estimate 30 second completion time
                progress_pct = min(95, int((elapsed / 30) * 100))
        elif job.get('status') == 'completed':
            progress_pct = 100
        
        return DeepfakeCheckStatusResponse(
            status="success",
            job_id=job_id,
            job_status=job.get('status', 'unknown'),
            progress_pct=progress_pct,
            confidence=job.get('confidence'),
            verdict=job.get('verdict'),
            verdict_label=job.get('verdict_label'),
            signals=job.get('signals'),
            user_explanation=job.get('user_explanation'),
            recommended_action=job.get('recommended_action'),
            evidence_source_id=job.get('evidence_source_id'),
            error=job.get('error_message'),
            retry_allowed=job.get('status') == 'failed',
            created_at=job.get('created_at').isoformat() if job.get('created_at') else None,
            started_at=job.get('started_at').isoformat() if job.get('started_at') else None,
            completed_at=job.get('completed_at').isoformat() if job.get('completed_at') else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Deepfake status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_deepfake_job(user_id: str, job_id: str):
    """
    Background worker for deepfake analysis.
    
    State transitions: queued -> running -> completed/failed
    """
    job_ref = db.collection('users').document(user_id).collection('deepfake_jobs').document(job_id)
    
    try:
        # 1. Update status to RUNNING
        now = datetime.utcnow()
        job_ref.update({
            "status": "running",
            "started_at": now
        })
        
        job = job_ref.get().to_dict()
        logger.info(f"🔄 Processing deepfake job {job_id}")
        
        # 2. Perform analysis using existing ProtectionAgent
        protection_agent = ProtectionAgent()
        
        result = await protection_agent.detect_potential_deepfake({
            "url": job.get("media_ref", ""),
            "content_snippet": "",
            "title": "",
            "source_type": job.get("media_type", "unknown")
        })
        
        # 3. Map result to verdict
        risk_score = result.get("risk_score", 0)
        verdict = get_verdict_from_score(risk_score)
        verdict_label = get_verdict_label(verdict)
        user_explanation = get_verdict_explanation(verdict)
        recommended_action = get_verdict_action(verdict)
        
        # Add any specific indicators to explanation
        if result.get("indicators"):
            user_explanation += " " + result.get("recommendation", "")
        
        # 4. Build signals from indicators
        signals = []
        for i, indicator in enumerate(result.get("indicators", [])):
            severity = "high" if "deepfake" in indicator.lower() else "medium"
            signals.append({
                "signal_id": f"SIG-{i}",
                "signal_type": "keyword_match",
                "severity": severity,
                "description": indicator,
                "confidence": 0.7
            })
        
        # 5. Calculate confidence
        confidence = min(risk_score / 10.0, 1.0)
        
        # 6. Update job with results
        job_ref.update({
            "status": "completed",
            "completed_at": datetime.utcnow(),
            "confidence": confidence,
            "verdict": verdict.value if hasattr(verdict, 'value') else verdict,
            "verdict_label": verdict_label,
            "signals": signals,
            "user_explanation": user_explanation,
            "recommended_action": recommended_action,
            "raw_output": result
        })
        
        logger.info(f"✅ Deepfake job {job_id} completed: {verdict_label}")
        
        # 7. Auto-attach to evidence if requested and mention_id provided
        if job.get("attach_to_evidence") and job.get("source_mention_id"):
            try:
                await _attach_analysis_to_evidence(user_id, job_id, job.get("source_mention_id"))
            except Exception as attach_err:
                logger.warning(f"⚠️ Failed to attach analysis to evidence: {attach_err}")
        
    except Exception as e:
        logger.error(f"❌ Deepfake job {job_id} failed: {e}")
        job_ref.update({
            "status": "failed",
            "completed_at": datetime.utcnow(),
            "error_message": str(e)
        })


async def _attach_analysis_to_evidence(user_id: str, job_id: str, mention_id: str):
    """
    Link a completed deepfake analysis to an evidence source.
    
    This allows the analysis results to appear in Evidence Reports.
    """
    # TODO: Implement full evidence chain integration
    # For now, just log the linkage
    logger.info(f"📎 Attaching deepfake analysis {job_id} to mention {mention_id} for user {user_id}")
    
    # Update the job with evidence linkage info
    job_ref = db.collection('users').document(user_id).collection('deepfake_jobs').document(job_id)
    job_ref.update({
        "evidence_linked": True,
        "evidence_linked_at": datetime.utcnow()
    })


# === Legacy endpoint for backward compatibility ===
@router.post("/deepfake-check-sync")
async def check_for_deepfake_sync(
    request: Dict[str, Any],
    user: dict = Depends(verify_token)
):
    """
    [DEPRECATED] Synchronous deepfake check - use POST /deepfake-check for async.
    
    Kept for backward compatibility with existing integrations.
    """
    content = request.get('content', {})
    
    if not content:
        raise HTTPException(status_code=400, detail="Content required")
    
    try:
        protection_agent = ProtectionAgent()
        result = await protection_agent.detect_potential_deepfake(content)
        
        return {
            "status": "success",
            "deprecated": True,
            "message": "This endpoint is deprecated. Use POST /deepfake-check for async analysis.",
            **result
        }
        
    except Exception as e:
        logger.error(f"❌ Deepfake check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reporting-guidance/{platform}")
async def get_reporting_guidance(
    platform: str,
    violation_type: str = "defamation"
):
    """
    Get step-by-step instructions for reporting on a specific platform.
    
    Platforms: facebook, instagram, twitter (x), linkedin, tiktok, youtube
    Violation types: defamation, impersonation, harassment, spam
    """
    try:
        protection_agent = ProtectionAgent()
        result = protection_agent.get_reporting_guidance(platform, violation_type)
        
        return {
            "status": "success",
            **result
        }
        
    except Exception as e:
        logger.error(f"❌ Reporting guidance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evidence-report")
async def generate_evidence_report(
    request: Dict[str, Any],
    user: dict = Depends(verify_token)
):
    """
    Generate formal evidence report for legal/police filing with tamper-evident hash chain.
    
    Request body:
        mentions: List[Dict] - Evidence items to include
        report_purpose: str - "legal", "police", or "platform"
        save_report: bool - Whether to persist to Firestore (default: True)
    
    Response:
        report: EvidenceReport with items, sources, and hash chain
        chain_valid: bool - Whether hash chain verified successfully
        saved_id: str - Report ID if saved
    """
    user_id = user['uid']
    mentions = request.get('mentions', [])
    report_purpose = request.get('report_purpose', 'legal')
    save_report = request.get('save_report', True)
    
    if not mentions:
        raise HTTPException(status_code=400, detail="Mentions required for report")
    
    try:
        # Get brand name
        settings_doc = db.collection('user_integrations').document(f"{user_id}_brand_monitoring").get()
        brand_name = "Unknown Brand"
        if settings_doc.exists:
            data = settings_doc.to_dict()
            brand_name = data.get('company_name') or data.get('brand_name', brand_name)
        
        protection_agent = ProtectionAgent()
        report = await protection_agent.generate_evidence_report(
            mentions=mentions,
            brand_name=brand_name,
            report_purpose=report_purpose,
            user_id=user_id
        )
        
        saved_id = None
        
        # Optionally persist the report
        if save_report:
            try:
                report_ref = db.collection('users').document(user_id).collection('evidence_reports').document(report['id'])
                report_ref.set(report)
                saved_id = report['id']
                logger.info(f"✅ Evidence report {saved_id} saved for user {user_id}")
            except Exception as save_err:
                logger.warning(f"⚠️ Failed to save report: {save_err}")
        
        return {
            "status": "success",
            "report": report,
            "chain_valid": report.get("chain_valid", False),
            "saved_id": saved_id
        }
        
    except Exception as e:
        logger.error(f"❌ Evidence report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evidence-report/{report_id}")
async def get_evidence_report(
    report_id: str,
    user: dict = Depends(verify_token)
):
    """
    Retrieve a previously generated evidence report.
    
    Response:
        report: EvidenceReport
        chain_valid: bool - Re-verified on retrieval
    """
    user_id = user['uid']
    
    try:
        from app.types.evidence_models import verify_chain_integrity
        
        report_ref = db.collection('users').document(user_id).collection('evidence_reports').document(report_id)
        doc = report_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
        
        report = doc.to_dict()
        
        # Re-verify chain integrity on retrieval
        verification = verify_chain_integrity(report)
        report['chain_valid'] = verification['valid']
        report['chain_verified_at'] = verification['verified_at']
        
        if not verification['valid']:
            logger.warning(f"⚠️ Report {report_id} chain integrity issues: {verification['errors']}")
        
        return {
            "status": "success",
            "report": report,
            "chain_valid": verification['valid'],
            "verification_errors": verification['errors'] if not verification['valid'] else []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get evidence report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evidence-report/{report_id}/export")
async def export_evidence_report(
    report_id: str,
    request: Request,
    user: dict = Depends(verify_token)
):
    """
    Export evidence report as a downloadable ZIP package.
    
    ZIP Contents:
    - report.json: Full EvidenceReport object
    - sources.json: Flattened list of EvidenceSource objects (sorted, redacted)
    - integrity.json: Chain verification result with hash and algorithm
    - manifest.json: File list with SHA-256 checksums
    
    Response Headers:
    - Content-Type: application/zip
    - Content-Disposition: attachment; filename="evidence-{id}.zip"
    """
    user_id = user['uid']
    
    # Get correlation ID from request headers
    request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    
    try:
        from app.types.evidence_models import verify_chain_integrity
        from app.utils.zip_builder import build_evidence_package_zip, get_export_filename
        
        # Fetch the report
        report_ref = db.collection('users').document(user_id).collection('evidence_reports').document(report_id)
        doc = report_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
        
        report = doc.to_dict()
        
        # Re-verify chain integrity before export
        verification = verify_chain_integrity(report)
        report['chain_valid'] = verification['valid']
        report['chain_verified_at'] = verification['verified_at']
        
        if not verification['valid']:
            logger.warning(f"⚠️ Exporting report {report_id} with chain integrity issues: {verification['errors']}")
        
        # Build the ZIP package
        zip_bytes = build_evidence_package_zip(
            report=report,
            user_id=user_id,
            request_id=request_id
        )
        
        filename = get_export_filename(report)
        
        logger.info(f"📦 Evidence package exported: {filename}, {len(zip_bytes)} bytes, request_id={request_id}")
        
        # Return as downloadable attachment
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Request-ID": request_id,
                "X-Chain-Valid": str(verification['valid']).lower()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Export evidence report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evidence-report/verify")
async def verify_evidence_report(
    request: Dict[str, Any],
    user: dict = Depends(verify_token)
):
    """
    Verify hash chain integrity of a report.
    
    Request body:
        report: Dict - Direct report payload to verify
        OR
        report_id: str - ID of saved report to verify
    
    Response:
        valid: bool
        errors: List[str]
        verified_at: datetime
    """
    user_id = user['uid']
    
    try:
        from app.types.evidence_models import verify_chain_integrity
        
        report = request.get('report')
        report_id = request.get('report_id')
        
        if not report and not report_id:
            raise HTTPException(status_code=400, detail="Either 'report' or 'report_id' required")
        
        # Fetch report if ID provided
        if report_id and not report:
            report_ref = db.collection('users').document(user_id).collection('evidence_reports').document(report_id)
            doc = report_ref.get()
            if not doc.exists:
                raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
            report = doc.to_dict()
        
        # Verify the chain
        verification = verify_chain_integrity(report)
        
        # Count deepfake analyses in the report
        deepfake_count = sum(
            1 for item in report.get('items', [])
            for source in item.get('sources', [])
            if source.get('deepfake_analysis')
        )
        
        log_level = "✅" if verification['valid'] else "⚠️"
        logger.info(f"{log_level} Chain verification for report: valid={verification['valid']}, deepfake_analyses={deepfake_count}")
        
        return {
            "status": "success",
            "valid": verification['valid'],
            "errors": verification['errors'],
            "verified_at": verification['verified_at'],
            "report_id": report.get('id', report_id),
            "report_hash": report.get('report_hash', ''),
            "deepfake_analyses_included": deepfake_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Verify evidence report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evidence-reports")
async def list_evidence_reports(
    limit: int = 20,
    user: dict = Depends(verify_token)
):
    """
    List all evidence reports for the current user.
    
    Response:
        reports: List of report summaries (id, created_at, subject, total_incidents, chain_valid)
    """
    user_id = user['uid']
    
    try:
        reports_ref = db.collection('users').document(user_id).collection('evidence_reports')
        docs = reports_ref.order_by('created_at', direction='DESCENDING').limit(limit).stream()
        
        reports = []
        for doc in docs:
            data = doc.to_dict()
            reports.append({
                "id": data.get('id', doc.id),
                "created_at": data.get('created_at'),
                "subject": data.get('subject', 'Unknown'),
                "total_incidents": data.get('total_incidents', 0),
                "report_purpose": data.get('report_purpose', 'legal'),
                "chain_valid": data.get('chain_valid', None),
                "report_hash": data.get('report_hash', '')[:16] + '...' if data.get('report_hash') else ''
            })
        
        return {
            "status": "success",
            "reports": reports,
            "total": len(reports)
        }
        
    except Exception as e:
        logger.error(f"❌ List evidence reports error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LEARNING & AUTOMATION ENDPOINTS
# ============================================================================

@router.post("/log-action")
async def log_user_action(
    request: Dict[str, Any],
    user: dict = Depends(verify_token)
):
    """
    Log a user action for learning. This helps the AI improve over time.
    
    Request body:
        mention_id: str - The mention this action relates to
        action_type: str - "respond", "amplify", "ignore", "report", "escalate"
        channels: List[str] - Channels used (if any)
        agenda: str - Strategic agenda applied
        notes: str (optional) - User notes
    
    The system uses this data to:
    1. Learn which actions work best for different situations
    2. Improve future recommendations
    3. Build competitor playbooks
    """
    user_id = user['uid']
    
    try:
        from app.services.bigquery_service import log_action
        import uuid
        
        action_id = str(uuid.uuid4())
        
        success = log_action(
            action_id=action_id,
            user_id=user_id,
            action_type=request.get('action_type', 'unknown'),
            channels_used=request.get('channels', []),
            mention_id=request.get('mention_id'),
            strategic_agenda=request.get('agenda'),
            ai_suggested=request.get('ai_suggested', False),
            user_approved=True  # User took action = approved
        )
        
        return {
            "status": "success" if success else "warning",
            "action_id": action_id,
            "logged": success,
            "message": "Action logged for learning" if success else "Action recorded locally only"
        }
        
    except Exception as e:
        logger.error(f"❌ Action logging error: {e}")
        # Don't fail the request - logging is enhancement
        return {
            "status": "warning",
            "logged": False,
            "message": "Action completed but logging failed"
        }


@router.post("/log-outcome")
async def log_action_outcome(
    request: Dict[str, Any],
    user: dict = Depends(verify_token)
):
    """
    Log the outcome of an action (for learning effectiveness).
    
    Request body:
        action_id: str - The action this outcome relates to
        outcome_type: str - "effective", "ineffective", "neutral"
        metric_type: str (optional) - "engagement", "sentiment_shift", "resolution"
        metric_value: float (optional) - Measured value
        notes: str (optional) - User notes
    
    This feedback loop makes the system smarter over time.
    """
    user_id = user['uid']
    
    try:
        from app.services.bigquery_service import log_outcome
        import uuid
        
        outcome_id = str(uuid.uuid4())
        
        # Map user feedback to metric
        outcome_type = request.get('outcome_type', 'neutral')
        metric_value = {
            'effective': 1.0,
            'neutral': 0.5,
            'ineffective': 0.0
        }.get(outcome_type, 0.5)
        
        success = log_outcome(
            outcome_id=outcome_id,
            action_id=request.get('action_id', 'unknown'),
            user_id=user_id,
            metric_type=request.get('metric_type', 'user_feedback'),
            metric_value=request.get('metric_value', metric_value),
            user_feedback=outcome_type,
            auto_detected=False
        )
        
        return {
            "status": "success" if success else "warning",
            "outcome_id": outcome_id,
            "logged": success,
            "message": "Outcome logged - AI will learn from this!"
        }
        
    except Exception as e:
        logger.error(f"❌ Outcome logging error: {e}")
        return {
            "status": "warning",
            "logged": False,
            "message": "Feedback received but logging failed"
        }


# ============================================================================
# SCANNER & AUTOMATION ENDPOINTS
# Note: POST /scan-now is defined in ADAPTIVE SCANNING section below (line ~2111)
# ============================================================================


@router.get("/scan-status")
async def get_scan_status(
    user: dict = Depends(verify_token)
):
    """
    Get status of the hourly scanner for current user.
    Shows when last scan was run and when next is scheduled.
    """
    user_id = user['uid']
    
    try:
        from app.services.brand_monitoring_scanner import get_scanner
        from datetime import timedelta
        
        scanner = get_scanner()
        last_scan = scanner.last_scan.get(user_id)
        
        if last_scan:
            next_scan = last_scan + timedelta(hours=1)
            return {
                "status": "success",
                "last_scan": last_scan.isoformat(),
                "next_scan": next_scan.isoformat(),
                "scanner_active": True
            }
        else:
            return {
                "status": "success",
                "last_scan": None,
                "next_scan": "Will run on next hourly cycle",
                "scanner_active": True
            }
        
    except Exception as e:
        logger.error(f"❌ Scan status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SOURCES & CAPABILITIES
# ============================================================================

@router.get("/sources")
async def get_supported_sources():
    """
    Get list of all sources the system can search for mentions.
    Use this to display supported platforms in the frontend.
    """
    return {
        "status": "success",
        "mention_sources": [
            {
                "id": "news",
                "name": "News Articles",
                "description": "Major news outlets and publications worldwide",
                "icon": "📰",
                "active": True
            },
            {
                "id": "web",
                "name": "Web Search",
                "description": "Google Search results, blogs, and online mentions",
                "icon": "🌐",
                "active": True
            },
            {
                "id": "linkedin",
                "name": "LinkedIn",
                "description": "Professional network posts and mentions",
                "icon": "💼",
                "active": False,
                "coming_soon": True
            },
            {
                "id": "twitter",
                "name": "X (Twitter)",
                "description": "Tweets and social conversations",
                "icon": "🐦",
                "active": False,
                "coming_soon": True
            },
            {
                "id": "facebook",
                "name": "Facebook",
                "description": "Public posts and pages",
                "icon": "👥",
                "active": False,
                "coming_soon": True
            },
            {
                "id": "instagram",
                "name": "Instagram",
                "description": "Posts, stories, and comments",
                "icon": "📸",
                "active": False,
                "coming_soon": True
            },
            {
                "id": "tiktok",
                "name": "TikTok",
                "description": "Video content and comments",
                "icon": "🎵",
                "active": False,
                "coming_soon": True
            },
            {
                "id": "youtube",
                "name": "YouTube",
                "description": "Video mentions and comments",
                "icon": "▶️",
                "active": False,
                "coming_soon": True
            }
        ],
        "reporting_platforms": [
            {"id": "facebook", "name": "Facebook", "icon": "👥"},
            {"id": "instagram", "name": "Instagram", "icon": "📸"},
            {"id": "twitter", "name": "X (Twitter)", "icon": "🐦"},
            {"id": "linkedin", "name": "LinkedIn", "icon": "💼"},
            {"id": "tiktok", "name": "TikTok", "icon": "🎵"},
            {"id": "youtube", "name": "YouTube", "icon": "▶️"}
        ],
        "content_channels": [
            {"id": "press_release", "name": "Press Release", "icon": "📝"},
            {"id": "linkedin", "name": "LinkedIn", "icon": "💼"},
            {"id": "instagram", "name": "Instagram", "icon": "📸"},
            {"id": "facebook", "name": "Facebook", "icon": "👥"},
            {"id": "tiktok", "name": "TikTok", "icon": "🎵"},
            {"id": "twitter", "name": "X (Twitter)", "icon": "🐦"},
            {"id": "threads", "name": "Threads", "icon": "🧵"},
            {"id": "email", "name": "Email", "icon": "📧"},
            {"id": "blog", "name": "Blog Post", "icon": "✍️"}
        ],
        "scan_frequency": "Every hour",
        "data_retention": {
            "raw_data": "2 years (GDPR)",
            "patterns": "Indefinite (anonymized)"
        }
    }


# ============================================================================
# ADAPTIVE SCANNING ENDPOINTS
# ============================================================================

class ThresholdRuleRequest(BaseModel):
    """A single threshold rule for adaptive scanning."""
    min_score: int
    max_score: int
    interval_min: int  # minutes
    interval_max: int  # minutes
    label: str


class QuietHoursConfigRequest(BaseModel):
    """Quiet hours configuration."""
    enabled: bool = False
    start: str = "22:00"
    end: str = "07:00"
    interval_minutes: int = 360


class ScanPolicyUpdateRequest(BaseModel):
    """Request to update scan policy."""
    mode: Optional[str] = None  # "adaptive" | "fixed"
    fixed_interval_minutes: Optional[int] = None
    thresholds: Optional[List[ThresholdRuleRequest]] = None
    min_interval_minutes: Optional[int] = None
    max_interval_minutes: Optional[int] = None
    backoff_multiplier: Optional[float] = None
    quiet_hours: Optional[QuietHoursConfigRequest] = None
    manual_priority: Optional[str] = None  # "urgent" | "watch" | "normal"


@router.get("/scan-policy")
async def get_scan_policy(user: dict = Depends(verify_token)):
    """
    Get current scan policy and threat assessment.
    
    Returns:
        - Current policy configuration
        - Current threat score and breakdown
        - Next scan time and reason
        - Scan status
    """
    user_id = user['uid']
    
    try:
        from app.services.adaptive_scan_service import get_adaptive_scan_service
        
        service = get_adaptive_scan_service()
        
        # Get brand ID (for MVP, use user_id as brand_id)
        brand_id = user_id
        
        # Get policy
        policy = await service.get_policy(brand_id, user_id)
        
        # Calculate current threat
        assessment = await service.calculate_current_threat(brand_id, user_id)
        
        return {
            "status": "success",
            "policy": {
                "mode": policy.mode.value,
                "fixed_interval_minutes": policy.fixed_interval_ms // 60000,
                "thresholds": [t.to_dict() for t in policy.thresholds],
                "min_interval_minutes": policy.min_interval_ms // 60000,
                "max_interval_minutes": policy.max_interval_ms // 60000,
                "backoff_multiplier": policy.backoff_multiplier,
                "quiet_hours": policy.quiet_hours.to_dict(),
                "manual_priority": policy.manual_priority
            },
            "current_threat": {
                "score": assessment.score,
                "label": assessment.label.value,
                "breakdown": assessment.breakdown.to_dict(),
                "reason": assessment.reason
            },
            "schedule": {
                "last_scan_at": policy.last_scan_at.isoformat() if policy.last_scan_at else None,
                "next_scan_at": policy.next_scan_at.isoformat() if policy.next_scan_at else None,
                "next_scan_reason": assessment.reason,
                "next_scan_interval_minutes": assessment.interval_ms // 60000
            },
            "scan_status": "idle"  # TODO: Check for running scans
        }
        
    except Exception as e:
        logger.error(f"❌ Scan policy fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/scan-policy")
async def update_scan_policy(
    request: ScanPolicyUpdateRequest,
    user: dict = Depends(verify_token)
):
    """
    Update scan policy configuration.
    
    Args:
        request: Policy updates (partial update supported)
    
    Returns:
        Updated policy and recalculated threat assessment
    """
    user_id = user['uid']
    
    try:
        from app.services.adaptive_scan_service import get_adaptive_scan_service
        
        service = get_adaptive_scan_service()
        brand_id = user_id
        
        # Build updates dict from non-None values
        updates = {}
        if request.mode is not None:
            updates["mode"] = request.mode
        if request.fixed_interval_minutes is not None:
            updates["fixed_interval_minutes"] = request.fixed_interval_minutes
        if request.thresholds is not None:
            updates["thresholds"] = [t.dict() for t in request.thresholds]
        if request.min_interval_minutes is not None:
            updates["min_interval_minutes"] = request.min_interval_minutes
        if request.max_interval_minutes is not None:
            updates["max_interval_minutes"] = request.max_interval_minutes
        if request.backoff_multiplier is not None:
            updates["backoff_multiplier"] = request.backoff_multiplier
        if request.quiet_hours is not None:
            updates["quiet_hours"] = request.quiet_hours.dict()
        if request.manual_priority is not None:
            updates["manual_priority"] = request.manual_priority
        
        # Update policy
        policy = await service.update_policy(brand_id, user_id, updates)
        
        # Recalculate threat with new policy
        assessment = await service.calculate_current_threat(brand_id, user_id)
        
        logger.info(f"✅ Updated scan policy for user: {user_id}")
        
        return {
            "status": "success",
            "policy": {
                "mode": policy.mode.value,
                "fixed_interval_minutes": policy.fixed_interval_ms // 60000,
                "thresholds": [t.to_dict() for t in policy.thresholds],
                "min_interval_minutes": policy.min_interval_ms // 60000,
                "max_interval_minutes": policy.max_interval_ms // 60000,
                "backoff_multiplier": policy.backoff_multiplier,
                "quiet_hours": policy.quiet_hours.to_dict(),
                "manual_priority": policy.manual_priority
            },
            "current_threat": {
                "score": assessment.score,
                "label": assessment.label.value,
                "reason": assessment.reason
            },
            "schedule": {
                "next_scan_at": policy.next_scan_at.isoformat() if policy.next_scan_at else None,
                "next_scan_interval_minutes": assessment.interval_ms // 60000
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Scan policy update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scan-telemetry")
async def get_scan_telemetry(
    hours: int = 24,
    user: dict = Depends(verify_token)
):
    """
    Get scan execution history and metrics for the last N hours.
    
    Args:
        hours: Hours of history to fetch (default 24)
    
    Returns:
        - Scan history timeline
        - Aggregated metrics (duration, failures, etc.)
        - Queue depth
        - Health indicators
    """
    user_id = user['uid']
    
    try:
        from app.services.adaptive_scan_service import get_adaptive_scan_service
        from datetime import datetime
        
        service = get_adaptive_scan_service()
        brand_id = user_id
        
        # Get scan history
        history = await service.get_scan_history(brand_id, user_id, hours=hours)
        
        # Calculate metrics
        total_scans = len(history)
        successful_scans = [h for h in history if h.get("status") == "success"]
        failed_scans = [h for h in history if h.get("status") == "failed"]
        
        avg_duration_ms = 0
        if successful_scans:
            avg_duration_ms = sum(h.get("duration_ms", 0) for h in successful_scans) / len(successful_scans)
        
        # Find last successful scan
        last_successful = None
        for h in history:
            if h.get("status") == "success":
                last_successful = h.get("completed_at")
                break
        
        # Count consecutive failures
        consecutive_failures = 0
        for h in history:
            if h.get("status") == "failed":
                consecutive_failures += 1
            else:
                break
        
        # Get pending jobs count
        pending_jobs = await service.get_pending_jobs_count(brand_id)
        
        return {
            "status": "success",
            "scan_history": history[:50],  # Limit to 50 entries
            "metrics": {
                "total_scans_24h": total_scans,
                "successful_scans": len(successful_scans),
                "failed_scans": len(failed_scans),
                "avg_duration_ms": int(avg_duration_ms),
                "avg_duration_seconds": round(avg_duration_ms / 1000, 1)
            },
            "queue": {
                "pending_jobs": pending_jobs
            },
            "health": {
                "last_successful_scan": last_successful,
                "consecutive_failures": consecutive_failures,
                "status": "healthy" if consecutive_failures < 3 else "degraded" if consecutive_failures < 5 else "unhealthy"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Scan telemetry error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan-now")
async def trigger_manual_scan(user: dict = Depends(verify_token)):
    """
    Trigger an immediate manual scan.
    
    This bypasses the adaptive scheduler and executes a scan immediately.
    The next scheduled scan will be recalculated after this scan completes.
    
    Returns:
        Job information and results summary
    """
    user_id = user['uid']
    
    try:
        from app.services.adaptive_scan_service import get_adaptive_scan_service
        
        service = get_adaptive_scan_service()
        brand_id = user_id
        
        logger.info(f"🔍 Manual scan triggered by user: {user_id}")
        
        # Trigger manual scan
        job = await service.trigger_manual_scan(brand_id, user_id)
        
        return {
            "status": "success",
            "message": "Scan completed",
            "job": {
                "job_id": job.job_id,
                "trigger_reason": job.trigger_reason.value,
                "status": job.status,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "result_summary": job.result_summary
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Manual scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

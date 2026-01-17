"""
Brand Monitoring Router
API endpoints for brand reputation monitoring, crisis management,
competitor tracking, and PR content generation.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from app.core.security import verify_token, db
from app.services.news_client import NewsClient
from app.services.web_search_client import WebSearchClient
from app.agents.brand_monitoring_agent import BrandMonitoringAgent
from app.agents.relevance_filter_agent import RelevanceFilterAgent
from app.agents.competitor_agent import CompetitorAgent
from app.agents.pr_agent import PRAgent
from app.agents.learning_agent import LearningAgent
from app.agents.protection_agent import ProtectionAgent

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
async def check_for_deepfake(
    request: Dict[str, Any],
    user: dict = Depends(verify_token)
):
    """
    Analyze content for potential deepfake/AI-generated indicators.
    
    Request body:
        content: Dict - The content to analyze (title, url, content_snippet)
    """
    content = request.get('content', {})
    
    if not content:
        raise HTTPException(status_code=400, detail="Content required")
    
    try:
        protection_agent = ProtectionAgent()
        result = await protection_agent.detect_potential_deepfake(content)
        
        return {
            "status": "success",
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
    Generate formal evidence report for legal/police filing.
    
    Request body:
        mentions: List[Dict] - Evidence items to include
        report_purpose: str - "legal", "police", or "platform"
    """
    user_id = user['uid']
    mentions = request.get('mentions', [])
    report_purpose = request.get('report_purpose', 'legal')
    
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
            report_purpose=report_purpose
        )
        
        return {
            "status": "success",
            "report": report
        }
        
    except Exception as e:
        logger.error(f"❌ Evidence report error: {e}")
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
# ============================================================================

@router.post("/scan-now")
async def trigger_scan_now(
    user: dict = Depends(verify_token)
):
    """
    Manually trigger a scan for the current user.
    Use this to get immediate results instead of waiting for hourly scan.
    """
    user_id = user['uid']
    
    try:
        from app.services.brand_monitoring_scanner import trigger_manual_scan
        
        # Get user config
        settings_doc = db.collection('user_integrations').document(f"{user_id}_brand_monitoring").get()
        
        if not settings_doc.exists:
            raise HTTPException(status_code=400, detail="Brand monitoring not configured")
        
        config = settings_doc.to_dict()
        result = await trigger_manual_scan(user_id, config)
        
        return {
            "status": "success",
            "scan_result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Manual scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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



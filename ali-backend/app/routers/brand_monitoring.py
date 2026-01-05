"""
Brand Monitoring Router
API endpoints for brand reputation monitoring and crisis management.
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
    max_results: int = 10,
    user: dict = Depends(verify_token)
):
    """
    Fetch and analyze brand mentions from news sources.
    Uses brand name from user profile if not provided.
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
            brand_name=brand_name,
            keywords=keywords,
            language=language,
            country=country,
            max_results=max_results
        )
        
        # Fetch broad web mentions (if enabled or just always for now)
        # We can perform these in parallel
        web_client = WebSearchClient()
        web_coroutine = web_client.search_web_mentions(
            brand_name=brand_name,
            keywords=keywords,
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
        # Filter out articles that mention brand name but are about different entities
        filter_agent = RelevanceFilterAgent()
        relevant_articles, filter_stats = await filter_agent.filter_articles(
            brand_profile=brand_profile,
            articles=unique_articles,
            feedback_patterns=negative_examples  # Use negative feedback as disambiguation patterns
        )
        
        logger.info(f"📊 Relevance filter: {filter_stats['relevant']}/{filter_stats['total']} articles kept ({filter_stats['filter_rate']}% filtered)")
        
        # Analyze sentiment only on relevant (filtered) articles
        monitoring_agent = BrandMonitoringAgent()
        analyzed_mentions = await monitoring_agent.analyze_mentions(
            brand_name=brand_name, 
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

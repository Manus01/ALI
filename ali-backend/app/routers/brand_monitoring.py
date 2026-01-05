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
from app.agents.brand_monitoring_agent import BrandMonitoringAgent

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


# --- Endpoints ---

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
        # Get brand name from request or user profile
        if not brand_name:
            # Try to get from brand profile
            brand_doc = db.collection('users').document(user_id).collection('brand_profile').document('current').get()
            if brand_doc.exists:
                brand_data = brand_doc.to_dict()
                brand_name = brand_data.get('brand_name')
            
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
        
        # Fetch stored settings for additional keywords
        keywords = []
        settings_doc = db.collection('user_integrations').document(f"{user_id}_brand_monitoring").get()
        if settings_doc.exists:
            settings = settings_doc.to_dict()
            keywords = settings.get('keywords', [])

        # Fetch news mentions
        news_client = NewsClient()
        articles = await news_client.search_brand_mentions(
            brand_name=brand_name,
            keywords=keywords,
            max_results=max_results
        )
        
        # Analyze sentiment
        monitoring_agent = BrandMonitoringAgent()
        analyzed_mentions = await monitoring_agent.analyze_mentions(brand_name, articles)
        
        # Calculate summary stats
        negative_count = sum(1 for m in analyzed_mentions if m.get('sentiment') == 'negative')
        positive_count = sum(1 for m in analyzed_mentions if m.get('sentiment') == 'positive')
        
        # Check if there are critical alerts (severity >= 7)
        critical_alerts = [m for m in analyzed_mentions if m.get('severity', 0) >= 7]
        
        return {
            "status": "success",
            "brand_name": brand_name,
            "summary": {
                "total": len(analyzed_mentions),
                "positive": positive_count,
                "neutral": len(analyzed_mentions) - positive_count - negative_count,
                "negative": negative_count,
                "critical_alerts": len(critical_alerts)
            },
            "mentions": analyzed_mentions,
            "has_critical": len(critical_alerts) > 0
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
                "alert_threshold": 5
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

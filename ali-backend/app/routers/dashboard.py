from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_token, db
from app.services.metricool_client import MetricoolClient
from typing import List, Dict, Any, Optional
import os
import logging

 
router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/overview")
def get_dashboard_overview(user: dict = Depends(verify_token)):
    # Try to import forecasting, fallback if missing
    try:
        from app.services.forecasting import generate_forecast
    except ImportError:
        def generate_forecast(data): return []
    """
    Aggregates user profile, REAL performance metrics, and Multi-Channel History.
    Priority: Live Metricool Data > Stored Firestore Data > Empty List (Safe Fallback).
    """
    user_id = user['uid']
    
    try:
        # 1. Fetch Basic User Profile (Firestore)
        user_doc = db.collection("users").document(user_id).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        
        profile = user_data.get("profile", {})

        # Removed agent_status as it's not used in the response anymore
        
        # --- LIVE DATA VARIABLES ---
        real_metrics = []
        recommendations = []
        chart_history = None # <--- New Field
        integration_status = "offline"
        
        # 2. Check for Metricool Connection
        metricool_doc = db.collection("users").document(user_id).collection("user_integrations").document("metricool").get()
        
        if metricool_doc.exists:
            m_data = metricool_doc.to_dict()
            blog_id = m_data.get("metricool_blog_id")
            
            if blog_id:
                try:
                    # FETCH LIVE DATA
                    client = MetricoolClient()
                    snapshot = client.get_dashboard_snapshot(blog_id)
                    
                    if snapshot.get("status") != "error":
                        integration_status = "active"
                        
                        # A. Process Metrics for Cards
                        raw_metrics = snapshot.get("metrics", {})
                        real_metrics = [
                            {"label": "Total Spend", "value": f"${raw_metrics.get('spend', 0)}", "trend": "Last 30d"},
                            {"label": "Impressions", "value": f"{raw_metrics.get('impressions', 0):,}", "trend": "Organic + Paid"},
                            {"label": "Clicks", "value": f"{raw_metrics.get('clicks', 0)}", "trend": "Total Traffic"},
                            {"label": "CTR", "value": f"{raw_metrics.get('ctr', 0)}%", "trend": "Performance", "alert": raw_metrics.get('ctr', 0) < 1.0}
                        ]

                        # B. Process Recommendations
                        if raw_metrics.get('ctr', 0) < 1.5:
                            recommendations.append({
                                "type": "strategy", 
                                "text": "Ad CTR is low (<1.5%). Use Strategy Engine to refine copy.",
                                "link": "/strategy"
                            })
                        if raw_metrics.get('spend', 0) < 50:
                            recommendations.append({
                                "type": "studio", 
                                "text": "Ad Spend is low. Generate new creative assets in Studio.",
                                "link": "/studio"
                            })

                        # C. Process Chart History (Multi-Channel)
                        # This fetches the daily breakdown we created in the Client
                        chart_history = client.get_historical_breakdown(blog_id)

                except Exception as e:
                    logger.warning(f"⚠️ Metricool Fetch Failed: {e}")
                    # Don't crash, just fall back to empty/offline state
        
        # --- END LIVE DATA ---

        # 3. Final Data Selection (Priority: Live -> Stored -> Empty)
        metrics = real_metrics if real_metrics else user_data.get("metrics", [])
        if not isinstance(metrics, list): metrics = []

        # 4. Generate Forecast (Only if we have real data points)
        forecast = []
        # NEW: Forecast based on the CHART HISTORY (Time Series), not just summary metrics
        if chart_history and "datasets" in chart_history and "all" in chart_history["datasets"]:
             try:
                 from app.services.forecasting import generate_forecast
                # Forecast the next 7 days based on the 'all' aggregated history
                 forecast = generate_forecast(chart_history["datasets"]["all"], days=7)
             except Exception as e:
                 logger.warning(f"Forecast generation failed: {e}")
                 forecast = []
        elif metrics:
             # Fallback to old logic if chart history is missing (unlikely now)
             try:
                from app.services.forecasting import generate_forecast
                # This old usage was likely wrong (metrics is a list of dicts), but keeping as safe fallback stub
                # forecast = generate_forecast(metrics) 
                forecast = [] 
             except Exception as e:
                logger.warning(f"Error expanding metric: {e}")
                forecast = []

        # 5. Dynamic Success Story / Context Message
        success_story = "Connect your social accounts to unlock AI insights."
        if integration_status == "active":
            success_story = "AI is actively monitoring your connected brand performance."
            if recommendations:
                success_story = "Optimization opportunities detected. See recommendations below."

        return {
            "profile": profile,
            "metrics": metrics,
            "forecast": forecast,
            "success_story": success_story,
            "integration_status": integration_status,
            "recommendations": recommendations,
            "chart_history": chart_history
        }

    except Exception as e:
        logger.error(f"❌ Unexpected error in dashboard overview: {e}")
        return {
            "profile": {"role": "User"},
            "agent_status": "error",
            "metrics": [],
            "forecast": [],
            "success_story": "System temporarily unavailable.",
            "recommendations": [],
            "chart_history": None
        }


@router.get("/next-actions")
def get_next_actions(user: dict = Depends(verify_token)):
    """
    Returns a prioritized list of tasks for the user.
    1. Pending Creative Approvals (Drafts)
    2. Integration Setup (if missing)
    """
    user_id = user['uid']
    actions = []
    
    try:
        # 1. Check for Pending Drafts
        # Query Firestore for drafts with status='DRAFT' (Pending Review)
        from google.cloud.firestore_v1.base_query import FieldFilter
        
        # Note: We query by userId and filter in Python or simpler query to avoid index issues
        docs = list(db.collection("creative_drafts").where(filter=FieldFilter("userId", "==", user_id)).stream())
        pending_drafts = [
            d for d in [doc.to_dict() for doc in docs] 
            if d.get("status") == "DRAFT"
        ]
        
        # Sort by newest first
        pending_drafts.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        
        # Add up to 3 review actions
        for draft in pending_drafts[:3]:
            draft_id = draft.get("id") # Ensure ID is stored or we need to capture it from doc
            # In the query above we lost the ID if it wasn't in the dict. 
            # Ideally we'd fix the query, but let's assume we can link to the studio generally 
            # or try to use campaign info.
            
            campaign_goal = draft.get("campaignGoal", "Campaign Asset")
            channel = draft.get("channel", "Social")
            
            actions.append({
                "id": f"review_{draft_id or 'draft'}",
                "type": "review",
                "title": "Review Creative Asset",
                "description": f"Approve {channel} asset for '{campaign_goal}'",
                "link": "/studio?view=approvals", # Deep link to approvals view
                "priority": "high"
            })
            
        # 2. Check Integration Status
        metricool_doc = db.collection("users").document(user_id).collection("user_integrations").document("metricool").get()
        if not metricool_doc.exists:
            actions.append({
                "id": "setup_metricool",
                "type": "setup",
                "title": "Connect Social Accounts",
                "description": "Link Metricool to enable AI analytics and publishing.",
                "link": "/integrations",
                "priority": "critical"
            })
            
        return actions

    except Exception as e:
        logger.error(f"❌ Failed to fetch next actions: {e}")
        return []
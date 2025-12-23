import os
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Metricool Agency Keys (Admin Level)
METRICOOL_USER_TOKEN = os.getenv("METRICOOL_USER_TOKEN")
METRICOOL_USER_ID = os.getenv("METRICOOL_USER_ID")
BASE_URL = "https://app.metricool.com/api"

class MetricoolClient:
    def __init__(self):
        if not METRICOOL_USER_TOKEN or not METRICOOL_USER_ID:
            raise ValueError("METRICOOL credentials missing.")
        
        self.headers = {
            "X-Mc-Auth": METRICOOL_USER_TOKEN,
            "Content-Type": "application/json"
        }
        self.user_id = METRICOOL_USER_ID

    # --- PUBLISHING ---
    def normalize_media(self, media_url: str) -> str:
        """Uploads media to Metricool before posting."""
        url = f"{BASE_URL}/actions/normalize/image/url"
        params = {"userId": self.user_id, "url": media_url}
        try:
            res = requests.post(url, headers=self.headers, params=params)
            res.raise_for_status()
            data = res.json()
            return data.get('url') or data.get('mediaId') or media_url
        except Exception as e:
            logger.error(f"Media Normalization Failed: {e}")
            raise ValueError(f"Media processing failed: {e}")

    def publish_post(self, blog_id: str, text: str, media_url: str = None) -> Dict[str, Any]:
        """Publishes a post to the user's specific Brand ID."""
        # Normalize media if present
        metricool_media = self.normalize_media(media_url) if media_url else None
        
        url = f"{BASE_URL}/v2/scheduler/posts"
        payload = {
            "blogId": int(blog_id),
            "userId": int(self.user_id),
            "post": {
                "text": text,
                "type": "status",
                "status": "published",
                "publicationDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "media": [metricool_media] if metricool_media else [],
                "providers": ["facebook", "instagram", "linkedin", "twitter"] # Default set
            }
        }
        
        try:
            res = requests.post(url, headers=self.headers, json=payload)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.HTTPError as e:
            raise ValueError(f"Metricool Post Failed: {res.text}")

    # --- RESEARCH DATA FETCHING ---
    def get_yesterday_stats(self, blog_id: str) -> Dict[str, float]:
        """
        Fetches a simplified snapshot of YESTERDAY'S performance across all networks.
        Used for the nightly research log.
        """
        # Calculate 'Yesterday' date range
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # NOTE: Metricool analytics endpoints vary by network. 
        # For this implementation, we assume a 'summary' or iterate top platforms.
        # This acts as a consolidated fetcher.
        
        # Example: Fetching Instagram (Organic + Ads)
        # In a real impl, you would call GET /stats/instagram, GET /stats/facebook, etc.
        # and sum them up. For this stub, we return aggregate placeholders 
        # that mimic the structure you need for the PhD analysis.
        
        url = f"{BASE_URL}/stats/summary" # Hypothetical unified endpoint or logic wrapper
        params = {
            "blogId": blog_id, 
            "from": yesterday, 
            "to": yesterday, 
            "userId": self.user_id
        }
        
        try:
            # res = requests.get(url, headers=self.headers, params=params)
            # data = res.json()
            
            # MOCKING RESPONSE to ensure downstream logic works (Replace with real calls)
            # In production, replace this dict with the parsed JSON from Metricool
            return {
                "total_spend": 120.50,   # From Ads
                "total_clicks": 340,     # From Organic + Ads
                "impressions": 15000,
                "ctr": 2.25              # Calculated or retrieved
            }
        except Exception as e:
            logger.error(f"Stats Fetch Failed: {e}")
            return {"total_spend": 0, "total_clicks": 0, "impressions": 0, "ctr": 0}
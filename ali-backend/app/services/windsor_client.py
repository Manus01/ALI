import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ali_platform.services.windsor_client")

class WindsorClient:
    """
    Client for Windsor.ai API to fetch multi-channel marketing data.
    """
    BASE_URL = "https://connect.windsor.ai/api"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Windsor API Key is required.")
        self.api_key = api_key

    def fetch_metrics(self, connector: str, days_lookback: int = 30) -> List[Dict[str, Any]]:
        """
        Fetches connectors data (e.g., 'facebook', 'google_ads', 'tiktok').
        
        Args:
            connector (str): The data source identifier (e.g., 'facebook', 'tiktok')
            days_lookback (int): Number of days to look back.
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_lookback)
        
        # Windsor API params structure (Standardized)
        params = {
            "api_key": self.api_key,
            "date_from": start_date.strftime("%Y-%m-%d"),
            "date_to": end_date.strftime("%Y-%m-%d"),
            "fields": "date,campaign,clicks,spend,impressions,ctr,cpc",
            "_renderer": "json"
        }

        # Handling connector-specific endpoints if necessary, 
        # but Windsor usually aggregates via the main connector URL pattern.
        # Assuming format: https://connect.windsor.ai/{connector}/json?api_key=...
        
        # However, the StrategyAgent passed "meta_ads" which might map to "facebook".
        # We'll map common internal names to Windsor connectors.
        connector_map = {
            "meta_ads": "facebook",
            "google_ads": "google_ads",
            "tiktok_ads": "tiktok",
            "linkedin_ads": "linkedin"
        }
        
        target_connector = connector_map.get(connector, connector)
        
        # Construct URL
        # Docs: https://connect.windsor.ai/
        # They usually offer a unified endpoint or specific ones. 
        # Let's use the standard connector endpoint pattern.
        url = f"https://connect.windsor.ai/{target_connector}"

        try:
            logger.info(f"🔌 Fetching Windsor Data for: {target_connector} ({days_lookback} days)")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # Windsor returns a list of objects usually.
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            elif isinstance(data, list):
                return data
                
            return []

        except Exception as e:
            logger.error(f"❌ Windsor.ai Fetch Error: {e}")
            # Non-blocking failure: return empty list so Agent can handle it gracefully
            return []

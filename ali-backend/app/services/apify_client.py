"""
Apify Client Service
Pay-as-you-go social media scraping via Apify actors.

Pricing (approximate):
- Facebook posts: $0.01/post
- Instagram posts: $0.50/1k posts
- LinkedIn posts: $1/1k posts
- Twitter/X posts: $2/1k posts
- TikTok posts: $1/1k posts

Free tier: $5/month in credits
"""
import os
import logging
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Apify API token
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
APIFY_BASE_URL = "https://api.apify.com/v2"

# Pre-built Apify actor IDs for social media scraping
APIFY_ACTORS = {
    "facebook": {
        "actor_id": "apify/facebook-posts-scraper",
        "name": "Facebook",
        "icon": "👥",
        "cost_per_1k": 10  # $0.01 per post = $10 per 1k
    },
    "instagram": {
        "actor_id": "apify/instagram-scraper",
        "name": "Instagram",
        "icon": "📸",
        "cost_per_1k": 0.50
    },
    "linkedin": {
        "actor_id": "curious_coder/linkedin-post-search-scraper",
        "name": "LinkedIn",
        "icon": "💼",
        "cost_per_1k": 1
    },
    "twitter": {
        "actor_id": "apidojo/tweet-scraper",
        "name": "X (Twitter)",
        "icon": "🐦",
        "cost_per_1k": 2
    },
    "tiktok": {
        "actor_id": "clockworks/tiktok-scraper",
        "name": "TikTok",
        "icon": "🎵",
        "cost_per_1k": 1
    }
}


class ApifyClient:
    """
    Client for Apify social media scraping actors.
    
    Usage:
    1. Sign up at apify.com (free tier includes $5/month)
    2. Get API token from Settings -> Integrations -> API
    3. Set APIFY_API_TOKEN environment variable
    """
    
    def __init__(self):
        self.api_token = APIFY_API_TOKEN
        self.base_url = APIFY_BASE_URL
        
        if not self.api_token:
            logger.warning("⚠️ APIFY_API_TOKEN not set - Apify scraping disabled")
    
    async def search_platform(
        self,
        platform: str,
        search_query: str,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search a social media platform for mentions.
        
        Args:
            platform: Platform ID (facebook, instagram, linkedin, twitter, tiktok)
            search_query: Brand name or keyword to search
            max_results: Maximum results to return
            
        Returns:
            List of post/mention objects
        """
        if not self.api_token:
            logger.warning("Apify API token not configured")
            return []
        
        if platform not in APIFY_ACTORS:
            logger.warning(f"Unknown platform: {platform}")
            return []
        
        actor_config = APIFY_ACTORS[platform]
        
        try:
            logger.info(f"🔍 Searching {actor_config['name']} via Apify for: {search_query}")
            
            # Run the actor
            run_url = f"{self.base_url}/acts/{actor_config['actor_id']}/runs"
            
            # Build input based on actor requirements
            actor_input = self._build_actor_input(platform, search_query, max_results)
            
            async with aiohttp.ClientSession() as session:
                # Start the actor run
                async with session.post(
                    run_url,
                    params={"token": self.api_token},
                    json=actor_input
                ) as response:
                    if response.status != 201:
                        error = await response.text()
                        logger.error(f"Apify actor start failed: {error}")
                        return []
                    
                    run_data = await response.json()
                    run_id = run_data.get("data", {}).get("id")
                
                if not run_id:
                    logger.error("No run ID returned from Apify")
                    return []
                
                # Wait for run to complete (with timeout)
                import asyncio
                for _ in range(30):  # Max 30 attempts (30 seconds)
                    await asyncio.sleep(1)
                    
                    status_url = f"{self.base_url}/actor-runs/{run_id}"
                    async with session.get(
                        status_url,
                        params={"token": self.api_token}
                    ) as status_response:
                        status_data = await status_response.json()
                        status = status_data.get("data", {}).get("status")
                        
                        if status == "SUCCEEDED":
                            break
                        elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                            logger.error(f"Apify run failed with status: {status}")
                            return []
                
                # Get results from dataset
                dataset_id = status_data.get("data", {}).get("defaultDatasetId")
                if not dataset_id:
                    return []
                
                dataset_url = f"{self.base_url}/datasets/{dataset_id}/items"
                async with session.get(
                    dataset_url,
                    params={"token": self.api_token, "limit": max_results}
                ) as dataset_response:
                    items = await dataset_response.json()
            
            # Normalize results
            results = self._normalize_results(platform, items, actor_config)
            
            logger.info(f"✅ Found {len(results)} results on {actor_config['name']}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Apify {platform} search failed: {e}")
            return []
    
    def _build_actor_input(
        self,
        platform: str,
        search_query: str,
        max_results: int
    ) -> Dict[str, Any]:
        """Build actor-specific input configuration."""
        
        # Each actor has different input requirements
        if platform == "facebook":
            return {
                "searchQueries": [search_query],
                "resultsLimit": max_results
            }
        elif platform == "instagram":
            return {
                "search": search_query,
                "resultsLimit": max_results,
                "searchType": "hashtag"  # or "user"
            }
        elif platform == "linkedin":
            return {
                "searchTerms": [search_query],
                "maxResults": max_results
            }
        elif platform == "twitter":
            return {
                "searchTerms": [search_query],
                "maxTweets": max_results
            }
        elif platform == "tiktok":
            return {
                "searchQueries": [search_query],
                "resultsPerPage": max_results
            }
        
        return {"query": search_query, "limit": max_results}
    
    def _normalize_results(
        self,
        platform: str,
        items: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Normalize actor results to standard mention format."""
        results = []
        
        for item in items:
            # Extract common fields (actors have different schemas)
            result = {
                "id": item.get("id") or item.get("url") or str(hash(str(item))),
                "title": item.get("text", item.get("caption", item.get("title", "")))[:200],
                "content": item.get("text") or item.get("caption") or item.get("description") or "",
                "description": (item.get("text") or item.get("caption") or "")[:500],
                "url": item.get("url") or item.get("postUrl") or item.get("link") or "",
                "source": "apify",
                "source_type": platform,
                "source_name": config["name"],
                "source_icon": config["icon"],
                "author": item.get("authorName") or item.get("username") or item.get("author") or "",
                "author_url": item.get("authorUrl") or item.get("profileUrl") or "",
                "likes": item.get("likes") or item.get("likesCount") or 0,
                "comments": item.get("comments") or item.get("commentsCount") or 0,
                "shares": item.get("shares") or item.get("sharesCount") or 0,
                "published_at": item.get("timestamp") or item.get("date") or datetime.utcnow().isoformat(),
                "platform": platform,
                "is_social_result": True,
                "raw_data": item  # Keep original for debugging
            }
            
            results.append(result)
        
        return results
    
    async def search_all_platforms(
        self,
        search_query: str,
        platforms: Optional[List[str]] = None,
        max_results_per_platform: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search all configured platforms for mentions.
        
        Args:
            search_query: Brand name or keyword
            platforms: List of platforms to search (default: all)
            max_results_per_platform: Max results per platform
            
        Returns:
            Combined list of mentions from all platforms
        """
        if platforms is None:
            platforms = list(APIFY_ACTORS.keys())
        
        import asyncio
        
        # Run searches in parallel
        tasks = [
            self.search_platform(platform, search_query, max_results_per_platform)
            for platform in platforms
        ]
        
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        for result in results_lists:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Platform search failed: {result}")
        
        logger.info(f"📊 Total Apify results: {len(all_results)}")
        return all_results


# Singleton instance
_client: Optional[ApifyClient] = None


def get_apify_client() -> ApifyClient:
    """Get or create singleton Apify client."""
    global _client
    if _client is None:
        _client = ApifyClient()
    return _client

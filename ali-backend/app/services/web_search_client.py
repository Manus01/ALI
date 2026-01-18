"""
Web Search Client Service
Integrates with DuckDuckGo Search (via duckduckgo-search package) for broad web monitoring.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

class WebSearchClient:
    """
    Client for performing broad web searches (forums, blogs, reddit, etc.).
    """
    
    def __init__(self):
        self.ddgs = DDGS()
        
    async def search_web_mentions(
        self, 
        brand_name: str, 
        keywords: Optional[List[str]] = None,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search the web for brand mentions using DuckDuckGo.
        
        Args:
            brand_name: The brand to search for
            keywords: Additional context keywords
            max_results: Max results to return
            
        Returns:
            List of simplified article objects
        """
        try:
            # Construct a broad query
            # e.g. "BrandName" (review OR complained OR scam OR launched OR announced)
            # For now, let's keep it simple to ensure hits
            query = f'"{brand_name}"'
            if keywords:
                # Add keywords as OR conditions if there are any, or just append them if deemed necessary context
                # To be safe and broad: "BrandName" (keyword1 OR keyword2)
                keywords_str = " OR ".join([f'"{k}"' for k in keywords[:5]]) # limit to 5 keywords
                if keywords_str:
                    query += f' ({keywords_str})'
            
            # Perform search (synchronous call wrapped if needed, DDGS is sync usually but fast)
            # Note: duckduckgo_search might block, usually fine for this scale or should be run in executor
            logger.info(f"🔍 Web searching for: {query}")
            
            results = []
            # 'text' search gives standard web results
            ddg_results = self.ddgs.text(query, max_results=max_results)
            
            for r in ddg_results:
                # Convert to our standard format
                # DDGS results: {'title':..., 'href':..., 'body':...}
                results.append({
                    "id": r.get('href'), # URL as ID
                    "title": r.get('title'),
                    "source": "web_search",
                    "source_name": self._extract_domain(r.get('href')),
                    "content": r.get('body', ''),
                    "description": r.get('body', ''),
                    "url": r.get('href'),
                    "published_at": datetime.utcnow().isoformat(), # DDFS doesn't always give date
                    "is_web_result": True
                })
                
            logger.info(f"✅ Found {len(results)} web results for {brand_name}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Web search failed: {e}")
            return []

    def _extract_domain(self, url: str) -> str:
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.replace('www.', '')
        except Exception:
            logger.debug("Domain extraction failed")
            return "Web Result"

    # Social media platform configurations for site-specific searches
    SOCIAL_PLATFORMS = {
        "linkedin": {
            "site": "linkedin.com",
            "name": "LinkedIn",
            "icon": "💼"
        },
        "facebook": {
            "site": "facebook.com",
            "name": "Facebook", 
            "icon": "👥"
        },
        "twitter": {
            "site": "twitter.com OR site:x.com",
            "name": "X (Twitter)",
            "icon": "🐦"
        },
        "instagram": {
            "site": "instagram.com",
            "name": "Instagram",
            "icon": "📸"
        },
        "tiktok": {
            "site": "tiktok.com",
            "name": "TikTok",
            "icon": "🎵"
        }
    }

    async def search_social_mentions(
        self,
        brand_name: str,
        platforms: Optional[List[str]] = None,
        max_results_per_platform: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for brand mentions on social media platforms using site-specific queries.
        
        Args:
            brand_name: The brand to search for
            platforms: List of platform IDs (linkedin, facebook, twitter, instagram, tiktok)
                      If None, searches all platforms
            max_results_per_platform: Max results per platform
            
        Returns:
            List of mentions with platform attribution
        """
        if platforms is None:
            platforms = list(self.SOCIAL_PLATFORMS.keys())
        
        all_results = []
        
        for platform_id in platforms:
            if platform_id not in self.SOCIAL_PLATFORMS:
                logger.warning(f"Unknown platform: {platform_id}")
                continue
                
            platform = self.SOCIAL_PLATFORMS[platform_id]
            
            try:
                # Build site-specific query
                query = f'"{brand_name}" site:{platform["site"]}'
                
                logger.info(f"🔍 Searching {platform['name']} for: {brand_name}")
                
                ddg_results = self.ddgs.text(query, max_results=max_results_per_platform)
                
                for r in ddg_results:
                    all_results.append({
                        "id": r.get('href'),
                        "title": r.get('title'),
                        "source": "social_search",
                        "source_type": platform_id,
                        "source_name": platform["name"],
                        "source_icon": platform["icon"],
                        "content": r.get('body', ''),
                        "description": r.get('body', ''),
                        "url": r.get('href'),
                        "published_at": datetime.utcnow().isoformat(),
                        "is_social_result": True,
                        "platform": platform_id
                    })
                
                logger.info(f"✅ Found {len(ddg_results)} results on {platform['name']}")
                
            except Exception as e:
                logger.error(f"❌ {platform['name']} search failed: {e}")
                continue
        
        logger.info(f"📊 Total social mentions found: {len(all_results)}")
        return all_results


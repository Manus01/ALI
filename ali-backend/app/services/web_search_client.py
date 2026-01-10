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

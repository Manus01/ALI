"""
News API Client Service
Integrates with NewsData.io for brand mention aggregation.
"""
import os
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class NewsClient:
    """
    Client for fetching news articles mentioning a brand.
    Uses NewsData.io API (free tier: 200 requests/day).
    """
    
    def __init__(self):
        self.api_key = os.getenv("NEWSDATA_API_KEY", "")
        self.base_url = "https://newsdata.io/api/1/latest"
        
    async def search_brand_mentions(
        self, 
        brand_name: str, 
        keywords: Optional[List[str]] = None,
        language: str = "en",
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for news articles mentioning the brand.
        
        Args:
            brand_name: The primary brand name to search for
            keywords: Additional keywords to include in search
            language: Language code (default: en)
            max_results: Maximum number of articles to return
            
        Returns:
            List of article dictionaries with title, source, content, url, date
        """
        if not self.api_key:
            logger.warning("⚠️ NEWSDATA_API_KEY not configured, using mock data")
            return self._get_mock_data(brand_name)
        
        try:
            # Build search query
            query_parts = [brand_name]
            if keywords:
                query_parts.extend(keywords)
            query = " OR ".join(query_parts)
            
            params = {
                "apikey": self.api_key,
                "q": query,
                "language": language,
                "size": min(max_results, 10)  # API limit per request
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=15) as response:
                    if response.status != 200:
                        logger.error(f"NewsData API error: {response.status}")
                        return self._get_mock_data(brand_name)
                    
                    data = await response.json()
                    
                    if data.get("status") != "success":
                        logger.error(f"NewsData API returned error: {data.get('results', {})}")
                        return self._get_mock_data(brand_name)
                    
                    articles = []
                    for item in data.get("results", []):
                        articles.append({
                            "id": item.get("article_id", ""),
                            "title": item.get("title", ""),
                            "source": item.get("source_id", "Unknown"),
                            "source_name": item.get("source_name", "Unknown Source"),
                            "content": item.get("content") or item.get("description", ""),
                            "description": item.get("description", ""),
                            "url": item.get("link", ""),
                            "image_url": item.get("image_url", ""),
                            "published_at": item.get("pubDate", ""),
                            "category": item.get("category", []),
                            "country": item.get("country", [])
                        })
                    
                    logger.info(f"✅ Fetched {len(articles)} articles for brand: {brand_name}")
                    return articles
                    
        except Exception as e:
            logger.error(f"❌ NewsData API request failed: {e}")
            return self._get_mock_data(brand_name)
    
    def _get_mock_data(self, brand_name: str) -> List[Dict[str, Any]]:
        """
        Returns mock data for development/testing when API is unavailable.
        Includes mix of positive, neutral, and negative mentions for testing.
        """
        now = datetime.utcnow()
        
        return [
            {
                "id": "mock_001",
                "title": f"{brand_name} Reports Record-Breaking Quarter",
                "source": "business_insider",
                "source_name": "Business Insider",
                "content": f"{brand_name} announced exceptional quarterly results, exceeding analyst expectations with a 25% increase in revenue. The company's strategic initiatives have positioned it as a market leader.",
                "description": f"Strong financial performance drives {brand_name} stock to new highs.",
                "url": "https://example.com/article1",
                "image_url": "",
                "published_at": (now - timedelta(hours=2)).isoformat(),
                "category": ["business"],
                "country": ["us"]
            },
            {
                "id": "mock_002",
                "title": f"{brand_name} Launches New Product Line",
                "source": "techcrunch",
                "source_name": "TechCrunch",
                "content": f"{brand_name} has unveiled its latest product lineup at their annual conference. Industry experts are analyzing the potential market impact.",
                "description": f"New products from {brand_name} hit the market.",
                "url": "https://example.com/article2",
                "image_url": "",
                "published_at": (now - timedelta(hours=5)).isoformat(),
                "category": ["technology"],
                "country": ["us"]
            },
            {
                "id": "mock_003",
                "title": f"Customer Complaints Mount Against {brand_name}",
                "source": "consumer_reports",
                "source_name": "Consumer Reports",
                "content": f"A growing number of customers have expressed frustration with {brand_name}'s customer service response times. Social media complaints have increased 40% this month. Critics say the company needs to address quality control issues immediately.",
                "description": f"Customers report issues with {brand_name} service quality.",
                "url": "https://example.com/article3",
                "image_url": "",
                "published_at": (now - timedelta(hours=8)).isoformat(),
                "category": ["business"],
                "country": ["us"]
            },
            {
                "id": "mock_004",
                "title": f"{brand_name} Faces Regulatory Scrutiny Over Data Practices",
                "source": "reuters",
                "source_name": "Reuters",
                "content": f"Regulators have launched an investigation into {brand_name}'s data handling practices following whistleblower allegations. The company could face significant fines if violations are confirmed. This scandal threatens to damage the brand's reputation.",
                "description": f"Investigation launched into {brand_name} data practices.",
                "url": "https://example.com/article4",
                "image_url": "",
                "published_at": (now - timedelta(hours=12)).isoformat(),
                "category": ["politics", "business"],
                "country": ["us", "eu"]
            },
            {
                "id": "mock_005",
                "title": f"{brand_name} Partners with Leading University",
                "source": "education_today",
                "source_name": "Education Today",
                "content": f"{brand_name} announced a strategic partnership with MIT to advance research in artificial intelligence. The collaboration will create internship opportunities for students.",
                "description": f"Academic partnership strengthens {brand_name} innovation pipeline.",
                "url": "https://example.com/article5",
                "image_url": "",
                "published_at": (now - timedelta(days=1)).isoformat(),
                "category": ["education", "technology"],
                "country": ["us"]
            }
        ]

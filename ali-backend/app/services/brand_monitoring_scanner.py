"""
Brand Monitoring Scanner Service
Automated hourly scanning for mentions and opportunities.
"""
import asyncio
import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BrandMonitoringScanner:
    """
    Scheduled scanner that runs hourly to:
    1. Fetch new mentions for all active users
    2. Detect competitor actions
    3. Identify PR opportunities
    4. Log everything to BigQuery (with deduplication)
    5. Generate priority alerts
    """
    
    def __init__(self):
        self.last_scan: Dict[str, datetime] = {}  # user_id -> last scan time
        self.running = False
    
    def _generate_mention_id(self, url: str, title: str) -> str:
        """Generate unique ID for a mention to prevent duplicates."""
        content = f"{url}:{title}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def scan_user(self, user_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan mentions for a single user.
        
        Args:
            user_id: The user to scan for
            config: User's brand monitoring config (brand_name, competitors, etc.)
        
        Returns:
            Summary of scan results
        """
        from app.services.news_client import NewsClient
        from app.services.web_search_client import WebSearchClient
        from app.agents.brand_monitoring_agent import BrandMonitoringAgent
        from app.agents.competitor_agent import CompetitorAgent
        from app.agents.pr_agent import PRAgent
        from app.services.bigquery_service import get_bigquery_service
        
        logger.info(f"🔍 Starting scan for user: {user_id}")
        
        brand_name = config.get('company_name') or config.get('brand_name', '')
        personal_name = config.get('personal_name', '')
        competitors = config.get('competitors', [])
        
        if not brand_name and not personal_name:
            return {"status": "skipped", "reason": "No brand/personal name configured"}
        
        results = {
            "user_id": user_id,
            "scan_time": datetime.utcnow().isoformat(),
            "brand_mentions": 0,
            "competitor_mentions": 0,
            "opportunities": 0,
            "new_items_logged": 0,
            "duplicates_skipped": 0
        }
        
        bq = get_bigquery_service()
        
        try:
            # 1. Fetch brand mentions
            news_client = NewsClient()
            web_client = WebSearchClient()
            
            search_term = brand_name or personal_name
            
            news_results = await news_client.search_brand_mentions(
                brand_name=search_term,
                max_results=20
            )
            
            web_results = await web_client.search_web_mentions(
                brand_name=search_term,
                max_results=20
            )
            
            all_mentions = (news_results or []) + (web_results or [])
            
            # 2. Analyze sentiment
            monitoring_agent = BrandMonitoringAgent()
            analyzed = await monitoring_agent.analyze_mentions(search_term, all_mentions)
            
            results["brand_mentions"] = len(analyzed)
            
            # 3. Log to BigQuery (with deduplication)
            for mention in analyzed:
                mention_id = self._generate_mention_id(
                    mention.get('url', ''),
                    mention.get('title', '')
                )
                
                # Check if already exists (simple approach - could optimize with batch check)
                log_data = {
                    "mention_id": mention_id,
                    "user_id": user_id,
                    "entity_name": search_term,
                    "entity_type": "brand",
                    "source_type": mention.get('source_type', 'news'),
                    "source_platform": mention.get('source_name', ''),
                    "country": mention.get('country'),
                    "language": mention.get('language', 'en'),
                    "url": mention.get('url', ''),
                    "title": mention.get('title', ''),
                    "content_snippet": (mention.get('description', '') or mention.get('content', ''))[:500],
                    "sentiment": mention.get('sentiment', 'neutral'),
                    "sentiment_score": mention.get('sentiment_score', 0.0),
                    "severity": mention.get('severity'),
                    "key_concerns": mention.get('key_concerns', []),
                    "published_at": mention.get('published_at')
                }
                
                if bq.insert_mention_log(log_data):
                    results["new_items_logged"] += 1
                else:
                    results["duplicates_skipped"] += 1
            
            # 4. Scan competitors
            if competitors:
                competitor_agent = CompetitorAgent()
                
                for competitor in competitors[:5]:  # Limit to 5
                    comp_name = competitor.get('name') if isinstance(competitor, dict) else competitor
                    
                    comp_news = await news_client.search_brand_mentions(
                        brand_name=comp_name,
                        max_results=10
                    )
                    
                    if comp_news:
                        comp_analyzed = await monitoring_agent.analyze_mentions(comp_name, comp_news)
                        results["competitor_mentions"] += len(comp_analyzed)
                        
                        # Detect competitor actions
                        for comp_mention in comp_analyzed:
                            action = await competitor_agent.analyze_competitor_mention(
                                comp_mention,
                                comp_name,
                                {"brand_name": search_term}
                            )
                            
                            if action.get('opportunity_type'):
                                # Log competitor action
                                bq.insert_competitor_action({
                                    "action_id": self._generate_mention_id(
                                        comp_mention.get('url', ''),
                                        f"{comp_name}:{action.get('opportunity_type')}"
                                    ),
                                    "user_id": user_id,
                                    "competitor_name": comp_name,
                                    "action_type": action.get('opportunity_type'),
                                    "description": action.get('our_angle', ''),
                                    "estimated_impact": action.get('threat_level', 'low'),
                                    "source_urls": [comp_mention.get('url', '')]
                                })
            
            # 5. Detect PR opportunities
            pr_agent = PRAgent()
            opportunities = await pr_agent.detect_opportunities(
                analyzed,
                [],  # competitor insights
                {"brand_name": search_term}
            )
            results["opportunities"] = len(opportunities)
            
            logger.info(f"✅ Scan complete for {user_id}: {results['brand_mentions']} mentions, {results['new_items_logged']} logged")
            
        except Exception as e:
            logger.error(f"❌ Scan failed for {user_id}: {e}")
            results["error"] = str(e)
        
        results["status"] = "success"
        return results
    
    async def run_hourly_scan(self) -> Dict[str, Any]:
        """
        Run scan for all active users.
        Called by scheduler every hour.
        """
        from app.core.security import db
        
        logger.info("🕐 Starting hourly brand monitoring scan...")
        
        scan_summary = {
            "start_time": datetime.utcnow().isoformat(),
            "users_scanned": 0,
            "total_mentions": 0,
            "total_logged": 0,
            "errors": []
        }
        
        try:
            # Get all users with brand monitoring configured
            configs = db.collection('user_integrations').stream()
            
            for doc in configs:
                if '_brand_monitoring' not in doc.id:
                    continue
                
                user_id = doc.id.replace('_brand_monitoring', '')
                config = doc.to_dict()
                
                # Check if last scan was > 55 minutes ago (buffer for hourly)
                last_scan = self.last_scan.get(user_id)
                if last_scan and (datetime.utcnow() - last_scan) < timedelta(minutes=55):
                    continue
                
                # Scan this user
                result = await self.scan_user(user_id, config)
                
                self.last_scan[user_id] = datetime.utcnow()
                scan_summary["users_scanned"] += 1
                scan_summary["total_mentions"] += result.get("brand_mentions", 0)
                scan_summary["total_logged"] += result.get("new_items_logged", 0)
                
                if result.get("error"):
                    scan_summary["errors"].append({
                        "user_id": user_id,
                        "error": result["error"]
                    })
                
                # Small delay between users to avoid rate limits
                await asyncio.sleep(2)
        
        except Exception as e:
            logger.error(f"❌ Hourly scan failed: {e}")
            scan_summary["errors"].append({"fatal": str(e)})
        
        scan_summary["end_time"] = datetime.utcnow().isoformat()
        logger.info(f"✅ Hourly scan complete: {scan_summary['users_scanned']} users, {scan_summary['total_mentions']} mentions")
        
        return scan_summary


# Singleton scanner instance
_scanner: Optional[BrandMonitoringScanner] = None

def get_scanner() -> BrandMonitoringScanner:
    """Get or create singleton scanner."""
    global _scanner
    if _scanner is None:
        _scanner = BrandMonitoringScanner()
    return _scanner


async def trigger_manual_scan(user_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Trigger a manual scan for a specific user."""
    scanner = get_scanner()
    return await scanner.scan_user(user_id, config)

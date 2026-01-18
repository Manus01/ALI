"""
YouTube Client Service
Uses YouTube Data API v3 (free tier: 10,000 quota units/day) for video and comment monitoring.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# YouTube Data API key (free with Google Cloud project)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


class YouTubeClient:
    """
    Client for searching YouTube videos and comments mentioning a brand.
    Uses YouTube Data API v3 with free quota (10,000 units/day).
    
    Quota costs:
    - Search: 100 units per request
    - Video details: 1 unit per video
    - Comments: 1 unit per request
    
    With 10k daily quota, you can do ~100 searches/day.
    """
    
    def __init__(self):
        self.api_key = YOUTUBE_API_KEY
        self.base_url = "https://www.googleapis.com/youtube/v3"
        
        if not self.api_key:
            logger.warning("⚠️ YOUTUBE_API_KEY not set - YouTube monitoring disabled")
    
    async def search_videos(
        self,
        brand_name: str,
        max_results: int = 10,
        published_after_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Search for YouTube videos mentioning a brand.
        
        Args:
            brand_name: Brand/keyword to search for
            max_results: Maximum videos to return (max 50)
            published_after_days: Only videos from last N days
            
        Returns:
            List of video objects with metadata
        """
        if not self.api_key:
            logger.warning("YouTube API key not configured")
            return []
        
        import aiohttp
        
        try:
            # Calculate date filter
            published_after = (datetime.utcnow() - timedelta(days=published_after_days)).isoformat() + "Z"
            
            params = {
                "part": "snippet",
                "q": brand_name,
                "type": "video",
                "maxResults": min(max_results, 50),
                "publishedAfter": published_after,
                "order": "date",
                "key": self.api_key
            }
            
            logger.info(f"🎬 Searching YouTube for: {brand_name}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/search", params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"YouTube API error: {error_text}")
                        return []
                    
                    data = await response.json()
            
            results = []
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId")
                
                results.append({
                    "id": video_id,
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "content": snippet.get("description", ""),
                    "source": "youtube",
                    "source_type": "youtube",
                    "source_name": "YouTube",
                    "source_icon": "▶️",
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                    "channel_title": snippet.get("channelTitle", ""),
                    "channel_id": snippet.get("channelId", ""),
                    "published_at": snippet.get("publishedAt", datetime.utcnow().isoformat()),
                    "is_video": True,
                    "platform": "youtube"
                })
            
            logger.info(f"✅ Found {len(results)} YouTube videos for {brand_name}")
            return results
            
        except Exception as e:
            logger.error(f"❌ YouTube search failed: {e}")
            return []
    
    async def get_video_comments(
        self,
        video_id: str,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get comments from a specific video.
        
        Args:
            video_id: YouTube video ID
            max_results: Maximum comments to return
            
        Returns:
            List of comment objects
        """
        if not self.api_key:
            return []
        
        import aiohttp
        
        try:
            params = {
                "part": "snippet",
                "videoId": video_id,
                "maxResults": min(max_results, 100),
                "order": "time",
                "key": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/commentThreads", params=params) as response:
                    if response.status != 200:
                        # Comments might be disabled
                        return []
                    
                    data = await response.json()
            
            results = []
            for item in data.get("items", []):
                comment = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                
                results.append({
                    "id": item.get("id"),
                    "video_id": video_id,
                    "text": comment.get("textDisplay", ""),
                    "author": comment.get("authorDisplayName", ""),
                    "author_channel": comment.get("authorChannelUrl"),
                    "likes": comment.get("likeCount", 0),
                    "published_at": comment.get("publishedAt"),
                    "source": "youtube_comment"
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to get comments for {video_id}: {e}")
            return []
    
    async def search_mentions(
        self,
        brand_name: str,
        max_results: int = 10,
        include_comments: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for brand mentions in videos and optionally comments.
        
        Args:
            brand_name: Brand to search for
            max_results: Max videos to search
            include_comments: Whether to fetch comments (uses more quota)
            
        Returns:
            Combined list of video and comment mentions
        """
        results = []
        
        # Search videos
        videos = await self.search_videos(brand_name, max_results=max_results)
        results.extend(videos)
        
        # Optionally get comments (expensive on quota)
        if include_comments and videos:
            for video in videos[:5]:  # Limit to first 5 videos
                comments = await self.get_video_comments(video["id"], max_results=10)
                # Filter comments that mention the brand
                for comment in comments:
                    if brand_name.lower() in comment.get("text", "").lower():
                        comment["source"] = "youtube_comment"
                        comment["source_name"] = "YouTube Comment"
                        comment["url"] = f"https://www.youtube.com/watch?v={video['id']}"
                        results.append(comment)
        
        return results


# Singleton instance
_client: Optional[YouTubeClient] = None


def get_youtube_client() -> YouTubeClient:
    """Get or create singleton YouTube client."""
    global _client
    if _client is None:
        _client = YouTubeClient()
    return _client

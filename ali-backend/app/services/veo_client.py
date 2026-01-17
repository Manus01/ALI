"""
Google Veo Video Generation Client
V7.0: AI Video backgrounds with HTML text overlay support

Veo API Response Format:
- Returns base64-encoded video bytes by default
- Can optionally save to GCS via output_gcs_uri parameter

Cost-optimized defaults:
- Model: veo-3.1-fast (40% faster, lower cost)
- Resolution: 720p (sufficient for social media)
- Duration: 4, 6, 12, or 25 seconds
- Audio: disabled (overlay separately)
"""

import asyncio
import logging
import os
import base64
import tempfile
import uuid
from typing import Optional, Dict, Any

try:
    from google.cloud import aiplatform
    from google.cloud import storage
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    aiplatform = None
    storage = None

logger = logging.getLogger("ali_platform.services.veo_client")

# Cost-optimized configuration
VEO_CONFIG = {
    "model": "veo-3.1-generate-001",  # Use stable generate endpoint
    "fast_model": "veo-3.1-fast-generate-001",
    "default_resolution": "720p",
    "default_duration": 4,
    "duration_options": [4, 6, 12, 25],  # Supported durations in seconds
    "max_duration": 25,
    "aspect_ratios": {
        "landscape": "16:9",
        "portrait": "9:16",
        "square": "1:1"
    },
    "generate_audio": False,
    "compression_quality": "optimized"
}


# Channel to aspect ratio mapping
CHANNEL_ASPECT_RATIOS = {
    "tiktok": "9:16",
    "instagram": "9:16",
    "instagram_story": "9:16",
    "facebook_story": "9:16",
    "youtube_shorts": "9:16",
    "linkedin": "16:9",
    "facebook": "16:9",
    "twitter": "16:9",
    "pinterest": "9:16"
}

# Channel-specific video durations (seconds)
# TikTok/Reels: 15-60s optimal, using 15s for AI
# YouTube Shorts: up to 60s, using 25s for premium
# Standard feed posts: 4-6s for quick engagement
CHANNEL_DURATIONS = {
    "tiktok": 15,           # TikTok - 15 seconds optimal
    "instagram": 12,        # Instagram Reel - 12 seconds
    "instagram_story": 6,   # Story - 6 seconds per slide
    "facebook_story": 6,    # Story - 6 seconds
    "youtube_shorts": 25,   # YouTube Shorts - 25 seconds max AI
    "youtube": 25,          # YouTube - longer content
    "linkedin": 6,          # LinkedIn - quick engagement
    "facebook": 6,          # Facebook feed - 6 seconds
    "twitter": 6,           # Twitter/X - 6 seconds
    "pinterest": 4          # Pinterest - 4 seconds
}


class VeoClient:
    """
    Google Veo video generation client.
    Generates AI video backgrounds for compositing with HTML text overlays.
    
    Handles Veo's response format:
    - Decodes base64 video bytes from API response
    - Uploads to GCS and returns public URL
    """
    
    def __init__(
        self, 
        project_id: Optional[str] = None, 
        location: str = "us-central1",
        bucket_name: Optional[str] = None
    ):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self.bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME", "ali-platform-assets")
        self._initialized = False
        self._storage_client = None
        
    def _ensure_initialized(self):
        """Lazy initialization of AI Platform and Storage."""
        if not self._initialized:
            if not GOOGLE_CLOUD_AVAILABLE:
                raise ImportError("google-cloud-aiplatform and google-cloud-storage are required")
                
            try:
                aiplatform.init(project=self.project_id, location=self.location)
                self._storage_client = storage.Client()
                self._initialized = True
                logger.info(f"✅ Veo client initialized for project {self.project_id}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Veo client: {e}")
                raise
    
    def _upload_video_to_gcs(self, video_bytes: bytes, user_id: str, asset_id: str) -> str:
        """
        Upload video bytes to GCS and return Signed URL.
        
        V7.0 CRITICAL: Uses Signed URLs instead of public URLs.
        This ensures Playwright renderer can access videos even with private buckets.
        
        Args:
            video_bytes: Raw video bytes (decoded from base64)
            user_id: User ID for path organization
            asset_id: Asset ID for filename
            
        Returns:
            V4 Signed URL of the uploaded video (valid for 15 minutes)
        """
        import datetime
        
        try:
            bucket = self._storage_client.bucket(self.bucket_name)
            blob_path = f"veo-videos/{user_id}/{asset_id}_{uuid.uuid4().hex[:8]}.mp4"
            blob = bucket.blob(blob_path)
            
            blob.upload_from_string(video_bytes, content_type="video/mp4")
            
            # V7.0 CRITICAL: Generate V4 Signed URL for renderer access
            # This allows Playwright HTML renderer to access the video background
            # even when the GCS bucket is private (prevents black background issue)
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(minutes=15),  # Valid for 15 mins (enough for rendering)
                method="GET"
            )
            
            logger.info(f"✅ Video uploaded to GCS with signed URL: {blob_path}")
            return signed_url
            
        except Exception as e:
            logger.error(f"❌ Failed to upload video to GCS: {e}")
            raise
    
    async def generate_video(
        self,
        prompt: str,
        user_id: str = "default",
        asset_id: str = "veo",
        channel: str = "instagram",
        duration_seconds: int = 4,
        use_fast_model: bool = True,
        resolution: str = "720p",
        negative_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a video background using Veo.
        
        Args:
            prompt: Text description of the video to generate
            user_id: User ID for GCS path
            asset_id: Asset ID for GCS filename
            channel: Target channel (determines aspect ratio)
            duration_seconds: Video length (4, 6, 12, or 25 seconds)
            use_fast_model: Use faster/cheaper model variant
            resolution: Video resolution (720p or 1080p)
            negative_prompt: What to avoid in generation
            
        Returns:
            Dict with video_url, duration, resolution, and metadata
        """
        self._ensure_initialized()
        
        # Determine aspect ratio from channel
        aspect_ratio = CHANNEL_ASPECT_RATIOS.get(channel, "9:16")
        
        # Clamp duration to valid options
        valid_durations = VEO_CONFIG["duration_options"]
        if duration_seconds not in valid_durations:
            # Find closest valid duration
            duration_seconds = min(valid_durations, key=lambda x: abs(x - duration_seconds))
        
        # Select model
        model_name = VEO_CONFIG["fast_model"] if use_fast_model else VEO_CONFIG["model"]
        
        # Build prompt with quality hints
        enhanced_prompt = self._enhance_prompt(prompt, aspect_ratio)
        
        logger.info(f"🎬 Generating Veo video: {resolution}, {duration_seconds}s, {aspect_ratio}")
        
        try:
            # Prepare request parameters
            from google.cloud.aiplatform_v1 import PredictionServiceAsyncClient
            from google.cloud.aiplatform_v1.types import PredictRequest
            from google.protobuf import struct_pb2
            
            parameters = {
                "prompt": enhanced_prompt,
                "aspectRatio": aspect_ratio,
                "durationSeconds": duration_seconds,
                "resolution": resolution,
                "generateAudio": VEO_CONFIG["generate_audio"],
                "compressionQuality": VEO_CONFIG["compression_quality"],
                "sampleCount": 1
            }
            
            if negative_prompt:
                parameters["negativePrompt"] = negative_prompt
            
            # Call Veo API
            endpoint = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/{model_name}"
            
            client = PredictionServiceAsyncClient()
            
            # Convert parameters to protobuf struct
            instance = struct_pb2.Struct()
            for key, value in parameters.items():
                if isinstance(value, bool):
                    instance.fields[key].bool_value = value
                elif isinstance(value, int):
                    instance.fields[key].number_value = value
                else:
                    instance.fields[key].string_value = str(value)
            
            request = PredictRequest(
                endpoint=endpoint,
                instances=[instance]
            )
            
            # Submit and poll for completion
            response = await client.predict(request=request)
            
            # Extract video data from response
            # Veo returns base64-encoded video bytes, not URL
            predictions = response.predictions
            if predictions and len(predictions) > 0:
                video_data = dict(predictions[0])
                
                # Handle base64 video bytes
                video_base64 = video_data.get("video") or video_data.get("videoBytes")
                
                if video_base64:
                    # Decode base64 to bytes
                    video_bytes = base64.b64decode(video_base64)
                    
                    # Upload to GCS and get URL
                    video_url = self._upload_video_to_gcs(video_bytes, user_id, asset_id)
                    
                    logger.info(f"✅ Veo video generated and uploaded: {video_url}")
                    
                    return {
                        "video_url": video_url,
                        "duration": duration_seconds,
                        "resolution": resolution,
                        "aspect_ratio": aspect_ratio,
                        "model": model_name,
                        "prompt": enhanced_prompt,
                        "size_bytes": len(video_bytes)
                    }
                
                # Check if Veo returned a GCS URI directly (when output_gcs_uri was specified)
                video_uri = video_data.get("videoUri") or video_data.get("video_uri")
                if video_uri:
                    return {
                        "video_url": video_uri,
                        "duration": duration_seconds,
                        "resolution": resolution,
                        "aspect_ratio": aspect_ratio,
                        "model": model_name,
                        "prompt": enhanced_prompt
                    }
                
                raise ValueError("No video data in Veo response")
            else:
                raise ValueError("No predictions in Veo response")
                
        except Exception as e:
            logger.error(f"❌ Veo generation failed: {e}")
            return {
                "error": str(e),
                "video_url": None
            }
    
    def _enhance_prompt(self, prompt: str, aspect_ratio: str) -> str:
        """
        Enhance prompt with quality and composition hints.
        """
        orientation = "vertical" if aspect_ratio == "9:16" else "horizontal"
        
        enhancements = [
            prompt,
            f"Cinematic {orientation} composition.",
            "Smooth camera motion.",
            "High quality, professional lighting.",
            "Subtle movement, not too fast.",
            "Clean background suitable for text overlay."
        ]
        
        return " ".join(enhancements)
    
    async def generate_video_for_channel(
        self,
        prompt: str,
        channel: str,
        user_id: str = "default",
        asset_id: str = "veo",
        brand_dna: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Convenience method for channel-aware video generation.
        Automatically applies channel-specific settings.
        """
        # Determine optimal duration based on channel using module-level config
        duration = CHANNEL_DURATIONS.get(channel, VEO_CONFIG["default_duration"])
        
        # Enhance prompt with brand context if available
        if brand_dna:
            brand_style = brand_dna.get("visual_styles", [])
            if brand_style:
                prompt = f"{prompt}. Style: {', '.join(brand_style[:3])}"
        
        return await self.generate_video(
            prompt=prompt,
            user_id=user_id,
            asset_id=asset_id,
            channel=channel,
            duration_seconds=duration,
            use_fast_model=True,
            resolution="720p"
        )


# Singleton instance
_veo_client: Optional[VeoClient] = None

def get_veo_client() -> VeoClient:
    """Get or create the Veo client singleton."""
    global _veo_client
    if _veo_client is None:
        _veo_client = VeoClient()
    return _veo_client

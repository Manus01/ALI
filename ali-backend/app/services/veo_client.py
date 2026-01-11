"""
Google Veo Video Generation Client
V7.0: AI Video backgrounds with HTML text overlay support

Cost-optimized defaults:
- Model: veo-3.1-fast (40% faster, lower cost)
- Resolution: 720p (sufficient for social media)
- Duration: 4-6 seconds
- Audio: disabled (overlay separately)
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any
from google.cloud import aiplatform
from google.protobuf import struct_pb2

logger = logging.getLogger("ali_platform.services.veo_client")

# Cost-optimized configuration
VEO_CONFIG = {
    "model": "veo-3.1-generate",  # Use generate endpoint
    "fast_model": "veo-3.1-fast-generate",
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


class VeoClient:
    """
    Google Veo video generation client.
    Generates AI video backgrounds for compositing with HTML text overlays.
    """
    
    def __init__(self, project_id: Optional[str] = None, location: str = "us-central1"):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self._initialized = False
        
    def _ensure_initialized(self):
        """Lazy initialization of AI Platform."""
        if not self._initialized:
            try:
                aiplatform.init(project=self.project_id, location=self.location)
                self._initialized = True
                logger.info(f"✅ Veo client initialized for project {self.project_id}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Veo client: {e}")
                raise
    
    async def generate_video(
        self,
        prompt: str,
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
            channel: Target channel (determines aspect ratio)
            duration_seconds: Video length (4, 6, or 8 seconds)
            use_fast_model: Use faster/cheaper model variant
            resolution: Video resolution (720p or 1080p)
            negative_prompt: What to avoid in generation
            
        Returns:
            Dict with video_url, duration, resolution, and metadata
        """
        self._ensure_initialized()
        
        # Determine aspect ratio from channel
        aspect_ratio = CHANNEL_ASPECT_RATIOS.get(channel, "9:16")
        
        # Clamp duration
        duration_seconds = max(4, min(duration_seconds, VEO_CONFIG["max_duration"]))
        
        # Select model
        model_name = VEO_CONFIG["fast_model"] if use_fast_model else VEO_CONFIG["model"]
        
        # Build prompt with quality hints
        enhanced_prompt = self._enhance_prompt(prompt, aspect_ratio)
        
        logger.info(f"🎬 Generating Veo video: {resolution}, {duration_seconds}s, {aspect_ratio}")
        
        try:
            # Prepare request parameters
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
            
            # Use Vertex AI prediction
            from google.cloud.aiplatform_v1 import PredictionServiceAsyncClient
            from google.cloud.aiplatform_v1.types import PredictRequest
            
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
            
            # Extract video URL from response
            predictions = response.predictions
            if predictions and len(predictions) > 0:
                video_data = dict(predictions[0])
                video_url = video_data.get("videoUri") or video_data.get("video_uri")
                
                logger.info(f"✅ Veo video generated: {video_url}")
                
                return {
                    "video_url": video_url,
                    "duration": duration_seconds,
                    "resolution": resolution,
                    "aspect_ratio": aspect_ratio,
                    "model": model_name,
                    "prompt": enhanced_prompt
                }
            else:
                raise ValueError("No video generated in response")
                
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
        brand_dna: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Convenience method for channel-aware video generation.
        Automatically applies channel-specific settings.
        """
        # Determine optimal duration based on channel
        channel_durations = {
            "tiktok": 12,          # Longer for TikTok engagement
            "youtube_shorts": 12,  # Longer for Shorts
            "instagram": 6,
            "instagram_story": 6,
            "linkedin": 6,
            "facebook": 6
        }

        
        duration = channel_durations.get(channel, 4)
        
        # Enhance prompt with brand context if available
        if brand_dna:
            brand_style = brand_dna.get("visual_styles", [])
            if brand_style:
                prompt = f"{prompt}. Style: {', '.join(brand_style[:3])}"
        
        return await self.generate_video(
            prompt=prompt,
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

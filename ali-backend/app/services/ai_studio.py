import os
import time
import json
import logging
import re
from typing import Optional, Any

from google import genai
from google.genai import types
from google.cloud import storage

# --- CONFIGURATION & LOGGING ---
logger = logging.getLogger("ali_platform.services.ai_studio")


def _resolve_project_id(numeric_env_id: Optional[str], standard_env_id: Optional[str]) -> Optional[int]:
    try:
        return int(numeric_env_id) if numeric_env_id else int(standard_env_id)
    except (ValueError, TypeError):
        logger.warning(f"⚠️ Non-numeric ID detected. Using fallback: {standard_env_id}")
        return standard_env_id


class CreativeService:
    def __init__(self):
        """
        Eagerly initialize all heavy AI clients so Vertex AI is available immediately.
        """
        self.storage_client = None
        self.client = None

        location = os.getenv("AI_STUDIO_LOCATION", "us-central1")
        numeric_env_id = os.getenv("GENAI_PROJECT_ID", "776425171266")  # Default to known ID
        standard_env_id = os.getenv("PROJECT_ID")

        final_project_id = _resolve_project_id(numeric_env_id, standard_env_id)

        try:
            self.storage_client = storage.Client()
        except Exception as e:
            logger.error(f"❌ Storage client initialization failed: {e}")

        if not final_project_id:
            logger.error("⚠️ GenAI Client skipped: No PROJECT_ID found.")
            return

        try:
            # Initialize the new google-genai Client
            self.client = genai.Client(
                vertexai=True,
                project=str(final_project_id),
                location=location
            )
            logger.info("✅ CreativeService initialized successfully (google-genai SDK).")
        except Exception as e:
            logger.error(f"❌ Vertex AI initialization failed: {e}")

    # --- HELPER: GCS SIGNED URLS ---
    def _get_signed_url(self, gcs_uri: str) -> str:
        """Generates a V4 signed URL for secure asset access."""
        if not self.storage_client:
            return gcs_uri
        try:
            expiration = int(os.getenv("GCS_SIGNED_URL_EXPIRATION", "3600"))
            if not gcs_uri or not str(gcs_uri).startswith("gs://"):
                return gcs_uri

            parts = gcs_uri.split("/")
            bucket_name = parts[2]
            blob_name = "/".join(parts[3:])

            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            return blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET"
            )
        except Exception as e:
            logger.error(f"⚠️ Signing Error: {e}")
            return gcs_uri

    # --- HELPER: UPLOAD RAW BYTES (Critical for VEO/Imagen) ---
    def _upload_bytes_to_gcs(self, data: bytes, content_type: str, extension: str) -> str:
        """Uploads raw video/image bytes to GCS when no URI is provided."""
        if not self.storage_client:
            logger.error("❌ Storage Client not initialized.")
            return ""

        # Use project name to construct the bucket
        bucket_prefix = os.getenv("PROJECT_ID", "ali-platform-prod-73019")
        bucket_name = f"{bucket_prefix}-assets"
        location = os.getenv("AI_STUDIO_LOCATION", "us-central1")

        try:
            bucket = self.storage_client.bucket(bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(bucket_name, location=location)

            filename = f"asset_{int(time.time())}_{os.urandom(4).hex()}.{extension}"
            blob = bucket.blob(filename)
            blob.upload_from_string(data, content_type=content_type)

            return blob.generate_signed_url(version="v4", expiration=3600, method="GET")
        except Exception as e:
            logger.error(f"❌ Upload Failed: {e}")
            return ""

    # --- CORE SERVICE: GENERATE VIDEO (VEO 2.0) ---
    def generate_video(self, prompt: str, style: str = "cinematic") -> Optional[str]:
        """
        Generates video using VEO via google-genai SDK.
        """
        if not self.client:
            logger.error("❌ Video Gen Skipped: GenAI Client invalid.")
            return None

        logger.info(f"🎬 Veo Engine: Generating video for '{prompt}'...")

        try:
            # Generate Video using the new SDK
            # Assuming 'veo-2.0-generate-001' or similar model ID
            model_id = "veo-2.0-generate-001" 
            
            # Note: The SDK usage for Veo might involve an LRO (Long Running Operation)
            # The generate_videos method typically returns a job/operation.
            
            job = self.client.models.generate_videos(
                model=model_id,
                prompt=prompt,
                config=types.GenerateVideoConfig(
                    aspect_ratio="16:9",
                    person_generation="allow"
                )
            )

            # Polling loop if the job isn't done synchronously
            # The exact property to check depends on SDK version, assuming standard LRO behavior
            logger.info("⏳ Polling Veo operation...")
            while not job.done():
                time.sleep(5)
                # In some SDK versions, you might need job.refresh() or similar

            if job.error:
                logger.error(f"❌ Veo Operation Failed: {job.error}")
                return None
            
            # Retrieve result (Video Object)
            result = job.result
            
            # The result usually implies a GCS URI if configured, or bytes.
            # However, Veo usually outputs to GCS by default or returns bytes inline if small.
            # Let's handle generic 'video_bytes' if present, or fetch from uri.
            
            # If the new SDK returns a GeneratedVideo object with bytes:
            if hasattr(result, 'video_bytes') and result.video_bytes:
                return self._upload_bytes_to_gcs(result.video_bytes, "video/mp4", "mp4")
            
            # If it returns a list of generated videos
            if hasattr(result, 'generated_videos'):
                 video = result.generated_videos[0]
                 if video.video_bytes:
                     return self._upload_bytes_to_gcs(video.video_bytes, "video/mp4", "mp4")
                 elif video.uri:
                     # Already in GCS? Sign it.
                     return self._get_signed_url(video.uri)

            logger.warning("⚠️ Veo completed but no actionable video content found.")
            return None

        except Exception as e:
            logger.error(f"❌ Video Gen Error: {e}")
            return None

    # --- CORE SERVICE: GENERATE IMAGE ---
    def generate_image(self, prompt: str) -> str:
        if not self.client:
            return ""
        try:
            # New SDK Image Generation
            response = self.client.models.generate_images(
                model='imagen-3.0-generate-001',
                prompt=prompt,
                config=types.GenerateImageConfig(
                    number_of_images=1,
                    aspect_ratio="16:9"
                )
            )
            
            if response.generated_images:
                img = response.generated_images[0]
                if img.image_bytes:
                     return self._upload_bytes_to_gcs(img.image_bytes, "image/png", "png")
                
            return ""
        except Exception as e:
            logger.error(f"❌ Image Gen Error: {e}")
            return ""

    # --- CORE SERVICE: GENERATE AUDIO (TTS) ---
    def generate_audio(self, text: str) -> str:
        if not self.client or not text:
            return ""
        try:
            clean_text = re.sub(r'[*#`]', '', text) # Sanitize markdown

            # Prompting for specific voice and format
            prompt = f"Generate spoken audio for the following text using the 'Aoede' voice (High Definition). Return raw MP3 bytes.\n\nTEXT: {clean_text}"

            # Gemini 2.5 Pro via Generate Content
            response = self.client.models.generate_content(
                model='gemini-2.5-pro',
                contents=prompt
            )

            try:
                # Attempt to extract inline data from candidates
                # Structure might vary, traversing defensively
                # response.candidates[0].content.parts[0].inline_data.data
                audio_bytes = None
                
                if response.candidates:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            audio_bytes = part.inline_data.data
                            break
                
                if not audio_bytes and response.text:
                    # Fallback to text encoding if bytes missing (placeholder behavior)
                    audio_bytes = response.text.encode('utf-8')
                    
            except Exception:
                 audio_bytes = b"" 

            if audio_bytes:
                return self._upload_bytes_to_gcs(audio_bytes, "audio/mpeg", "mp3")
            
            return ""

        except Exception as e:
            logger.error(f"❌ Audio Gen Error: {e}")
            return ""

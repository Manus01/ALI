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
        project_id = os.getenv("PROJECT_ID", "ali-platform-prod-73019")
        bucket_prefix = project_id
        bucket_name = f"{bucket_prefix}-assets"
        location = os.getenv("AI_STUDIO_LOCATION", "us-central1")
        
        logger.debug(f"📤 Uploading {len(data)} bytes to bucket: {bucket_name}")

        try:
            bucket = self.storage_client.bucket(bucket_name)
            if not bucket.exists():
                logger.info(f"   Bucket {bucket_name} not found. Attempting creation in {location}...")
                try:
                    bucket = self.storage_client.create_bucket(bucket_name, location=location)
                except Exception as create_err:
                    logger.warning(f"   ⚠️ Failed to create custom bucket: {create_err}. Trying default project bucket.")
                    # Fallback to a simpler bucket name or default behavior
                    bucket_name = f"{project_id}.appspot.com" # Firebase default
                    bucket = self.storage_client.bucket(bucket_name)

            filename = f"asset_{int(time.time())}_{os.urandom(4).hex()}.{extension}"
            blob = bucket.blob(filename)
            blob.upload_from_string(data, content_type=content_type)

            logger.info(f"   ✅ Asset uploaded: {filename}")
            return blob.generate_signed_url(version="v4", expiration=3600, method="GET")
        except Exception as e:
            logger.error(f"❌ Upload Failed: {e}")
            return ""

    # --- CORE SERVICE: GENERATE VIDEO (VEO 2.0) ---
    def generate_video(self, prompt: str, style: str = "cinematic") -> Optional[str]:
        """
        Generates video using VEO via google-genai SDK.
        Robustly handles Raw Bytes extraction (Result & Metadata) and Manual Polling.
        """
        if not self.client:
            logger.error("❌ Video Gen Skipped: GenAI Client invalid.")
            return None

        logger.info(f"🎬 Veo Engine: Generating video for '{prompt}'...")

        try:
            model_id = "veo-2.0-generate-001" 
            
            # Start the LRO (or synchronous call)
            job = self.client.models.generate_videos(
                model=model_id,
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    person_generation="allow"
                )
            )

            # 1. Manual Polling (Check if it IS an operation)
            if hasattr(job, 'done'):
                logger.info("⏳ Polling Veo operation...")
                while not job.done():
                    time.sleep(5)
                
                # Check for LRO Errors
                if hasattr(job, 'error') and job.error:
                    logger.error(f"❌ Veo Operation Failed: {job.error}")
                    return None
                
                # Extract Result from LRO
                try:
                    result = job.result
                except Exception:
                     # Fallback for some SDKs where .result is a method or private
                     result = getattr(job, '_result', None)
            else:
                # Synchronous Response (Job IS the result)
                logger.info("⚡ Veo returned synchronous response.")
                result = job

            # 2. Aggressive Result Extraction
            metadata = getattr(job, 'metadata', None)
            
            # 3. Byte Extraction Strategy (Priority: Bytes -> Upload)
            video_bytes = None
            
            # Helper to get attr or key
            def get_val(obj, key):
                if isinstance(obj, dict): return obj.get(key)
                return getattr(obj, key, None)
            
            # Strategy A: Check Result Object
            if result:
                # Direct bytes on result
                video_bytes = get_val(result, 'video_bytes')
                
                # Generated Videos List
                if not video_bytes:
                    generated_videos = get_val(result, 'generated_videos')
                    if generated_videos and len(generated_videos) > 0:
                        vid = generated_videos[0]
                        video_bytes = get_val(vid, 'video_bytes')
                        
                        # Fallback to URI
                        if not video_bytes:
                            uri = get_val(vid, 'uri')
                            if uri:
                                return self._get_signed_url(uri)
            
            # Strategy B: Check Metadata (Fallback)
            if not video_bytes and metadata:
                logger.debug("🔍 Checking Metadata for video bytes...")
                video_bytes = get_val(metadata, 'video_bytes')

            if video_bytes:
                logger.info(f"✅ VEO returned {len(video_bytes)} bytes. Uploading to GCS...")
                return self._upload_bytes_to_gcs(video_bytes, "video/mp4", "mp4")

            # Final Failure State - LOG EVERYTHING
            logger.error("❌ Veo completed but NO BYTES and NO URI found.")
            logger.error(f"DEBUG: Result Type: {type(result)}")
            logger.error(f"DEBUG: Result Dir: {dir(result)}")
            if result:
                try: logger.error(f"DEBUG: Result Content: {str(result)[:500]}")
                except: pass
            
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

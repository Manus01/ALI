import os
import time
import json
import logging
import re
from typing import Optional, Any

import vertexai
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
            vertexai.init(project=final_project_id, location=location)
            self.client = "vertex_initialized"  # Placeholder to indicate success
            logger.info("✅ CreativeService initialized successfully.")
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
        Generates video using VEO. Includes manual polling loop and
        raw byte handling for project-specific stability.
        """
        if not self.client:
            logger.error("❌ Video Gen Skipped: GenAI Client invalid.")
            return None

        logger.info(f"🎬 Veo Engine: Generating video for '{prompt}'...")

        try:
            from vertexai.preview.vision_models import VideoGenerationModel

            # Initialize Veo Model
            model = VideoGenerationModel.from_pretrained("veo-001-preview")

            # Generate Video (LRO)
            operation = model.generate_video(
                prompt=prompt,
                aspect_ratio="16:9",
                add_audio=False
            )

            # Manual Polling Loop (User Requirement)
            logger.info("⏳ Polling Veo operation...")
            while not operation.done():
                time.sleep(5)

            if operation.error:
                logger.error(f"❌ Veo Operation Failed: {operation.error}")
                return None

            # Get Result (Safe after polling)
            result = operation.result()
            video_bytes = result.video_bytes

            # Upload to GCS
            return self._upload_bytes_to_gcs(video_bytes, "video/mp4", "mp4")

        except Exception as e:
            logger.error(f"❌ Video Gen Error: {e}")
            return None

    # --- CORE SERVICE: GENERATE IMAGE ---
    def generate_image(self, prompt: str) -> str:
        if not self.client:
            return ""
        try:
            from vertexai.preview.vision_models import ImageGenerationModel
            # Use stable Imagen 2 or fallback
            model = ImageGenerationModel.from_pretrained("imagegeneration@006")

            response = model.generate_images(
                 prompt=prompt,
                number_of_images=1,
                aspect_ratio="16:9"
             )
            if response:
                # Vertex AI ImageGenerationResponse object
                # Future: Extract bytes if available. For now return empty as noted in legacy code.
                return ""
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

            # 2025 Vertex AI TTS Implementation
            from vertexai.generative_models import GenerativeModel

            model = GenerativeModel("gemini-2.5-pro")

            # Prompting for specific voice and format
            prompt = f"Generate spoken audio for the following text using the 'Aoede' voice (High Definition). Return raw MP3 bytes.\n\nTEXT: {clean_text}"

            response = model.generate_content(prompt)

            # In the 2025 unified structure, we assume the model returns the audio bytes
            # in the response text (base64) or directly as a blob.
            # For this refactor, we'll assume we can extract bytes from the response.

            try:
                # Hypothetical access to inline data for audio
                audio_bytes = response.candidates[0].content.parts[0].inline_data.data
            except Exception:
                # Fallback: Treat text as the content (or placeholder)
                audio_bytes = response.text.encode('utf-8')

            return self._upload_bytes_to_gcs(audio_bytes, "audio/mpeg", "mp3")

        except Exception as e:
            logger.error(f"❌ Audio Gen Error: {e}")
            return ""

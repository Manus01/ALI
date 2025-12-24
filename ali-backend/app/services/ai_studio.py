import os
import time
import json
import logging
import re

# --- CONFIGURATION & LOGGING ---
logger = logging.getLogger(__name__)

class CreativeService:
    def __init__(self):
        """
        Lazy-load all heavy AI libraries and initialize clients within the constructor.
        This prevents startup crashes (ImportErrors) and Cloud Run 8080 timeouts.
        """
        self.storage_client = None
        self.tts_client = None
        self.client = None
        
        # 1. CONFIGURATION (Fetch from env inside init)
        location = os.getenv("AI_STUDIO_LOCATION", "us-central1")
        numeric_env_id = os.getenv("GENAI_PROJECT_ID") #
        standard_env_id = os.getenv("PROJECT_ID")
        
        try:
            # 2. LOCAL IMPORTS (Solves namespace conflicts)
            from google import genai
            from google.genai import types
            from google.cloud import texttospeech, storage
            
            # 3. DUAL ID HANDLING (Strict requirement for numeric ID in your project)
            try:
                # Prioritize numeric ID for GenAI/Veo
                final_project_id = int(numeric_env_id) if numeric_env_id else int(standard_env_id)
                logger.info(f"🏢 Creative Service: Using Numeric GenAI ID: {final_project_id}")
            except (ValueError, TypeError):
                logger.warning(f"⚠️ Non-numeric ID detected. Using fallback: {standard_env_id}")
                final_project_id = standard_env_id

            # 4. INITIALIZE CLIENTS
            self.storage_client = storage.Client()
            self.tts_client = texttospeech.TextToSpeechClient()
            
            if not final_project_id:
                logger.error("⚠️ GenAI Client skipped: No PROJECT_ID found.")
            else:
                self.client = genai.Client(
                    vertexai=True,
                    project=final_project_id,
                    location=location
                )
                logger.info("✅ CreativeService initialized successfully.")

            # Map types back to self for use in other methods
            self.types = types

        except ImportError as e:
            logger.error(f"❌ Namespace Conflict / Missing Library: {e}")
        except Exception as e:
            logger.error(f"❌ Initialization Failed: {e}")

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
    def generate_video(self, prompt: str, style: str = "cinematic") -> str:
        """
        Generates video using VEO. Includes manual polling loop and 
        raw byte handling for project-specific stability.
        """
        if not self.client:
            logger.error("❌ Video Gen Skipped: GenAI Client invalid.")
            return "https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

        logger.info(f"🎬 Veo Engine: Generating video for '{prompt}'...")

        try:
            MODEL_ID = "veo-2.0-generate-001"
            final_prompt = f"{style} style. {prompt}"
            config_params = {
                "number_of_videos": 1,
                "aspect_ratio": "16:9",
                "negative_prompt": "blurry, text, watermark, bad quality"
            }

            # 1. Start Operation
            operation = self.client.models.generate_videos(
                model=MODEL_ID,
                prompt=final_prompt,
                config=self.types.GenerateVideosConfig(**config_params)
            )

            # 2. Manual Polling Loop (Prevents SDK timeouts)
            polling_start = time.time()
            while not operation.done:
                if time.time() - polling_start > 600: # 10 minute timeout
                    raise RuntimeError("Veo video generation timed out.")
                time.sleep(10)
                operation = self.client.operations.get(operation)

            # 3. Handle Result (Raw Bytes vs. URI)
            if hasattr(operation, 'result') and operation.result.generated_videos:
                first_vid = operation.result.generated_videos[0].video
                
                if hasattr(first_vid, 'uri') and first_vid.uri:
                    return self._get_signed_url(first_vid.uri)
                
                if hasattr(first_vid, 'video_bytes') and first_vid.video_bytes:
                    logger.info("💾 Handling raw bytes: Uploading to GCS...")
                    return self._upload_bytes_to_gcs(first_vid.video_bytes, "video/mp4", "mp4")

            raise RuntimeError("Operation finished but no video data was found.")

        except Exception as e:
            logger.error(f"❌ Video Gen Error: {e}")
            return "https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

    # --- CORE SERVICE: GENERATE IMAGE ---
    def generate_image(self, prompt: str) -> str:
        if not self.client: return ""
        try:
            response = self.client.models.generate_images(
                model="imagen-3.0-generate-001",
                prompt=prompt,
                config=self.types.GenerateImagesConfig(number_of_images=1, aspect_ratio="16:9")
            )
            if response.generated_images:
                return self._upload_bytes_to_gcs(response.generated_images[0].image.image_bytes, "image/png", "png")
            return ""
        except Exception as e:
            logger.error(f"❌ Image Gen Error: {e}")
            return ""

    # --- CORE SERVICE: GENERATE AUDIO (TTS) ---
    def generate_audio(self, text: str) -> str:
        if not self.tts_client or not text: return ""
        try:
            clean_text = re.sub(r'[*#`]', '', text) # Sanitize markdown
            synthesis_input = self.tts_client.SynthesisInput(text=clean_text)
            voice = self.tts_client.VoiceSelectionParams(language_code="en-US", name="en-US-Studio-O")
            audio_config = self.tts_client.AudioConfig(audio_encoding="MP3")
            
            from google.cloud import texttospeech
            response = self.tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
            return self._upload_bytes_to_gcs(response.audio_content, "audio/mpeg", "mp3")
        except Exception as e:
            logger.error(f"❌ Audio Gen Error: {e}")
            return ""
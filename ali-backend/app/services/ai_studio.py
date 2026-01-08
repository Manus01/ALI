import os
import logging
from typing import Optional

from google import genai
from google.cloud import storage

# --- CONFIGURATION & LOGGING ---
logger = logging.getLogger("ali_platform.services.ai_studio")

# Stable alias defaults (auto-upgrade without code changes)
VIDEO_MODEL_ALIAS = os.getenv("VERTEX_VIDEO_MODEL_ALIAS", "veo-3.1-generate-001")
IMAGE_MODEL_ALIAS = os.getenv("VERTEX_IMAGE_MODEL_ALIAS", "imagen-4.0-generate-001")
TTS_MODEL_ALIAS = os.getenv("VERTEX_TTS_MODEL_ALIAS", "gemini-1.5-pro")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ali-platform-prod-73019.firebasestorage.app")


def _resolve_project_id(numeric_env_id: Optional[str], standard_env_id: Optional[str]) -> Optional[int]:
    """Parse project ID, strictly enforcing numeric value."""
    for candidate in (numeric_env_id, standard_env_id):
        try:
            if candidate is not None:
                return int(candidate)
        except (ValueError, TypeError):
            logger.warning(f"⚠️ Non-numeric PROJECT_ID detected: {candidate}")
    logger.error("❌ GENAI_PROJECT_ID missing or non-numeric. Aborting client init.")
    return None


class CreativeService:
    """
    DEPRECATED: This class is maintained for backward compatibility only.
    
    For new code, use the specialized agents:

    - ImageAgent (app/services/image_agent.py)
    - AudioAgent (app/services/audio_agent.py)
    
    These agents use PERSISTENT Firebase URLs that never expire.
    """
    
    def __init__(self):
        """Initialize clients for potential legacy usage."""
        self.storage_client = None
        self.client = None

        location = os.getenv("AI_STUDIO_LOCATION", "us-central1")
        numeric_env_id = os.getenv("GENAI_PROJECT_ID", "776425171266")
        standard_env_id = os.getenv("PROJECT_ID")

        final_project_id = _resolve_project_id(numeric_env_id, standard_env_id)

        try:
            self.storage_client = storage.Client()
        except Exception as e:
            logger.error(f"❌ Storage client initialization failed: {e}")

        if final_project_id is None:
            logger.warning("⚠️ GenAI Client skipped: No PROJECT_ID found.")
            return

        try:
            self.client = genai.Client(
                vertexai=True,
                project=str(int(final_project_id)),
                location=location
            )
            logger.info("✅ CreativeService initialized (DEPRECATED - use VideoAgent/ImageAgent/AudioAgent).")
        except Exception as e:
            logger.error(f"❌ Vertex AI initialization failed: {e}")

    # All generation methods removed - use specialized agents instead
    # See: image_agent.py, audio_agent.py

# Stable alias defaults (auto-upgrade without code changes)
VIDEO_MODEL_ALIAS = os.getenv("VERTEX_VIDEO_MODEL_ALIAS", "veo-3.1-generate-001")
IMAGE_MODEL_ALIAS = os.getenv("VERTEX_IMAGE_MODEL_ALIAS", "imagen-3.0")
TTS_MODEL_ALIAS = os.getenv("VERTEX_TTS_MODEL_ALIAS", "gemini-1.5-pro")
BUCKET_NAME = "ali-platform-prod-73019.firebasestorage.app"


def _resolve_project_id(numeric_env_id: Optional[str], standard_env_id: Optional[str]) -> Optional[int]:
    """Parse project ID, strictly enforcing numeric value."""
    for candidate in (numeric_env_id, standard_env_id):
        try:
            if candidate is not None:
                return int(candidate)
        except (ValueError, TypeError):
            logger.warning(f"⚠️ Non-numeric PROJECT_ID detected: {candidate}")
    logger.error("❌ GENAI_PROJECT_ID missing or non-numeric. Aborting client init.")
    return None


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

        if final_project_id is None:
            logger.error("⚠️ GenAI Client skipped: No PROJECT_ID found.")
            return

        try:
            # Initialize the new google-genai Client
            self.client = genai.Client(
                vertexai=True,
                project=str(int(final_project_id)),
                location=location
            )
            logger.info("✅ CreativeService initialized successfully (google-genai SDK).")
        except Exception as e:
            logger.error(f"❌ Vertex AI initialization failed: {e}")

    # --- HELPER: GCS SIGNED URLS ---
    def _gs_to_https(self, gcs_uri: str) -> str:
        """Convert a gs:// URI into a public HTTPS URL.

        We use this when signing fails so downstream validators still receive
        an http(s) link rather than a gs:// scheme.
        """
        if gcs_uri and str(gcs_uri).startswith("gs://"):
            parts = gcs_uri.split("/")
            if len(parts) >= 4:
                bucket_name = parts[2]
                blob_name = "/".join(parts[3:])
                return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
        return gcs_uri

    def _get_signed_url(self, gcs_uri: str) -> str:
        """Generates a V4 signed URL for secure asset access."""
        if not self.storage_client:
            # Fallback: convert gs://bucket/path to a direct HTTPS URL so downstream
            # validators receive a web-accessible link instead of failing on scheme.
            if gcs_uri and str(gcs_uri).startswith("gs://"):
                parts = gcs_uri.split("/")
                if len(parts) >= 4:
                    bucket_name = parts[2]
                    blob_name = "/".join(parts[3:])
                    return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
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
            # Even if signing fails, return an HTTPS URL to avoid invalid URL errors downstream.
            return self._gs_to_https(gcs_uri)

    # --- HELPER: UPLOAD RAW BYTES (Critical for VEO/Imagen) ---
    def _upload_bytes_to_gcs(self, data: bytes, content_type: str, extension: str) -> str:
        """Uploads raw video/image bytes to GCS when no URI is provided."""
        if not self.storage_client:
            logger.error("❌ Storage Client not initialized.")
            return ""

        logger.debug(f"📤 Uploading {len(data)} bytes to bucket: {BUCKET_NAME}")

        try:
            bucket = self.storage_client.bucket(BUCKET_NAME)

            filename = f"asset_{int(time.time())}_{os.urandom(4).hex()}.{extension}"
            blob = bucket.blob(filename)
            blob.upload_from_string(data, content_type=content_type)

            logger.info(f"   ✅ Asset uploaded: {filename}")
            return blob.generate_signed_url(version="v4", expiration=3600, method="GET")
        except Exception as e:
            logger.error(f"❌ Upload Failed: {e}")
            return ""

    # --- DEPRECATED METHODS ---
    # As of Jan 2026, media generation has been moved to specialized agents:

    # - ImageAgent (app/services/image_agent.py)
    # - AudioAgent (app/services/audio_agent.py)
    #
    # These methods are removed to enforce usage of the new Persistent URL services.

import os
import time
import logging
from google.cloud import storage

logger = logging.getLogger(__name__)

class GCSService:
    def __init__(self):
        self.storage_client = None
        try:
            self.storage_client = storage.Client()
        except Exception as e:
            logger.error(f"⚠️ Storage Client Init Failed: {e}")

        # Mimic the logic from ai_studio.py to find the correct bucket
        self.project_id = os.getenv("PROJECT_ID")
        self.bucket_name = f"{self.project_id}-assets"
        self.location = os.getenv("AI_STUDIO_LOCATION", "us-central1")
        
        # Expiration for signed URLs (default 1 hour)
        try:
            self.expiration = int(os.getenv("GCS_SIGNED_URL_EXPIRATION", "3600"))
        except:
            self.expiration = 3600

    def upload_video(self, file_obj, filename: str, content_type: str = "video/mp4") -> str:
        """
        Uploads bytes or file object to GCS and returns a Signed or Public URL.
        Matches logic from ai_studio.py
        """
        if not self.storage_client:
            raise ValueError("Storage Client not initialized.")

        # 1. Get or Create Bucket
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(self.bucket_name, location=self.location)
        except Exception:
            # Fallback: try getting it again, maybe checking exists() failed due to permissions
            bucket = self.storage_client.bucket(self.bucket_name)

        # 2. Create Blob
        # Generate a unique name if one wasn't provided, or enforce uniqueness
        if not filename:
            filename = f"published_video_{int(time.time())}.mp4"
        
        # Ensure path is clean
        blob_path = f"published_assets/{filename}"
        blob = bucket.blob(blob_path)

        # 3. Upload
        if isinstance(file_obj, bytes):
            blob.upload_from_string(file_obj, content_type=content_type)
        else:
            blob.upload_from_file(file_obj, content_type=content_type)

        # 4. Generate URL (Signed V4 preferred for security, else Public)
        try:
            # Try to generate a signed URL first (safer)
            return blob.generate_signed_url(
                version="v4",
                expiration=self.expiration,
                method="GET"
            )
        except Exception as e:
            logger.warning(f"Could not sign URL, attempting to return public link: {e}")
            # Fallback to public link (requires bucket to be public)
            return blob.public_url
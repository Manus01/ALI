import os
import time
import logging
from typing import Optional
from google.cloud import storage

logger = logging.getLogger(__name__)

class GCSService:
    def __init__(self):
        self.storage_client = None
        try:
            # 1. Initialize Client 
            # This automatically picks up the 'GOOGLE_APPLICATION_CREDENTIALS' env var 
            # we set in Cloud Run (pointing to /app/secrets/service-account.json)
            self.storage_client = storage.Client()
            
            # 2. Robust Project ID Detection (The Fix)
            # If "PROJECT_ID" env var is missing, get it directly from the authenticated client
            self.project_id = os.getenv("PROJECT_ID") or self.storage_client.project
            
            if not self.project_id:
                logger.warning("⚠️ Could not determine Project ID. Bucket operations may fail.")

            # 3. Define Bucket Name
            self.bucket_name = f"{self.project_id}-assets"
            self.location = os.getenv("AI_STUDIO_LOCATION", "us-central1")
            
            logger.info(f"✅ GCS Service Active. Using Bucket: {self.bucket_name}")

        except Exception as e:
            logger.error(f"⚠️ Storage Client Init Failed: {e}")

        # Expiration for signed URLs (default 1 hour)
        try:
            self.expiration = int(os.getenv("GCS_SIGNED_URL_EXPIRATION", "3600"))
        except Exception as e:
            logger.error(f"GCS Setup Failed: {e}")
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
                logger.info(f"Creating new bucket: {self.bucket_name}")
                bucket = self.storage_client.create_bucket(self.bucket_name, location=self.location)
        except Exception as e:
            logger.warning(f"Bucket check failed (might already exist or permission issue): {e}")
            # Fallback: Just try to grab the bucket object assuming it exists
            bucket = self.storage_client.bucket(self.bucket_name)

        # 2. Create Blob
        # Generate a unique name if one wasn't provided
        if not filename:
            filename = f"published_video_{int(time.time())}.mp4"
        
        # Ensure path is clean
        blob_path = f"published_assets/{filename}"
        blob = bucket.blob(blob_path)

        # 3. Upload
        logger.info(f"Uploading {filename} to {self.bucket_name}...")
        try:
            if isinstance(file_obj, bytes):
                blob.upload_from_string(file_obj, content_type=content_type)
            else:
                blob.upload_from_file(file_obj, content_type=content_type)
        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            raise e

        # 4. Generate URL (Signed V4 preferred for security, else Public)
        try:
            # Try to generate a signed URL first (safer)
            url = blob.generate_signed_url(
                version="v4",
                expiration=self.expiration,
                method="GET"
            )
            return url
        except Exception as e:
            logger.warning(f"Could not sign URL, attempting fallback to public link: {e}")
            # Fallback to public link (requires bucket to be public)
            return blob.public_url

    def generate_signed_url(
        self,
        bucket_name: str,
        blob_path: str,
        expiration: Optional[int] = None
    ) -> Optional[str]:
        """Generate a fresh signed URL for an existing object."""
        if not self.storage_client:
            logger.warning("⚠️ Storage Client not initialized.")
            return None

        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            return blob.generate_signed_url(
                version="v4",
                expiration=expiration or self.expiration,
                method="GET"
            )
        except Exception as e:
            logger.warning(f"Could not generate signed URL for {bucket_name}/{blob_path}: {e}")
            return None

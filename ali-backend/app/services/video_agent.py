import os
import time
import logging
from typing import Optional, Any
from google import genai
from google.genai import types
from google.cloud import storage

# Configure Logger
logger = logging.getLogger("ali_platform.services.video_agent")

# Configuration
BUCKET_NAME = "ali-platform-prod-73019.firebasestorage.app"
VIDEO_MODEL = "veo-3.1-generate-001"

class VideoAgent:
    def __init__(self):
        """Initializes the VideoAgent with Vertex AI and Storage clients."""
        try:
            self.storage_client = storage.Client()
        except Exception as e:
            logger.error(f"❌ Storage Client Init Failed: {e}")
            self.storage_client = None

        self.client = None
        self._init_genai_client()

    def _init_genai_client(self):
        """Initializes the Google GenAI client with integer Project ID."""
        try:
            project_id_str = os.getenv("GENAI_PROJECT_ID", os.getenv("PROJECT_ID", "776425171266"))
            try:
                project_id = int(project_id_str)
            except (ValueError, TypeError):
                logger.error(f"❌ Invalid Project ID: {project_id_str}. Must be integer.")
                return

            location = os.getenv("AI_STUDIO_LOCATION", "us-central1")
            self.client = genai.Client(
                vertexai=True,
                project=str(project_id),
                location=location
            )
            logger.info("✅ VideoAgent initialized (VEO 3.1).")
        except Exception as e:
            logger.error(f"❌ VideoAgent Client Init Failed: {e}")

    def _upload_bytes(self, data: bytes, extension: str = "mp4", content_type: str = "video/mp4") -> str:
        """Uploads raw bytes to GCS and returns a signed URL."""
        if not self.storage_client: return ""
        try:
            bucket = self.storage_client.bucket(BUCKET_NAME)
            filename = f"video_{int(time.time())}_{os.urandom(4).hex()}.{extension}"
            blob = bucket.blob(filename)
            blob.upload_from_string(data, content_type=content_type)
            logger.info(f"   ✅ Video Uploaded: {filename}")
            return blob.generate_signed_url(version="v4", expiration=3600, method="GET")
        except Exception as e:
            logger.error(f"❌ Upload Failed: {e}")
            return ""

    def _get_signed_url(self, gcs_uri: str) -> str:
        """Generates a signed URL from a gs:// URI."""
        if not self.storage_client: return gcs_uri
        try:
            if gcs_uri.startswith("gs://"):
                parts = gcs_uri.split("/")
                bucket_name = parts[2]
                blob_name = "/".join(parts[3:])
                blob = self.storage_client.bucket(bucket_name).blob(blob_name)
                return blob.generate_signed_url(version="v4", expiration=3600, method="GET")
        except Exception:
            pass
        return gcs_uri

    # --- HELPER: Image Object Creation ---
    def _prepare_image_part(self, image_input: str) -> Optional[types.Part]:
        """Creates a Part object from GCS URI or Base64."""
        if not image_input: return None
        try:
            if image_input.startswith("gs://"):
                return types.Part.from_uri(image_input, mime_type="image/png")
            else:
                # Assume Base64
                import base64
                return types.Part.from_bytes(base64.b64decode(image_input), mime_type="image/png")
        except Exception as e:
            logger.error(f"❌ Failed to process reference image: {e}")
            return None

    def generate_video(self, prompt: str, reference_image: Optional[str] = None, brand_dna: Optional[str] = None) -> Optional[str]:
        """
        Generates a video using Veo 3.1.
        Supports:
        - Adaptive Inputs (Reference Image)
        - Contextual Prompts (Brand DNA)
        """
        if not self.client: return None
        
        # 1. Contextual Prompting (Brand DNA)
        final_prompt = prompt
        if brand_dna:
            final_prompt = f"{prompt} Style requirements: {brand_dna}. Maintain consistent brand aesthetics."
            
        logger.info(f"🎬 VEO 3.1 Generating: {final_prompt[:50]}...")
        if reference_image:
             logger.info("   📸 Using Reference Image for conditioning.")

        try:
            # 2. Output Configuration
            output_gcs_uri = f"gs://{BUCKET_NAME}"
            
            # 3. Construct Content (Prompt + Optional Image)
            # Veo supports Multi-modal prompts for Image-to-Video
            contents = [final_prompt]
            
            if reference_image:
                img_part = self._prepare_image_part(reference_image)
                if img_part:
                    contents.append(img_part)
            
            # 4. Call Model
            job = self.client.models.generate_videos(
                model=VIDEO_MODEL,
                prompt=contents, # Pass list of [Text, Image]
                config=types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    person_generation="allow",
                    # We define output URI but also handle bytes if they come back
                    output_gcs_uri=output_gcs_uri 
                )
            )

            # 5. Manual Polling
            if hasattr(job, "done"):
                while not job.done():
                    time.sleep(5)
            
            # 6. Result Extraction
            # Target 'generated_videos' list in job.result or job.response
            generated_videos = None
            result = getattr(job, "result", None)
            
            # Try getting generated_videos from result object
            if result:
                generated_videos = getattr(result, "generated_videos", None)
            
            # Fallback: Try from response object if result didn't have it
            if not generated_videos and hasattr(job, "response"):
                 generated_videos = getattr(job.response, "generated_videos", None)

            if not generated_videos:
                logger.error("❌ No generated_videos list found in response.")
                return None

            # Iterate deeply
            video_uri = None
            video_bytes = None
            
            for vid in generated_videos:
                # Path A: Bytes
                # Check .video.video_bytes, .video_bytes, .bytes
                candidate_bytes = getattr(vid, "video_bytes", None)
                if not candidate_bytes:
                     inner_video = getattr(vid, "video", None)
                     if inner_video:
                         candidate_bytes = getattr(inner_video, "video_bytes", None)
                
                if candidate_bytes:
                    video_bytes = candidate_bytes
                    break # Found bytes
                
                # Path B: URI
                # Check .gcs_uri, .gcsUri, .uri
                candidate_uri = getattr(vid, "gcs_uri", None) or \
                                getattr(vid, "gcsUri", None) or \
                                getattr(vid, "uri", None)
                
                if candidate_uri:
                    video_uri = candidate_uri
                    break # Found URI

            # Action
            if video_bytes:
                logger.info("RETRIEVED BYTES")
                return self._upload_bytes(video_bytes)
            
            if video_uri:
                logger.info(f"RETRIEVED URI: {video_uri}")
                return self._get_signed_url(video_uri)

            logger.error("❌ Failed to extract Video Bytes or URI.")
            return None

        except Exception as e:
            logger.error(f"❌ Video Generation Error: {e}")
            return None

import os
import time
import logging
import uuid
import urllib.parse
from typing import Optional, Any, Callable
from google import genai
from google.genai import types
from google.cloud import storage

# Configure Logger
logger = logging.getLogger("ali_platform.services.video_agent")

# Configuration
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ali-platform-prod-73019.firebasestorage.app")
# Veo 3 Fast: Optimized for speed (3-4 min vs 13+ min for standard)
VIDEO_MODEL = os.getenv("VEO_MODEL", "veo-3.1-fast-generate-001")
# VIDEO_ENABLED: Set to "true" to enable video generation (Veo is slow, default OFF for reliability)
VIDEO_ENABLED = os.getenv("VIDEO_ENABLED", "false").lower() == "true"
MAX_RETRIES = 3
POLL_INTERVAL = 5

class VideoAgent:
    def __init__(self):
        """
        Initializes the VideoAgent with Vertex AI and Storage clients.
        
        Raises:
            Exception: If storage client initialization fails
        """
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
            project_id = os.getenv("GENAI_PROJECT_ID", os.getenv("PROJECT_ID", "776425171266"))
            
            location = os.getenv("AI_STUDIO_LOCATION", "us-central1")
            self.client = genai.Client(
                vertexai=True,
                project=str(project_id),
                location=location
            )
            logger.info("✅ VideoAgent initialized (VEO 3.1).")
        except Exception as e:
            logger.error(f"❌ VideoAgent Client Init Failed: {e}")

    def _upload_bytes(self, data: bytes, folder: str = "general", extension: str = "mp4", content_type: str = "video/mp4") -> dict:
        """
        Uploads raw bytes to GCS and returns a dict with persistent Firebase Download URL.
        
        Returns:
            dict: {"url": str, "gcs_object_key": str, "bucket": str} or empty strings on failure
        """
        if not self.storage_client: return {"url": "", "gcs_object_key": ""}
        try:
            bucket = self.storage_client.bucket(BUCKET_NAME)
            # Use folder structure as requested
            filename = f"{folder}/video_{int(time.time())}_{os.urandom(4).hex()}.{extension}"
            blob = bucket.blob(filename)
            
            # Generate a random UUID token for Firebase
            token = str(uuid.uuid4())
            metadata = {"firebaseStorageDownloadTokens": token}
            blob.metadata = metadata
            
            # Upload with metadata
            blob.upload_from_string(data, content_type=content_type)
            # Must patch metadata after upload to ensure it persists if not set during upload
            blob.metadata = metadata
            blob.patch()
            
            logger.info(f"   ✅ Video Uploaded (Persistent): {filename}")
            
            # Construct Persistent URL
            encoded_path = urllib.parse.quote(filename, safe="")
            public_url = f"https://firebasestorage.googleapis.com/v0/b/{BUCKET_NAME}/o/{encoded_path}?alt=media&token={token}"
            
            return {
                "url": public_url,
                "gcs_object_key": filename,
                "bucket": BUCKET_NAME
            }
        except Exception as e:
            logger.error(f"❌ Upload Failed: {e}")
            return {"url": "", "gcs_object_key": ""}

    def _convert_gcs_uri_to_persistent_url(self, gcs_uri: str) -> dict:
        """
        Converts a gs:// URI to a persistent Firebase URL by copying the blob
        with a download token. This ensures URLs never expire.
        
        Returns:
            dict: {"url": str, "gcs_object_key": str} or fallback
        """
        if not self.storage_client or not gcs_uri: 
            return {"url": gcs_uri, "gcs_object_key": ""}
        
        try:
            if not gcs_uri.startswith("gs://"):
                return {"url": gcs_uri, "gcs_object_key": ""}
                
            parts = gcs_uri.split("/")
            source_bucket_name = parts[2]
            source_blob_name = "/".join(parts[3:])
            
            # 1. Access Source Blob
            source_bucket = self.storage_client.bucket(source_bucket_name)
            source_blob = source_bucket.blob(source_blob_name)
            
            # 2. Download Content (In-memory is fine for generated clips < 50MB)
            logger.info("   ⬇️ Downloading Veo output to re-upload with persistent token...")
            content = source_blob.download_as_bytes()
            
            # 3. Re-upload as Persistent Asset
            return self._upload_bytes(content, folder="tutorials", extension="mp4", content_type="video/mp4")
            
        except Exception as e:
            logger.error(f"❌ Persistent Conversion Failed: {e}")
            # Fallback: Signed URL (Expire warning)
            try:
                if gcs_uri.startswith("gs://"):
                    parts = gcs_uri.split("/")
                    bucket_name = parts[2]
                    blob_name = "/".join(parts[3:])
                    blob = self.storage_client.bucket(bucket_name).blob(blob_name)
                    signed = blob.generate_signed_url(version="v4", expiration=3600, method="GET")
                    return {"url": signed, "gcs_object_key": blob_name, "warning": "signed_url_expiry"}
            except:
                pass
            return {"url": gcs_uri, "gcs_object_key": ""}

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

    def generate_video(self, prompt: str, reference_image_uri: Optional[str] = None, brand_dna: Optional[str] = None, folder: str = "general", progress_callback: Optional[Callable[[str], None]] = None) -> Optional[str]:
        """
        Generates a video using Veo 3.1.
        Supports:
        - Adaptive Inputs (Reference Image URI)
        - Contextual Prompts (Brand DNA)
        - Folder Organization
        - Progress Callback for status broadcasting
        """
        # Skip video generation if disabled (default) - use images instead
        if not VIDEO_ENABLED:
            logger.info("⏭️ Video generation disabled (VIDEO_ENABLED=false). Use image fallback.")
            return None
            
        if not self.client: return None
        
        # 1. Pydantic Fix: String-Strict Validation
        # Ensure prompt is a flat string.
        clean_prompt = prompt
        if isinstance(clean_prompt, list):
            clean_prompt = clean_prompt[0]
        
        # 2. Contextual Prompting (Brand DNA)
        if brand_dna:
            clean_prompt = f"{clean_prompt} Style requirements: {brand_dna}. Maintain consistent brand aesthetics."
        
        logger.info(f"🎬 VEO 3.1 Generating: {clean_prompt[:50]}...")

        if reference_image_uri:
             logger.info("   📸 Using Reference Image (Reference support pending SDK update).")
             # Note: Multi-modal reference support in Veo with strict string prompts requires specific config 
             # or waiting for SDK Pydantic fix. For now, we proceed with Text-to-Video.

        try:
            # 2. Output Configuration
            output_gcs_uri = f"gs://{BUCKET_NAME}/{folder}"
            
            # 3. Call Model - auto-detect method
            generate_method = getattr(self.client.models, "generate_videos", None)
            
            if generate_method:
                 job = generate_method(
                    model=VIDEO_MODEL,
                    prompt=clean_prompt,
                    config=types.GenerateVideosConfig(
                        aspect_ratio="16:9",
                        resolution="1080p",  # Standard HD - faster than 4K
                        person_generation="allow_adult",
                        output_gcs_uri=output_gcs_uri,
                        number_of_videos=1
                    )
                )
            else:
                logger.warning("⚠️ generate_videos not found, falling back to generate_content")
                job = self.client.models.generate_content(
                    model=VIDEO_MODEL,
                    contents=clean_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="video/mp4" # Attempting best-effort
                    )
                )

            # 5. Robust Polling with Extended Timeout
            if hasattr(job, "done"):
                start_time = time.time()
                timeout = 1200  # 20 minutes max (safety margin for complex prompts)
                last_progress_log = 0
                
                is_done_func = job.done if callable(job.done) else lambda: job.done
                
                while not is_done_func():
                    elapsed = time.time() - start_time
                    if elapsed > timeout:
                        logger.error(f"❌ Video Generation Timed Out after {timeout}s")
                        return None
                    
                    # Log and broadcast progress every 30 seconds
                    elapsed_int = int(elapsed)
                    if elapsed_int >= last_progress_log + 30:
                        last_progress_log = elapsed_int
                        progress_msg = f"Video processing... {elapsed_int}s elapsed"
                        logger.info(f"   ⏳ VEO Processing... ({elapsed_int}s)")
                        if progress_callback:
                            try:
                                progress_callback(progress_msg)
                            except Exception:
                                pass  # Don't let callback errors stop generation
                        
                    time.sleep(5)
            
            
            # 6. Result Extraction (Fixed)
            generated_videos = None
            
            # Handle result() vs result property
            result_attr = getattr(job, "result", None)
            final_result = None
            
            if callable(result_attr):
                try:
                    final_result = result_attr()
                except Exception as e:
                    logger.warning(f"Result call failed: {e}")
            else:
                final_result = result_attr

            # Try getting generated_videos from result object
            if final_result:
                generated_videos = getattr(final_result, "generated_videos", None)
            
            # Fallback: Try from response object 
            if not generated_videos and hasattr(job, "response"):
                 generated_videos = getattr(job.response, "generated_videos", None)
            
            # Fallback for generate_content (candidates)
            if not generated_videos and hasattr(final_result, "candidates"):
                 # Adapt candidates to expected structure if possible
                 pass 

            if not generated_videos:
                logger.error("❌ No generated_videos list found in response.")
                return None

            # Iterate deeply
            video_uri = None
            video_bytes = None
            
            for vid in generated_videos:
                # Path A: Bytes
                # Check .video.video_bytes (Double-nested as per Vertex AI 2026 standards)
                candidate_bytes = None
                
                # Nested check (Priority)
                inner_video = getattr(vid, "video", None)
                if inner_video:
                    candidate_bytes = getattr(inner_video, "video_bytes", None) or getattr(inner_video, "bytes", None)
                
                # Flat check (Fallback)
                if not candidate_bytes:
                    candidate_bytes = getattr(vid, "video_bytes", None) or getattr(vid, "bytes", None)

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
                # Return full dict result (URL + Key)
                return self._upload_bytes(video_bytes, folder=folder)
            
            if video_uri:
                logger.info(f"RETRIEVED URI: {video_uri}")
                # Return full dict result (URL + Key)
                return self._convert_gcs_uri_to_persistent_url(video_uri)

            logger.error("❌ Failed to extract Video Bytes or URI.")
            return None

        except Exception as e:
            logger.error(f"❌ Video Generation Error: {e}")
            return None

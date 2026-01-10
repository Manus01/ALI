import os
import time
import asyncio
import logging
import uuid
import urllib.parse
from typing import Optional
from google import genai
from google.genai import types
from google.cloud import storage
from google.api_core.exceptions import ResourceExhausted
import traceback

# Configure Logger
logger = logging.getLogger("ali_platform.services.image_agent")

# Configuration
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ali-platform-prod-73019.firebasestorage.app")
IMAGE_MODEL = "imagen-4.0-generate-001"  # Upgraded to Imagen 4.0 GA (Jan 2025)

# V4.0 Enhanced Retry Configuration
IMAGE_GENERATION_TIMEOUT = int(os.getenv("IMAGE_GENERATION_TIMEOUT", "120"))  # 2 minutes per image
MAX_RETRIES = int(os.getenv("IMAGE_MAX_RETRIES", "5"))  # Increased from 3 to 5
RETRY_BASE_DELAY = float(os.getenv("IMAGE_RETRY_BASE_DELAY", "2.0"))  # Exponential base


class ImageAgent:
    def __init__(self):
        """Initializes the ImageAgent."""
        try:
            self.storage_client = storage.Client()
        except Exception as e:
            logger.error(f"❌ Storage Client Init Failed: {e}")
            self.storage_client = None

        self.client = None
        self._init_genai_client()

    def _init_genai_client(self):
        """Initializes the Google GenAI client."""
        try:
            project_id = os.getenv("GENAI_PROJECT_ID", os.getenv("PROJECT_ID", "776425171266"))
            location = os.getenv("AI_STUDIO_LOCATION", "us-central1")
            self.client = genai.Client(
                vertexai=True,
                project=str(project_id),
                location=location
            )
            logger.info("✅ ImageAgent initialized (Imagen 4.0).")
        except Exception as e:
            logger.error(f"❌ ImageAgent Client Init Failed: {e}")

    def _upload_bytes(self, data: bytes, folder: str = "general", extension: str = "png", content_type: str = "image/png") -> dict:
        """Uploads raw bytes to GCS and returns a persistent Firebase Download URL."""
        if not self.storage_client:
            return {"url": "", "gcs_object_key": ""}
        try:
            bucket = self.storage_client.bucket(BUCKET_NAME)
            filename = f"{folder}/image_{int(time.time())}_{os.urandom(4).hex()}.{extension}"
            blob = bucket.blob(filename)
            
            # Generate Token
            token = str(uuid.uuid4())
            metadata = {"firebaseStorageDownloadTokens": token}
            blob.metadata = metadata

            blob.upload_from_string(data, content_type=content_type)
            blob.metadata = metadata
            blob.patch()
            
            logger.info(f"   ✅ Image Uploaded (Persistent): {filename}")
            
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

    def _prepare_image_part(self, image_input: str) -> Optional[types.Part]:
        """Creates a Part object from GCS URI or Base64."""
        if not image_input:
            return None
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

    def generate_image(self, prompt: str, reference_image_uri: Optional[str] = None, brand_dna: Optional[str] = None, folder: str = "general") -> Optional[str]:
        """
        Generates an image using Imagen 4.0.
        Supports:
        - Adaptive Inputs (Reference Image URI)
        - Contextual Prompts (Brand DNA)
        - Folder Organization
        - Retry logic for Rate Limits (429)
        """
        if not self.client:
            return None
        
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # V4.0: Enhanced retry logic with configurable retries
        for attempt in range(MAX_RETRIES):
            try:
                # Check if we've exceeded total timeout
                if time.time() - start_time > IMAGE_GENERATION_TIMEOUT:
                    logger.error(f"❌ Total timeout exceeded for request {request_id}")
                    return {"error": "timeout", "message": "Generation timeout exceeded"}
                # 1. Pydantic Fix: String-Strict Validation
                clean_prompt = prompt
                if isinstance(clean_prompt, list):
                    clean_prompt = clean_prompt[0]

                # 2. Contextual Prompting (Brand DNA)
                if brand_dna:
                    clean_prompt = f"{clean_prompt} Style requirements: {brand_dna}. Maintain brand consistency."

                logger.info(f"🎨 Imagen 4.0 Generating: {clean_prompt[:50]}...")
                
                # 3. Reference Image Logic (Campaign Branding)
                reference_images_config = None
                
                if reference_image_uri:
                    logger.info("   📸 Using Reference Image (Subject Ref ID: 1).")
                    try:
                        # Append Trigger
                        clean_prompt += " [1]"
                        
                        gcs_source = types.GcsSource(uris=[reference_image_uri])
                        
                        reference_images_config = [
                            types.ReferenceImage(
                                id=1,
                                subject_image=types.SubjectImage(gcs_source=gcs_source),
                                description="Brand Reference"
                            )
                        ]
                    except Exception as ref_e:
                        logger.warning(f"⚠️ Failed to configure Reference Image: {ref_e}. Proceeding with text only.")

                # 4. Generate with Imagen 4.0 config - optimized for speed
                job_config = types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                    output_mime_type="image/jpeg",
                    output_compression_quality=80
                )
                
                # Inject reference images if valid
                if reference_images_config:
                    if hasattr(job_config, "reference_images"):
                        job_config.reference_images = reference_images_config
                    else:
                        logger.warning("⚠️ GenerateImageConfig missing 'reference_images' attr.")
                
                response = self.client.models.generate_images(
                    model=IMAGE_MODEL,
                    prompt=clean_prompt,
                    config=job_config
                )

                if response.generated_images:
                    img = response.generated_images[0]
                    # Robust bytes extraction (SDK 2025 standard: .image.image_bytes)
                    image_obj = getattr(img, 'image', img)
                    img_bytes = getattr(image_obj, 'image_bytes', None) or getattr(image_obj, '_image_bytes', None)
                    if not img_bytes:
                        # Fallback: try direct bytes attribute
                        img_bytes = getattr(img, 'image_bytes', None)
                    if img_bytes:
                        # Return full dict (URL + Key) - using JPEG for faster processing
                        return self._upload_bytes(img_bytes, folder=folder, extension="jpg", content_type="image/jpeg")
                
                logger.warning("⚠️ No image bytes returned from Imagen 4.0.")
                return None

            except (ValueError, TypeError) as e:
                logger.error(f"❌ Input Validation Error (Request ID: {request_id}): {e}")
                return {"error": "validation", "message": str(e)}

            except ResourceExhausted as e:
                logger.warning(f"⚠️ Quota Hit (Attempt {attempt+1}/{MAX_RETRIES}, Request ID: {request_id}): {e}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BASE_DELAY ** (attempt + 1)
                    logger.info(f"⏳ Quota backoff: waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Quota exhausted after {MAX_RETRIES} attempts for request {request_id}")
                    return {"error": "quota_exhausted", "message": "Rate limit exceeded after max retries"}

            except Exception as e:
                error_str = str(e).lower()
                
                # Content Policy - don't retry, return error info
                if "blocked" in error_str or "safety" in error_str or "policy" in error_str:
                    logger.warning(f"⚠️ Content policy blocked for request {request_id}: {e}")
                    return {"error": "content_policy", "message": "Content blocked by safety policy"}
                
                # Timeout or Network - retry with backoff
                if "timeout" in error_str or "deadline" in error_str or "unavailable" in error_str:
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_BASE_DELAY ** attempt
                        logger.warning(f"⚠️ Timeout/Network error (Attempt {attempt+1}), retrying in {wait_time:.1f}s: {e}")
                        time.sleep(wait_time)
                        continue
                
                # Rate Limit - retry with backoff
                if "429" in error_str or "quota" in error_str or "resource exhausted" in error_str:
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_BASE_DELAY ** (attempt + 1)
                        logger.warning(f"⚠️ Rate Limit Hit (Generic, Attempt {attempt+1}): {e}")
                        time.sleep(wait_time)
                        continue
                
                # Unknown error - log and fail
                logger.error(f"❌ Image Generation Error (Request ID: {request_id}): {e}")
                traceback.print_exc()
                return {"error": "generation_failed", "message": str(e)}
        
        # All retries exhausted
        logger.error(f"❌ All {MAX_RETRIES} retries exhausted for request {request_id}")
        return {"error": "max_retries", "message": "All generation attempts failed"}


async def generate_image_with_retry(prompt: str, reference_image_uri: Optional[str] = None, brand_dna: Optional[str] = None, folder: str = "general", max_retries: int = 3) -> Optional[dict]:
    """
    Async wrapper for image generation with retry logic.
    Returns dict with 'url' and 'gcs_object_key' or None on failure.
    """
    agent = ImageAgent()
    
    for attempt in range(max_retries):
        try:
            result = agent.generate_image(
                prompt=prompt,
                reference_image_uri=reference_image_uri,
                brand_dna=brand_dna,
                folder=folder
            )
            if result:
                return result
        except ResourceExhausted as e:
            print(f"Quota hit (attempt {attempt + 1}): {e}")
            await asyncio.sleep(2 ** attempt)  # Exponential Backoff
        except Exception as e:
            print(f"Gen Error: {e}")
            return None
    
    return None

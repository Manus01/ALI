import os
import time
import logging
import uuid
import urllib.parse
from typing import Optional
from google import genai
from google.genai import types
from google.cloud import storage

# Configure Logger
logger = logging.getLogger("ali_platform.services.image_agent")

# Configuration
BUCKET_NAME = "ali-platform-prod-73019.firebasestorage.app"
IMAGE_MODEL = "imagen-3.0-generate-001"

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
            project_id_str = os.getenv("GENAI_PROJECT_ID", os.getenv("PROJECT_ID", "776425171266"))
            try:
                project_id = int(project_id_str)
            except (ValueError, TypeError):
                logger.error(f"❌ Invalid Project ID. Must be integer.")
                return

            location = os.getenv("AI_STUDIO_LOCATION", "us-central1")
            self.client = genai.Client(
                vertexai=True,
                project=str(project_id),
                location=location
            )
            logger.info("✅ ImageAgent initialized (Imagen 3.0).")
        except Exception as e:
            logger.error(f"❌ ImageAgent Client Init Failed: {e}")

    def _upload_bytes(self, data: bytes, folder: str = "general", extension: str = "png", content_type: str = "image/png") -> str:
        """Uploads raw bytes to GCS and returns a persistent Firebase Download URL."""
        if not self.storage_client: return ""
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
            return public_url
        except Exception as e:
            logger.error(f"❌ Upload Failed: {e}")
            return ""

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

    def generate_image(self, prompt: str, reference_image_uri: Optional[str] = None, brand_dna: Optional[str] = None, folder: str = "general") -> Optional[str]:
        """
        Generates an image using Imagen 3.0.
        Supports:
        - Adaptive Inputs (Reference Image URI)
        - Contextual Prompts (Brand DNA)
        - Folder Organization
        """
        if not self.client: return None
        
        # 1. Prompt Augmentation
        final_prompt = prompt
        if brand_dna:
            final_prompt = f"{prompt} Style requirements: {brand_dna}. Maintain brand consistency."

        logger.info(f"🎨 Imagen 3.0 Generating: {final_prompt[:50]}...")
        if reference_image_uri:
             logger.info("   📸 Using Reference Image.")

        try:
             # 2. Construct Prompt Content
             contents = [final_prompt]
             if reference_image_uri:
                 img_part = self._prepare_image_part(reference_image_uri)
                 if img_part:
                     contents.append(img_part)

             # 3. Generate
             # Note: Imagen 3.0 supports multi-modal prompts for some editing/variation tasks.
             # If strictly Text-to-Image, it handles text. If Image provided, it treats as conditioning.
             response = self.client.models.generate_images(
                model=IMAGE_MODEL,
                prompt=contents, 
                config=types.GenerateImageConfig(
                    number_of_images=1,
                    aspect_ratio="16:9"
                )
             )

             if response.generated_images:
                img = response.generated_images[0]
                if img.image_bytes:
                    return self._upload_bytes(img.image_bytes, folder=folder)
            
             logger.warning("⚠️ No image bytes returned.")
             return None

        except Exception as e:
            logger.error(f"❌ Image Generation Error: {e}")
            return None

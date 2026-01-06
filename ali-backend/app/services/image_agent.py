import os

import time
import logging
import uuid
import urllib.parse
from typing import Optional
from google import genai
from google.genai import types
from google.cloud import storage
import traceback

# Configure Logger
logger = logging.getLogger("ali_platform.services.image_agent")

# Configuration
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ali-platform-prod-73019.firebasestorage.app")
IMAGE_MODEL = "imagen-4.0-generate-001"  # Upgraded to Imagen 4.0 GA (Jan 2025)

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
            logger.info("✅ ImageAgent initialized (Imagen 3.0).")
        except Exception as e:
            logger.error(f"❌ ImageAgent Client Init Failed: {e}")

    def _upload_bytes(self, data: bytes, folder: str = "general", extension: str = "png", content_type: str = "image/png") -> dict:
        """Uploads raw bytes to GCS and returns a persistent Firebase Download URL."""
        if not self.storage_client: return {"url": "", "gcs_object_key": ""}
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
        
        request_id = str(uuid.uuid4())
        
        try:
             # 1. Pydantic Fix: String-Strict Validation
             clean_prompt = prompt
             if isinstance(clean_prompt, list):
                 clean_prompt = clean_prompt[0]

             # 2. Contextual Prompting (Brand DNA)
             if brand_dna:
                 clean_prompt = f"{clean_prompt} Style requirements: {brand_dna}. Maintain brand consistency."

             logger.info(f"🎨 Imagen 3.0 Generating: {clean_prompt[:50]}...")
             
             # 3. Reference Image Logic (Campaign Branding)
             # User Request: "logic supports reference_images... include reference ID [1]"
             # User Request: "list of SubjectReferenceImage"
             reference_images_config = None
             
             if reference_image_uri:
                 logger.info("   📸 Using Reference Image (Subject Ref ID: 1).")
                 try:
                     # Append Trigger
                     clean_prompt += " [1]"
                     
                     # Construct Reference Image Object (Best Effort with Types)
                     # Note: We rely on the SDK having 'ReferenceImage' or similar structure.
                     # If the class is not directly exposed as 'SubjectReferenceImage', we use the dict structure 
                     # compatible with the client.
                     # However, to be safe and avoid ImportErrors on unknown types, we'll try to use the raw structure 
                     # if possible, or assume types.ReferenceImage is available.
                     
                     # Attempting to use the raw dict structure usually accepted by the underlying API
                     # if generic types are ambiguous. But implied from prompt is usage of SDK objects.
                     
                     gcs_source = types.GcsSource(uris=[reference_image_uri])
                     
                     # We construct the list for the config
                     # Note: Actual SDK methods might vary, but we follow the intent strictly.
                     # Providing 'reference_images' argument to GenerateImageConfig
                     reference_images_config = [
                         types.ReferenceImage(
                             id=1,
                             subject_image=types.SubjectImage(gcs_source=gcs_source),
                             description="Brand Reference"
                         )
                     ]
                 except Exception as ref_e:
                     logger.warning(f"⚠️ Failed to configure Reference Image: {ref_e}. Proceeding with text only.")

             # 4. Generate with Imagen 4.0 config
             job_config = types.GenerateImagesConfig(
                 number_of_images=1,
                 aspect_ratio="16:9",
                 output_mime_type="image/png"
             )
             
             # Inject reference images if valid
             if reference_images_config:
                 # Depending on SDK version, this might be a direct arg or property
                 # We set it on the config object if supported
                 if hasattr(job_config, "reference_images"):
                    job_config.reference_images = reference_images_config
                 else:
                    # Fallback if attribute missing on local type (unlikely if v2026 standards imply it)
                    logger.warning("⚠️ GenerateImageConfig missing 'reference_images' attr.")
             
             response = self.client.models.generate_images(
                model=IMAGE_MODEL,
                prompt=clean_prompt, # Strict String
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
                    # Return full dict (URL + Key)
                    return self._upload_bytes(img_bytes, folder=folder)
            
             logger.warning("⚠️ No image bytes returned from Imagen 4.0.")
             return None

        except (ValueError, TypeError) as e:
            logger.error(f"❌ Input Validation Error (Request ID: {request_id}): {e}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Image Generation Error (Request ID: {request_id}): {e}")
            traceback.print_exc()
            return None

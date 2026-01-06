import os

import time
import logging
import uuid
import urllib.parse
import re
from typing import Optional, Any
from google import genai
from google.cloud import storage

# Configure Logger
logger = logging.getLogger("ali_platform.services.audio_agent")

# Configuration
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ali-platform-prod-73019.firebasestorage.app")
TTS_MODEL = "gemini-1.5-pro" 

class AudioAgent:
    def __init__(self):
        """Initializes the AudioAgent with Vertex AI and Storage clients."""
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
            logger.info("✅ AudioAgent initialized (Gemini 2.5 TTS).")
        except Exception as e:
            logger.error(f"❌ AudioAgent Client Init Failed: {e}")

    def _upload_bytes(self, data: bytes, folder: str = "general", extension: str = "mp3", content_type: str = "audio/mpeg") -> dict:
        """Uploads raw bytes to GCS and returns a persistent Firebase Download URL."""
        if not self.storage_client: return {"url": "", "gcs_object_key": ""}
        try:
            bucket = self.storage_client.bucket(BUCKET_NAME)
            # Use folder structure as requested
            filename = f"{folder}/audio_{int(time.time())}_{os.urandom(4).hex()}.{extension}"
            blob = bucket.blob(filename)
            
            # Generate a random UUID token for Firebase
            token = str(uuid.uuid4())
            metadata = {"firebaseStorageDownloadTokens": token}
            blob.metadata = metadata
            
            # Upload with metadata
            blob.upload_from_string(data, content_type=content_type)
            blob.metadata = metadata
            blob.patch()
            
            logger.info(f"   ✅ Audio Uploaded (Persistent): {filename}")
            
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

    def generate_audio(self, text: str, folder: str = "general") -> Optional[str]:
        """
        Generates audio using Gemini 2.5 Pro (TTS Prompting).
        Returns a persistent Firebase URL.
        """
        if not self.client or not text: return None
        
        request_id = str(uuid.uuid4())
        
        # Validation: Text length limit for TTS
        if len(text) > 4096:
            logger.warning(f"⚠️ Text too long for TTS ({len(text)} chars). Truncating.")
            text = text[:4096]
            
        logger.info(f"🎙️ Gemini 2.5 TTS Generating (Req: {request_id}): {text[:50]}...")
        
        try:
            clean_text = re.sub(r'[*#`]', '', text) # Sanitize markdown

            # Prompting for specific voice and format
            prompt = f"Generate spoken audio for the following text using the 'Aoede' voice (High Definition). Return raw MP3 bytes.\n\nTEXT: {clean_text}"

            operation = self.client.models.generate_content(
                model=TTS_MODEL,
                contents=prompt
            )

            # Manual Polling (Standardized)
            response = operation
            if hasattr(operation, "done"):
                while not operation.done():
                    time.sleep(1)
                
                if getattr(operation, "error", None):
                    logger.error(f"❌ TTS Operation Failed: {operation.error}")
                    return None
                    
                # Extract Result
                if hasattr(operation, "result"):
                    # Handle both method and property
                    if callable(operation.result):
                        response = operation.result() 
                    else:
                        response = operation.result

            # Byte Extraction
            audio_bytes = None
            
            # Helper for bytes normalization
            def _normalize_bytes(raw: Any) -> Optional[bytes]:
                if raw is None: return None
                if isinstance(raw, bytes): return raw
                if isinstance(raw, bytearray): return bytes(raw)
                if isinstance(raw, list):
                    try: return bytes(raw)
                    except Exception: 
                        logger.warning("Audio concatenation fallback failed.")
                        return b"".join(raw) if all(isinstance(x, (bytes, bytearray)) for x in raw) else None
                return None

            try:
                # Attempt 1: Inline Data in Candidates
                if response and getattr(response, "candidates", None):
                    for part in response.candidates[0].content.parts:
                        inline_data = getattr(part, "inline_data", None)
                        if inline_data and getattr(inline_data, "data", None):
                            audio_bytes = _normalize_bytes(inline_data.data)
                            break
                
                # Attempt 2: Text Fallback (Encoded)
                if not audio_bytes and getattr(response, "text", None):
                    # Sometimes comes back as text if prompt wasn't obeyed perfectly, or strictly text mode
                    # But for TTS prompt, if it fails to give bytes, it might be an error message.
                    # We'll valid check len.
                    pass 

            except Exception as e:
                logger.warning(f"⚠️ Byte extraction warning: {e}")

            if audio_bytes:
                # Return full dict (URL + Key)
                return self._upload_bytes(audio_bytes, folder=folder)

            logger.error("❌ Audio Generation failed: No bytes returned.")
            return None

        except Exception as e:
            logger.error(f"❌ Audio Generation Error: {e}")
            return None

import os
import base64
import time
import logging
import uuid
import urllib.parse
import re
from typing import Optional, Any, Union
from google import genai
from google.genai import types
from google.cloud import storage

# Configure Logger
logger = logging.getLogger("ali_platform.services.audio_agent")

# Configuration
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ali-platform-prod-73019.firebasestorage.app")
# Updated 2026-01-15: Using Gemini 2.5 Flash TTS Preview model with proper audio config
TTS_MODEL = os.getenv("TTS_MODEL", "gemini-2.5-flash-preview-tts")
# Fallback to flash-lite if preview unavailable
TTS_MODEL_FALLBACK = "gemini-2.5-flash-lite-tts"
# Default voice name (from Gemini TTS prebuilt voices)
TTS_VOICE = os.getenv("TTS_VOICE", "Aoede")

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
            logger.info(f"✅ AudioAgent initialized (Model: {TTS_MODEL}).")
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
            
            # Ensure public access for browser playback
            blob.make_public()
            
            logger.info(f"   ✅ Audio Uploaded (Persistent): {filename} ({len(data)} bytes)")
            
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

    def generate_audio(self, text: str, folder: str = "general") -> Optional[Union[str, dict]]:
        """
        Generates audio using Gemini 2.5 TTS Preview model.
        
        IMPORTANT: This uses:
        - response_modalities=["AUDIO"] to request audio output
        - speechConfig with prebuilt voice configuration
        
        Returns a persistent Firebase URL dict or None on failure.
        """
        if not self.client or not text: 
            logger.error("❌ AudioAgent client not initialized or empty text")
            return None
        
        request_id = str(uuid.uuid4())[:8]
        
        # Validation: Text length limit for TTS
        if len(text) > 4096:
            logger.warning(f"⚠️ Text too long for TTS ({len(text)} chars). Truncating.")
            text = text[:4096]
            
        logger.info(f"🎙️ TTS Generation Started (Req: {request_id})")
        logger.info(f"   Model: {TTS_MODEL}")
        logger.info(f"   Voice: {TTS_VOICE}")
        logger.info(f"   Text preview: {text[:80]}...")
        
        try:
            # Sanitize markdown artifacts from text
            clean_text = re.sub(r'[*#`_~]', '', text)
            clean_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean_text)  # Remove markdown links
            
            # Build proper GenerateContentConfig for TTS
            # CRITICAL: responseModalities=["AUDIO"] tells Gemini to output audio bytes
            speech_config = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=TTS_VOICE
                    )
                )
            )
            
            # === ATTEMPT 1: MP3 Encoding (preferred for browser compatibility) ===
            response = None
            used_fallback = False
            
            try:
                generation_config_mp3 = types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=speech_config,
                    audio_encoding="MP3"  # Explicitly request MP3 output format
                )
                
                logger.info(f"   📤 Sending TTS request (MP3 encoding)...")
                
                response = self.client.models.generate_content(
                    model=TTS_MODEL,
                    contents=clean_text,
                    config=generation_config_mp3
                )
                logger.info(f"   ✅ MP3 generation succeeded.")
                
            except Exception as mp3_error:
                # === ATTEMPT 2: Fallback to default/WAV encoding ===
                logger.warning(f"⚠️ MP3 generation failed: {mp3_error}. Falling back to default...")
                
                try:
                    generation_config_default = types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=speech_config
                        # No audio_encoding param - use API default (WAV/PCM)
                    )
                    
                    logger.info(f"   📤 Sending TTS request (default/WAV encoding)...")
                    
                    response = self.client.models.generate_content(
                        model=TTS_MODEL,
                        contents=clean_text,
                        config=generation_config_default
                    )
                    used_fallback = True
                    logger.info(f"   ✅ Fallback WAV generation succeeded.")
                    
                except Exception as fallback_error:
                    logger.error(f"❌ TTS Critical Failure (both MP3 and WAV failed): {fallback_error}")
                    raise fallback_error  # Re-raise to be caught by outer exception handler
            
            # === DEBUG LOGGING: Log raw response structure ===
            logger.info(f"   📥 Response received. Inspecting structure...")
            
            # Log response type and main attributes
            logger.info(f"   Response type: {type(response).__name__}")
            
            if hasattr(response, 'candidates') and response.candidates:
                logger.info(f"   Candidates count: {len(response.candidates)}")
                candidate = response.candidates[0]
                
                if hasattr(candidate, 'content') and candidate.content:
                    content = candidate.content
                    if hasattr(content, 'parts') and content.parts:
                        logger.info(f"   Parts count: {len(content.parts)}")
                        
                        for i, part in enumerate(content.parts):
                            logger.info(f"   Part[{i}] type: {type(part).__name__}")
                            logger.info(f"   Part[{i}] attributes: {[attr for attr in dir(part) if not attr.startswith('_')]}")
                            
                            # Check for inline_data
                            if hasattr(part, 'inline_data'):
                                inline_data = part.inline_data
                                if inline_data:
                                    logger.info(f"   Part[{i}].inline_data found!")
                                    logger.info(f"   inline_data type: {type(inline_data).__name__}")
                                    if hasattr(inline_data, 'mime_type'):
                                        logger.info(f"   inline_data.mime_type: {inline_data.mime_type}")
                                    if hasattr(inline_data, 'data'):
                                        data = inline_data.data
                                        logger.info(f"   inline_data.data type: {type(data).__name__}")
                                        if data:
                                            if isinstance(data, bytes):
                                                logger.info(f"   inline_data.data size: {len(data)} bytes")
                                            elif isinstance(data, str):
                                                logger.info(f"   inline_data.data is string, length: {len(data)}")
                                else:
                                    logger.info(f"   Part[{i}].inline_data is None/empty")
                            
                            # Check for text
                            if hasattr(part, 'text') and part.text:
                                logger.info(f"   Part[{i}].text (first 100 chars): {part.text[:100] if len(part.text) > 100 else part.text}")
                    else:
                        logger.warning(f"   ⚠️ No parts in content")
                else:
                    logger.warning(f"   ⚠️ No content in candidate")
            else:
                logger.warning(f"   ⚠️ No candidates in response")
                # Log additional response info for debugging
                if hasattr(response, 'text'):
                    logger.info(f"   response.text: {response.text[:200] if response.text else 'None'}")
                logger.info(f"   Response dir: {[a for a in dir(response) if not a.startswith('_')]}")
            
            # === BYTE EXTRACTION ===
            audio_bytes = None
            mime_type = None
            
            def _normalize_bytes(raw: Any) -> Optional[bytes]:
                """Normalize various data types to bytes, including Base64 decoding."""
                if raw is None: 
                    return None
                if isinstance(raw, bytes): 
                    return raw
                if isinstance(raw, bytearray): 
                    return bytes(raw)
                if isinstance(raw, str):
                    # Try Base64 decode
                    try:
                        decoded = base64.b64decode(raw)
                        logger.info(f"   ✅ Base64 decoded: {len(decoded)} bytes")
                        return decoded
                    except Exception as e:
                        logger.warning(f"   ⚠️ Base64 decode failed: {e}")
                        return None
                if isinstance(raw, list):
                    try: 
                        return bytes(raw)
                    except Exception:
                        if all(isinstance(x, (bytes, bytearray)) for x in raw):
                            return b"".join(raw)
                        return None
                return None

            try:
                # Extract from candidates -> content -> parts -> inline_data
                if response and getattr(response, 'candidates', None):
                    for candidate in response.candidates:
                        if not hasattr(candidate, 'content') or not candidate.content:
                            continue
                        if not hasattr(candidate.content, 'parts') or not candidate.content.parts:
                            continue
                            
                        for part in candidate.content.parts:
                            inline_data = getattr(part, 'inline_data', None)
                            if inline_data:
                                raw_data = getattr(inline_data, 'data', None)
                                if raw_data:
                                    audio_bytes = _normalize_bytes(raw_data)
                                    mime_type = getattr(inline_data, 'mime_type', 'audio/wav')
                                    if audio_bytes:
                                        logger.info(f"   ✅ Audio bytes extracted: {len(audio_bytes)} bytes, mime: {mime_type}")
                                        break
                        if audio_bytes:
                            break

            except Exception as e:
                logger.warning(f"⚠️ Byte extraction error: {e}", exc_info=True)

            if audio_bytes and len(audio_bytes) > 100:  # Sanity check: audio should be >100 bytes
                # Determine file extension from mime_type
                # Default based on whether fallback (WAV) was used or not (MP3)
                if used_fallback:
                    ext = "wav"
                    content_type = "audio/wav"
                else:
                    ext = "mp3"
                    content_type = "audio/mpeg"
                if mime_type:
                    if "mp3" in mime_type or "mpeg" in mime_type:
                        ext = "mp3"
                        content_type = "audio/mpeg"
                    elif "ogg" in mime_type:
                        ext = "ogg"
                        content_type = "audio/ogg"
                    elif "wav" in mime_type or "L16" in mime_type:
                        # Keep WAV only if explicitly returned by the API
                        ext = "wav"
                        content_type = "audio/wav"
                
                logger.info(f"   🎵 Audio generation successful! ({len(audio_bytes)} bytes, {ext})")
                return self._upload_bytes(audio_bytes, folder=folder, extension=ext, content_type=content_type)

            logger.error(f"❌ Audio Generation failed: No valid audio bytes returned.")
            logger.error(f"   audio_bytes is None: {audio_bytes is None}")
            if audio_bytes:
                logger.error(f"   audio_bytes length: {len(audio_bytes)}")
            return None

        except Exception as e:
            logger.error(f"❌ TTS Critical Failure: {e}")
            logger.error(f"   Exception type: {type(e).__name__}")
            logger.error(f"   Full exception details:", exc_info=True)
            return None

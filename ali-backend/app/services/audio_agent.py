import os
import base64
import time
import logging
import uuid
import urllib.parse
import re
import struct
from typing import Optional, Any, Union
from google import genai
from google.genai import types
from google.cloud import storage
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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

    def _add_wav_header(self, pcm_data: bytes, sample_rate: int = 24000, 
                        bits_per_sample: int = 16, num_channels: int = 1) -> bytes:
        """
        Adds WAV headers to raw L16 PCM audio data.
        
        Gemini TTS outputs raw PCM (audio/L16) without headers.
        Browsers require proper WAV container format to play audio.
        
        Args:
            pcm_data: Raw PCM audio bytes
            sample_rate: Sample rate in Hz (Gemini TTS uses 24000Hz)
            bits_per_sample: Bits per sample (16 for L16)
            num_channels: Number of audio channels (1 for mono)
        
        Returns:
            Complete WAV file bytes with proper headers
        """
        # WAV file structure:
        # - RIFF header (12 bytes)
        # - fmt subchunk (24 bytes for PCM)
        # - data subchunk (8 bytes header + audio data)
        
        data_size = len(pcm_data)
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        file_size = 36 + data_size  # Total file size minus 8 bytes for RIFF header
        
        # Build WAV header
        wav_header = struct.pack(
            '<4sI4s'       # RIFF chunk descriptor
            '4sIHHIIHH'    # fmt subchunk  
            '4sI',         # data subchunk header
            b'RIFF',       # ChunkID
            file_size,     # ChunkSize (file size - 8)
            b'WAVE',       # Format
            b'fmt ',       # Subchunk1ID
            16,            # Subchunk1Size (16 for PCM)
            1,             # AudioFormat (1 = PCM)
            num_channels,  # NumChannels
            sample_rate,   # SampleRate
            byte_rate,     # ByteRate
            block_align,   # BlockAlign
            bits_per_sample,  # BitsPerSample
            b'data',       # Subchunk2ID
            data_size      # Subchunk2Size
        )
        
        logger.info(f"   📦 WAV header added: {len(wav_header)} bytes header + {data_size} bytes audio")
        return wav_header + pcm_data

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda retry_state: logger.warning(
            f"⚠️ TTS Retry: Attempt {retry_state.attempt_number} failed, retrying..."
        )
    )
    def _generate_tts_with_retry(self, clean_text: str, generation_config):
        """Internal method with retry logic for TTS API calls."""
        return self.client.models.generate_content(
            model=TTS_MODEL,
            contents=clean_text,
            config=generation_config
        )

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
            
            # === AUDIO GENERATION ===
            # Note: Gemini TTS outputs PCM/WAV audio by default.
            # The audio_encoding param does NOT exist in GenerateContentConfig.
            # HTML5 <audio> elements support WAV playback natively.
            
            # NOTE: Custom safety_settings removed (2026-01-17)
            # Adjusting safety filters requires monthly invoiced billing.
            # Using default safety settings which work for educational content.
            
            generation_config = types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=speech_config
            )
            
            logger.info(f"   📤 Sending TTS request...")
            
            # Use retry-wrapped internal method for resilience against transient failures
            response = self._generate_tts_with_retry(clean_text, generation_config)
            
            # === BLOCKED CONTENT DETECTION ===
            # Check if content was blocked by safety filters
            if response and hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, 'finish_reason', None)
                if finish_reason and hasattr(finish_reason, 'name'):
                    finish_reason_name = finish_reason.name
                    blocked_reasons = ['SAFETY', 'RECITATION', 'BLOCKLIST', 'PROHIBITED_CONTENT', 'SPII']
                    if finish_reason_name in blocked_reasons:
                        logger.warning(
                            f"🚫 [GENERATION_BLOCKED] TTS blocked. "
                            f"Reason: {finish_reason_name}, "
                            f"Text preview: {clean_text[:80]}..."
                        )
                        # Return None to trigger retry/fallback handling
                        return None
                    elif finish_reason_name != 'STOP':
                        logger.warning(
                            f"⚠️ [CONTENT_ALERT] TTS non-standard finish. "
                            f"Reason: {finish_reason_name}"
                        )
            
            logger.info(f"   ✅ TTS generation succeeded.")
            
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
                # Gemini TTS outputs raw L16 PCM by default (NOT WAV with headers)
                ext = "wav"
                content_type = "audio/wav"
                needs_wav_header = True  # Default: assume raw PCM needs headers
                
                if mime_type:
                    if "mp3" in mime_type or "mpeg" in mime_type:
                        ext = "mp3"
                        content_type = "audio/mpeg"
                        needs_wav_header = False
                    elif "ogg" in mime_type:
                        ext = "ogg"
                        content_type = "audio/ogg"
                        needs_wav_header = False
                    elif "wav" in mime_type:
                        # If it's already a proper WAV file (has RIFF header), skip
                        if audio_bytes[:4] == b'RIFF':
                            logger.info("   🎵 Audio already has WAV header, skipping header addition")
                            needs_wav_header = False
                        else:
                            # Raw WAV/PCM without headers
                            needs_wav_header = True
                    elif "L16" in mime_type or "pcm" in mime_type.lower():
                        # Raw L16 PCM - definitely needs headers
                        needs_wav_header = True
                
                # Add WAV headers if needed for browser compatibility
                final_audio = audio_bytes
                if needs_wav_header:
                    logger.info("   🔧 Adding WAV headers to raw PCM data for browser compatibility...")
                    final_audio = self._add_wav_header(audio_bytes)
                
                logger.info(f"   🎵 Audio generation successful! ({len(final_audio)} bytes, {ext})")
                return self._upload_bytes(final_audio, folder=folder, extension=ext, content_type=content_type)

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

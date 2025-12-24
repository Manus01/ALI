import os
import time
import json
import logging
import re

# --- CONFIGURATION & INIT ---
logger = logging.getLogger(__name__)
LOCATION = os.getenv("AI_STUDIO_LOCATION", "us-central1")

# 1. DUAL ID HANDLING
numeric_env_id = os.getenv("GENAI_PROJECT_ID")
standard_env_id = os.getenv("PROJECT_ID")

PROJECT_ID = None

if numeric_env_id:
    from google import genai
    from google.genai import types
    from google.cloud import texttospeech
    from google.cloud import storage
    from google.api_core.exceptions import Unauthorized, Forbidden, DeadlineExceeded

    try:
        PROJECT_ID = int(numeric_env_id)
        print(f"🏢 Creative Service: Using Numeric GenAI ID: {PROJECT_ID}")
    except ValueError:
        PROJECT_ID = standard_env_id
else:
    try:
        PROJECT_ID = int(standard_env_id)
    except (ValueError, TypeError):
        print(f"⚠️ WARNING: PROJECT_ID ('{standard_env_id}') is not numeric. Veo Video Gen requires a numeric ID.")
        PROJECT_ID = standard_env_id

# 2. Robust Expiration Handling
try:
    GCS_SIGNED_URL_EXPIRATION = int(os.getenv("GCS_SIGNED_URL_EXPIRATION", "3600"))
except Exception:
    GCS_SIGNED_URL_EXPIRATION = 3600


class CreativeService:
    def __init__(self):
        # Initialize clients safely to prevent 500 Server Errors on startup
        self.storage_client = None
        self.tts_client = None
        self.client = None

        # 1. Init Storage
        try:
            self.storage_client = storage.Client()
        except Exception as e:
            print(f"⚠️ Storage Client Init Failed: {e}")

        # 2. Init TTS
        try:
            self.tts_client = texttospeech.TextToSpeechClient()
        except Exception as e:
            print(f"⚠️ TTS Client Init Failed: {e}")

        # 3. Init GenAI (Veo/Imagen)
        try:
            if not PROJECT_ID:
                print("⚠️ GenAI Skipped: No PROJECT_ID found.")
            else:
                self.client = genai.Client(
                    vertexai=True,
                    project=PROJECT_ID,
                    location=LOCATION
                )
        except Exception as e:
            print(f"⚠️ GenAI Client Init Failed: {e}")

    def _get_signed_url(self, gcs_uri: str) -> str:
        if not self.storage_client:
            return gcs_uri
            
        try:
            if not gcs_uri or not str(gcs_uri).startswith("gs://"):
                return gcs_uri
            
            parts = gcs_uri.split("/")
            bucket_name = parts[2]
            blob_name = "/".join(parts[3:])
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            gen_signed = getattr(blob, "generate_signed_url", None)
            if callable(gen_signed):
                return gen_signed(
                    version="v4",
                    expiration=int(GCS_SIGNED_URL_EXPIRATION),
                    method="GET"
                )
            return getattr(blob, "public_url", gcs_uri)
        except Exception as e:
            print(f"⚠️ Signing Error: {e}")
            return gcs_uri

    def _upload_bytes_to_gcs(self, data: bytes, content_type: str, extension: str) -> str:
        if not self.storage_client:
            print("❌ Cannot upload: Storage Client not initialized.")
            return ""

        bucket_prefix = os.getenv("PROJECT_ID", str(PROJECT_ID))
        bucket_name = f"{bucket_prefix}-assets"
        
        try:
            bucket = self.storage_client.bucket(bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(bucket_name, location=LOCATION)
        except Exception:
            try:
                bucket = self.storage_client.bucket(bucket_name)
            except:
                return ""

        filename = f"asset_{int(time.time())}_{os.urandom(4).hex()}.{extension}"
        blob = bucket.blob(filename)
        blob.upload_from_string(data, content_type=content_type)
        
        try:
            gen_signed = getattr(blob, "generate_signed_url", None)
            if callable(gen_signed):
                return gen_signed(version="v4", expiration=int(GCS_SIGNED_URL_EXPIRATION), method="GET")
            return getattr(blob, "public_url", "")
        except:
            return ""

    def generate_video(self, prompt: str, style: str = "cinematic") -> str:
        if not self.client:
            print("❌ Video Gen Skipped: GenAI Client invalid.")
            return "https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

        print(f"🎬 Veo Engine: Generating video for '{prompt}'...", flush=True)

        try:
            MODEL_ID = "veo-2.0-generate-001" 
            
            clean_prompt = (str(prompt).strip() if prompt else "").strip()
            if not clean_prompt:
                clean_prompt = f"{style} educational video"
            
            final_prompt = f"{style} style. {clean_prompt}"

            config_params = {
                "number_of_videos": 1,
                "aspect_ratio": "16:9",
                "negative_prompt": "blurry, text, watermark, bad quality"
            }

            # 1. Start Job
            operation = self.client.models.generate_videos(
                model=MODEL_ID,
                prompt=final_prompt,
                config=types.GenerateVideosConfig(**config_params)
            )

            if not operation:
                raise RuntimeError("API returned no operation.")

            print(f"⏳ Job Sent. Polling...", flush=True)

            # 2. Polling Loop
            polling_start = time.time()
            while not operation.done:
                if time.time() - polling_start > 600:
                    raise RuntimeError("Veo video generation timed out (10 min limit).")

                time.sleep(10)
                
                try:
                    # Refresh status
                    operation = self.client.operations.get(operation)
                except Exception as e:
                    print(f"⚠️ Polling retry warning: {e}")
                    # Fallback to name-based polling if object polling fails
                    if hasattr(operation, 'name'):
                        operation = self.client.operations.get(operation.name)

            # 3. Check for Errors
            if hasattr(operation, 'error') and operation.error:
                 raise RuntimeError(f"Veo Failure: {operation.error}")

            # 4. Extract Video Data (Bytes or URI)
            generated_videos = []
            
            result_payload = getattr(operation, "result", None)
            
            if result_payload:
                 generated_videos = getattr(result_payload, "generated_videos", [])
            elif hasattr(operation, "generated_videos"):
                 generated_videos = getattr(operation, "generated_videos", [])
            elif isinstance(operation, dict):
                 generated_videos = operation.get("generated_videos", [])

            if generated_videos:
                first_vid = generated_videos[0]
                
                if hasattr(first_vid, 'video'):
                    # CASE A: URI Returned
                    if hasattr(first_vid.video, 'uri') and first_vid.video.uri:
                        return self._get_signed_url(first_vid.video.uri)
                    
                    # CASE B: Raw Bytes Returned
                    if hasattr(first_vid.video, 'video_bytes') and first_vid.video.video_bytes:
                        print("💾 Received raw video bytes. Uploading to GCS...", flush=True)
                        return self._upload_bytes_to_gcs(first_vid.video.video_bytes, "video/mp4", "mp4")

                elif isinstance(first_vid, dict):
                     v = first_vid.get('video', {})
                     if v.get('uri'):
                         return self._get_signed_url(v['uri'])
                     if v.get('video_bytes'):
                         return self._upload_bytes_to_gcs(v['video_bytes'], "video/mp4", "mp4")

            # Diagnostic Dump
            print("--- ⚠️ RAW RESULT DUMP ⚠️ ---", flush=True)
            try:
                debug_data = operation.to_dict() if hasattr(operation, 'to_dict') else str(operation)
                print(json.dumps(debug_data, indent=2, default=str), flush=True)
            except:
                print(operation, flush=True)

            raise RuntimeError("Veo finished but returned no valid video data.")

        except Exception as e:
            print(f"❌ Video Gen Error: {e}")
            return "https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

    def generate_image(self, prompt: str) -> str:
        if not self.client:
            return "https://placehold.co/1200x675/EEE/31343C?text=AI+Client+Error"

        print(f"🎨 Creative Engine: Painting '{prompt}'...", flush=True)
        try:
            response = self.client.models.generate_images(
                model="imagen-3.0-generate-001",
                prompt=f"Professional educational diagram: {prompt}. Minimalist, high contrast, clear text.",
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9"
                )
            )
            
            if getattr(response, "generated_images", None):
                image_bytes = response.generated_images[0].image.image_bytes
                return self._upload_bytes_to_gcs(image_bytes, "image/png", "png")
            
            return "https://placehold.co/1200x675/EEE/31343C?text=AI+Diagram+Failed"

        except Exception as e:
            print(f"❌ Image Gen Error: {e}")
            return "https://placehold.co/1200x675/EEE/31343C?text=AI+Diagram+Error"

    def generate_audio(self, text: str) -> str:
        print("🎤 Generating Audio Speech...")
        if not text: return ""

        # --- SANITIZATION: REMOVE MARKDOWN ---
        try:
            # 1. Remove Asterisks (used for bold/italic/lists)
            clean_text = re.sub(r'\*+', '', text)
            # 2. Remove Hashes (headers) and Backticks (code)
            clean_text = re.sub(r'[#`]', '', clean_text)
            # 3. Collapse extra spaces
            clean_text = " ".join(clean_text.split())
        except Exception:
            clean_text = text.replace("*", "").replace("#", "")

        if not self.tts_client:
            print("❌ Audio Skipped: TTS Client invalid.")
            return ""

        try:
            synthesis_input = texttospeech.SynthesisInput(text=clean_text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US", 
                name="en-US-Studio-O"
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            response = self.tts_client.synthesize_speech(
                input=synthesis_input, 
                voice=voice, 
                audio_config=audio_config
            )

            return self._upload_bytes_to_gcs(response.audio_content, "audio/mpeg", "mp3")

        except Exception as e:
            print(f"❌ Audio Gen Error: {e}")
            return "https://www2.cs.uic.edu/~i101/SoundFiles/CantinaBand3.wav"
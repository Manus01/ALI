import os
import logging
import vertexai
from vertexai.generative_models import GenerativeModel
from google.api_core import exceptions
from typing import Optional

# Configure Logger
logger = logging.getLogger("ali_platform.services.llm_factory")

# Initialize Vertex AI globally using Identity (No Keys)
# Prefer GENAI_PROJECT_ID if set (Standard for this project)
project_id = os.environ.get("GENAI_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
location = os.environ.get("VERTEX_LOCATION", "us-central1")

try:
    if project_id:
        vertexai.init(project=project_id, location=location)
    else:
        # Auto-detect project on Cloud Run / GKE
        vertexai.init(location=location)
except Exception as e:
    logger.error(f"⚠️ Vertex AI Init Failed: {e}. AI features may be unavailable.")

# 🏛️ Stable Aliases (Auto-healing)
# 🏛️ Stable Aliases (Auto-healing)
MODEL_ALIASES = {
    "complex": os.getenv("VERTEX_MODEL_ALIAS_COMPLEX", "gemini-2.5-pro"),
    "fast": os.getenv("VERTEX_MODEL_ALIAS_FAST", "gemini-2.5-pro"),
    "lite": os.getenv("VERTEX_MODEL_ALIAS_LITE", "gemini-2.5-pro"),
}

def get_model(intent: str = "fast") -> GenerativeModel:
    """
    Surgically selects the best Gemini model based on task intent.
    Automatically handles version updates via stable aliases.
    """
    model_name = MODEL_ALIASES.get(intent, MODEL_ALIASES["fast"])
    
    try:
        # Initial attempt with the stable alias
        return GenerativeModel(model_name)
    except exceptions.NotFound:
        # 🛡️ Emergency Fallback: If for some reason the alias is unavailable,
        # we try the base 'pro' to ensure the app never crashes.
        logger.warning(f"⚠️ Alias {model_name} not found. Falling back to base 2.5-pro.")
        return GenerativeModel("gemini-2.5-pro")

# Helper to auto-detect complexity based on prompt length or keywords
def get_model_smart(prompt: str) -> GenerativeModel:
    if len(prompt) > 2000 or "strategy" in prompt.lower() or "blueprint" in prompt.lower():
        return get_model("complex")
    return get_model("fast")
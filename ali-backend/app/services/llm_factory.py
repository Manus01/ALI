import os
import vertexai
from vertexai.generative_models import GenerativeModel
from google.api_core import exceptions

# Initialize Vertex AI globally using Identity (No Keys)
vertexai.init(
    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("VERTEX_LOCATION", "us-central1")
)

# 🏛️ 2025 Stable Aliases (Auto-healing)
MODELS = {
    "complex": "gemini-2.5-pro",  # For PhD Blueprints, Strategies
    "fast": "gemini-2.5-flash",   # For Suggestions, Chat, UI tasks
    "lite": "gemini-2.5-flash-lite" # For ultra-fast data parsing
}

def get_model(intent: str = "fast"):
    """
    Surgically selects the best Gemini model based on task intent.
    Automatically handles version updates via stable aliases.
    """
    model_name = MODELS.get(intent, MODELS["fast"])
    
    try:
        # Initial attempt with the stable alias
        return GenerativeModel(model_name)
    except exceptions.NotFound:
        # 🛡️ Emergency Fallback: If for some reason the alias is unavailable,
        # we try the base 'flash' to ensure the app never crashes.
        print(f"⚠️ Alias {model_name} not found. Falling back to base Flash.")
        return GenerativeModel("gemini-2.5-flash")

# Helper to auto-detect complexity based on prompt length or keywords
def get_model_smart(prompt: str):
    if len(prompt) > 2000 or "strategy" in prompt.lower() or "blueprint" in prompt.lower():
        return get_model("complex")
    return get_model("fast")
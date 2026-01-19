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

# 🏛️ Stable Aliases (Auto-healing) - Use current model versions
# Updated 2026-01-07: Gemini 1.5 Pro deprecated, using Gemini 2.5 family
MODEL_ALIASES = {
    "complex": os.getenv("VERTEX_MODEL_ALIAS_COMPLEX", "gemini-2.5-pro"),
    "fast": os.getenv("VERTEX_MODEL_ALIAS_FAST", "gemini-2.5-flash"),
    "lite": os.getenv("VERTEX_MODEL_ALIAS_LITE", "gemini-2.0-flash-001"),
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
        # 🛡️ Emergency Fallback: Try Gemini 2.5 Flash (most widely available)
        logger.warning(f"⚠️ Alias {model_name} not found. Falling back to gemini-2.5-flash.")
        return GenerativeModel("gemini-2.5-flash")

# Helper to auto-detect complexity based on prompt length or keywords
def get_model_smart(prompt: str) -> GenerativeModel:
    if len(prompt) > 2000 or "strategy" in prompt.lower() or "blueprint" in prompt.lower():
        return get_model("complex")
    return get_model("fast")


def log_generation_diagnostics(response, context: str = "") -> dict:
    """
    Logs detailed generation diagnostics for troubleshooting blocked content.
    
    Args:
        response: The GenerativeModel response object
        context: Optional context string for logging (e.g., "tutorial blueprint")
    
    Returns:
        dict with diagnostic info: {finish_reason, safety_ratings, is_blocked}
    """
    diagnostics = {
        "finish_reason": None,
        "safety_ratings": [],
        "is_blocked": False,
        "block_reason": None
    }
    
    try:
        if not response or not hasattr(response, 'candidates') or not response.candidates:
            diagnostics["is_blocked"] = True
            diagnostics["block_reason"] = "No candidates returned"
            logger.warning(f"⚠️ [GENERATION_BLOCKED] {context}: No candidates in response")
            return diagnostics
        
        candidate = response.candidates[0]
        
        # Extract finish reason
        finish_reason = getattr(candidate, 'finish_reason', None)
        if finish_reason:
            if hasattr(finish_reason, 'name'):
                diagnostics["finish_reason"] = finish_reason.name
            else:
                diagnostics["finish_reason"] = str(finish_reason)
        
        # Extract safety ratings
        safety_ratings = getattr(candidate, 'safety_ratings', [])
        if safety_ratings:
            diagnostics["safety_ratings"] = [
                {
                    "category": getattr(r, 'category', 'UNKNOWN'),
                    "probability": getattr(r, 'probability', 'UNKNOWN'),
                    "blocked": getattr(r, 'blocked', False)
                }
                for r in safety_ratings
            ]
        
        # Check if generation was blocked
        blocked_reasons = ['SAFETY', 'RECITATION', 'BLOCKLIST', 'PROHIBITED_CONTENT', 'SPII']
        if diagnostics["finish_reason"] in blocked_reasons:
            diagnostics["is_blocked"] = True
            diagnostics["block_reason"] = diagnostics["finish_reason"]
            
            # Log warning with safety details
            safety_str = ", ".join([
                f"{r['category']}:{r['probability']}" 
                for r in diagnostics["safety_ratings"]
            ]) if diagnostics["safety_ratings"] else "N/A"
            
            logger.warning(
                f"🚫 [GENERATION_BLOCKED] {context}. "
                f"Finish Reason: {diagnostics['finish_reason']}, "
                f"Safety Ratings: {safety_str}"
            )
        elif diagnostics["finish_reason"] and diagnostics["finish_reason"] != 'STOP':
            # Log non-standard finish reasons as warnings
            logger.warning(
                f"⚠️ [CONTENT_ALERT] {context}. "
                f"Finish Reason: {diagnostics['finish_reason']}"
            )
    
    except Exception as e:
        logger.warning(f"⚠️ Diagnostic extraction failed: {e}")
    
    return diagnostics


def generate_with_diagnostics(model, prompt: str, context: str = "", **kwargs):
    """
    Wrapper that generates content and logs detailed diagnostics.
    
    Args:
        model: GenerativeModel instance
        prompt: The prompt string
        context: Context for logging (e.g., "curriculum blueprint for digital marketing")
        **kwargs: Additional arguments to pass to generate_content
    
    Returns:
        The response from generate_content
    
    Raises:
        ValueError: If content was blocked by safety filters
    """
    response = model.generate_content(prompt, **kwargs)
    diagnostics = log_generation_diagnostics(response, context)
    
    if diagnostics["is_blocked"]:
        raise ValueError(
            f"Content generation blocked: {diagnostics['block_reason']}. "
            f"Context: {context}"
        )
    
    return response
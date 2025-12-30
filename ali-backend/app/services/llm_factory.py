import os
import logging
import vertexai
from vertexai.generative_models import GenerativeModel

logger = logging.getLogger(__name__)

def get_model(task_type: str = 'fast'):
    """
    Factory to get a Gemini model instance using Vertex AI SDK.
    
    Args:
        task_type (str): 'fast' for low-latency tasks (Flash), 'complex' for reasoning (Pro).
    """
    try:
        project_id = os.getenv("PROJECT_ID") or os.getenv("GENAI_PROJECT_ID")
        location = os.getenv("AI_STUDIO_LOCATION", "us-central1")
        
        if not project_id:
            # Try to infer from environment or let vertexai auto-detect
            logger.info("?? LLM Factory: No PROJECT_ID env var, letting Vertex AI auto-detect.")
            vertexai.init(location=location)
        else:
            vertexai.init(project=project_id, location=location)
            
        # Determine model name based on task type
        if task_type == 'complex':
            model_name = "gemini-1.5-pro-002"
            fallback_name = "gemini-1.5-pro"
        else:
            model_name = "gemini-1.5-flash-002"
            fallback_name = "gemini-1.5-flash"
            
        logger.info(f"?? LLM Factory: Using Vertex AI (Project: {project_id}, Model: {model_name})")
        
        try:
            return GenerativeModel(model_name)
        except Exception as e:
            logger.warning(f"?? LLM Factory: Failed to load {model_name}, falling back to {fallback_name}. Error: {e}")
            return GenerativeModel(fallback_name)
         
    except Exception as e:
        logger.error(f"? LLM Factory: Vertex AI Init Failed: {e}")
        raise ValueError(f"Could not initialize Vertex AI Model: {e}")

# Backward compatibility alias if needed, but we are refactoring usages.
get_gemini_model = get_model

import os
import logging
import vertexai
from vertexai.generative_models import GenerativeModel

logger = logging.getLogger(__name__)

def get_gemini_model(model_name: str = "gemini-1.5-flash"):
    """
    Factory to get a Gemini model instance using Vertex AI SDK.
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
            
        logger.info(f"?? LLM Factory: Using Vertex AI (Project: {project_id})")
        return GenerativeModel(model_name)
        
    except Exception as e:
        logger.error(f"? LLM Factory: Vertex AI Init Failed: {e}")
        raise ValueError(f"Could not initialize Vertex AI Model: {e}")

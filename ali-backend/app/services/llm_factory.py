import os
import logging

logger = logging.getLogger(__name__)

def get_gemini_model(model_name: str = "gemini-1.5-flash"):
    """
    Factory to get a Gemini model instance.
    Prioritizes AI Studio (API Key) if available, otherwise falls back to Vertex AI (ADC).
    """
    api_key = os.getenv("GEMINI_API_KEY")

    # STRATEGY 1: AI STUDIO (API KEY)
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            logger.info(f"?? LLM Factory: Using AI Studio (Key: ...{api_key[-4:]})")
            return genai.GenerativeModel(model_name)
        except ImportError:
            logger.error("? LLM Factory: google-generativeai not installed.")
        except Exception as e:
            logger.error(f"? LLM Factory: AI Studio Init Failed: {e}")

    # STRATEGY 2: VERTEX AI (ADC / IAM)
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        
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
        
    except ImportError:
        logger.error("? LLM Factory: google-cloud-aiplatform not installed.")
    except Exception as e:
        logger.error(f"? LLM Factory: Vertex AI Init Failed: {e}")

    # FALLBACK: FAIL
    raise ValueError("Could not initialize Gemini Model. Check GEMINI_API_KEY or Vertex AI credentials.")

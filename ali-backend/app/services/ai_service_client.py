import os
import logging
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("ali_platform.services.ai_service_client")

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL")


def _fallback_generate_tutorial(user_id: str, topic: str, context: Optional[str] = None, progress_callback=None) -> Dict[str, Any]:
    from app.agents.tutorial_agent import generate_tutorial
    return generate_tutorial(user_id, topic, context=context, progress_callback=progress_callback)


def generate_tutorial(user_id: str, topic: str, context: Optional[str] = None, progress_callback=None) -> Dict[str, Any]:
    if not AI_SERVICE_URL:
        logger.warning("AI_SERVICE_URL not set. Falling back to local tutorial generation.")
        return _fallback_generate_tutorial(user_id, topic, context=context, progress_callback=progress_callback)

    payload = {"userId": user_id, "topic": topic, "context": context}
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(f"{AI_SERVICE_URL}/ai/tutorials/generate", json=payload)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"AI service generation failed: {e}. Falling back to local generation.")
        return _fallback_generate_tutorial(user_id, topic, context=context, progress_callback=progress_callback)


def scout_sources(topic: str) -> Dict[str, Any]:
    if not AI_SERVICE_URL:
        logger.warning("AI_SERVICE_URL not set. Scout not available.")
        return {"sources": []}
    with httpx.Client(timeout=30.0) as client:
        response = client.post(f"{AI_SERVICE_URL}/ai/research/scout", json={"topic": topic})
        response.raise_for_status()
        return response.json()


def deep_dive(urls: list[str]) -> Dict[str, Any]:
    if not AI_SERVICE_URL:
        logger.warning("AI_SERVICE_URL not set. Deep dive not available.")
        return {"sources": []}
    with httpx.Client(timeout=60.0) as client:
        response = client.post(f"{AI_SERVICE_URL}/ai/research/dive", json={"urls": urls})
        response.raise_for_status()
        return response.json()

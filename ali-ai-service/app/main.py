import os
import sys
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_PATH = os.path.join(BASE_DIR, "ali-backend")
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)

from app.agents.tutorial_agent import generate_tutorial, review_tutorial_quality
from app.services import research_service


app = FastAPI(title="ALI AI Service")
AI_SERVICE_TOKEN = os.getenv("AI_SERVICE_TOKEN")


def _verify_request(request: Request):
    if not AI_SERVICE_TOKEN:
        return
    token = request.headers.get("X-AI-Token")
    if token != AI_SERVICE_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


class GenerateRequest(BaseModel):
    userId: str
    topic: str
    context: str | None = None


class ScoutRequest(BaseModel):
    topic: str
    limit: int = 10


class DiveRequest(BaseModel):
    urls: list[str]


class CriticRequest(BaseModel):
    tutorial: dict
    blueprint: dict | None = None


@app.post("/ai/tutorials/generate")
def generate(req: GenerateRequest, request: Request):
    _verify_request(request)
    try:
        result = generate_tutorial(req.userId, req.topic, context=req.context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/research/scout")
def scout(req: ScoutRequest, request: Request):
    _verify_request(request)
    sources = research_service.scout_sources(req.topic, limit=req.limit)
    return {"sources": sources}


@app.post("/ai/research/dive")
def dive(req: DiveRequest, request: Request):
    _verify_request(request)
    sources = research_service.deep_dive(req.urls)
    return {"sources": sources}


@app.post("/ai/tutorials/critic")
def critic(req: CriticRequest, request: Request):
    _verify_request(request)
    report = review_tutorial_quality(req.tutorial, req.blueprint or {})
    return {"report": report}

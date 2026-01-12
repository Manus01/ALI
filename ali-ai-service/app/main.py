import os
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_PATH = os.path.join(BASE_DIR, "ali-backend")
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)

from app.agents.tutorial_agent import generate_tutorial, review_tutorial_quality
from app.services import research_service


app = FastAPI(title="ALI AI Service")


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
def generate(req: GenerateRequest):
    try:
        result = generate_tutorial(req.userId, req.topic, context=req.context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/research/scout")
def scout(req: ScoutRequest):
    sources = research_service.scout_sources(req.topic, limit=req.limit)
    return {"sources": sources}


@app.post("/ai/research/dive")
def dive(req: DiveRequest):
    sources = research_service.deep_dive(req.urls)
    return {"sources": sources}


@app.post("/ai/tutorials/critic")
def critic(req: CriticRequest):
    report = review_tutorial_quality(req.tutorial, req.blueprint or {})
    return {"report": report}

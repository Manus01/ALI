from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.core.security import verify_token
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class StrategyRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=1000)

@router.post("/generate")
async def generate_marketing_strategy(
    request: StrategyRequest, 
    user: dict = Depends(verify_token)
):
    """
    Generates a strategy using the user's REAL data from Windsor.ai.
    """
    user_id = user['uid']
    logger.info(f"🧠 Strategy Generation requested by User {user_id}")

    try:
        from app.agents.strategy_agent import StrategyAgent
        agent = StrategyAgent()
        # We pass the user_id so the agent can look up the correct API keys and fetch data
        result_json = agent.generate_strategy(
            user_prompt=request.prompt,
            user_id=user_id
        )
        
        # Parse the JSON string returned by the agent into a dict
        import json
        return json.loads(result_json)

    except Exception as e:
        logger.error(f"❌ Strategy Generation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
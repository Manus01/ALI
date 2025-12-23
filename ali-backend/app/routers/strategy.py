from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from app.core.security import verify_token
from app.agents.strategy_agent import StrategyAgent
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize the Agent
agent = StrategyAgent()

class StrategyRequest(BaseModel):
    prompt: str

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
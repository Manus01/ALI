from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import verify_token
import time

router = APIRouter()

class ExecutionRequest(BaseModel):
    tool: str
    params: dict

@router.post("/execute")
def execute_marketing_action(body: ExecutionRequest, user: dict = Depends(verify_token)):
    """
    Executes a marketing action directly on the platform API.
    """
    print(f"⚡ Executing tool '{body.tool}' for user {user['uid']}...")
    
    try:
        # Simulate API Latency
        time.sleep(1.5)
        
        if body.tool == "pause_campaign":
            # In production: Load credentials via CryptoService -> Call TikTok/FB API
            # For now, we simulate success
            camp_id = body.params.get('campaign_id', 'Unknown')
            return {
                "status": "success", 
                "message": f"Successfully paused Campaign {camp_id} on {body.params.get('platform', 'platform')}."
            }
            
        elif body.tool == "increase_budget":
            amount = body.params.get('amount_percent', '10')
            return {
                "status": "success", 
                "message": f"Budget increased by {amount}%."
            }
            
        elif body.tool == "manual":
            return {"status": "info", "message": "This task requires manual intervention."}
            
        else:
            raise HTTPException(status_code=400, detail="Unknown tool type.")

    except Exception as e:
        print(f"❌ Execution Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
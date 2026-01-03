import os
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.services.windsor_client import WindsorClient
from app.services.crypto_service import CryptoService
from app.services.llm_factory import get_model
from app.core.security import db

logger = logging.getLogger(__name__)

# --- 1. DEFINE PREDICTION MODEL ---

class PredictionResult(BaseModel):
    """The predicted outcome of a marketing strategy."""
    metric: str = Field(description="The marketing metric being predicted (e.g., 'CPC', 'Conversion Rate', 'Spend').")
    current_value: float = Field(description="The current measured value of the metric.")
    predicted_change_percentage: float = Field(description="The predicted change in the metric as a percentage (positive for increase, negative for decrease).")
    confidence_score: float = Field(description="A score from 0.0 to 1.0 indicating the agent's confidence in the prediction.")
    rationale: str = Field(description="A brief explanation of why this prediction was made based on the data and strategy.")

# --- 2. DEFINE TOOLS (PREDICTION LOGIC) ---

async def predict_cpc_change(
    current_cpc: float, 
    campaign_data: List[Dict], 
    proposed_strategy: str
) -> PredictionResult:
    """
    Analyzes historical campaign data and a proposed marketing strategy to predict 
    the percentage change in Cost Per Click (CPC).
    """
    # Prompt for the specialized Prediction LLM call
    prompt = f"""
    Analyze the following current CPC and campaign data. Based ONLY on the provided data 
    and the proposed strategy, provide a realistic prediction of the CPC change.
    
    - Current Average CPC: {current_cpc}
    - Proposed Strategy: {proposed_strategy}
    - Historical Campaign Data (Last 30 Days Summary):
    {json.dumps(campaign_data[:10], indent=2)} 

    Determine the predicted change percentage for the CPC (e.g., -10.5 for a 10.5% decrease) 
    and a confidence score (0.0 to 1.0).
    """

    try:
        from vertexai.generative_models import GenerationConfig
        
        model = get_model(intent='fast')
         
        # ASYNC FIX
        response = await model.generate_content_async(
            prompt,
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                response_schema=PredictionResult.model_json_schema(),
            )
        )
        
        result_dict = json.loads(response.text)
        return PredictionResult(**result_dict)

    except Exception as e:
        print(f"Prediction Error: {e}")
        return PredictionResult(
            metric="CPC",
            current_value=current_cpc,
            predicted_change_percentage=0.0,
            confidence_score=0.0,
            rationale="Prediction service unavailable."
        )

# --- 3. THE STRATEGY AGENT (WINDSOR INTEGRATED) ---

class StrategyAgent(BaseAgent):
    """
    An agent that fetches REAL data from Windsor.ai and generates actionable strategies.
    """
    def __init__(self, agent_name: str = "StrategyAgent"):
        super().__init__("StrategyAgent")
        self.model_instance = None 
        self.client = None
        self.tools = [predict_cpc_change]
        self.db = db
        self.crypto_service = CryptoService()
        self._ensure_client()

    def _ensure_client(self):
        if self.client: return self.client
        try:
            self.client = get_model(intent='complex')
        except Exception as e:
            logger.error(f"GenAI client init failed: {e}")
            self.client = None
        return self.client

    def _fetch_real_data(self, user_id: str) -> List[Dict]:
        """Internal helper: Fetches real ad metrics from Windsor.ai for this user."""
        try:
            doc_ref = self.db.collection("user_integrations").document(f"{user_id}_windsor_ai")
            doc = doc_ref.get()
            
            if not doc.exists or doc.to_dict().get("status") != "active":
                logger.warning(f"StrategyAgent: No Windsor.ai integration found for user {user_id}")
                return []

            encrypted_key = doc.to_dict().get("credentials")
            api_key = self.crypto_service.decrypt_credential(user_id, encrypted_key)
            
            windsor = WindsorClient(api_key=api_key)
            meta_data = windsor.fetch_metrics("meta_ads", days_lookback=30)
            return meta_data
            
        except Exception as e:
            logger.error(f"StrategyAgent Data Fetch Error: {e}")
            return []

    async def generate_strategy(self, user_prompt: str, user_id: str) -> str:
        """
        Generates a marketing strategy based on REAL Windsor.ai data.
        """
        client = self._ensure_client()
        if not client:
            return json.dumps({
                "title": "AI Unavailable",
                "summary": "GenAI client not initialized.",
                "strategy_steps": [],
                "metrics_to_watch": [],
                "prediction": None,
                "created_at": datetime.now().isoformat()
            })

        # 1. GET REAL DATA
        historical_data = self._fetch_real_data(user_id)
        
        if not historical_data:
            return json.dumps({
                "title": "Data Connection Required",
                "summary": "I cannot generate a data-driven strategy because no Ad Data is connected.",
                "strategy_steps": ["Go to the 'Integrations' page.", "Connect your Ad Accounts (Windsor.ai).", "Try again."],
                "metrics_to_watch": [],
                "prediction": None,
                "created_at": datetime.now().isoformat()
            })

        # 2. CALCULATE METRICS (Simple Aggregation)
        total_spend = sum(float(d.get('spend', 0) or 0) for d in historical_data)
        total_clicks = sum(int(d.get('clicks', 0) or 0) for d in historical_data)
        current_cpc = round(total_spend / total_clicks, 2) if total_clicks > 0 else 0.0

        # 3. PREPARE PROMPT
        user_prompt_with_data = f"""
        User Goal: {user_prompt}
        
        Current Performance:
        - Total Spend (30d): ${total_spend}
        - Avg CPC: ${current_cpc}
        
        Recent Campaign Data:
        {json.dumps(historical_data[:15], indent=2)}
        """

        # 4. AGENT EXECUTION LOOP (ASYNC)
        try:
            from vertexai.generative_models import Content, Part
            messages = [Content(role="user", parts=[Part.from_text(user_prompt_with_data)])]
            
            # ASYNC FIX
            response = await client.generate_content_async(
                 contents=messages
            )

            # B. Handle Tool Call (Simplified text return for stability)
            return response.text

        except Exception as e:
            logger.error(f"Strategy Gen Error: {e}")
            return json.dumps({"error": str(e)})
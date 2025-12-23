import os
import json
import pandas as pd
import google.generativeai as genai
from google.cloud import firestore
from app.agents.state import AgentState

# Configure the native SDK
# This bypasses litellm issues entirely
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("⚠️ GEMINI_API_KEY not found. Strategist node will fail.")

# --- NODE 1: THE ANALYST ---
def analyst_node(state: AgentState) -> dict:
    """
    The 'Data Detective'.
    Reads REAL data from Firestore and finds anomalies.
    """
    print("🕵️ Analyst Agent: Reading REAL data from Firestore...")
    user_id = state.get("user_id")
    
    # 1. Fetch from Firestore
    db = firestore.Client()
    docs = db.collection('users').document(user_id).collection('campaign_performance').stream()
    
    # Convert to list of dicts
    data = [doc.to_dict() for doc in docs]
    anomalies = []

    if not data:
        return {"anomalies": ["No data found. Please connect an integration first."]}

    # 2. Convert to DataFrame
    df = pd.DataFrame(data)

    # Normalize columns (handle different APIs)
    # TikTok: cpc, ctr | Yandex: Clicks, Cost, Impressions
    if "Cost" in df.columns and "Clicks" in df.columns:
        # Calculate calculated metrics for Yandex
        df["cpc"] = pd.to_numeric(df["Cost"]) / pd.to_numeric(df["Clicks"]).replace(0, 1)
        df["ctr"] = (pd.to_numeric(df["Clicks"]) / pd.to_numeric(df["Impressions"]).replace(0, 1)) * 100
        df["spend"] = pd.to_numeric(df["Cost"])
        df["conversion"] = 0 # Yandex report didn't have conversions in our simple query

    # Rule 1: High CPC Check (> $3.00)
    if "cpc" in df.columns:
        df["cpc"] = pd.to_numeric(df["cpc"], errors='coerce')
        high_cpc = df[df["cpc"] > 3.0] 
        for _, row in high_cpc.iterrows():
            cid = row.get('campaign_id') or row.get('CampaignName') or 'Unknown'
            val = row['cpc']
            anomalies.append(f"High CPC (${val:.2f}) detected in campaign {cid}.")

    # Rule 2: Low CTR Check (< 0.5%)
    if "ctr" in df.columns:
        df["ctr"] = pd.to_numeric(df["ctr"], errors='coerce')
        low_ctr = df[df["ctr"] < 0.5] 
        for _, row in low_ctr.iterrows():
            cid = row.get('campaign_id') or row.get('CampaignName') or 'Unknown'
            val = row['ctr']
            anomalies.append(f"Low CTR ({val:.2f}%) detected in campaign {cid}. Ad creative may be fatigued.")

    # Rule 3: Wasted Spend (Spend > $50 with 0 Conversions)
    if "spend" in df.columns:
        df["spend"] = pd.to_numeric(df["spend"], errors='coerce')
        # Check for conversion column existence
        if "conversion" in df.columns:
            df["conversion"] = pd.to_numeric(df["conversion"], errors='coerce')
            wasted = df[(df["spend"] > 50) & (df["conversion"] == 0)]
            for _, row in wasted.iterrows():
                cid = row.get('campaign_id') or row.get('CampaignName') or 'Unknown'
                val = row['spend']
                anomalies.append(f"Wasted Spend: Campaign {cid} spent ${val} with 0 conversions.")

    if not anomalies:
        anomalies.append("Performance is stable. No major anomalies detected.")

    print(f"✅ Analyst found {len(anomalies)} items.")
    return {"anomalies": anomalies}


# --- NODE 2: THE STRATEGIST ---
def strategist_node(state: AgentState) -> dict:
    """
    The 'Marketing Genius'.
    Generates EXECUTABLE strategies with tool parameters.
    """
    print("🧠 Strategist Agent: Generating executable plan...")
    
    anomalies = state.get("anomalies", [])
    issues_text = "\n".join(f"- {issue}" for issue in anomalies)
    
    # 1. Prompt for Structured Output
    prompt = f"""
    You are a Senior Marketing Strategist.
    Here are the problems identified in the user's campaigns:
    {issues_text}

    Propose a concrete Action Plan.
    CRITICAL: For each action, determine if it can be automated using these tools:
    - 'pause_campaign' (Requires 'campaign_id')
    - 'increase_budget' (Requires 'campaign_id', 'amount_percent')
    
    RETURN JSON ONLY:
    {{
      "title": "Strategy Name",
      "rationale": "Why we are doing this.",
      "actions": [
        {{
            "description": "Pause the high CPA campaign",
            "tool": "pause_campaign",
            "params": {{ "campaign_id": "12345", "platform": "tiktok" }} 
        }},
        {{
            "description": "Review creative assets manually",
            "tool": "manual",
            "params": {{}} 
        }}
      ]
    }}
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        content = response.text.replace("```json", "").replace("```", "").strip()
        plan = json.loads(content)

    except Exception as e:
        print(f"⚠️ AI Error: {e}")
        plan = {
            "title": "Manual Strategy (Fallback)",
            "rationale": "AI service temporarily unavailable.",
            "actions": [
                {"description": "Check campaign settings manually", "tool": "manual", "params": {}}
            ]
        }

    print("✅ Strategy Generated.")
    return {"strategy_plan": plan}
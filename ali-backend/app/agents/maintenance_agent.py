import os
import json
from dotenv import load_dotenv

load_dotenv()

def review_tutorial_relevance(tutorial_data: dict, current_metrics: list, user_profile: dict) -> dict:
    """
    Analyzes if a tutorial is still valid based on new data using 4C/ID principles.
    Returns: { "is_outdated": bool, "reason": str }
    """
    print(f"🕵️ Gardener: Reviewing '{tutorial_data.get('title')}'...")
    
    # 1. Summarize Current Context
    metrics_summary = ""
    for m in current_metrics[:5]: 
        metrics_summary += f"- {m.get('date', 'Unknown')}: CPC={m.get('cpc', 0)}, CTR={m.get('ctr', 0)}\n"

    learning_style = user_profile.get("learning_style", "VISUAL")
    
    # 2. Prompt for Evaluation
    prompt = f"""
    Act as a Senior Instructional Designer (4C/ID expert).
    Review this existing tutorial against the user's CURRENT situation.
    
    EXISTING TUTORIAL TOPIC: "{tutorial_data.get('title')}"
    CREATED: {tutorial_data.get('timestamp')}
    
    USER'S CURRENT DATA (Real-Time):
    {metrics_summary}
    
    EVALUATION CRITERIA:
    1. Authenticity: Is the 'Learning Task' (Scenario) still relevant? 
       (e.g., if the tutorial fixes High CPC, but CPC is now low ($0.50), it is no longer authentic).
    2. Data Accuracy: Does the tutorial reference outdated metrics?
    
    OUTPUT JSON ONLY:
    {{
        "is_outdated": true, 
        "reason": "CPC has dropped to $0.50, so this 'High CPC' lesson is no longer relevant.",
        "recommended_action": "archive"
    }}
    (Or "is_outdated": false if it's still good).
    """
    
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
 
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"❌ Review Error: {e}")
        return {"is_outdated": False, "reason": "Error during review"}
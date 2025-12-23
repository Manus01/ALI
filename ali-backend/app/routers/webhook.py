from fastapi import APIRouter, Request
from google.cloud import firestore
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Map Airbyte source definition IDs to user-friendly platform names
# (You will update these IDs later with real ones from your logs)
SOURCE_PLATFORM_MAP = {
    "linkedin": "LinkedIn Ads",
    "meta": "Facebook Marketing",
    "google": "Google Ads",
    "tiktok": "TikTok Marketing",
}

@router.post("/airbyte/webhook")
async def handle_airbyte_webhook(request: Request):
    """
    Receives Airbyte job status updates.
    Accepts raw Request object to avoid 422 Validation Errors.
    """
    try:
        # 1. Parse the Raw JSON
        payload = await request.json()
        
        # --- DEBUG LOG: SEE EXACTLY WHAT AIRBYTE SENT ---
        print("\n" + "="*50)
        print(f"📦 RECEIVED WEBHOOK PAYLOAD:")
        print(payload)
        print("="*50 + "\n")
        # ------------------------------------------------

        # 2. Extract Key Fields (Safely)
        # We use .get() so it never crashes if a field is missing
        job_status = payload.get("status") or payload.get("job_status")
        connection_id = payload.get("connectionId") or payload.get("connection_id")
        
        # 3. Only process failures
        if job_status != "failed":
            return {"message": f"Ignored status: {job_status}"}

        # 4. Find the User (Mock Logic for MVP)
        # Since we can't easily map ConnectionID -> User without a DB lookup,
        # We will log the alert for now.
        failure_reason = payload.get("failureReason", {}).get("externalMessage", "Unknown Error")
        
        print(f"🚨 ALERT: Connection {connection_id} FAILED!")
        print(f"⚠️ Reason: {failure_reason}")

        # In a real production app, you would query Firestore here:
        # db = firestore.Client()
        # Find user where 'linkedin_connection_id' == connection_id...
        
        return {"status": "processed", "alert": "logged"}

    except Exception as e:
        print(f"❌ Webhook Error: {e}")
        # Return 200 OK anyway so Airbyte stops retrying
        return {"status": "error", "detail": str(e)}
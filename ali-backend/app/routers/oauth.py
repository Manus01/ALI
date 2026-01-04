from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from google.cloud import firestore
from app.core.security import verify_token
from app.services.airbyte_client import AirbyteClient
import json

import logging
router = APIRouter()
logger = logging.getLogger(__name__)

# Defines the structure of the data coming from the frontend
class ConnectRequest(BaseModel):
    details: dict 

# --- CONFIGURATION MAPPER ---
# Maps frontend fields to the specific JSON structure Airbyte requires
def map_to_airbyte_config(platform, details):
    if platform == 'linkedin':
        return {
            "start_date": "1970-01-01T00:00:00Z",
            "credentials": {
                "auth_method": "o_auth2.0",
                "client_id": details.get("client_id"),
                "client_secret": details.get("client_secret"),
                "refresh_token": details.get("refresh_token")
            },
            # Airbyte expects a list of account IDs, or empty to fetch all
            "account_ids": [int(details.get("ad_account_id"))] if details.get("ad_account_id") else []
        }
    elif platform == 'meta':
        return {
            "start_date": "1970-01-01T00:00:00Z",
            "access_token": details.get("access_token"),
            "account_id": details.get("ad_account_id"),
            "include_deleted": False,
            "fetch_thumbnail_images": False
        }
    elif platform == 'google':
        return {
            "credentials": {
                "developer_token": details.get("developer_token"),
                "client_id": details.get("client_id"),
                "client_secret": details.get("client_secret"),
                "refresh_token": details.get("refresh_token")
            },
            "customer_id": details.get("customer_id"),
            "start_date": "1970-01-01"
        }
    return {}

@router.post("/connect/{platform}")
def connect_platform(
    platform: str, 
    body: ConnectRequest, 
    background_tasks: BackgroundTasks, 
    user: dict = Depends(verify_token)
):
    try:
        logger.info(f"🔌 Connecting {platform} to Airbyte for user {user['uid']}...")
        
        # 1. Initialize Airbyte Client
        ab_client = AirbyteClient()
        if not ab_client.workspace_id:
            raise HTTPException(status_code=503, detail="Airbyte Service Unavailable")

        # 2. Find the Source Definition ID
        # These names must match what is in your Airbyte UI
        source_name_map = {
            "linkedin": "LinkedIn Ads",
            "meta": "Facebook Marketing",
            "google": "Google Ads"
        }
        
        def_id = ab_client.get_definition_id(source_name_map.get(platform, ""))
        if not def_id:
            raise HTTPException(status_code=400, detail=f"Airbyte connector for {platform} not found. Please install it in Airbyte UI.")

        # 3. Create the Source in Airbyte
        config = map_to_airbyte_config(platform, body.details)
        source_name = f"User-{user['uid']}-{platform.upper()}"
        
        # This call will FAIL if the credentials are invalid (Airbyte checks them!)
        source_response = ab_client.create_source(source_name, def_id, config)
        source_id = source_response.get("sourceId")

        # 4. Save Status to Firestore
        db = firestore.Client()
        db.collection("user_integrations").document(user['uid']).set({
            f"{platform}_status": "active",
            f"{platform}_airbyte_source_id": source_id,
            f"{platform}_last_sync": firestore.SERVER_TIMESTAMP
        }, merge=True)

        return {"status": "connected", "platform": platform, "airbyte_source_id": source_id}

    except ValueError as ve:
        # Airbyte rejected the config (e.g. bad password)
        logger.error(f"❌ Airbyte Config Error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"❌ Internal Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/integrations")
def get_integrations_status(user: dict = Depends(verify_token)):
    try:
        db = firestore.Client()
        doc = db.collection("user_integrations").document(user['uid']).get()
        if not doc.exists: return {}
        data = doc.to_dict()
        status_map = {}
        for key, val in data.items():
            if key.endswith("_status"):
                clean_name = key.replace("_status", "")
                status_map[clean_name] = val
        return status_map
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
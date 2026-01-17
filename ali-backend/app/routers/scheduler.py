"""
Scheduler Router: Internal endpoints for Cloud Scheduler jobs.
These endpoints are called by GCP Cloud Scheduler and verified via OIDC tokens.
"""
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# Expected audience for OIDC token verification
# This should match your Cloud Run service URL
# Fallback to the known production URL if env var is missing
FALLBACK_AUDIENCE = "https://ali-backend-ibayai5n2q-uc.a.run.app"
EXPECTED_AUDIENCE = os.getenv("CLOUD_RUN_SERVICE_URL", FALLBACK_AUDIENCE)

if not EXPECTED_AUDIENCE:
    logger.warning("⚠️ No CLOUD_RUN_SERVICE_URL set and no fallback used. Scheduler verification may fail.")
else:
    logger.info(f"✅ Scheduler configured with EXPECTED_AUDIENCE: {EXPECTED_AUDIENCE}")

def verify_scheduler_token(authorization: Optional[str] = Header(None)) -> bool:
    """
    Verifies the OIDC token from Cloud Scheduler.
    In production, this validates the JWT token from Google.
    For development, we allow bypassing with a secret header.
    """
    # Development bypass
    dev_secret = os.getenv("SCHEDULER_DEV_SECRET")
    if dev_secret and authorization == f"Bearer {dev_secret}":
        logger.info("🔧 Scheduler: Dev token accepted")
        return True
    
    # Production: Verify OIDC token
    if not authorization or not authorization.startswith("Bearer "):
        return False
    
    token = authorization.replace("Bearer ", "")
    
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests
        
        # Verify the token
        claims = id_token.verify_oauth2_token(
            token, 
            requests.Request(),
            audience=EXPECTED_AUDIENCE
        )
        
        # Check if it's from Cloud Scheduler
        if claims.get("email", "").endswith("gserviceaccount.com"):
            logger.info(f"✅ Scheduler: Token verified for {claims.get('email')}")
            return True
        
        return False
        
    except Exception as e:
        logger.warning(f"⚠️ Scheduler token verification failed: {e}")
        return False


@router.post("/scheduler/watchdog")
async def scheduled_watchdog(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Endpoint called by Cloud Scheduler to run the Troubleshooting Agent.
    Runs every hour (configured in Cloud Scheduler).
    
    Cloud Scheduler Config:
    - Frequency: 0 * * * * (every hour)
    - Target: HTTP
    - URL: https://YOUR-CLOUD-RUN-URL/internal/scheduler/watchdog
    - HTTP method: POST
    - Auth header: Add OIDC token
    - Service account: Cloud Scheduler service account with invoker permissions
    """
    # Verify caller is Cloud Scheduler
    if not verify_scheduler_token(authorization):
        logger.warning("🚫 Unauthorized scheduler call attempt")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    logger.info("🕐 Scheduled Watchdog: Starting system health scan...")
    
    try:
        from app.agents.troubleshooting_agent import TroubleshootingAgent
        
        agent = TroubleshootingAgent()
        result = agent.run_troubleshooter()
        
        logger.info(f"🐕 Scheduled Watchdog Complete: {result}")
        return {
            "status": "success",
            "triggered_by": "cloud_scheduler",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"❌ Scheduled Watchdog Error: {e}")
        # Return 200 to prevent Cloud Scheduler from retrying
        # The error is logged and will be caught by the next run
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/scheduler/health")
async def scheduler_health():
    """
    Health check endpoint for Cloud Scheduler monitoring.
    Returns basic health status without authentication.
    """
    return {"status": "healthy", "service": "watchdog_scheduler"}


@router.post("/scheduler/brand-monitoring-scan")
async def scheduled_brand_monitoring_scan(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Endpoint called by Cloud Scheduler to run hourly brand monitoring scan.
    Scans all users for new mentions, detects opportunities, and logs to BigQuery.
    
    Cloud Scheduler Config:
    - Frequency: 0 * * * * (every hour)
    - Target: HTTP
    - URL: https://YOUR-CLOUD-RUN-URL/internal/scheduler/brand-monitoring-scan
    - HTTP method: POST
    - Auth header: Add OIDC token
    - Service account: Cloud Scheduler service account with invoker permissions
    """
    # Verify caller is Cloud Scheduler
    if not verify_scheduler_token(authorization):
        logger.warning("🚫 Unauthorized brand monitoring scan attempt")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    logger.info("🔍 Scheduled Brand Monitoring: Starting hourly scan...")
    
    try:
        from app.services.brand_monitoring_scanner import get_scanner
        
        scanner = get_scanner()
        result = await scanner.run_hourly_scan()
        
        logger.info(f"✅ Scheduled Brand Monitoring Complete: {result.get('users_scanned', 0)} users scanned")
        return {
            "status": "success",
            "triggered_by": "cloud_scheduler",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"❌ Scheduled Brand Monitoring Error: {e}")
        # Return 200 to prevent Cloud Scheduler from retrying
        return {
            "status": "error",
            "error": str(e)
        }


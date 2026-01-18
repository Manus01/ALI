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
    Endpoint called by Cloud Scheduler to run adaptive brand monitoring scans.
    
    Behavior:
    1. Query all scan_policies where next_scan_at <= now
    2. For each due policy, calculate threat score and schedule
    3. Execute scan with idempotency (skip duplicates in same hour bucket)
    4. Log "why scanning now" metadata to BigQuery
    5. Apply backoff on consecutive failures
    
    Cloud Scheduler Config:
    - Frequency: */5 * * * * (every 5 minutes for adaptive responsiveness)
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
    
    logger.info("🔍 Adaptive Scanner: Checking for due scans...")
    
    try:
        result = await run_adaptive_scans()
        
        logger.info(
            f"✅ Adaptive Scanner Complete: "
            f"{result['scanned']} scanned, {result['skipped']} skipped (duplicate/pending)"
        )
        return {
            "status": "success",
            "triggered_by": "cloud_scheduler_adaptive",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"❌ Adaptive Scanner Error: {e}")
        # Return 200 to prevent Cloud Scheduler from retrying
        return {
            "status": "error",
            "error": str(e)
        }


async def run_adaptive_scans() -> dict:
    """
    Run adaptive scans for all brands that are due based on their policies.
    
    Returns:
        dict with scanned, skipped, and failed counts
    """
    from datetime import datetime
    from app.services.adaptive_scan_service import get_adaptive_scan_service, ScanPolicy
    from app.core.security import db
    
    service = get_adaptive_scan_service()
    now = datetime.utcnow()
    
    scanned = 0
    skipped = 0
    failed = 0
    
    try:
        # Query policies where next_scan_at <= now OR next_scan_at is null (never scheduled)
        policies_ref = db.collection("scan_policies")
        
        # Get all policies and filter in memory (Firestore doesn't support OR on different fields)
        all_policies = policies_ref.stream()
        
        for doc in all_policies:
            policy_data = doc.to_dict()
            brand_id = policy_data.get("brand_id")
            user_id = policy_data.get("user_id")
            next_scan_at_str = policy_data.get("next_scan_at")
            
            if not brand_id or not user_id:
                continue
            
            # Check if scan is due
            is_due = False
            if next_scan_at_str is None:
                # Never scheduled - scan now
                is_due = True
            else:
                try:
                    next_scan_at = datetime.fromisoformat(next_scan_at_str.replace('Z', '+00:00'))
                    # Remove timezone info for comparison (both are UTC)
                    if next_scan_at.tzinfo:
                        next_scan_at = next_scan_at.replace(tzinfo=None)
                    is_due = next_scan_at <= now
                except (ValueError, AttributeError):
                    # Invalid date format - scan now
                    is_due = True
            
            if not is_due:
                continue
            
            # Check for pending jobs (idempotency)
            pending_count = await service.get_pending_jobs_count(brand_id)
            if pending_count > 0:
                logger.debug(f"⏭️ Skipping {brand_id}: {pending_count} pending jobs")
                skipped += 1
                continue
            
            # Execute adaptive scan
            try:
                policy = ScanPolicy.from_dict(policy_data)
                
                # Calculate current threat and schedule
                assessment = await service.threat_engine.calculate_threat_score(
                    brand_id, user_id, policy
                )
                
                # Schedule and execute job
                job = await service.schedule_next_scan(brand_id, user_id, assessment, policy)
                await service.execute_scan(job)
                
                logger.info(
                    f"🎯 Scanned {brand_id}: threat={assessment.score} ({assessment.label.value}), "
                    f"next in {assessment.interval_ms // 60000}min"
                )
                scanned += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to scan {brand_id}: {e}")
                failed += 1
                
                # Record failure for backoff
                try:
                    db.collection("scan_policies").document(brand_id).update({
                        "last_failure_at": now.isoformat(),
                        "consecutive_failures": policy_data.get("consecutive_failures", 0) + 1
                    })
                except Exception:
                    pass
    
    except Exception as e:
        logger.error(f"❌ Error querying policies: {e}")
        raise
    
    return {
        "scanned": scanned,
        "skipped": skipped,
        "failed": failed,
        "timestamp": now.isoformat()
    }

#!/usr/bin/env python3
"""
SMOKE TEST: Tutorial Generation Pipeline
=========================================

Purpose: Verify the entire tutorial generation chain is working after recent Firestore Index fix.

This test:
1. Cleans stuck "PROCESSING" tasks older than 1 hour → Marks them FAILED
2. Injects a test Tutorial Request (topic: "The History of Espresso")  
3. Triggers generation directly via process_tutorial_job
4. Monitors for critical errors:
   - 400 Index Error: Missing Firestore composite index
   - 429 ResourceExhausted: Gemini API quota exceeded
5. Verifies final tutorial document exists with modules

Result: PASS (if tutorial exists) or FAIL (with error signature)

Usage:
    cd ali-backend
    python -m scripts.smoke_test_tutorial_pipeline
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("smoke_test")

# Test constants
SMOKE_TEST_TOPIC = "The History of Espresso"
SMOKE_TEST_USER_ID = "smoke_test_user"
STUCK_THRESHOLD_HOURS = 1

# Result tracking
test_result = {
    "status": None,  # "PASS" or "FAIL"
    "error_signature": None,
    "details": {}
}


def log_banner(msg: str):
    """Print a visually distinct banner for test phases."""
    logger.info("=" * 60)
    logger.info(f"🧪 {msg}")
    logger.info("=" * 60)


def init_firebase():
    """Initialize Firebase Admin SDK."""
    try:
        from app.core.security import db
        if db is None:
            raise RuntimeError("Firestore 'db' is None - check Firebase initialization")
        logger.info("✅ Firebase initialized successfully")
        return db
    except Exception as e:
        logger.critical(f"❌ Firebase init failed: {e}")
        test_result["status"] = "FAIL"
        test_result["error_signature"] = "FIREBASE_INIT_FAILURE"
        test_result["details"]["error"] = str(e)
        return None


def clean_stuck_processing_tasks(db) -> int:
    """
    Phase 1: Clean State
    Find tutorial_requests with status="PROCESSING" older than 1 hour.
    Mark them as "FAILED" to prevent queue clogging.
    
    Returns: Number of cleaned up tasks
    """
    log_banner("PHASE 1: Cleaning Stuck PROCESSING Tasks")
    
    try:
        from google.cloud import firestore
        from google.cloud.firestore_v1.base_query import FieldFilter
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=STUCK_THRESHOLD_HOURS)
        cleaned_count = 0
        
        # Query for PROCESSING tasks
        # Note: This may require a composite index on (status, updatedAt)
        query = db.collection("tutorial_requests").where(
            filter=FieldFilter("status", "==", "PROCESSING")
        )
        
        for doc in query.stream():
            data = doc.to_dict()
            # Check if task is older than threshold
            updated_at = data.get("updatedAt") or data.get("createdAt")
            
            if updated_at:
                # Handle Firestore timestamp
                if hasattr(updated_at, 'timestamp'):
                    task_time = datetime.fromtimestamp(updated_at.timestamp(), tz=timezone.utc)
                else:
                    task_time = updated_at
                
                if task_time < cutoff_time:
                    # Mark as FAILED
                    doc.reference.update({
                        "status": "FAILED",
                        "failedAt": firestore.SERVER_TIMESTAMP,
                        "failureReason": f"Auto-cleaned by smoke test: stuck > {STUCK_THRESHOLD_HOURS}h"
                    })
                    logger.warning(f"⚠️ Cleaned stuck task: {doc.id} (last updated: {task_time})")
                    cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"🧹 Cleaned {cleaned_count} stuck PROCESSING tasks")
        else:
            logger.info("✅ No stuck PROCESSING tasks found")
        
        test_result["details"]["stuck_tasks_cleaned"] = cleaned_count
        return cleaned_count
        
    except Exception as e:
        error_str = str(e)
        # Check for index error
        if "400" in error_str and "index" in error_str.lower():
            logger.error(f"❌ Index Error during cleanup query: {e}")
            test_result["status"] = "FAIL"
            test_result["error_signature"] = "400_INDEX_MISSING"
            test_result["details"]["phase"] = "cleanup"
            test_result["details"]["error"] = error_str
            return -1
        else:
            logger.warning(f"⚠️ Cleanup query failed (non-fatal): {e}")
            return 0


def ensure_test_user_exists(db) -> bool:
    """
    Phase 1.5: Ensure Test User Exists
    Create a minimal user document if it doesn't exist.
    The generate_tutorial function requires user.to_dict()["profile"] to exist.
    
    Returns: True if user exists/created, False on failure
    """
    log_banner("PHASE 1.5: Ensuring Test User Document Exists")
    
    try:
        from google.cloud import firestore
        
        user_ref = db.collection("users").document(SMOKE_TEST_USER_ID)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            logger.info(f"OK Test user '{SMOKE_TEST_USER_ID}' already exists")
            return True
        
        # Create minimal user document
        user_data = {
            "email": "smoke_test@example.com",
            "name": "Smoke Test User",
            "profile": {
                "marketing_knowledge": "INTERMEDIATE",
                "learning_style": "VISUAL",
                "industry": "Technology",
                "description": "Test user for smoke testing the tutorial pipeline"
            },
            "is_admin": False,
            "isTest": True,  # Mark as test for easy cleanup
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        
        user_ref.set(user_data)
        logger.info(f"OK Created test user document: {SMOKE_TEST_USER_ID}")
        test_result["details"]["test_user_created"] = True
        return True
        
    except Exception as e:
        logger.error(f"FAIL Failed to create test user: {e}")
        test_result["status"] = "FAIL"
        test_result["error_signature"] = "TEST_USER_CREATION_FAILED"
        test_result["details"]["error"] = str(e)
        return False


def inject_test_request(db) -> Optional[str]:
    """
    Phase 2: Inject Test Request
    Create a dummy tutorial request with status="APPROVED" (skipping admin queue).
    
    Returns: Request ID or None on failure
    """
    log_banner("PHASE 2: Injecting Test Request")
    
    try:
        from google.cloud import firestore
        
        # Generate unique request ID for this test run
        test_run_id = f"smoke_test_{int(time.time())}"
        
        request_data = {
            "topic": SMOKE_TEST_TOPIC,
            "userId": SMOKE_TEST_USER_ID,
            "status": "APPROVED",  # Skip admin queue for testing
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "context": "Automated smoke test - verify tutorial generation pipeline",
            "adminDecision": {
                "action": "approved",
                "approvedBy": "smoke_test_automation",
                "approvedAt": firestore.SERVER_TIMESTAMP
            },
            "isTest": True  # Mark as test for easy cleanup
        }
        
        doc_ref = db.collection("tutorial_requests").document(test_run_id)
        doc_ref.set(request_data)
        
        logger.info(f"OK Test request created: {test_run_id}")
        logger.info(f"   Topic: {SMOKE_TEST_TOPIC}")
        logger.info(f"   User: {SMOKE_TEST_USER_ID}")
        
        test_result["details"]["request_id"] = test_run_id
        return test_run_id
        
    except Exception as e:
        logger.error(f"FAIL Failed to inject test request: {e}")
        test_result["status"] = "FAIL"
        test_result["error_signature"] = "REQUEST_INJECTION_FAILED"
        test_result["details"]["error"] = str(e)
        return None


def trigger_generation(db, request_id: str) -> Optional[str]:
    """
    Phase 3: Trigger Generation
    Directly invoke the tutorial generation pipeline.
    
    Returns: Tutorial ID on success, None on failure
    """
    log_banner("PHASE 3: Triggering Tutorial Generation")
    
    try:
        from google.cloud import firestore
        
        # Update request status to GENERATING
        request_ref = db.collection("tutorial_requests").document(request_id)
        request_ref.update({"status": "GENERATING"})
        logger.info("📤 Request status updated to GENERATING")
        
        # Create a job document (mirrors admin.py behavior)
        job_ref = db.collection("jobs").document()
        job_id = job_ref.id
        
        job_ref.set({
            "id": job_id,
            "user_id": SMOKE_TEST_USER_ID,
            "type": "tutorial_generation",
            "topic": SMOKE_TEST_TOPIC,
            "status": "processing",
            "request_id": request_id,
            "created_at": firestore.SERVER_TIMESTAMP,
            "triggered_by": "smoke_test_automation"
        })
        logger.info(f"📋 Job created: {job_id}")
        
        # Create notification placeholder
        notification_ref = db.collection("users").document(SMOKE_TEST_USER_ID).collection("notifications").document(job_id)
        notification_ref.set({
            "user_id": SMOKE_TEST_USER_ID,
            "type": "info",
            "status": "processing",
            "title": "Smoke Test Generation",
            "message": f"Generating tutorial on '{SMOKE_TEST_TOPIC}'...",
            "read": False,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        
        # --- TRIGGER THE ACTUAL GENERATION ---
        logger.info("🚀 Invoking generate_tutorial()...")
        logger.info("   ⏳ This may take 60-120 seconds...")
        
        start_time = time.time()
        
        try:
            # Import and call the AI generation
            from app.services.ai_service_client import generate_tutorial
            
            def progress_callback(msg):
                logger.info(f"   📊 Progress: {msg}")
            
            tutorial_data = generate_tutorial(
                user_id=SMOKE_TEST_USER_ID,
                topic=SMOKE_TEST_TOPIC,
                progress_callback=progress_callback,
                notification_id=notification_ref.id
            )
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Generation completed in {elapsed:.1f}s")
            
            tutorial_id = tutorial_data.get("id")
            if tutorial_id:
                logger.info(f"📙 Tutorial ID: {tutorial_id}")
                
                # Update request to COMPLETED
                request_ref.update({
                    "status": "COMPLETED",
                    "tutorialId": tutorial_id,
                    "completedAt": firestore.SERVER_TIMESTAMP
                })
                
                # Update job
                job_ref.update({
                    "status": "completed",
                    "result_id": tutorial_id,
                    "completed_at": firestore.SERVER_TIMESTAMP
                })
                
                test_result["details"]["tutorial_id"] = tutorial_id
                test_result["details"]["generation_time_seconds"] = round(elapsed, 1)
                return tutorial_id
            else:
                logger.error("❌ Tutorial data returned but missing 'id'")
                test_result["status"] = "FAIL"
                test_result["error_signature"] = "TUTORIAL_ID_MISSING"
                test_result["details"]["tutorial_data_keys"] = list(tutorial_data.keys()) if tutorial_data else []
                return None
                
        except Exception as gen_error:
            elapsed = time.time() - start_time
            error_str = str(gen_error)
            error_traceback = traceback.format_exc()
            
            logger.error(f"❌ Generation failed after {elapsed:.1f}s")
            logger.error(f"   Error: {error_str}")
            
            # Classify the error
            if "429" in error_str or "ResourceExhausted" in error_str or "quota" in error_str.lower():
                test_result["status"] = "FAIL"
                test_result["error_signature"] = "429_RESOURCE_EXHAUSTED"
                logger.error("🚨 CRITICAL: Gemini API quota exhausted!")
                
            elif "400" in error_str and "index" in error_str.lower():
                test_result["status"] = "FAIL"
                test_result["error_signature"] = "400_INDEX_MISSING"
                logger.error("🚨 CRITICAL: Missing Firestore composite index!")
                
            elif "403" in error_str:
                test_result["status"] = "FAIL"
                test_result["error_signature"] = "403_PERMISSION_DENIED"
                logger.error("🚨 CRITICAL: Permission denied - check service account!")
                
            elif "500" in error_str or "internal" in error_str.lower():
                test_result["status"] = "FAIL"
                test_result["error_signature"] = "500_INTERNAL_ERROR"
                
            else:
                test_result["status"] = "FAIL"
                test_result["error_signature"] = "GENERATION_ERROR"
            
            test_result["details"]["error"] = error_str
            test_result["details"]["traceback"] = error_traceback
            test_result["details"]["elapsed_seconds"] = round(elapsed, 1)
            
            # Update request to FAILED
            request_ref.update({
                "status": "FAILED",
                "failedAt": firestore.SERVER_TIMESTAMP,
                "failureReason": error_str[:500]
            })
            
            # Update job
            job_ref.update({
                "status": "failed",
                "error": error_str[:500]
            })
            
            return None
            
    except Exception as e:
        logger.error(f"❌ Phase 3 setup failed: {e}")
        test_result["status"] = "FAIL"
        test_result["error_signature"] = "GENERATION_SETUP_FAILED"
        test_result["details"]["error"] = str(e)
        return None


def verify_tutorial_content(db, tutorial_id: str) -> bool:
    """
    Phase 4: Verify Tutorial Content
    Check that the tutorial document exists and has expected structure.
    
    Returns: True if valid, False otherwise
    """
    log_banner("PHASE 4: Verifying Tutorial Content")
    
    try:
        # Check global tutorials collection
        tutorial_doc = db.collection("tutorials").document(tutorial_id).get()
        
        if not tutorial_doc.exists:
            logger.error(f"❌ Tutorial {tutorial_id} not found in 'tutorials' collection")
            test_result["status"] = "FAIL"
            test_result["error_signature"] = "TUTORIAL_NOT_FOUND"
            return False
        
        data = tutorial_doc.to_dict()
        logger.info(f"✅ Tutorial document exists")
        
        # Verify expected fields
        expected_fields = ["title", "description", "content"]
        missing_fields = [f for f in expected_fields if f not in data]
        
        if missing_fields:
            logger.warning(f"⚠️ Missing fields: {missing_fields}")
        
        # Check for content/modules
        content = data.get("content", [])
        sections = data.get("sections", [])
        modules = content if content else sections
        
        if modules and len(modules) > 0:
            logger.info(f"✅ Tutorial has {len(modules)} sections/modules")
            
            # Sample one section to verify structure
            first_section = modules[0]
            logger.info(f"   📖 First section: {first_section.get('title', 'Untitled')}")
            
            # Check for content blocks
            blocks = first_section.get("blocks", [])
            if blocks:
                logger.info(f"   📦 First section has {len(blocks)} content blocks")
            
            test_result["details"]["section_count"] = len(modules)
            test_result["details"]["has_content_blocks"] = len(blocks) > 0
        else:
            logger.warning("⚠️ Tutorial has no sections/modules")
            test_result["details"]["section_count"] = 0
        
        # Check user's private copy
        private_doc = db.collection("users").document(SMOKE_TEST_USER_ID).collection("tutorials").document(tutorial_id).get()
        if private_doc.exists:
            logger.info("✅ User's private copy exists")
            test_result["details"]["private_copy_exists"] = True
        else:
            logger.warning("⚠️ User's private copy not found")
            test_result["details"]["private_copy_exists"] = False
        
        # Overall validation
        is_valid = len(modules) > 0
        if is_valid:
            logger.info("✅ Tutorial structure is valid")
            test_result["status"] = "PASS"
        else:
            logger.error("❌ Tutorial structure is invalid (no modules)")
            test_result["status"] = "FAIL"
            test_result["error_signature"] = "EMPTY_TUTORIAL"
        
        return is_valid
        
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Verification failed: {e}")
        
        # Check for index error during read
        if "400" in error_str and "index" in error_str.lower():
            test_result["status"] = "FAIL"
            test_result["error_signature"] = "400_INDEX_MISSING"
        else:
            test_result["status"] = "FAIL" 
            test_result["error_signature"] = "VERIFICATION_ERROR"
        
        test_result["details"]["error"] = error_str
        return False


def cleanup_test_data(db, request_id: str, tutorial_id: Optional[str]):
    """
    Optional cleanup of test data.
    By default, we keep the data for debugging.
    """
    logger.info("🧹 Test data preserved for debugging:")
    logger.info(f"   - Request: tutorial_requests/{request_id}")
    if tutorial_id:
        logger.info(f"   - Tutorial: tutorials/{tutorial_id}")
    logger.info("   - To clean: delete documents with 'isTest: true'")


def print_final_report():
    """Print the final test report."""
    print("\n")
    print("=" * 60)
    print("SMOKE TEST REPORT")
    print("=" * 60)
    
    status = test_result.get("status", "UNKNOWN")
    
    if status == "PASS":
        print("[PASS] Tutorial Generation Pipeline is OPERATIONAL")
        print("")
        if test_result["details"].get("tutorial_id"):
            print(f"   Tutorial ID: {test_result['details']['tutorial_id']}")
        if test_result["details"].get("generation_time_seconds"):
            print(f"   Generation Time: {test_result['details']['generation_time_seconds']}s")
        if test_result["details"].get("section_count"):
            print(f"   Sections: {test_result['details']['section_count']}")
    else:
        print("[FAIL] Tutorial Generation Pipeline FAILED")
        print("")
        error_sig = test_result.get("error_signature", "UNKNOWN")
        print(f"   Error Signature: {error_sig}")
        print("")
        
        # Specific guidance based on error type
        if error_sig == "429_RESOURCE_EXHAUSTED":
            print("[!] DIAGNOSIS: Gemini API Quota Exhausted")
            print("   -> Check Google Cloud Console for API quota status")
            print("   -> Wait for quota reset or request increase")
            
        elif error_sig == "400_INDEX_MISSING":
            print("[!] DIAGNOSIS: Missing Firestore Composite Index")
            print("   -> Check logs for the exact index URL")
            print("   -> Run: firebase deploy --only firestore:indexes")
            print("   -> Or manually create the index in Firebase Console")
            
        elif error_sig == "403_PERMISSION_DENIED":
            print("[!] DIAGNOSIS: Service Account Permission Issue")
            print("   -> Verify service account has Firestore access")
            print("   -> Check IAM roles in Google Cloud Console")
            
        elif error_sig == "FIREBASE_INIT_FAILURE":
            print("[!] DIAGNOSIS: Firebase initialization failed")
            print("   -> Check GOOGLE_APPLICATION_CREDENTIALS env var")
            print("   -> Verify service account JSON file exists")
        
        if test_result["details"].get("error"):
            print("")
            print("   Error Details:")
            error_msg = test_result["details"]["error"]
            # Truncate long errors
            if len(error_msg) > 300:
                error_msg = error_msg[:300] + "..."
            print(f"   {error_msg}")
    
    print("")
    print("=" * 60)
    
    # Return exit code
    return 0 if status == "PASS" else 1


def main():
    """Execute the full smoke test."""
    log_banner("TUTORIAL PIPELINE SMOKE TEST")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Test Topic: {SMOKE_TEST_TOPIC}")
    logger.info(f"Test User: {SMOKE_TEST_USER_ID}")
    print("")
    
    # Phase 0: Initialize
    db = init_firebase()
    if db is None:
        return print_final_report()
    
    # Phase 1: Clean stuck tasks
    cleaned = clean_stuck_processing_tasks(db)
    if cleaned < 0:  # Error during cleanup
        return print_final_report()
    
    # Phase 1.5: Ensure test user exists (required for generate_tutorial)
    if not ensure_test_user_exists(db):
        return print_final_report()
    
    # Phase 2: Inject test request
    request_id = inject_test_request(db)
    if request_id is None:
        return print_final_report()
    
    # Phase 3: Trigger generation
    tutorial_id = trigger_generation(db, request_id)
    if tutorial_id is None:
        cleanup_test_data(db, request_id, None)
        return print_final_report()
    
    # Phase 4: Verify content
    is_valid = verify_tutorial_content(db, tutorial_id)
    
    # Cleanup (preserve data for now)
    cleanup_test_data(db, request_id, tutorial_id)
    
    # Final report
    return print_final_report()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

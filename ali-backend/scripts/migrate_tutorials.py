#!/usr/bin/env python3
"""
Tutorial Migration Script
Migrates existing tutorials to the new lifecycle model (spec v2.2 §7)
AND assigns them to the Saga Map hierarchy (spec v2.2 §4.3).

Usage:
    python scripts/migrate_tutorials.py [--dry-run] [--user-id <uid>]

Options:
    --dry-run    Show what would be migrated without making changes
    --user-id    Migrate tutorials for a specific user only
"""
import os
import sys
import hashlib
import argparse
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# --- SAGA MAP CONSTANTS ---
DEFAULT_COURSE_ID = "course_general"
DEFAULT_COURSE_TITLE = "General"
DEFAULT_COURSE_DESCRIPTION = "General learning content not assigned to a specific course."

DEFAULT_MODULE_ID = "module_uncategorized"
DEFAULT_MODULE_TITLE = "Uncategorized"
DEFAULT_MODULE_DESCRIPTION = "Tutorials not yet assigned to a specific module."


def get_firestore_client():
    """Initialize Firestore client."""
    try:
        from google.cloud import firestore
        return firestore.Client()
    except Exception as e:
        logger.error(f"Failed to initialize Firestore: {e}")
        logger.info("Make sure GOOGLE_APPLICATION_CREDENTIALS is set or running with ADC")
        sys.exit(1)


def generate_content_hash(content: str) -> str:
    """Generate hash from tutorial content for versioning."""
    return hashlib.sha256(str(content).encode()).hexdigest()[:12]


def ensure_default_course_module(db, dry_run: bool = False) -> tuple:
    """
    Ensure the default Course and Module exist for orphan tutorials.
    Spec v2.2 §4.3: Saga Map hierarchy.
    
    Returns:
        (course_id, module_id) tuple
    """
    logger.info("\n🗺️  Ensuring Default Course/Module (Saga Map)...")
    
    # Check if default course exists
    course_ref = db.collection("courses").document(DEFAULT_COURSE_ID)
    course_doc = course_ref.get()
    
    if not course_doc.exists:
        if dry_run:
            logger.info(f"🔍 [DRY RUN] Would create default course: '{DEFAULT_COURSE_TITLE}'")
        else:
            course_ref.set({
                "id": DEFAULT_COURSE_ID,
                "tenantId": "default",
                "title": DEFAULT_COURSE_TITLE,
                "description": DEFAULT_COURSE_DESCRIPTION,
                "status": "PUBLISHED",
                "moduleIds": [DEFAULT_MODULE_ID],
                "coverImageUrl": None,
                "category": "general",
                "difficulty": "NOVICE",
                "estimatedHours": None,
                "prerequisites": [],
                "createdBy": "migration_script",
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat(),
                "publishedAt": datetime.utcnow().isoformat(),
            })
            logger.info(f"✅ Created default course: '{DEFAULT_COURSE_TITLE}'")
    else:
        logger.info(f"⏭️  Default course already exists: '{DEFAULT_COURSE_TITLE}'")
    
    # Check if default module exists
    module_ref = db.collection("modules").document(DEFAULT_MODULE_ID)
    module_doc = module_ref.get()
    
    if not module_doc.exists:
        if dry_run:
            logger.info(f"🔍 [DRY RUN] Would create default module: '{DEFAULT_MODULE_TITLE}'")
        else:
            module_ref.set({
                "id": DEFAULT_MODULE_ID,
                "courseId": DEFAULT_COURSE_ID,
                "title": DEFAULT_MODULE_TITLE,
                "description": DEFAULT_MODULE_DESCRIPTION,
                "sequence": 1,
                "tutorialIds": [],  # Will be populated during migration
                "unlockConditions": [{
                    "type": "ALWAYS_UNLOCKED",
                    "prerequisiteModuleIds": None,
                    "minimumScore": None,
                    "unlockedBy": None,
                    "unlockedAt": None,
                }],
                "estimatedMinutes": None,
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat(),
            })
            logger.info(f"✅ Created default module: '{DEFAULT_MODULE_TITLE}'")
    else:
        logger.info(f"⏭️  Default module already exists: '{DEFAULT_MODULE_TITLE}'")
    
    return (DEFAULT_COURSE_ID, DEFAULT_MODULE_ID)


def add_tutorial_to_default_module(db, tutorial_id: str, dry_run: bool = False):
    """Add a tutorial ID to the default module's tutorialIds array."""
    if dry_run:
        return
    
    try:
        from google.cloud import firestore as fs
        module_ref = db.collection("modules").document(DEFAULT_MODULE_ID)
        module_ref.update({
            "tutorialIds": fs.ArrayUnion([tutorial_id]),
            "updatedAt": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.warning(f"⚠️ Could not add {tutorial_id} to module: {e}")


def migrate_tutorial(doc, db, course_id: str, module_id: str, dry_run: bool = False) -> bool:
    """
    Migrate a single tutorial to the new lifecycle model AND Saga Map hierarchy.
    
    Adds:
    - status: PUBLISHED (existing tutorials are already live)
    - versions: Array with initial version
    - currentVersion: Reference to the version
    - courseId: Reference to parent course (Saga Map)
    - moduleId: Reference to parent module (Saga Map)
    - migratedAt: Timestamp
    
    Returns True if migrated, False if skipped.
    """
    data = doc.to_dict()
    doc_id = doc.id
    
    # Check migration status
    already_has_status = "status" in data and data["status"]
    already_has_course = "courseId" in data and data["courseId"]
    
    if already_has_status and already_has_course:
        logger.info(f"⏭️  Skipping {doc_id} (fully migrated)")
        return False
    
    # Generate version info
    content = str(data.get("content", "")) + str(data.get("sections", ""))
    content_hash = generate_content_hash(content)
    
    # Get creation timestamp
    timestamp = data.get("timestamp")
    if timestamp:
        if hasattr(timestamp, 'isoformat'):
            timestamp_str = timestamp.isoformat()
        else:
            timestamp_str = str(timestamp)
    else:
        timestamp_str = datetime.utcnow().isoformat()
    
    # Build update data
    update_data = {}
    
    # Add lifecycle fields if missing
    if not already_has_status:
        update_data.update({
            "status": "PUBLISHED",
            "versions": [{
                "versionId": f"v1_{content_hash}",
                "hash": content_hash,
                "timestamp": timestamp_str,
                "modelVersion": data.get("model_version", "gemini-2.5-pro"),
                "publishedBy": "migration_script"
            }],
            "currentVersion": f"v1_{content_hash}",
        })
    
    # Add Saga Map fields if missing
    if not already_has_course:
        update_data.update({
            "courseId": course_id,
            "moduleId": module_id,
        })
    
    # Add migration tracking
    update_data.update({
        "migratedAt": datetime.utcnow().isoformat(),
        "migrationVersion": "2.0"  # v2.0 includes Saga Map
    })
    
    if dry_run:
        logger.info(f"🔍 [DRY RUN] Would migrate: {doc_id}")
        logger.info(f"   Title: {data.get('title', 'Untitled')}")
        if not already_has_status:
            logger.info(f"   Status: PUBLISHED, Version: v1_{content_hash}")
        if not already_has_course:
            logger.info(f"   CourseId: {course_id}, ModuleId: {module_id}")
        return True
    
    try:
        doc.reference.update(update_data)
        
        # Add to module's tutorialIds
        if not already_has_course:
            add_tutorial_to_default_module(db, doc_id, dry_run)
        
        logger.info(f"✅ Migrated: {doc_id} - {data.get('title', 'Untitled')}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to migrate {doc_id}: {e}")
        return False


def migrate_global_tutorials(db, course_id: str, module_id: str, dry_run: bool = False) -> dict:
    """Migrate all tutorials in the global 'tutorials' collection."""
    logger.info("\n📚 Migrating Global Tutorials Collection...")
    
    results = {"migrated": 0, "skipped": 0, "failed": 0}
    
    tutorials = db.collection("tutorials").stream()
    
    for doc in tutorials:
        try:
            if migrate_tutorial(doc, db, course_id, module_id, dry_run):
                results["migrated"] += 1
            else:
                results["skipped"] += 1
        except Exception as e:
            logger.error(f"❌ Error processing {doc.id}: {e}")
            results["failed"] += 1
    
    return results


def migrate_user_tutorials(db, course_id: str, module_id: str, user_id: str = None, dry_run: bool = False) -> dict:
    """Migrate tutorials in user subcollections."""
    logger.info("\n👤 Migrating User Tutorial Subcollections...")
    
    results = {"migrated": 0, "skipped": 0, "failed": 0}
    
    if user_id:
        # Migrate specific user
        users = [db.collection("users").document(user_id).get()]
        if not users[0].exists:
            logger.error(f"User {user_id} not found")
            return results
    else:
        # Migrate all users
        users = db.collection("users").stream()
    
    for user_doc in users:
        uid = user_doc.id if hasattr(user_doc, 'id') else user_id
        user_tutorials = db.collection("users").document(uid).collection("tutorials").stream()
        
        for doc in user_tutorials:
            try:
                if migrate_tutorial(doc, db, course_id, module_id, dry_run):
                    results["migrated"] += 1
                else:
                    results["skipped"] += 1
            except Exception as e:
                logger.error(f"❌ Error processing user/{uid}/tutorials/{doc.id}: {e}")
                results["failed"] += 1
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Migrate tutorials to lifecycle model + Saga Map")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--user-id", type=str, help="Migrate specific user only")
    parser.add_argument("--global-only", action="store_true", help="Only migrate global collection")
    parser.add_argument("--users-only", action="store_true", help="Only migrate user subcollections")
    parser.add_argument("--skip-saga-map", action="store_true", help="Skip Saga Map hierarchy creation")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("ALI Tutorial Migration Script")
    logger.info("Spec v2.2 §7: Lifecycle Model")
    logger.info("Spec v2.2 §4.3: Saga Map (CourseManifest Hierarchy)")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
    
    db = get_firestore_client()
    
    # Step 1: Ensure default Course/Module exists
    if not args.skip_saga_map:
        course_id, module_id = ensure_default_course_module(db, args.dry_run)
    else:
        logger.info("⏭️  Skipping Saga Map hierarchy creation")
        course_id = DEFAULT_COURSE_ID
        module_id = DEFAULT_MODULE_ID
    
    total_results = {"migrated": 0, "skipped": 0, "failed": 0}
    
    # Step 2: Migrate global tutorials
    if not args.users_only:
        results = migrate_global_tutorials(db, course_id, module_id, args.dry_run)
        for key in total_results:
            total_results[key] += results[key]
    
    # Step 3: Migrate user subcollection tutorials
    if not args.global_only:
        results = migrate_user_tutorials(db, course_id, module_id, args.user_id, args.dry_run)
        for key in total_results:
            total_results[key] += results[key]
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✅ Migrated: {total_results['migrated']}")
    logger.info(f"⏭️  Skipped:  {total_results['skipped']}")
    logger.info(f"❌ Failed:   {total_results['failed']}")
    
    if not args.skip_saga_map:
        logger.info(f"\n🗺️  Saga Map:")
        logger.info(f"   Default Course: {course_id}")
        logger.info(f"   Default Module: {module_id}")
    
    if args.dry_run:
        logger.info("\n🔍 This was a DRY RUN. Run without --dry-run to apply changes.")
    else:
        logger.info("\n🎉 Migration complete!")


if __name__ == "__main__":
    main()


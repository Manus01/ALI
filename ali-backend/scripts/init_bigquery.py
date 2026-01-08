#!/usr/bin/env python3
"""
BigQuery Initialization Script
Sets up all required datasets and tables for ALI Platform.

Usage:
    python scripts/init_bigquery.py [--dry-run]
"""
import os
import sys
import argparse
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Initialize BigQuery datasets and tables")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("ALI BigQuery Initialization")
    logger.info("Spec v2.4 §13: Data Storage Setup")
    logger.info("=" * 60)
    
    try:
        from app.services.bigquery_service import BigQueryService
    except ImportError as e:
        logger.error(f"Failed to import BigQueryService: {e}")
        logger.info("Make sure google-cloud-bigquery is installed")
        sys.exit(1)
    
    service = BigQueryService()
    
    if not service.client:
        logger.error("BigQuery client not available")
        sys.exit(1)
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - Checking what would be created")
        logger.info(f"\nProject: {service.project_id}")
        logger.info(f"Dataset: {service.dataset_id}")
        logger.info("\nTables to create:")
        logger.info("  - prediction_logs (partitioned by created_at)")
        logger.info("  - unified_analytics_history (partitioned by date)")
        logger.info("  - generation_logs (partitioned by created_at)")
        return
    
    logger.info(f"\nProject: {service.project_id}")
    logger.info(f"Dataset: {service.dataset_id}")
    
    results = service.initialize_all_tables()
    
    logger.info("\n" + "=" * 60)
    logger.info("INITIALIZATION RESULTS")
    logger.info("=" * 60)
    
    all_success = True
    for table_name, success in results.items():
        status = "✅" if success else "❌"
        logger.info(f"{status} {table_name}")
        if not success:
            all_success = False
    
    if all_success:
        logger.info("\n🎉 All tables initialized successfully!")
    else:
        logger.warning("\n⚠️ Some tables failed to initialize. Check logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

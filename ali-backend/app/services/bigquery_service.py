"""
BigQuery Dataset and Table Setup for ALI Platform
Spec v2.4 §13: Data Storage for Predictions and Analytics

This module provides:
1. Dataset/Table creation utilities
2. Schema definitions for prediction_logs and unified_analytics_history
3. Helper functions for inserting/querying data
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from google.cloud import bigquery
    BQ_AVAILABLE = True
except ImportError:
    BQ_AVAILABLE = False
    bigquery = None

logger = logging.getLogger(__name__)

# --- SCHEMA DEFINITIONS (Spec v2.4 §13) ---

PREDICTION_LOGS_SCHEMA = [
    bigquery.SchemaField("prediction_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("tenant_id", "STRING"),
    bigquery.SchemaField("prediction_type", "STRING", mode="REQUIRED"),  # CPA, ROAS, Leads, etc.
    bigquery.SchemaField("model_tier", "STRING"),  # TIER_1 (stats) or TIER_2 (ML)
    bigquery.SchemaField("model_version", "STRING"),
    bigquery.SchemaField("horizon_days", "INTEGER"),
    bigquery.SchemaField("forecast_values", "JSON"),
    bigquery.SchemaField("confidence_score", "FLOAT"),
    bigquery.SchemaField("confidence_band_lower", "FLOAT"),
    bigquery.SchemaField("confidence_band_upper", "FLOAT"),
    bigquery.SchemaField("supporting_signals", "JSON"),
    bigquery.SchemaField("actual_values", "JSON"),  # Filled in later for accuracy tracking
    bigquery.SchemaField("accuracy_mape", "FLOAT"),  # Mean Absolute Percentage Error
    bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("evaluated_at", "TIMESTAMP"),  # When actuals were compared
]

UNIFIED_ANALYTICS_SCHEMA = [
    bigquery.SchemaField("record_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("tenant_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("platform", "STRING", mode="REQUIRED"),  # meta, google, linkedin
    # Canonical metrics (unified across platforms)
    bigquery.SchemaField("unified_cost", "FLOAT"),
    bigquery.SchemaField("unified_impressions", "INTEGER"),
    bigquery.SchemaField("unified_clicks", "INTEGER"),
    bigquery.SchemaField("unified_conversions", "INTEGER"),
    bigquery.SchemaField("unified_ctr", "FLOAT"),
    bigquery.SchemaField("unified_cpc", "FLOAT"),
    bigquery.SchemaField("unified_cpa", "FLOAT"),
    bigquery.SchemaField("unified_roas", "FLOAT"),
    # Hierarchy mapping
    bigquery.SchemaField("campaign_id", "STRING"),
    bigquery.SchemaField("campaign_name", "STRING"),
    bigquery.SchemaField("adset_id", "STRING"),  # AdSet (Meta) / AdGroup (Google)
    bigquery.SchemaField("adset_name", "STRING"),
    bigquery.SchemaField("creative_id", "STRING"),
    bigquery.SchemaField("creative_name", "STRING"),
    # Raw platform data (for debugging)
    bigquery.SchemaField("raw_platform_data", "JSON"),
    bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED"),
]

GENERATION_LOGS_SCHEMA = [
    bigquery.SchemaField("generation_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("generation_type", "STRING"),  # tutorial, ad_creative, prediction
    bigquery.SchemaField("topic", "STRING"),
    bigquery.SchemaField("model_version", "STRING"),
    bigquery.SchemaField("rubric_verdict", "STRING"),  # PASS or FAIL
    bigquery.SchemaField("rubric_score", "FLOAT"),
    bigquery.SchemaField("status", "STRING"),  # DRAFT, PUBLISHED, etc.
    bigquery.SchemaField("duration_seconds", "FLOAT"),
    bigquery.SchemaField("token_count_input", "INTEGER"),
    bigquery.SchemaField("token_count_output", "INTEGER"),
    bigquery.SchemaField("error_message", "STRING"),
    bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
]


class BigQueryService:
    """Service for BigQuery operations in ALI Platform."""
    
    def __init__(self, project_id: Optional[str] = None, dataset_id: str = "ali_analytics"):
        if not BQ_AVAILABLE:
            logger.warning("⚠️ BigQuery not available. Install google-cloud-bigquery.")
            self.client = None
            return
            
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "ali-platform-prod-73019")
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=self.project_id)
        
    def _get_table_ref(self, table_name: str) -> str:
        return f"{self.project_id}.{self.dataset_id}.{table_name}"
    
    def ensure_dataset_exists(self) -> bool:
        """Create dataset if it doesn't exist."""
        if not self.client:
            return False
            
        dataset_ref = bigquery.Dataset(f"{self.project_id}.{self.dataset_id}")
        dataset_ref.location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        
        try:
            self.client.get_dataset(dataset_ref)
            logger.info(f"✅ Dataset {self.dataset_id} exists")
            return True
        except Exception:
            try:
                self.client.create_dataset(dataset_ref, exists_ok=True)
                logger.info(f"✅ Created dataset {self.dataset_id}")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to create dataset: {e}")
                return False
    
    def ensure_table_exists(self, table_name: str, schema: List) -> bool:
        """Create table with schema if it doesn't exist."""
        if not self.client:
            return False
            
        table_ref = self._get_table_ref(table_name)
        table = bigquery.Table(table_ref, schema=schema)
        
        # Set partitioning for time-series tables
        if "created_at" in [f.name for f in schema]:
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="created_at"
            )
        elif "date" in [f.name for f in schema]:
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="date"
            )
        
        try:
            self.client.get_table(table_ref)
            logger.info(f"✅ Table {table_name} exists")
            return True
        except Exception:
            try:
                self.client.create_table(table, exists_ok=True)
                logger.info(f"✅ Created table {table_name}")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to create table {table_name}: {e}")
                return False
    
    def initialize_all_tables(self) -> Dict[str, bool]:
        """Initialize all required tables for ALI Platform."""
        results = {}
        
        if not self.ensure_dataset_exists():
            return {"dataset": False}
        
        tables = [
            ("prediction_logs", PREDICTION_LOGS_SCHEMA),
            ("unified_analytics_history", UNIFIED_ANALYTICS_SCHEMA),
            ("generation_logs", GENERATION_LOGS_SCHEMA),
        ]
        
        for table_name, schema in tables:
            results[table_name] = self.ensure_table_exists(table_name, schema)
        
        return results
    
    def insert_prediction_log(self, data: Dict[str, Any]) -> bool:
        """Insert a prediction log entry."""
        if not self.client:
            logger.warning("⚠️ BigQuery not available, skipping insert")
            return False
            
        table_ref = self._get_table_ref("prediction_logs")
        
        # Ensure required fields
        data.setdefault("created_at", datetime.utcnow().isoformat())
        
        try:
            errors = self.client.insert_rows_json(table_ref, [data])
            if errors:
                logger.error(f"❌ Insert errors: {errors}")
                return False
            return True
        except Exception as e:
            logger.error(f"❌ Failed to insert prediction log: {e}")
            return False
    
    def insert_analytics_records(self, records: List[Dict[str, Any]]) -> int:
        """Insert multiple analytics records. Returns count of successful inserts."""
        if not self.client or not records:
            return 0
            
        table_ref = self._get_table_ref("unified_analytics_history")
        
        # Ensure required fields
        for record in records:
            record.setdefault("ingested_at", datetime.utcnow().isoformat())
        
        try:
            errors = self.client.insert_rows_json(table_ref, records)
            if errors:
                logger.error(f"❌ Insert errors: {errors}")
                return len(records) - len(errors)
            return len(records)
        except Exception as e:
            logger.error(f"❌ Failed to insert analytics records: {e}")
            return 0
    
    def query_prediction_accuracy(self, user_id: str, days: int = 30) -> List[Dict]:
        """Query prediction accuracy metrics for drift detection."""
        if not self.client:
            return []
            
        query = f"""
        SELECT 
            prediction_type,
            model_tier,
            AVG(accuracy_mape) as avg_mape,
            COUNT(*) as prediction_count
        FROM `{self._get_table_ref('prediction_logs')}`
        WHERE user_id = @user_id
          AND evaluated_at IS NOT NULL
          AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
        GROUP BY prediction_type, model_tier
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                bigquery.ScalarQueryParameter("days", "INT64", days),
            ]
        )
        
        try:
            results = self.client.query(query, job_config=job_config)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
            return []


# --- CONVENIENCE FUNCTIONS ---

_bq_service: Optional[BigQueryService] = None

def get_bigquery_service() -> BigQueryService:
    """Get or create singleton BigQuery service."""
    global _bq_service
    if _bq_service is None:
        _bq_service = BigQueryService()
    return _bq_service


def log_prediction(
    prediction_id: str,
    user_id: str,
    prediction_type: str,
    forecast_values: Dict,
    confidence_score: float,
    model_tier: str = "TIER_1",
    **kwargs
) -> bool:
    """Convenience function to log a prediction."""
    service = get_bigquery_service()
    return service.insert_prediction_log({
        "prediction_id": prediction_id,
        "user_id": user_id,
        "prediction_type": prediction_type,
        "model_tier": model_tier,
        "forecast_values": forecast_values,
        "confidence_score": confidence_score,
        **kwargs
    })

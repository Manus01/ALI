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

# --- BRAND INTELLIGENCE SCHEMAS ---

BRAND_MENTIONS_LOG_SCHEMA = [
    bigquery.SchemaField("mention_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("entity_name", "STRING", mode="REQUIRED"),  # Brand or competitor name
    bigquery.SchemaField("entity_type", "STRING"),  # "brand" or "competitor"
    bigquery.SchemaField("source_type", "STRING"),  # "news", "social", "blog", "forum"
    bigquery.SchemaField("source_platform", "STRING"),  # "linkedin", "twitter", etc.
    bigquery.SchemaField("country", "STRING"),  # ISO country code (e.g., "US", "GB", "DE")
    bigquery.SchemaField("language", "STRING"),  # ISO language code (e.g., "en", "de")
    bigquery.SchemaField("url", "STRING"),
    bigquery.SchemaField("title", "STRING"),
    bigquery.SchemaField("content_snippet", "STRING"),  # First 500 chars
    bigquery.SchemaField("sentiment", "STRING"),  # "positive", "neutral", "negative"
    bigquery.SchemaField("sentiment_score", "FLOAT"),  # -1.0 to 1.0
    bigquery.SchemaField("severity", "INTEGER"),  # 1-10 for negative
    bigquery.SchemaField("key_concerns", "JSON"),  # List of concerns
    bigquery.SchemaField("detected_at", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("published_at", "TIMESTAMP"),
]

ACTIONS_LOG_SCHEMA = [
    bigquery.SchemaField("action_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("mention_id", "STRING"),  # Related mention
    bigquery.SchemaField("action_type", "STRING"),  # "respond", "amplify", "ignore", "escalate"
    bigquery.SchemaField("channels_used", "JSON"),  # ["linkedin", "press_release"]
    bigquery.SchemaField("content_generated", "JSON"),  # Content per channel
    bigquery.SchemaField("strategic_agenda", "STRING"),  # Agenda used
    bigquery.SchemaField("ai_suggested", "BOOLEAN"),  # Was this AI-recommended?
    bigquery.SchemaField("user_approved", "BOOLEAN"),  # Did user approve?
    bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
]

OUTCOMES_LOG_SCHEMA = [
    bigquery.SchemaField("outcome_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("action_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("metric_type", "STRING"),  # "engagement", "sentiment_shift", "reach"
    bigquery.SchemaField("metric_value", "FLOAT"),
    bigquery.SchemaField("baseline_value", "FLOAT"),
    bigquery.SchemaField("user_feedback", "STRING"),  # "effective", "ineffective", null
    bigquery.SchemaField("auto_detected", "BOOLEAN"),
    bigquery.SchemaField("measured_at", "TIMESTAMP", mode="REQUIRED"),
]

COMPETITOR_ACTIONS_LOG_SCHEMA = [
    bigquery.SchemaField("action_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),  # Who's monitoring
    bigquery.SchemaField("competitor_name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("action_type", "STRING"),  # "campaign", "pr", "product_launch", etc.
    bigquery.SchemaField("description", "STRING"),  # AI-generated summary
    bigquery.SchemaField("estimated_impact", "STRING"),  # "high", "medium", "low"
    bigquery.SchemaField("source_urls", "JSON"),  # Evidence URLs
    bigquery.SchemaField("detected_at", "TIMESTAMP", mode="REQUIRED"),
]

BRAND_HEALTH_SCORES_SCHEMA = [
    bigquery.SchemaField("score_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("overall_score", "FLOAT"),  # 0-100
    bigquery.SchemaField("sentiment_score", "FLOAT"),  # Component
    bigquery.SchemaField("visibility_score", "FLOAT"),  # Component
    bigquery.SchemaField("response_score", "FLOAT"),  # Component
    bigquery.SchemaField("competitor_position", "INTEGER"),  # Rank vs competitors
    bigquery.SchemaField("score_breakdown", "JSON"),  # Detailed components
    bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
]

ANONYMIZED_PATTERNS_SCHEMA = [
    bigquery.SchemaField("pattern_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("pattern_type", "STRING"),  # "response", "content", "competitor"
    bigquery.SchemaField("industry", "STRING"),  # Industry category
    bigquery.SchemaField("situation", "STRING"),  # "negative_press", "product_launch", etc.
    bigquery.SchemaField("strategy_used", "STRING"),  # What approach
    bigquery.SchemaField("agenda", "STRING"),  # Strategic agenda
    bigquery.SchemaField("effectiveness_avg", "FLOAT"),  # Avg outcome score
    bigquery.SchemaField("sample_count", "INTEGER"),  # How many examples
    bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
]

# --- ADAPTIVE SCANNING SCHEMA ---

SCAN_LOGS_SCHEMA = [
    bigquery.SchemaField("log_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("brand_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    
    # Job metadata
    bigquery.SchemaField("job_id", "STRING"),
    bigquery.SchemaField("trigger_reason", "STRING"),  # "adaptive_critical", "manual", etc.
    bigquery.SchemaField("threat_score_at_schedule", "INTEGER"),
    bigquery.SchemaField("policy_mode", "STRING"),  # "adaptive" or "fixed"
    
    # Execution metrics
    bigquery.SchemaField("started_at", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("completed_at", "TIMESTAMP"),
    bigquery.SchemaField("duration_ms", "INTEGER"),
    bigquery.SchemaField("status", "STRING"),  # "success" or "failed"
    bigquery.SchemaField("error_message", "STRING"),
    
    # Results
    bigquery.SchemaField("mentions_found", "INTEGER"),
    bigquery.SchemaField("new_mentions_logged", "INTEGER"),
    bigquery.SchemaField("opportunities_detected", "INTEGER"),
    
    # Post-scan assessment
    bigquery.SchemaField("threat_score_post", "INTEGER"),
    bigquery.SchemaField("threat_breakdown", "JSON"),
    
    # Scheduling
    bigquery.SchemaField("next_scan_scheduled_for", "TIMESTAMP"),
    bigquery.SchemaField("scan_interval_ms", "INTEGER"),
]

# --- MARKET RADAR SCHEMAS (Competitor Intelligence) ---

COMPETITOR_EVENTS_LOG_SCHEMA = [
    bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("competitor_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("competitor_name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    
    # Event classification
    bigquery.SchemaField("event_type", "STRING", mode="REQUIRED"),  # pricing, product, etc.
    bigquery.SchemaField("themes", "STRING", mode="REPEATED"),  # Extracted themes
    
    # Detection metadata
    bigquery.SchemaField("detected_at", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("source_url", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("source_type", "STRING"),  # news, rss, social, website_diff
    
    # Content
    bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("summary", "STRING"),
    bigquery.SchemaField("raw_snippet", "STRING"),
    
    # Scoring
    bigquery.SchemaField("impact_score", "INTEGER"),  # 1-10
    bigquery.SchemaField("confidence", "FLOAT"),  # 0.0-1.0
    
    # Filtering
    bigquery.SchemaField("region", "STRING"),  # ISO country code
    bigquery.SchemaField("cluster_id", "STRING"),  # Assigned ThemeCluster ID
    
    # Integrity
    bigquery.SchemaField("event_hash", "STRING"),
]

THEME_CLUSTERS_LOG_SCHEMA = [
    bigquery.SchemaField("cluster_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("theme_name", "STRING", mode="REQUIRED"),
    
    # Aggregation
    bigquery.SchemaField("event_count", "INTEGER"),
    bigquery.SchemaField("competitors_involved", "STRING", mode="REPEATED"),
    
    # Insights
    bigquery.SchemaField("why_it_matters", "STRING"),
    bigquery.SchemaField("suggested_actions", "STRING", mode="REPEATED"),
    
    # Metadata
    bigquery.SchemaField("priority", "INTEGER"),  # 1-10
    bigquery.SchemaField("time_range_start", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("time_range_end", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    
    # Integrity
    bigquery.SchemaField("cluster_hash", "STRING"),
]

WEEKLY_DIGESTS_LOG_SCHEMA = [
    bigquery.SchemaField("digest_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("generated_at", "TIMESTAMP", mode="REQUIRED"),
    
    # Time range
    bigquery.SchemaField("time_range_start", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("time_range_end", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("time_range_label", "STRING"),  # 7d, 30d, etc.
    
    # Metrics
    bigquery.SchemaField("total_events", "INTEGER"),
    bigquery.SchemaField("competitors_active", "INTEGER"),
    bigquery.SchemaField("high_impact_events", "INTEGER"),
    bigquery.SchemaField("dominant_theme", "STRING"),
    
    # Content references
    bigquery.SchemaField("top_cluster_ids", "STRING", mode="REPEATED"),
    bigquery.SchemaField("notable_event_ids", "STRING", mode="REPEATED"),
    
    # Export
    bigquery.SchemaField("export_url", "STRING"),
    bigquery.SchemaField("export_format", "STRING"),
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
        except Exception as e:
            logger.debug(f"Dataset access check failed (assuming creation needed): {e}")
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
        except Exception as e:
            logger.debug(f"Table access check failed (assuming creation needed): {e}")
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
            # Original tables
            ("prediction_logs", PREDICTION_LOGS_SCHEMA),
            ("unified_analytics_history", UNIFIED_ANALYTICS_SCHEMA),
            ("generation_logs", GENERATION_LOGS_SCHEMA),
            # Brand Intelligence tables
            ("brand_mentions_log", BRAND_MENTIONS_LOG_SCHEMA),
            ("actions_log", ACTIONS_LOG_SCHEMA),
            ("outcomes_log", OUTCOMES_LOG_SCHEMA),
            ("competitor_actions_log", COMPETITOR_ACTIONS_LOG_SCHEMA),
            ("brand_health_scores", BRAND_HEALTH_SCORES_SCHEMA),
            ("anonymized_patterns", ANONYMIZED_PATTERNS_SCHEMA),
            # Adaptive Scanning
            ("scan_logs", SCAN_LOGS_SCHEMA),
            # Market Radar (Competitor Intelligence)
            ("competitor_events_log", COMPETITOR_EVENTS_LOG_SCHEMA),
            ("theme_clusters_log", THEME_CLUSTERS_LOG_SCHEMA),
            ("weekly_digests_log", WEEKLY_DIGESTS_LOG_SCHEMA),
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
    
    # --- BRAND INTELLIGENCE INSERT METHODS ---
    
    def _insert_to_table(self, table_name: str, data: Dict[str, Any], timestamp_field: str = "created_at") -> bool:
        """Generic insert helper for any table."""
        if not self.client:
            logger.warning("⚠️ BigQuery not available, skipping insert")
            return False
            
        table_ref = self._get_table_ref(table_name)
        data.setdefault(timestamp_field, datetime.utcnow().isoformat())
        
        try:
            errors = self.client.insert_rows_json(table_ref, [data])
            if errors:
                logger.error(f"❌ Insert errors for {table_name}: {errors}")
                return False
            return True
        except Exception as e:
            logger.error(f"❌ Failed to insert to {table_name}: {e}")
            return False
    
    def insert_mention_log(self, data: Dict[str, Any]) -> bool:
        """Log a detected mention to BigQuery."""
        return self._insert_to_table("brand_mentions_log", data, "detected_at")
    
    def insert_action_log(self, data: Dict[str, Any]) -> bool:
        """Log a PR action taken."""
        return self._insert_to_table("actions_log", data, "created_at")
    
    def insert_outcome_log(self, data: Dict[str, Any]) -> bool:
        """Log an action outcome measurement."""
        return self._insert_to_table("outcomes_log", data, "measured_at")
    
    def insert_competitor_action(self, data: Dict[str, Any]) -> bool:
        """Log an observed competitor action."""
        return self._insert_to_table("competitor_actions_log", data, "detected_at")
    
    def insert_health_score(self, data: Dict[str, Any]) -> bool:
        """Log a brand health score snapshot."""
        return self._insert_to_table("brand_health_scores", data, "created_at")
    
    def insert_pattern(self, data: Dict[str, Any]) -> bool:
        """Insert or update an anonymized pattern."""
        return self._insert_to_table("anonymized_patterns", data, "updated_at")
    
    # --- MARKET RADAR INSERT METHODS ---
    
    def insert_competitor_event(self, data: Dict[str, Any]) -> bool:
        """Log a competitor event to BigQuery."""
        return self._insert_to_table("competitor_events_log", data, "detected_at")
    
    def insert_competitor_events_batch(self, events: List[Dict[str, Any]]) -> int:
        """Insert multiple competitor events. Returns count of successful inserts."""
        if not self.client or not events:
            return 0
            
        table_ref = self._get_table_ref("competitor_events_log")
        
        for event in events:
            event.setdefault("detected_at", datetime.utcnow().isoformat())
        
        try:
            errors = self.client.insert_rows_json(table_ref, events)
            if errors:
                logger.error(f"❌ Batch insert errors: {errors}")
                return len(events) - len(errors)
            return len(events)
        except Exception as e:
            logger.error(f"❌ Failed to batch insert competitor events: {e}")
            return 0
    
    def insert_theme_cluster(self, data: Dict[str, Any]) -> bool:
        """Log a theme cluster to BigQuery."""
        return self._insert_to_table("theme_clusters_log", data, "created_at")
    
    def insert_weekly_digest(self, data: Dict[str, Any]) -> bool:
        """Log a weekly digest to BigQuery."""
        return self._insert_to_table("weekly_digests_log", data, "generated_at")
    
    # --- MARKET RADAR QUERY METHODS ---
    
    def query_competitor_events(
        self, 
        user_id: str, 
        competitor_id: Optional[str] = None,
        event_type: Optional[str] = None,
        theme: Optional[str] = None,
        region: Optional[str] = None,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict]:
        """Query competitor events with optional filters."""
        if not self.client:
            return []
        
        # Build dynamic WHERE clauses
        conditions = ["user_id = @user_id", "detected_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)"]
        params = [
            bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
            bigquery.ScalarQueryParameter("days", "INT64", days),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]
        
        if competitor_id:
            conditions.append("competitor_id = @competitor_id")
            params.append(bigquery.ScalarQueryParameter("competitor_id", "STRING", competitor_id))
        
        if event_type:
            conditions.append("event_type = @event_type")
            params.append(bigquery.ScalarQueryParameter("event_type", "STRING", event_type))
        
        if region:
            conditions.append("region = @region")
            params.append(bigquery.ScalarQueryParameter("region", "STRING", region))
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
        SELECT *
        FROM `{self._get_table_ref('competitor_events_log')}`
        WHERE {where_clause}
        ORDER BY detected_at DESC
        LIMIT @limit
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        
        try:
            results = self.client.query(query, job_config=job_config)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"❌ Competitor events query failed: {e}")
            return []
    
    def query_events_by_theme_summary(self, user_id: str, days: int = 7) -> Dict[str, int]:
        """Get event count by theme for clustering summary."""
        if not self.client:
            return {}
        
        query = f"""
        SELECT theme, COUNT(*) as count
        FROM `{self._get_table_ref('competitor_events_log')}`,
        UNNEST(themes) as theme
        WHERE user_id = @user_id
          AND detected_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
        GROUP BY theme
        ORDER BY count DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                bigquery.ScalarQueryParameter("days", "INT64", days),
            ]
        )
        
        try:
            results = self.client.query(query, job_config=job_config)
            return {row["theme"]: row["count"] for row in results}
        except Exception as e:
            logger.error(f"❌ Theme summary query failed: {e}")
            return {}
    
    def query_theme_clusters(self, user_id: str, days: int = 30, min_priority: int = 1) -> List[Dict]:
        """Query theme clusters with optional filters."""
        if not self.client:
            return []
        
        query = f"""
        SELECT *
        FROM `{self._get_table_ref('theme_clusters_log')}`
        WHERE user_id = @user_id
          AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
          AND priority >= @min_priority
        ORDER BY priority DESC, created_at DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                bigquery.ScalarQueryParameter("days", "INT64", days),
                bigquery.ScalarQueryParameter("min_priority", "INT64", min_priority),
            ]
        )
        
        try:
            results = self.client.query(query, job_config=job_config)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"❌ Theme clusters query failed: {e}")
            return []

    # --- BRAND INTELLIGENCE QUERY METHODS ---

    
    def query_similar_mentions(self, user_id: str, sentiment: str, entity_type: str = "brand", limit: int = 10) -> List[Dict]:
        """Find similar past mentions to power recommendations."""
        if not self.client:
            return []
            
        query = f"""
        SELECT 
            mention_id, entity_name, title, sentiment, sentiment_score, severity,
            source_type, detected_at
        FROM `{self._get_table_ref('brand_mentions_log')}`
        WHERE user_id = @user_id
          AND entity_type = @entity_type
          AND sentiment = @sentiment
        ORDER BY detected_at DESC
        LIMIT @limit
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                bigquery.ScalarQueryParameter("entity_type", "STRING", entity_type),
                bigquery.ScalarQueryParameter("sentiment", "STRING", sentiment),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ]
        )
        
        try:
            results = self.client.query(query, job_config=job_config)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
            return []
    
    def get_brand_health_trend(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get brand health score trend for charting."""
        if not self.client:
            return []
            
        query = f"""
        SELECT date, overall_score, sentiment_score, visibility_score, response_score
        FROM `{self._get_table_ref('brand_health_scores')}`
        WHERE user_id = @user_id
          AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
        ORDER BY date ASC
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
    
    def get_geographic_sentiment_breakdown(self, user_id: str, days: int = 30, entity_type: str = "brand") -> Dict[str, Any]:
        """
        Get sentiment breakdown by country.
        Returns top 5 positive, top 5 negative, and full list for detailed report.
        """
        if not self.client:
            return {"top_positive": [], "top_negative": [], "all_countries": []}
            
        query = f"""
        WITH country_stats AS (
            SELECT 
                country,
                COUNT(*) as mention_count,
                AVG(sentiment_score) as avg_sentiment,
                COUNTIF(sentiment = 'positive') as positive_count,
                COUNTIF(sentiment = 'negative') as negative_count,
                COUNTIF(sentiment = 'neutral') as neutral_count
            FROM `{self._get_table_ref('brand_mentions_log')}`
            WHERE user_id = @user_id
              AND entity_type = @entity_type
              AND country IS NOT NULL
              AND detected_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
            GROUP BY country
        )
        SELECT 
            country,
            mention_count,
            avg_sentiment,
            positive_count,
            negative_count,
            neutral_count,
            ROUND(positive_count * 100.0 / mention_count, 1) as positive_pct,
            ROUND(negative_count * 100.0 / mention_count, 1) as negative_pct
        FROM country_stats
        ORDER BY avg_sentiment DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                bigquery.ScalarQueryParameter("entity_type", "STRING", entity_type),
                bigquery.ScalarQueryParameter("days", "INT64", days),
            ]
        )
        
        try:
            results = list(self.client.query(query, job_config=job_config))
            all_countries = [dict(row) for row in results]
            
            # Top 5 positive (highest avg_sentiment)
            top_positive = all_countries[:5]
            
            # Top 5 negative (lowest avg_sentiment, reverse the list)
            top_negative = all_countries[-5:][::-1] if len(all_countries) >= 5 else all_countries[::-1]
            
            return {
                "top_positive": top_positive,
                "top_negative": top_negative,
                "all_countries": all_countries,
                "total_countries": len(all_countries)
            }
        except Exception as e:
            logger.error(f"❌ Geographic query failed: {e}")
            return {"top_positive": [], "top_negative": [], "all_countries": [], "total_countries": 0}


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


def log_mention(
    mention_id: str,
    user_id: str,
    entity_name: str,
    entity_type: str,
    sentiment: str,
    **kwargs
) -> bool:
    """Convenience function to log a brand/competitor mention."""
    service = get_bigquery_service()
    return service.insert_mention_log({
        "mention_id": mention_id,
        "user_id": user_id,
        "entity_name": entity_name,
        "entity_type": entity_type,
        "sentiment": sentiment,
        **kwargs
    })


def log_action(
    action_id: str,
    user_id: str,
    action_type: str,
    channels_used: List[str],
    **kwargs
) -> bool:
    """Convenience function to log a PR action taken."""
    service = get_bigquery_service()
    return service.insert_action_log({
        "action_id": action_id,
        "user_id": user_id,
        "action_type": action_type,
        "channels_used": channels_used,
        **kwargs
    })


def log_outcome(
    outcome_id: str,
    action_id: str,
    user_id: str,
    metric_type: str,
    metric_value: float,
    **kwargs
) -> bool:
    """Convenience function to log an action outcome."""
    service = get_bigquery_service()
    return service.insert_outcome_log({
        "outcome_id": outcome_id,
        "action_id": action_id,
        "user_id": user_id,
        "metric_type": metric_type,
        "metric_value": metric_value,
        **kwargs
    })


import logging
from datetime import datetime
from google.cloud import firestore
from app.services.metricool_client import MetricoolClient

logger = logging.getLogger(__name__)
db = firestore.Client()

def run_nightly_performance_log():
    """
    CRITICAL RESEARCH TASK:
    Iterates through all users with a connected Metricool ID.
    Fetches yesterday's stats.
    Saves a snapshot to 'ad_performance_logs' for longitudinal study.
    """
    logger.info("📉 Starting Nightly Performance Log...")
    
    # 1. Find all active Metricool integrations
    # Iterate through all users and check their sub-collection
    users = db.collection("users").stream()
    
    integrations = []
    for user_doc in users:
        user_id = user_doc.id
        metricool_doc = db.collection("users").document(user_id).collection("user_integrations").document("metricool").get()
        if metricool_doc.exists:
            data = metricool_doc.to_dict()
            if data.get("status") == "active" and data.get("metricool_blog_id"):
                data["user_id"] = user_id  # Ensure user_id is in the data
                integrations.append(data)
    
    client = MetricoolClient()
    count = 0

    for data in integrations:
        user_id = data.get("user_id")
        blog_id = data.get("metricool_blog_id")
            
        try:
            # 2. Fetch Stats (Yesterday)
            stats = client.get_yesterday_stats(blog_id)
            
            # 3. Create Log Entry
            log_entry = {
                "user_id": user_id,
                "metricool_blog_id": blog_id,
                "date": datetime.utcnow().strftime('%Y-%m-%d'), # Log Date
                "timestamp": datetime.utcnow(),
                "total_spend": stats.get("total_spend", 0),
                "total_clicks": stats.get("total_clicks", 0),
                "impressions": stats.get("impressions", 0),
                "ctr": stats.get("ctr", 0)
            }
            
            # 4. Save to Firestore (New Collection)
            # We use a composite key to prevent duplicates: userID_date
            log_id = f"{user_id}_{log_entry['date']}"
            db.collection("ad_performance_logs").document(log_id).set(log_entry)
            
            count += 1
            logger.info(f"✅ Logged stats for User {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to log user {user_id}: {e}")

    logger.info(f"🏁 Nightly Log Complete. Processed {count} users.")
    return {"status": "success", "processed": count}
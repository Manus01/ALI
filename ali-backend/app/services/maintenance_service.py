from google.cloud import firestore
from app.core.security import db

def run_weekly_maintenance(user_id: str):
    print(f"🧹 Maintenance: Starting run for {user_id}...")
    
    # --- LAZY IMPORTS ---
    # Import heavy agents only when the function runs
    from app.agents.maintenance_agent import review_tutorial_relevance
    from app.agents.tutorial_agent import generate_tutorial
    from app.agents.nodes import analyst_node
    
    # 1. Get User Data & Real Metrics
    user_ref = db.collection('users').document(user_id)
    user_snap = user_ref.get()
    if not user_snap.exists: return
    user_data = user_snap.to_dict()
    
    # Fetch recent performance metrics (Limit 10)
    # Note: Ensure you have data in 'campaign_performance' subcollection from Phase 2
    docs = user_ref.collection('campaign_performance').limit(10).stream()
    current_metrics = [d.to_dict() for d in docs]
    
    # 2. Review Existing Tutorials
    # We check all tutorials created by this user
    tutorials = db.collection('tutorials').where(filter=firestore.FieldFilter('created_by', '==', user_id)).stream()
    
    updates_count = 0
    
    for tut_doc in tutorials:
        tut = tut_doc.to_dict()
        # Skip if it's already an update or archived
        if tut.get('is_update') or tut.get('archived'): continue
        
        # Ask AI: Is this relevant?
        review = review_tutorial_relevance(tut, current_metrics, user_data.get('profile', {}))
        
        if review.get('is_outdated'):
            print(f"🔄 Updating outdated lesson: {tut['title']}")
            
            # Generate the "Delta" lesson (4C/ID compliant update)
            generate_tutorial(user_id, f"UPDATE: {tut['title']}", is_delta=True, context=review.get('reason'))
            
            # Notify
            db.collection("users").document(user_id).collection("notifications").add({
                 "type": "info",
                 "title": "Lesson Updated",
                 "message": f"New insights for '{tut['title']}': {review.get('reason')}",
                 "read": False,
                 "created_at": firestore.SERVER_TIMESTAMP
            })
            updates_count += 1
            
            # Optional: Mark old tutorial as archived?
            # tut_doc.reference.update({"archived": True})

    # 3. Check for NEW Anomalies (Auto-Assign Curriculum)
    # We reuse the Analyst Node logic!
    state = {"user_id": user_id, "campaign_data": current_metrics}
    analysis = analyst_node(state)
    
    new_count = 0
    for anomaly in analysis.get("anomalies", []):
        if "No data" in anomaly or "stable" in anomaly.lower(): continue
        
        # Simple check to avoid duplicates (In prod, use vector search)
        # For now, we just auto-generate one if it looks critical
        print(f"🆕 Auto-creating lesson for: {anomaly}")
        
        # Create a full 4C/ID course for this new problem
        generate_tutorial(user_id, f"Fixing: {anomaly}")
        
        db.collection("users").document(user_id).collection("notifications").add({
             "type": "info",
             "title": "New Course Assigned",
             "message": f"AI assigned a new lesson to fix: {anomaly}",
             "read": False,
             "created_at": firestore.SERVER_TIMESTAMP
        })
        new_count += 1

    print(f"✅ Maintenance Complete. Updates: {updates_count}, New: {new_count}")
    
    # Final "Complete" Notification
    db.collection("users").document(user_id).collection("notifications").add({
        "type": "success",
        "title": "Maintenance Complete",
        "message": f"Review finished. {updates_count} updates, {new_count} new lessons.",
        "read": False,
        "created_at": firestore.SERVER_TIMESTAMP
    })
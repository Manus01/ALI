import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# Initialize (Force re-init to script context)
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {'projectId': os.getenv("PROJECT_ID")})

db = firestore.client()

def clean_stuck_jobs():
    print("🧹 Cleaning stuck jobs and notifications...")
    
    # 1. Clear Notifications
    notes = db.collection("notifications").stream()
    count = 0
    for note in notes:
        note.reference.delete()
        count += 1
    print(f"   - Deleted {count} notifications.")

    # 2. Clear Jobs
    jobs = db.collection("jobs").stream()
    count = 0
    for job in jobs:
        job.reference.delete()
        count += 1
    print(f"   - Deleted {count} jobs.")
    
    print("✨ Database is clean.")

if __name__ == "__main__":
    clean_stuck_jobs()
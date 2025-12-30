from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_token
from google.cloud import firestore

router = APIRouter()

@router.delete("/{notification_id}")
def delete_notification(notification_id: str, user: dict = Depends(verify_token)):
    """
    Deletes a notification document from Firestore.
    """
    try:
        db = firestore.Client()
        # Verify ownership before deleting
        # SENIOR DEV FIX: Delete from user's subcollection
        notif_ref = db.collection("users").document(user['uid']).collection("notifications").document(notification_id)
        doc = notif_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Notification not found")
            
        notif_ref.delete()
        return {"status": "success"}
    except Exception as e:
        print(f"❌ Notification Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
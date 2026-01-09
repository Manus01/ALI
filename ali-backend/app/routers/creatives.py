"""
User-facing Creative Endpoints for Self-Approval Workflow.

This router allows users to:
- View their own draft creatives
- Publish their own drafts (without admin intervention)
- View their published creatives

Spec: User Self-Approval Model (replacing Admin-Approval for creatives)
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_token, db
from google.cloud import firestore
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/my-drafts")
def get_my_drafts(user: dict = Depends(verify_token)):
    """
    Fetch current user's draft creatives (status IN [DRAFT, PENDING]).
    Returns only creatives owned by the authenticated user.
    """
    try:
        uid = user['uid']
        
        # Query creativeDrafts collection for user's own drafts
        query = db.collection("creativeDrafts")\
            .where("userId", "==", uid)\
            .where("status", "in", ["DRAFT", "PENDING"])\
            .order_by("createdAt", direction=firestore.Query.DESCENDING)\
            .limit(50)
        
        drafts = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            drafts.append(data)
        
        return {"drafts": drafts}
    except Exception as e:
        logger.error(f"❌ Fetch My Drafts Error: {e}")
        return {"drafts": [], "error": str(e)}


@router.post("/{draft_id}/publish")
def publish_my_draft(draft_id: str, user: dict = Depends(verify_token)):
    """
    Allow OWNER to publish their own draft.
    
    Permission Logic:
    - Verify draft.userId == current_user.uid
    - If not owner → 403 Forbidden
    - If owner → update status to PUBLISHED
    """
    try:
        uid = user['uid']
        
        doc_ref = db.collection("creativeDrafts").document(draft_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        data = doc.to_dict()
        
        # OWNERSHIP CHECK - Core of Self-Approval Model
        if data.get("userId") != uid:
            logger.warning(f"⚠️ Unauthorized publish attempt: User {uid} tried to publish draft {draft_id} owned by {data.get('userId')}")
            raise HTTPException(status_code=403, detail="You can only publish your own creatives")
        
        # Check if already published
        if data.get("status") == "PUBLISHED":
            return {"status": "PUBLISHED", "message": "Draft is already published."}
        
        # Update to PUBLISHED
        doc_ref.update({
            "status": "PUBLISHED",
            "publishedAt": firestore.SERVER_TIMESTAMP,
            "publishedBy": user.get("email", uid)
        })
        
        # ATOMIC INCREMENT: Track ads_generated for user leaderboard (Admin Hub)
        try:
            user_ref = db.collection("users").document(uid)
            user_ref.update({
                "stats.ads_generated": firestore.Increment(1)
            })
            logger.info(f"📊 Incremented ads_generated for user {uid}")
        except Exception as stats_err:
            # Non-fatal - don't block publish if stats update fails
            logger.warning(f"⚠️ Failed to increment ads_generated for {uid}: {stats_err}")
        
        logger.info(f"✅ Creative {draft_id} self-published by owner {uid}")
        
        return {"status": "PUBLISHED", "message": "Creative published successfully."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Publish My Draft Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-published")
def get_my_published(user: dict = Depends(verify_token)):
    """
    Fetch current user's published creatives (status = PUBLISHED).
    Returns only creatives owned by the authenticated user.
    """
    try:
        uid = user['uid']
        
        # Query creativeDrafts collection for user's published creatives
        query = db.collection("creativeDrafts")\
            .where("userId", "==", uid)\
            .where("status", "==", "PUBLISHED")\
            .order_by("publishedAt", direction=firestore.Query.DESCENDING)\
            .limit(50)
        
        published = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            published.append(data)
        
        return {"published": published}
    except Exception as e:
        logger.error(f"❌ Fetch My Published Error: {e}")
        return {"published": [], "error": str(e)}

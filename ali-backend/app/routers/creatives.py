"""
Creative drafts endpoints for authenticated users.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import db, get_current_user_id

router = APIRouter()


@router.get("/my-drafts")
def get_my_drafts(user_id: str = Depends(get_current_user_id)) -> List[dict]:
    """
    Fetch current user's draft creatives (status IN [DRAFT, PENDING] or missing).
    Returns only creatives owned by the authenticated user.
    
    Note: Filtering and sorting done in Python to avoid Firestore compound index requirements.
    """
    try:
        # Query only by user_id to avoid compound index requirement
        docs = db.collection("creative_drafts").where("userId", "==", user_id).stream()
        
        # Convert to list of dicts
        all_docs = [doc.to_dict() for doc in docs]
        
        # V3.1 FIX: Return ALL drafts (including FAILED) so users can see failed generations
        # No status filtering - users need to see what failed to debug issues
        drafts = all_docs
        
        # Sort in Python by createdAt descending (use 0 for missing values for proper sorting)
        drafts.sort(key=lambda x: x.get("createdAt") or 0, reverse=True)
        
        # Return limited results
        return drafts[:50]
    except Exception as e:
        print(f"Error fetching drafts: {e}")
        return []


@router.get("/my-published")
def get_my_published(user_id: str = Depends(get_current_user_id)) -> List[dict]:
    """
    Fetch current user's published creatives (status = PUBLISHED).
    Returns only creatives owned by the authenticated user.
    
    Note: Filtering and sorting done in Python to avoid Firestore compound index requirements.
    """
    try:
        # Query only by user_id to avoid compound index requirement
        docs = db.collection("creative_drafts").where("userId", "==", user_id).stream()
        
        # Convert to list of dicts
        all_docs = [doc.to_dict() for doc in docs]
        
        # Filter in Python: keep only PUBLISHED items
        published = [d for d in all_docs if d.get("status") == "PUBLISHED"]
        
        # Sort in Python by publishedAt descending (handle missing values safely)
        published.sort(key=lambda x: x.get("publishedAt", ""), reverse=True)
        
        # Return limited results
        return published[:50]
    except Exception as e:
        print(f"Error fetching published: {e}")
        return []

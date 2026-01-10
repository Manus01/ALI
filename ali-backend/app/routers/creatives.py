"""
Creative drafts endpoints for authenticated users.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

from app.core.security import db, get_current_user_id

router = APIRouter()


@router.get("/my-drafts")
def get_my_drafts(user_id: str = Depends(get_current_user_id)) -> List[dict]:
    """
    Fetch current user's draft creatives (status IN [DRAFT, PENDING]).
    Returns only creatives owned by the authenticated user.
    """
    try:
        query = (
            db.collection("creativeDrafts")
            .where("userId", "==", user_id)
            .where("status", "in", ["DRAFT", "PENDING"])
            .order_by("createdAt", direction=firestore.Query.DESCENDING)
            .limit(50)
        )
        return [doc.to_dict() for doc in query.stream()]
    except Exception as e:
        print(f"Error: {e}")
        return []


@router.get("/my-published")
def get_my_published(user_id: str = Depends(get_current_user_id)) -> List[dict]:
    """
    Fetch current user's published creatives (status = PUBLISHED).
    Returns only creatives owned by the authenticated user.
    """
    try:
        query = (
            db.collection("creativeDrafts")
            .where("userId", "==", user_id)
            .where("status", "==", "PUBLISHED")
            .order_by("publishedAt", direction=firestore.Query.DESCENDING)
            .limit(50)
        )
        return [doc.to_dict() for doc in query.stream()]
    except Exception as e:
        print(f"Error: {e}")
        return []

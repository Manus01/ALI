import logging
from typing import Any, Dict, List, Optional

from app.core.security import db

logger = logging.getLogger(__name__)


class KnowledgeService:
    def __init__(self, firestore_client=None):
        self.db = firestore_client or db

    def query(self, brand_id: Optional[str], limit: int = 25) -> List[Dict[str, Any]]:
        if not brand_id or not self.db:
            return []

        try:
            packs_query = (
                self.db.collection("knowledge_packs")
                .where("userId", "==", brand_id)
                .limit(limit)
                .stream()
            )
        except Exception as exc:
            logger.warning("⚠️ KnowledgeService query failed: %s", exc)
            return []

        facts: List[Dict[str, Any]] = []
        for pack_doc in packs_query:
            pack_data = pack_doc.to_dict()
            for fact in pack_data.get("facts", []):
                facts.append(
                    {
                        "pack_id": pack_data.get("packId") or pack_doc.id,
                        "fact_id": fact.get("fact_id"),
                        "text": fact.get("text"),
                        "topic_tags": fact.get("topic_tags", pack_data.get("topicTags", [])),
                        "citation": fact.get("citation", {}),
                    }
                )
                if len(facts) >= limit:
                    return facts

        return facts


_knowledge_service: Optional[KnowledgeService] = None


def get_knowledge_service() -> KnowledgeService:
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service

"""
Knowledge Packs Service
Spec v2.5 Web Search §5: Truth Source JSON and Vector Retrieval

Provides:
1. Knowledge Pack CRUD operations
2. Fact extraction and citation management
3. Vector embedding storage and retrieval (RAG)
4. Semantic change detection for monitoring
"""
import os
import json
import logging
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum

try:
    from google.cloud import firestore
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    firestore = None

try:
    import vertexai
    from vertexai.language_models import TextEmbeddingModel
    VERTEX_AVAILABLE = True
except ImportError:
    VERTEX_AVAILABLE = False
    vertexai = None

logger = logging.getLogger(__name__)


class CredibilityTier(str, Enum):
    """Source credibility tiers per spec v2.5 §3."""
    AUTHORITATIVE = "AUTHORITATIVE"  # .gov, .edu, official brand sites
    ESTABLISHED = "ESTABLISHED"       # Major news, industry publications
    USER_GENERATED = "USER_GENERATED" # Social media, forums
    BLOCKED = "BLOCKED"               # Known misinformation sources


@dataclass
class CitationObject:
    """Citation with credibility scoring per spec v2.5 §5.1."""
    url: str
    domain: str
    title: str
    retrieved_at: str
    supporting_quote: str
    quote_context: str
    confidence_score: float = 0.0  # 0-100
    credibility_score: float = 0.0  # 0-100
    credibility_tier: str = CredibilityTier.USER_GENERATED.value
    author: Optional[str] = None
    published_at: Optional[str] = None
    license_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedFact:
    """Fact with citation and embedding reference."""
    fact_id: str
    text: str
    citation: CitationObject
    topic_tags: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    embedding_ref: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["citation"] = self.citation.to_dict()
        return data


@dataclass
class KnowledgePack:
    """Knowledge Pack / Truth Source JSON per spec v2.5 §5."""
    pack_id: str
    user_id: str
    topic_tags: List[str]
    created_at: str
    valid_until: str
    volatility_score: float = 50.0  # 0-100, how rapidly topic changes
    sources: List[Dict] = field(default_factory=list)
    facts: List[ExtractedFact] = field(default_factory=list)
    embeddings_ref: Optional[str] = None
    change_log: List[Dict] = field(default_factory=list)
    status: str = "ACTIVE"
    
    def to_dict(self) -> Dict[str, Any]:
        data = {
            "packId": self.pack_id,
            "userId": self.user_id,
            "topicTags": self.topic_tags,
            "createdAt": self.created_at,
            "validUntil": self.valid_until,
            "volatilityScore": self.volatility_score,
            "sources": self.sources,
            "facts": [f.to_dict() for f in self.facts],
            "embeddingsRef": self.embeddings_ref,
            "changeLog": self.change_log,
            "status": self.status,
        }
        return data
    
    def add_fact(self, fact: ExtractedFact):
        """Add a fact to the pack."""
        self.facts.append(fact)
    
    def is_expired(self) -> bool:
        """Check if pack needs refresh."""
        valid_until = datetime.fromisoformat(self.valid_until.replace("Z", "+00:00"))
        return datetime.utcnow() > valid_until.replace(tzinfo=None)


# Credibility scoring rules
CREDIBILITY_DOMAINS = {
    CredibilityTier.AUTHORITATIVE: [
        ".gov", ".edu", "who.int", "cdc.gov", "nih.gov",
        "nature.com", "science.org", "lancet.com",
    ],
    CredibilityTier.ESTABLISHED: [
        "reuters.com", "apnews.com", "bbc.com", "nytimes.com",
        "wsj.com", "economist.com", "forbes.com", "techcrunch.com",
        "hubspot.com", "marketingweek.com", "adweek.com",
    ],
    CredibilityTier.BLOCKED: [
        # Known misinformation domains would go here
    ],
}


class KnowledgePacksService:
    """
    Service for managing Knowledge Packs.
    Spec v2.5: Web Research & Monitoring
    """
    
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv(
            "GOOGLE_CLOUD_PROJECT", 
            "ali-platform-prod-73019"
        )
        
        self.db = None
        self.embedding_model = None
        
        if FIRESTORE_AVAILABLE:
            try:
                self.db = firestore.Client()
            except Exception as e:
                logger.warning(f"⚠️ Firestore init failed: {e}")
        
        if VERTEX_AVAILABLE:
            try:
                vertexai.init(project=self.project_id)
                self.embedding_model = TextEmbeddingModel.from_pretrained(
                    "textembedding-gecko@003"
                )
            except Exception as e:
                logger.warning(f"⚠️ Vertex AI embedding model init failed: {e}")
    
    def _generate_pack_id(self, user_id: str, topic: str) -> str:
        """Generate unique pack ID."""
        hash_input = f"{user_id}:{topic}:{datetime.utcnow().isoformat()}"
        return f"kp_{hashlib.sha256(hash_input.encode()).hexdigest()[:16]}"
    
    def _generate_fact_id(self, text: str) -> str:
        """Generate unique fact ID."""
        return f"fact_{hashlib.sha256(text.encode()).hexdigest()[:12]}"
    
    def get_credibility_tier(self, domain: str) -> CredibilityTier:
        """Determine credibility tier for a domain."""
        domain_lower = domain.lower()
        
        # Check blocked first
        for blocked in CREDIBILITY_DOMAINS.get(CredibilityTier.BLOCKED, []):
            if blocked in domain_lower:
                return CredibilityTier.BLOCKED
        
        # Check authoritative
        for auth in CREDIBILITY_DOMAINS.get(CredibilityTier.AUTHORITATIVE, []):
            if auth in domain_lower:
                return CredibilityTier.AUTHORITATIVE
        
        # Check established
        for est in CREDIBILITY_DOMAINS.get(CredibilityTier.ESTABLISHED, []):
            if est in domain_lower:
                return CredibilityTier.ESTABLISHED
        
        return CredibilityTier.USER_GENERATED
    
    def calculate_credibility_score(self, domain: str, tier: CredibilityTier) -> float:
        """Calculate credibility score 0-100."""
        base_scores = {
            CredibilityTier.AUTHORITATIVE: 90,
            CredibilityTier.ESTABLISHED: 70,
            CredibilityTier.USER_GENERATED: 40,
            CredibilityTier.BLOCKED: 0,
        }
        return base_scores.get(tier, 40)
    
    def create_citation(
        self,
        url: str,
        domain: str,
        title: str,
        supporting_quote: str,
        quote_context: str = "",
        author: Optional[str] = None,
        published_at: Optional[str] = None
    ) -> CitationObject:
        """Create a citation with auto-calculated credibility."""
        tier = self.get_credibility_tier(domain)
        score = self.calculate_credibility_score(domain, tier)
        
        return CitationObject(
            url=url,
            domain=domain,
            title=title,
            retrieved_at=datetime.utcnow().isoformat(),
            supporting_quote=supporting_quote,
            quote_context=quote_context,
            credibility_tier=tier.value,
            credibility_score=score,
            confidence_score=score * 0.9,  # Slightly lower than credibility
            author=author,
            published_at=published_at,
        )
    
    def create_fact(
        self,
        text: str,
        citation: CitationObject,
        topic_tags: List[str] = None
    ) -> ExtractedFact:
        """Create an extracted fact with citation."""
        return ExtractedFact(
            fact_id=self._generate_fact_id(text),
            text=text,
            citation=citation,
            topic_tags=topic_tags or [],
            confidence_score=citation.confidence_score,
        )
    
    def create_knowledge_pack(
        self,
        user_id: str,
        topic_tags: List[str],
        facts: List[ExtractedFact],
        sources: List[Dict],
        volatility_score: float = 50.0,
        validity_days: int = 7
    ) -> KnowledgePack:
        """Create a new Knowledge Pack."""
        pack_id = self._generate_pack_id(user_id, "|".join(topic_tags))
        
        valid_until = datetime.utcnow() + timedelta(days=validity_days)
        
        pack = KnowledgePack(
            pack_id=pack_id,
            user_id=user_id,
            topic_tags=topic_tags,
            created_at=datetime.utcnow().isoformat(),
            valid_until=valid_until.isoformat(),
            volatility_score=volatility_score,
            sources=sources,
            facts=facts,
        )
        
        # Save to Firestore
        if self.db:
            self.db.collection("knowledge_packs").document(pack_id).set(pack.to_dict())
            logger.info(f"✅ Created Knowledge Pack: {pack_id}")
        
        return pack
    
    def get_knowledge_pack(self, pack_id: str) -> Optional[KnowledgePack]:
        """Retrieve a Knowledge Pack by ID."""
        if not self.db:
            return None
        
        try:
            doc = self.db.collection("knowledge_packs").document(pack_id).get()
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            
            # Reconstruct pack from Firestore data
            facts = []
            for f_data in data.get("facts", []):
                citation = CitationObject(**f_data.get("citation", {}))
                fact = ExtractedFact(
                    fact_id=f_data["fact_id"],
                    text=f_data["text"],
                    citation=citation,
                    topic_tags=f_data.get("topic_tags", []),
                    confidence_score=f_data.get("confidence_score", 0),
                )
                facts.append(fact)
            
            return KnowledgePack(
                pack_id=data["packId"],
                user_id=data["userId"],
                topic_tags=data["topicTags"],
                created_at=data["createdAt"],
                valid_until=data["validUntil"],
                volatility_score=data.get("volatilityScore", 50),
                sources=data.get("sources", []),
                facts=facts,
                embeddings_ref=data.get("embeddingsRef"),
                change_log=data.get("changeLog", []),
                status=data.get("status", "ACTIVE"),
            )
        except Exception as e:
            logger.error(f"❌ Failed to get Knowledge Pack: {e}")
            return None
    
    def search_packs_by_topic(
        self,
        user_id: str,
        topic_tags: List[str],
        include_expired: bool = False
    ) -> List[Dict]:
        """Search for Knowledge Packs by topic."""
        if not self.db:
            return []
        
        try:
            query = self.db.collection("knowledge_packs")\
                .where("userId", "==", user_id)
            
            packs = []
            for doc in query.stream():
                data = doc.to_dict()
                
                # Check topic overlap
                pack_tags = set(data.get("topicTags", []))
                search_tags = set(topic_tags)
                
                if pack_tags & search_tags:  # Intersection
                    # Check expiry
                    if not include_expired:
                        valid_until = datetime.fromisoformat(
                            data.get("validUntil", "2000-01-01").replace("Z", "+00:00")
                        )
                        if datetime.utcnow() > valid_until.replace(tzinfo=None):
                            continue
                    
                    packs.append(data)
            
            return packs
        except Exception as e:
            logger.error(f"❌ Failed to search Knowledge Packs: {e}")
            return []
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts using Vertex AI."""
        if not self.embedding_model:
            logger.warning("⚠️ Embedding model not available")
            return []
        
        try:
            embeddings = self.embedding_model.get_embeddings(texts)
            return [e.values for e in embeddings]
        except Exception as e:
            logger.error(f"❌ Failed to generate embeddings: {e}")
            return []
    
    def semantic_search(
        self,
        user_id: str,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Semantic search across user's Knowledge Packs.
        Returns most relevant facts for the query.
        
        Note: Full vector search requires Firestore Vector Search or
        Vertex AI Matching Engine. This is a simplified implementation.
        """
        if not self.embedding_model:
            logger.warning("⚠️ Semantic search requires embedding model")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.generate_embeddings([query])
            if not query_embedding:
                return []
            
            query_vec = query_embedding[0]
            
            # Get all active packs for user
            if not self.db:
                return []
            
            packs = self.db.collection("knowledge_packs")\
                .where("userId", "==", user_id)\
                .where("status", "==", "ACTIVE")\
                .stream()
            
            # Score all facts
            scored_facts = []
            for pack_doc in packs:
                pack_data = pack_doc.to_dict()
                
                for fact_data in pack_data.get("facts", []):
                    # Generate fact embedding
                    fact_text = fact_data.get("text", "")
                    fact_embeddings = self.generate_embeddings([fact_text])
                    
                    if fact_embeddings:
                        # Cosine similarity
                        import math
                        fact_vec = fact_embeddings[0]
                        
                        dot_product = sum(a * b for a, b in zip(query_vec, fact_vec))
                        norm_a = math.sqrt(sum(a ** 2 for a in query_vec))
                        norm_b = math.sqrt(sum(b ** 2 for b in fact_vec))
                        
                        similarity = dot_product / (norm_a * norm_b) if norm_a and norm_b else 0
                        
                        scored_facts.append({
                            "text": fact_text,
                            "citation": fact_data.get("citation"),
                            "similarity": similarity,
                            "packId": pack_data.get("packId"),
                        })
            
            # Sort by similarity and return top K
            scored_facts.sort(key=lambda x: x["similarity"], reverse=True)
            return scored_facts[:top_k]
            
        except Exception as e:
            logger.error(f"❌ Semantic search failed: {e}")
            return []
    
    def detect_content_change(
        self,
        pack_id: str,
        new_facts: List[ExtractedFact]
    ) -> Dict[str, Any]:
        """
        Detect semantic changes between current and new facts.
        Spec v2.5 §8: Semantic Change Detection.
        """
        existing_pack = self.get_knowledge_pack(pack_id)
        if not existing_pack:
            return {"changes": [], "severity": "INFORMATIONAL"}
        
        existing_texts = {f.text for f in existing_pack.facts}
        new_texts = {f.text for f in new_facts}
        
        added = new_texts - existing_texts
        removed = existing_texts - new_texts
        
        changes = []
        severity = "INFORMATIONAL"
        
        if added:
            changes.append({
                "type": "ADDED",
                "count": len(added),
                "sample": list(added)[:3],
            })
        
        if removed:
            changes.append({
                "type": "REMOVED",
                "count": len(removed),
                "sample": list(removed)[:3],
            })
            
            # Removals may indicate outdated info - higher severity
            if len(removed) > len(existing_texts) * 0.3:
                severity = "IMPORTANT"
            if len(removed) > len(existing_texts) * 0.5:
                severity = "CRITICAL"
        
        return {
            "packId": pack_id,
            "changes": changes,
            "severity": severity,
            "detectedAt": datetime.utcnow().isoformat(),
        }


# Singleton instance
_kp_service: Optional[KnowledgePacksService] = None

def get_knowledge_packs_service() -> KnowledgePacksService:
    """Get or create singleton KnowledgePacksService."""
    global _kp_service
    if _kp_service is None:
        _kp_service = KnowledgePacksService()
    return _kp_service

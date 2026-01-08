"""
Canonical Ad Model Mapper Service
Spec v2.4 §5: Inputs & Data Normalization

This module provides:
1. Platform-specific field mapping to unified metrics
2. Canonical schema validation
3. Cross-platform metric normalization
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class AdPlatform(str, Enum):
    """Supported advertising platforms."""
    META = "meta"
    GOOGLE = "google"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"


@dataclass
class CanonicalAdRecord:
    """
    Canonical Ad Model - Unified schema for cross-platform comparison.
    Spec v2.4 §5.1: The Canonical Ad Model (Unified Schema)
    """
    record_id: str
    tenant_id: str
    user_id: str
    date: str  # YYYY-MM-DD
    platform: str
    
    # Unified metrics
    unified_cost: float = 0.0
    unified_impressions: int = 0
    unified_clicks: int = 0
    unified_conversions: int = 0
    
    # Calculated metrics
    unified_ctr: float = 0.0
    unified_cpc: float = 0.0
    unified_cpa: float = 0.0
    unified_roas: float = 0.0
    
    # Hierarchy mapping
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    adset_id: Optional[str] = None  # AdSet (Meta) / AdGroup (Google)
    adset_name: Optional[str] = None
    creative_id: Optional[str] = None
    creative_name: Optional[str] = None
    
    # Raw data for debugging
    raw_platform_data: Optional[Dict] = field(default_factory=dict)
    
    def calculate_derived_metrics(self):
        """Calculate CTR, CPC, CPA, ROAS from base metrics."""
        if self.unified_impressions > 0:
            self.unified_ctr = (self.unified_clicks / self.unified_impressions) * 100
        
        if self.unified_clicks > 0:
            self.unified_cpc = self.unified_cost / self.unified_clicks
        
        if self.unified_conversions > 0:
            self.unified_cpa = self.unified_cost / self.unified_conversions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for BigQuery insertion."""
        return {
            "record_id": self.record_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "date": self.date,
            "platform": self.platform,
            "unified_cost": self.unified_cost,
            "unified_impressions": self.unified_impressions,
            "unified_clicks": self.unified_clicks,
            "unified_conversions": self.unified_conversions,
            "unified_ctr": self.unified_ctr,
            "unified_cpc": self.unified_cpc,
            "unified_cpa": self.unified_cpa,
            "unified_roas": self.unified_roas,
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "adset_id": self.adset_id,
            "adset_name": self.adset_name,
            "creative_id": self.creative_id,
            "creative_name": self.creative_name,
            "raw_platform_data": self.raw_platform_data,
            "ingested_at": datetime.utcnow().isoformat(),
        }


# --- PLATFORM FIELD MAPPINGS ---

META_FIELD_MAP = {
    # Cost
    "spend": "unified_cost",
    "amount_spent": "unified_cost",
    # Impressions
    "impressions": "unified_impressions",
    # Clicks
    "clicks": "unified_clicks",
    "link_clicks": "unified_clicks",
    # Conversions - Meta uses various event names
    "conversions": "unified_conversions",
    "purchase": "unified_conversions",
    "complete_registration": "unified_conversions",
    "lead": "unified_conversions",
    # Hierarchy
    "campaign_id": "campaign_id",
    "campaign_name": "campaign_name",
    "adset_id": "adset_id",
    "adset_name": "adset_name",
    "ad_id": "creative_id",
    "ad_name": "creative_name",
}

GOOGLE_FIELD_MAP = {
    # Cost (Google uses micros, needs conversion)
    "cost_micros": "unified_cost",  # Divide by 1,000,000
    "cost": "unified_cost",
    # Impressions
    "impressions": "unified_impressions",
    # Clicks
    "clicks": "unified_clicks",
    # Conversions
    "conversions": "unified_conversions",
    "all_conversions": "unified_conversions",
    # Hierarchy
    "campaign_id": "campaign_id",
    "campaign_name": "campaign_name",
    "ad_group_id": "adset_id",
    "ad_group_name": "adset_name",
    "ad_id": "creative_id",
    "ad_name": "creative_name",
}

LINKEDIN_FIELD_MAP = {
    # Cost
    "costInLocalCurrency": "unified_cost",
    "totalCost": "unified_cost",
    # Impressions
    "impressions": "unified_impressions",
    # Clicks
    "clicks": "unified_clicks",
    "landingPageClicks": "unified_clicks",
    # Conversions
    "conversionValueInLocalCurrency": "unified_conversions",
    "externalWebsiteConversions": "unified_conversions",
    # Hierarchy
    "campaign": "campaign_id",
    "campaignName": "campaign_name",
    "creative": "creative_id",
}


class CanonicalAdMapper:
    """
    Maps platform-specific ad data to the Canonical Ad Model.
    Spec v2.4 §5: The Backend must map platform-specific fields to unified metrics.
    """
    
    def __init__(self, tenant_id: str, user_id: str):
        self.tenant_id = tenant_id
        self.user_id = user_id
    
    def _generate_record_id(self, platform: str, date: str, campaign_id: str, 
                           adset_id: Optional[str] = None) -> str:
        """Generate unique record ID for deduplication."""
        components = [self.user_id, platform, date, campaign_id, adset_id or ""]
        hash_input = "|".join(components)
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _extract_field(self, data: Dict, platform_map: Dict, target_field: str) -> Any:
        """Extract a field using platform-specific mapping."""
        for platform_field, mapped_field in platform_map.items():
            if mapped_field == target_field and platform_field in data:
                return data[platform_field]
        return None
    
    def map_meta_data(self, raw_data: List[Dict], date: str) -> List[CanonicalAdRecord]:
        """Map Meta (Facebook) Ads data to canonical model."""
        records = []
        
        for item in raw_data:
            campaign_id = item.get("campaign_id", "unknown")
            adset_id = item.get("adset_id")
            
            record = CanonicalAdRecord(
                record_id=self._generate_record_id(AdPlatform.META, date, campaign_id, adset_id),
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                date=date,
                platform=AdPlatform.META.value,
                unified_cost=float(item.get("spend", 0) or item.get("amount_spent", 0) or 0),
                unified_impressions=int(item.get("impressions", 0) or 0),
                unified_clicks=int(item.get("clicks", 0) or item.get("link_clicks", 0) or 0),
                unified_conversions=self._extract_meta_conversions(item),
                campaign_id=campaign_id,
                campaign_name=item.get("campaign_name"),
                adset_id=adset_id,
                adset_name=item.get("adset_name"),
                creative_id=item.get("ad_id"),
                creative_name=item.get("ad_name"),
                raw_platform_data=item,
            )
            record.calculate_derived_metrics()
            records.append(record)
        
        return records
    
    def _extract_meta_conversions(self, item: Dict) -> int:
        """Extract conversions from Meta's various action types."""
        # Meta stores conversions in 'actions' array with different action_type
        conversions = 0
        
        # Direct conversion field
        if "conversions" in item:
            conversions = int(item["conversions"])
        
        # Actions array (more detailed)
        for action in item.get("actions", []):
            action_type = action.get("action_type", "")
            if action_type in ["purchase", "complete_registration", "lead", "omni_purchase"]:
                conversions += int(action.get("value", 0))
        
        return conversions
    
    def map_google_data(self, raw_data: List[Dict], date: str) -> List[CanonicalAdRecord]:
        """Map Google Ads data to canonical model."""
        records = []
        
        for item in raw_data:
            campaign_id = item.get("campaign_id", "unknown")
            adgroup_id = item.get("ad_group_id")
            
            # Google uses cost_micros (divide by 1,000,000)
            cost = item.get("cost_micros", 0) or item.get("cost", 0)
            if "cost_micros" in item:
                cost = float(cost) / 1_000_000
            
            record = CanonicalAdRecord(
                record_id=self._generate_record_id(AdPlatform.GOOGLE, date, campaign_id, adgroup_id),
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                date=date,
                platform=AdPlatform.GOOGLE.value,
                unified_cost=float(cost),
                unified_impressions=int(item.get("impressions", 0) or 0),
                unified_clicks=int(item.get("clicks", 0) or 0),
                unified_conversions=int(item.get("conversions", 0) or item.get("all_conversions", 0) or 0),
                campaign_id=campaign_id,
                campaign_name=item.get("campaign_name"),
                adset_id=adgroup_id,
                adset_name=item.get("ad_group_name"),
                creative_id=item.get("ad_id"),
                creative_name=item.get("ad_name"),
                raw_platform_data=item,
            )
            record.calculate_derived_metrics()
            records.append(record)
        
        return records
    
    def map_linkedin_data(self, raw_data: List[Dict], date: str) -> List[CanonicalAdRecord]:
        """Map LinkedIn Ads data to canonical model."""
        records = []
        
        for item in raw_data:
            campaign_id = str(item.get("campaign", "unknown"))
            
            record = CanonicalAdRecord(
                record_id=self._generate_record_id(AdPlatform.LINKEDIN, date, campaign_id),
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                date=date,
                platform=AdPlatform.LINKEDIN.value,
                unified_cost=float(item.get("costInLocalCurrency", 0) or item.get("totalCost", 0) or 0),
                unified_impressions=int(item.get("impressions", 0) or 0),
                unified_clicks=int(item.get("clicks", 0) or item.get("landingPageClicks", 0) or 0),
                unified_conversions=int(item.get("externalWebsiteConversions", 0) or 0),
                campaign_id=campaign_id,
                campaign_name=item.get("campaignName"),
                creative_id=str(item.get("creative", "")) if item.get("creative") else None,
                raw_platform_data=item,
            )
            record.calculate_derived_metrics()
            records.append(record)
        
        return records
    
    def map_platform_data(self, platform: str, raw_data: List[Dict], date: str) -> List[CanonicalAdRecord]:
        """Route to appropriate platform mapper."""
        platform_lower = platform.lower()
        
        if platform_lower in ["meta", "facebook"]:
            return self.map_meta_data(raw_data, date)
        elif platform_lower in ["google", "google_ads"]:
            return self.map_google_data(raw_data, date)
        elif platform_lower == "linkedin":
            return self.map_linkedin_data(raw_data, date)
        else:
            logger.warning(f"⚠️ Unknown platform: {platform}")
            return []
    
    def aggregate_by_day(self, records: List[CanonicalAdRecord]) -> Dict[str, Dict]:
        """Aggregate records by date for daily summaries."""
        aggregated = {}
        
        for record in records:
            key = f"{record.platform}_{record.date}"
            
            if key not in aggregated:
                aggregated[key] = {
                    "platform": record.platform,
                    "date": record.date,
                    "total_cost": 0.0,
                    "total_impressions": 0,
                    "total_clicks": 0,
                    "total_conversions": 0,
                    "campaign_count": 0,
                }
            
            aggregated[key]["total_cost"] += record.unified_cost
            aggregated[key]["total_impressions"] += record.unified_impressions
            aggregated[key]["total_clicks"] += record.unified_clicks
            aggregated[key]["total_conversions"] += record.unified_conversions
            aggregated[key]["campaign_count"] += 1
        
        # Calculate derived metrics for aggregates
        for agg in aggregated.values():
            if agg["total_impressions"] > 0:
                agg["ctr"] = (agg["total_clicks"] / agg["total_impressions"]) * 100
            if agg["total_clicks"] > 0:
                agg["cpc"] = agg["total_cost"] / agg["total_clicks"]
            if agg["total_conversions"] > 0:
                agg["cpa"] = agg["total_cost"] / agg["total_conversions"]
        
        return aggregated


# --- CONVENIENCE FUNCTIONS ---

def normalize_platform_data(
    user_id: str,
    tenant_id: str,
    platform: str,
    raw_data: List[Dict],
    date: str
) -> List[Dict]:
    """
    Convenience function to normalize platform data to canonical model.
    Returns list of dicts ready for BigQuery insertion.
    """
    mapper = CanonicalAdMapper(tenant_id=tenant_id, user_id=user_id)
    records = mapper.map_platform_data(platform, raw_data, date)
    return [r.to_dict() for r in records]

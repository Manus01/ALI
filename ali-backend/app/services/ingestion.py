import os
import time
import csv
import logging
from typing import Any, Dict, Iterable, List, Optional
import requests

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)
# TikTok Ads integrated report endpoint
TIKTOK_REPORT_URL = "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/"

def tiktok_ads_source(access_token: str, advertiser_id: str):
    """
    DLT source factory for TikTok Ads reporting.
    Lazily imports dlt to avoid heavy startup cost.
    """
    try:
        import dlt
    except Exception as e:
        logger.error(f"❌ dlt library unavailable: {e}")
        raise RuntimeError(f"dlt library unavailable: {e}")

    @dlt.resource(write_disposition="append")
    def campaign_performance() -> Iterable[List[Dict[str, Any]]]:
        headers = {"Access-Token": access_token}
        page = 1
        page_size = 1000
        max_retries = 3
        total_pages: Optional[int] = None

        while True:
            body = {
                "advertiser_id": advertiser_id,
                "report_type": "BASIC",
                "data_level": "AUCTION_CAMPAIGN",
                "dimensions": ["campaign_id", "stat_time_day"],
                "metrics": ["spend", "cpc", "impressions", "ctr", "conversion"],
                "page": page,
                "page_size": page_size,
            }

            attempt = 0
            last_exc: Optional[Exception] = None
            
            while attempt < max_retries:
                try:
                    resp = requests.get(TIKTOK_REPORT_URL, headers=headers, params=body, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except requests.RequestException as exc:
                    last_exc = exc
                    attempt += 1
                    time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"Failed to fetch TikTok report: {last_exc}")

            records = []
            try:
                data_field = data.get("data") if isinstance(data, dict) else data
                if isinstance(data_field, dict):
                    records = data_field.get("list") or []
                    page_info = data_field.get("page_info") or {}
                    if total_pages is None:
                        total_pages = page_info.get("total_page")
                elif isinstance(data_field, list):
                    records = data_field
            except Exception:
                raise RuntimeError(f"Unexpected TikTok response format: {data!r}")

            yield records

            if total_pages is None or page >= int(total_pages):
                break
            page += 1
            time.sleep(0.2)

    return [campaign_performance]

def yandex_ads_source(access_token: str, client_login: str):
    """
    DLT source factory for Yandex.Direct reporting.
    Lazily imports dlt to avoid heavy startup cost.
    """
    try:
        import dlt
    except Exception as e:
        logger.error(f"❌ dlt library unavailable: {e}")
        raise RuntimeError(f"dlt library unavailable: {e}")

    YANDEX_REPORT_URL = "https://api.direct.yandex.com/json/v5/reports"

    @dlt.resource(write_disposition="append")
    def keyword_performance() -> Iterable[List[Dict[str, Any]]]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-Login": client_login,
            "Accept-Language": "en",
            "processingMode": "auto",
        }
        params = {
            "params": {
                "SelectionCriteria": {},
                "FieldNames": ["Date", "CampaignName", "Impressions", "Clicks", "Cost"],
                "ReportName": f"Report_{int(time.time())}",
                "ReportType": "CUSTOM_REPORT",
                "DateRangeType": "LAST_7_DAYS",
                "Format": "TSV",
                "IncludeVAT": "NO",
                "IncludeDiscount": "NO",
            }
        }

        max_retries = 6
        attempt = 0
        backoff = 2

        while True:
            try:
                resp = requests.post(YANDEX_REPORT_URL, headers=headers, json=params, timeout=60)
            except requests.RequestException as exc:
                attempt += 1
                if attempt >= max_retries:
                    raise RuntimeError(f"Network error: {exc}")
                time.sleep(backoff)
                backoff *= 2
                continue

            if resp.status_code in (201, 202):
                attempt += 1
                if attempt >= max_retries:
                    raise RuntimeError("Yandex report pending too long")
                retry_after = resp.headers.get("Retry-After")
                wait = int(retry_after) if retry_after else backoff
                time.sleep(wait)
                backoff *= 2
                continue

            if not resp.ok:
                raise RuntimeError(f"Yandex request failed: {resp.status_code}")

            text = resp.text
            if not text:
                yield []
                return

            lines = [ln for ln in text.splitlines() if ln.strip()]
            start_index = 0
            for i, line in enumerate(lines):
                if line.startswith("Date"):
                    start_index = i
                    break
            
            reader = csv.DictReader(lines[start_index:], delimiter="\t")
            records = []
            for row in reader:
                records.append({k: v for k, v in row.items()})

            yield records
            return

    return [keyword_performance]

def run_ingestion_pipeline(source_name: str, access_token: str, ad_account_id: str, user_id: str) -> dict:
    """
    Runs the pipeline and loads data into Firestore under the user's document.
    Ensures Firestore client is initialized only when called.
    """
    logger.info(f"🚀 Starting Ingestion for User: {user_id}...")
    
    # Lazy init of Firestore to prevent global client overhead at boot
    # Lazy init of Firestore to prevent global client overhead at boot
    from app.core.security import db as firestore_db
    # Remap to 'db' for local compatibility
    db = firestore_db
    
    if source_name == 'tiktok':
        data_generator = tiktok_ads_source(access_token, ad_account_id)
    elif source_name == 'yandex':
        data_generator = yandex_ads_source(access_token, ad_account_id) 
    else:
        raise ValueError("Unknown source")

    record_count = 0
    batch = db.batch()
    
    # pick the first dlt resource
    resource = list(data_generator)[0]
    
    for page in resource():
        for record in page:
            # Create unique ID. Fallback to random if fields missing.
            date_val = record.get('stat_time_day') or record.get('Date') or str(int(time.time()))
            camp_id = record.get('campaign_id') or record.get('CampaignName') or 'unknown'
            doc_id = f"{date_val}_{camp_id}".replace("/", "-")
            
            doc_ref = db.collection('users').document(user_id)\
                        .collection('campaign_performance').document(doc_id)
            
            batch.set(doc_ref, record)
            record_count += 1

            if record_count % 400 == 0: # Safe Firestore batch limit
                batch.commit()
                batch = db.batch()

    if record_count > 0:
        batch.commit()
        
    logger.info(f"✅ Ingested {record_count} records for {user_id}")
    return {"status": "success", "count": record_count}
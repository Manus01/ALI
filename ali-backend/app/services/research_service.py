import json
import os
import re
import logging
from datetime import datetime, timezone
from typing import Dict, List
from urllib.parse import quote_plus

import httpx
from google.cloud import storage

logger = logging.getLogger("ali_platform.services.research_service")


def scout_sources(topic: str, limit: int = 10) -> List[Dict[str, str]]:
    query = quote_plus(topic)
    url = f"https://duckduckgo.com/html/?q={query}"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers={"User-Agent": "ALI Research Bot"})
            response.raise_for_status()
    except Exception as e:
        logger.warning(f"Scout request failed: {e}")
        return []

    links = re.findall(r'href="(https?://[^"]+)"', response.text)
    sources = []
    for link in links:
        if "duckduckgo.com" in link:
            continue
        sources.append({"url": link})
        if len(sources) >= limit:
            break
    return sources


def deep_dive(urls: List[str]) -> List[Dict[str, str]]:
    results = []
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        for url in urls:
            try:
                response = client.get(url, headers={"User-Agent": "ALI Research Bot"})
                response.raise_for_status()
                html = response.text
                title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
                title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else url
                paragraph_matches = re.findall(r"<p[^>]*>(.*?)</p>", html, re.IGNORECASE | re.DOTALL)
                clean_paragraphs = [
                    re.sub(r"<[^>]+>", "", p).strip() for p in paragraph_matches
                ]
                facts = [p for p in clean_paragraphs if len(p.split()) > 6][:3]
                results.append({
                    "url": url,
                    "title": title,
                    "retrievedAt": datetime.now(timezone.utc).isoformat(),
                    "extractedFacts": facts
                })
            except Exception as e:
                logger.warning(f"Deep dive failed for {url}: {e}")
    return results


def store_evidence_bundle(bundle: Dict[str, any], bucket_name: str | None = None) -> str | None:
    bucket = bucket_name or os.getenv("GCS_BUCKET_NAME")
    if not bucket:
        logger.warning("GCS bucket not configured for evidence bundle storage.")
        return None
    try:
        storage_client = storage.Client()
        bucket_ref = storage_client.bucket(bucket)
        blob_name = f"evidence/{bundle.get('id', 'bundle')}-{int(datetime.now().timestamp())}.json"
        blob = bucket_ref.blob(blob_name)
        blob.upload_from_string(json.dumps(bundle, indent=2), content_type="application/json")
        return f"gs://{bucket}/{blob_name}"
    except Exception as e:
        logger.error(f"Evidence bundle storage failed: {e}")
        return None

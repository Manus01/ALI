import json
import os
import re
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List
from urllib.parse import quote_plus, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from google.cloud import storage

logger = logging.getLogger("ali_platform.services.research_service")

ALLOWLIST_DOMAINS = {d.strip() for d in os.getenv("RESEARCH_ALLOWLIST_DOMAINS", "").split(",") if d.strip()}
DENYLIST_DOMAINS = {d.strip() for d in os.getenv("RESEARCH_DENYLIST_DOMAINS", "").split(",") if d.strip()}
REQUEST_DELAY_SEC = float(os.getenv("RESEARCH_REQUEST_DELAY_SEC", "0.5"))


def _is_domain_allowed(url: str) -> bool:
    domain = urlparse(url).netloc.lower()
    if any(domain.endswith(deny) for deny in DENYLIST_DOMAINS):
        return False
    if ALLOWLIST_DOMAINS:
        return any(domain.endswith(allow) for allow in ALLOWLIST_DOMAINS)
    return True


def _is_allowed_by_robots(url: str) -> bool:
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = RobotFileParser()
        rp.set_url(f"{base}/robots.txt")
        rp.read()
        return rp.can_fetch("ALIResearchBot", url)
    except Exception as e:
        logger.debug(f"robots.txt check failed for {url}: {e}, allowing by default")
        return True


def _credibility_score(url: str) -> int:
    domain = urlparse(url).netloc.lower()
    if domain.endswith(".gov") or domain.endswith(".edu"):
        return 90
    if "wikipedia.org" in domain:
        return 70
    return 50


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
        if not _is_domain_allowed(link):
            continue
        sources.append({"url": link, "credibilityScore": _credibility_score(link)})
        if len(sources) >= limit:
            break
    return sources


def deep_dive(urls: List[str]) -> List[Dict[str, str]]:
    results = []
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        for url in urls:
            try:
                if not _is_domain_allowed(url):
                    continue
                if not _is_allowed_by_robots(url):
                    logger.info(f"Skipping due to robots.txt: {url}")
                    continue
                time.sleep(REQUEST_DELAY_SEC)
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
                    "extractedFacts": facts,
                    "credibilityScore": _credibility_score(url)
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

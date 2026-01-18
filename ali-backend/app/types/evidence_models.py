"""
Evidence Chain Models
Data models for the tamper-evident evidence artifact system.

Provides schemas for:
- EvidenceSource: Atomic unit of proof with collection metadata
- EvidenceItem: A claim/violation with linked sources
- EvidenceReport: Complete report with hash chain integrity
- EvidenceExportBundle: Manifest for exported evidence packages
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import hashlib


# =============================================================================
# ENUMS
# =============================================================================

class CollectionMethod(str, Enum):
    """How evidence was collected."""
    AUTOMATED_SCAN = "automated_scan"      # From brand monitoring scanner
    MANUAL_UPLOAD = "manual_upload"        # User-uploaded screenshot
    API_FETCH = "api_fetch"                # Direct API retrieval
    ARCHIVE_ORG = "archive_org"            # Wayback Machine capture


class EvidenceType(str, Enum):
    """Categories of evidence items."""
    MENTION = "mention"
    VIOLATION = "violation"
    DEEPFAKE = "deepfake"
    IMPERSONATION = "impersonation"
    HARASSMENT = "harassment"
    DEFAMATION = "defamation"
    MISINFORMATION = "misinformation"


# =============================================================================
# DEEPFAKE ANALYSIS SUMMARY (for embedding in EvidenceSource)
# =============================================================================

class DeepfakeAnalysisSummary(BaseModel):
    """
    Stable subset of DeepfakeAnalysis for embedding in EvidenceSource.
    
    Only includes fields that should affect hash integrity.
    Excludes volatile fields: progress_pct, started_at, job_status, raw_output
    """
    id: str = Field(..., description="Deepfake job ID (e.g., DFA-XXXXXX)")
    verdict: str = Field(..., description="likely_authentic, inconclusive, likely_manipulated, confirmed_synthetic")
    verdict_label: str = Field(..., description="Human-readable verdict with emoji")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    completed_at: Optional[str] = Field(None, description="ISO timestamp of completion")
    signals: List[Dict[str, Any]] = Field(default_factory=list, description="Top signals for display")
    user_explanation: Optional[str] = Field(None, description="Plain English explanation")
    
    class Config:
        use_enum_values = True


# =============================================================================
# HASHING UTILITIES
# =============================================================================

def compute_source_hash(
    raw_snippet: str, 
    url: str, 
    collected_at: str,
    deepfake_summary: Optional[Dict[str, Any]] = None
) -> str:
    """
    Compute tamper-evident hash for a single source.
    
    Hash = SHA-256(raw_snippet | url | collected_at | deepfake_stable_fields)
    
    Args:
        raw_snippet: The text content from the source
        url: The source URL
        collected_at: ISO format timestamp of collection
        deepfake_summary: Optional deepfake analysis summary (stable fields only)
    
    Returns:
        64-character hex string (SHA-256)
    
    Note:
        Deepfake stable fields included: verdict, confidence, completed_at
        These fields are immutable after analysis completion.
    """
    payload = f"{raw_snippet}|{url}|{collected_at}"
    
    # Include stable deepfake fields if present
    if deepfake_summary:
        stable_fields = (
            f"|{deepfake_summary.get('verdict', '')}"
            f"|{deepfake_summary.get('confidence', '')}"
            f"|{deepfake_summary.get('completed_at', '')}"
        )
        payload += stable_fields
    
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def compute_item_hash(claim_text: str, source_hashes: List[str]) -> str:
    """
    Compute tamper-evident hash for an evidence item.
    
    Hash = SHA-256(claim_text + "|" + sorted_source_hashes_joined)
    
    Args:
        claim_text: The claim or violation text
        source_hashes: List of source hashes (will be sorted for determinism)
    
    Returns:
        64-character hex string (SHA-256)
    """
    sorted_hashes = sorted(source_hashes)
    payload = f"{claim_text}|{'|'.join(sorted_hashes)}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def compute_report_hash(item_hashes: List[str]) -> str:
    """
    Compute tamper-evident hash for the entire report.
    
    Hash = SHA-256(sorted_item_hashes_joined)
    
    Args:
        item_hashes: List of item hashes (will be sorted for determinism)
    
    Returns:
        64-character hex string (SHA-256)
    """
    sorted_hashes = sorted(item_hashes)
    payload = '|'.join(sorted_hashes)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def verify_chain_integrity(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify the hash chain from sources -> items -> report.
    
    Traverses bottom-up, recomputes each hash, and compares against stored values.
    Any mismatch indicates potential tampering.
    
    Args:
        report: Dictionary containing the full EvidenceReport
    
    Returns:
        {"valid": bool, "errors": [...], "verified_at": str}
    """
    errors = []
    
    for item in report.get('items', []):
        # Verify each source hash
        source_hashes = []
        for source in item.get('sources', []):
            collected_at = source.get('collected_at', '')
            if isinstance(collected_at, datetime):
                collected_at = collected_at.isoformat()
            
            # Include deepfake analysis in hash computation if present
            deepfake_summary = source.get('deepfake_analysis')
            
            expected = compute_source_hash(
                source.get('raw_snippet', ''),
                source.get('url', ''),
                collected_at,
                deepfake_summary=deepfake_summary
            )
            actual = source.get('source_hash', '')
            if expected != actual:
                errors.append(f"Source {source.get('id', 'unknown')}: hash mismatch")
            source_hashes.append(actual)
        
        # Verify item hash
        expected_item = compute_item_hash(
            item.get('claim_text', ''),
            source_hashes
        )
        actual_item = item.get('item_hash', '')
        if expected_item != actual_item:
            errors.append(f"Item {item.get('id', 'unknown')}: hash mismatch")
    
    # Verify report hash
    item_hashes = [item.get('item_hash', '') for item in report.get('items', [])]
    expected_report = compute_report_hash(item_hashes)
    actual_report = report.get('report_hash', '')
    if expected_report != actual_report:
        errors.append("Report: hash mismatch")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "verified_at": datetime.utcnow().isoformat()
    }


# =============================================================================
# PII REDACTION
# =============================================================================

import re

PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
}


def redact_pii(text: str) -> str:
    """
    Replace PII with [REDACTED] placeholders.
    
    Currently handles: email addresses, phone numbers, SSNs.
    
    Args:
        text: Raw text that may contain PII
    
    Returns:
        Text with PII replaced by [REDACTED-TYPE] placeholders
    """
    if not text:
        return text
    
    redacted = text
    for pii_type, pattern in PII_PATTERNS.items():
        redacted = re.sub(pattern, f'[REDACTED-{pii_type.upper()}]', redacted, flags=re.IGNORECASE)
    return redacted


# =============================================================================
# EVIDENCE SOURCE - The atomic unit of proof
# =============================================================================

class EvidenceSource(BaseModel):
    """
    A single source backing an evidence item.
    
    Represents the raw data collected from a platform, including metadata
    about when and how it was captured for chain-of-custody purposes.
    """
    id: str = Field(..., description="Unique source ID (uuid)")
    item_id: str = Field(..., description="Parent EvidenceItem ID")
    platform: str = Field(..., description="Source platform (twitter, news, web, etc.)")
    url: str = Field(..., description="Original content URL")
    collected_at: datetime = Field(..., description="When this source was captured")
    raw_snippet: str = Field(..., description="Text excerpt from source")
    redacted_snippet: Optional[str] = Field(None, description="PII-redacted version")
    media_refs: List[str] = Field(default_factory=list, description="URLs to media files")
    screenshot_ref: Optional[str] = Field(None, description="GCS path to screenshot")
    method: CollectionMethod = Field(
        default=CollectionMethod.AUTOMATED_SCAN,
        description="How source was collected"
    )
    source_hash: str = Field(..., description="SHA-256(raw_snippet + url + collected_at + deepfake_stable_fields)")
    deepfake_analysis_id: Optional[str] = Field(None, description="Linked DeepfakeAnalysis job ID")
    deepfake_analysis: Optional[Dict[str, Any]] = Field(
        None, 
        description="Embedded deepfake analysis summary (if available and completed)"
    )
    
    class Config:
        use_enum_values = True


# =============================================================================
# EVIDENCE ITEM - A claim with linked sources
# =============================================================================

class EvidenceItem(BaseModel):
    """
    A single claim/violation in the report.
    
    Groups related sources that substantiate a specific claim, with
    an item-level hash aggregating all source hashes.
    """
    id: str = Field(..., description="Unique item ID (uuid)")
    report_id: str = Field(..., description="Parent EvidenceReport ID")
    type: EvidenceType = Field(..., description="Category of evidence")
    claim_text: str = Field(..., description="The specific claim or violation")
    severity: int = Field(..., ge=1, le=10, description="Severity score 1-10")
    sources: List[EvidenceSource] = Field(default_factory=list)
    item_hash: str = Field(..., description="SHA-256(claim_text + sorted(source_hashes))")
    
    class Config:
        use_enum_values = True


# =============================================================================
# EVIDENCE REPORT - The complete report document
# =============================================================================

class EvidenceReport(BaseModel):
    """
    Complete evidence report with chain integrity.
    
    The root document aggregating all evidence items and their sources,
    with a report-level hash that serves as the root of trust.
    """
    id: str = Field(..., description="Unique report ID (e.g., RPT-XXXXXX)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    brand_id: str = Field(..., description="User/brand identifier")
    time_range: Dict[str, Any] = Field(..., description="{'start': datetime, 'end': datetime}")
    version: int = Field(default=1, description="Report version for amendments")
    generated_by: str = Field(default="ali_protection_agent")
    report_purpose: str = Field(default="legal", description="legal, police, or platform")
    
    # Summary fields (AI-generated)
    executive_summary: str = Field(default="")
    pattern_analysis: Optional[str] = None
    potential_legal_violations: List[str] = Field(default_factory=list)
    recommended_next_steps: List[str] = Field(default_factory=list)
    
    # Evidence chain
    items: List[EvidenceItem] = Field(default_factory=list)
    
    # Integrity
    report_hash: str = Field(..., description="SHA-256(sorted(item_hashes))")
    hash_algorithm: str = Field(default="SHA-256")
    
    # Metadata
    legal_disclaimer: str = Field(default="")
    export_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


# =============================================================================
# EVIDENCE EXPORT BUNDLE
# =============================================================================

class EvidenceExportBundle(BaseModel):
    """
    Manifest for exported evidence package.
    
    Describes the contents of a ZIP or JSON bundle exported for
    legal/compliance use, including file checksums.
    """
    bundle_id: str = Field(..., description="Unique bundle ID (e.g., BDL-XXXXXX)")
    report_id: str = Field(..., description="Source report ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    format_version: str = Field(default="1.0")
    
    # Contents
    report_json_path: str = Field(default="report.json")
    sources_json_path: str = Field(default="sources.json")
    pdf_path: Optional[str] = Field(None, description="Path to PDF if generated")
    media_manifest: List[Dict[str, str]] = Field(
        default_factory=list,
        description="[{'source_id': '...', 'path': 'media/001.png'}]"
    )
    
    # Integrity
    bundle_hash: str = Field(..., description="SHA-256 of all file hashes combined")
    
    # Deepfake Analysis Summary
    deepfake_analyses_summary: Dict[str, Any] = Field(
        default_factory=lambda: {
            "total_analyzed": 0,
            "verdicts": {"authentic": 0, "manipulated": 0, "inconclusive": 0}
        },
        description="Summary of deepfake analyses included in this bundle"
    )
    
    # Legal metadata
    chain_of_custody: Dict[str, Any] = Field(default_factory=lambda: {
        "generated_by_user": "",
        "generated_at": "",
        "verification_url": ""
    })
    
    class Config:
        use_enum_values = True


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class GenerateEvidenceReportRequest(BaseModel):
    """Request body for generating an evidence report."""
    mentions: List[Dict[str, Any]] = Field(..., description="Evidence items to include")
    report_purpose: str = Field(default="legal", description="legal, police, or platform")
    include_screenshots: bool = Field(default=False)
    save_report: bool = Field(default=True, description="Persist to Firestore")


class ExportEvidenceBundleRequest(BaseModel):
    """Request body for exporting an evidence bundle."""
    format: str = Field(default="json", description="json or zip")
    include_pdf: bool = Field(default=False)


class VerifyEvidenceReportRequest(BaseModel):
    """Request body for verifying report integrity."""
    report: Optional[Dict[str, Any]] = Field(None, description="Direct payload")
    report_id: Optional[str] = Field(None, description="Or fetch by ID")

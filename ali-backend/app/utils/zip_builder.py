"""
Evidence Package ZIP Builder

Utility for building deterministic, tamper-evident ZIP evidence packages.

Features:
- Deterministic JSON serialization (sorted keys, consistent formatting)
- SHA-256 hash computation for each file
- Manifest generation with file checksums
- In-memory ZIP assembly (streaming can be added later for large packages)
"""
import json
import hashlib
import io
import os
import zipfile
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# SERIALIZATION UTILITIES
# =============================================================================

def serialize_deterministic(data: Any) -> str:
    """
    Serialize data to JSON with deterministic ordering.
    
    - Keys are sorted alphabetically at all levels
    - Consistent indentation (2 spaces)
    - No trailing whitespace
    
    Args:
        data: Any JSON-serializable object
        
    Returns:
        Deterministic JSON string
    """
    def _serialize_value(obj: Any) -> Any:
        """Recursively convert datetime objects and sort dicts."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: _serialize_value(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [_serialize_value(item) for item in obj]
        return obj
    
    normalized = _serialize_value(data)
    return json.dumps(normalized, indent=2, ensure_ascii=False, sort_keys=True)


def compute_file_hash(content: bytes) -> str:
    """
    Compute SHA-256 hash of file content.
    
    Args:
        content: Raw bytes of the file
        
    Returns:
        64-character hex string (SHA-256)
    """
    return hashlib.sha256(content).hexdigest()


# =============================================================================
# SOURCE FLATTENING
# =============================================================================

def flatten_sources(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract all EvidenceSource objects from a report into a flat list.
    
    Sources are sorted by:
    1. collected_at (ascending)
    2. url (alphabetically)
    
    This ensures deterministic ordering for consistent hashing.
    
    Args:
        report: Full EvidenceReport dictionary
        
    Returns:
        Sorted list of source dictionaries
    """
    sources = []
    
    for item in report.get('items', []):
        for source in item.get('sources', []):
            # Include parent references for traceability
            source_copy = dict(source)
            source_copy['_parent_item_id'] = item.get('id', '')
            sources.append(source_copy)
    
    # Sort by collected_at, then url for determinism
    def sort_key(s):
        collected_at = s.get('collected_at', '')
        if isinstance(collected_at, datetime):
            collected_at = collected_at.isoformat()
        return (collected_at, s.get('url', ''))
    
    return sorted(sources, key=sort_key)


# =============================================================================
# PROVENANCE DOCUMENT
# =============================================================================

def build_provenance_document(
    user_id: str,
    request_id: Optional[str] = None,
    environment: Optional[str] = None,
    app_version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build provenance metadata document.
    
    Args:
        user_id: ID or email of user exporting (or "unknown")
        request_id: X-Request-ID from middleware
        environment: Environment (staging/prod), defaults to ENVIRONMENT env var
        app_version: Optional app version or git commit
        
    Returns:
        Provenance document with export metadata
    """
    doc = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "exported_by": user_id if user_id else "unknown",
        "request_id": request_id or "",
        "environment": environment or os.environ.get("ENVIRONMENT", "unknown")
    }
    if app_version:
        doc["app_version"] = app_version
    return doc


# =============================================================================
# INTEGRITY DOCUMENT
# =============================================================================

def build_integrity_document(
    report: Dict[str, Any],
    request_id: Optional[str] = None,
    package_hash: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build the integrity verification document.
    
    Args:
        report: Full EvidenceReport dictionary
        request_id: Correlation ID for tracing
        package_hash: SHA-256 hash of manifest.json bytes
        
    Returns:
        Integrity document with verification status
    """
    return {
        "verified": report.get('chain_valid', False),
        "reportHash": report.get('report_hash', ''),
        "packageHash": package_hash or "",
        "algorithm": report.get('hash_algorithm', 'SHA-256'),
        "generatedAt": datetime.utcnow().isoformat(),
        "requestId": request_id or '',
        "itemCount": len(report.get('items', [])),
        "sourceCount": sum(
            len(item.get('sources', []))
            for item in report.get('items', [])
        ),
        "deepfakeAnalysesCount": sum(
            1 for item in report.get('items', [])
            for source in item.get('sources', [])
            if source.get('deepfake_analysis')
        )
    }


# =============================================================================
# MANIFEST BUILDER
# =============================================================================

def build_manifest(files: Dict[str, bytes]) -> Dict[str, Any]:
    """
    Build the manifest document listing all files and their checksums.
    
    Args:
        files: Dictionary mapping filename to content bytes
        
    Returns:
        Manifest document with file list and checksums
    """
    file_entries = []
    
    for filename, content in sorted(files.items()):
        file_entries.append({
            "path": filename,
            "sizeBytes": len(content),
            "sha256": compute_file_hash(content)
        })
    
    return {
        "version": "1.0",
        "createdAt": datetime.utcnow().isoformat(),
        "totalFiles": len(files),
        "files": file_entries
    }


# =============================================================================
# ZIP PACKAGE BUILDER
# =============================================================================

def build_evidence_package_zip(
    report: Dict[str, Any],
    user_id: str,
    request_id: Optional[str] = None,
    environment: Optional[str] = None,
    app_version: Optional[str] = None
) -> bytes:
    """
    Build a complete Evidence Package as a ZIP file.
    
    ZIP Contents:
    - report.json: Full EvidenceReport object
    - sources.json: Flattened list of all EvidenceSource objects
    - provenance.json: Export metadata (who, when, environment)
    - integrity.json: Chain verification status and package hash
    - manifest.json: File list with SHA-256 checksums
    
    Args:
        report: Full EvidenceReport dictionary
        user_id: ID of the user exporting (for audit logging)
        request_id: Correlation ID from X-Request-ID header
        environment: Environment (staging/prod), defaults to ENVIRONMENT env var
        app_version: Optional app version or git commit
        
    Returns:
        In-memory ZIP file as bytes
    """
    logger.info(f"📦 Building evidence package for report {report.get('id', 'unknown')}")
    
    # Step 1: Serialize deterministic content files
    report_json = serialize_deterministic(report).encode('utf-8')
    
    sources = flatten_sources(report)
    sources_json = serialize_deterministic(sources).encode('utf-8')
    
    # Step 2: Build provenance document
    provenance_doc = build_provenance_document(
        user_id=user_id,
        request_id=request_id,
        environment=environment,
        app_version=app_version
    )
    provenance_json = serialize_deterministic(provenance_doc).encode('utf-8')
    
    # Step 3: Build manifest from content files (excluding integrity which depends on manifest)
    content_files = {
        "report.json": report_json,
        "sources.json": sources_json,
        "provenance.json": provenance_json,
    }
    manifest_doc = build_manifest(content_files)
    manifest_json = serialize_deterministic(manifest_doc).encode('utf-8')
    
    # Step 4: Compute package_hash = SHA256(manifest.json bytes)
    package_hash = compute_file_hash(manifest_json)
    
    # Step 5: Build integrity document WITH package_hash
    integrity_doc = build_integrity_document(
        report=report,
        request_id=request_id,
        package_hash=package_hash
    )
    integrity_json = serialize_deterministic(integrity_doc).encode('utf-8')
    
    # Step 6: Assemble all files for ZIP
    all_files = {
        "integrity.json": integrity_json,
        "manifest.json": manifest_json,
        "provenance.json": provenance_json,
        "report.json": report_json,
        "sources.json": sources_json,
    }
    
    # Step 7: Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, content in sorted(all_files.items()):
            zf.writestr(filename, content)
    
    zip_bytes = zip_buffer.getvalue()
    
    logger.info(
        f"✅ Evidence package built: {len(zip_bytes)} bytes, "
        f"{len(all_files)} files, package_hash={package_hash[:16]}..., request_id={request_id}"
    )
    
    return zip_bytes


def get_export_filename(report: Dict[str, Any]) -> str:
    """
    Generate a safe filename for the evidence package.
    
    Args:
        report: Full EvidenceReport dictionary
        
    Returns:
        Filename like "evidence-RPT-ABC123.zip"
    """
    report_id = report.get('id', 'unknown')
    # Sanitize ID for filesystem safety
    safe_id = ''.join(c for c in report_id if c.isalnum() or c in '-_')
    return f"evidence-{safe_id}.zip"

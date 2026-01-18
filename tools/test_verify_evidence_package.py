"""
Unit tests for the Evidence Package Verifier.

Run with: python -m pytest test_verify_evidence_package.py -v
"""

import hashlib
import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from verify_evidence_package import (
    CheckResult,
    VerificationReport,
    compute_sha256,
    verify_package,
    verify_structure,
    verify_file_hashes,
    verify_package_hash,
    verify_report_hash,
    verify_provenance,
    format_report,
)


# =============================================================================
# FIXTURES: Create test ZIP files in memory
# =============================================================================

def serialize_deterministic(data) -> str:
    """Mirror the backend's deterministic JSON serialization."""
    def _serialize_value(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: _serialize_value(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [_serialize_value(item) for item in obj]
        return obj
    
    normalized = _serialize_value(data)
    return json.dumps(normalized, indent=2, ensure_ascii=False, sort_keys=True)


def create_valid_zip() -> bytes:
    """Create a valid evidence package ZIP in memory."""
    report = {
        "id": "RPT-TEST123",
        "chain_valid": True,
        "report_hash": "abc123def456789",
        "hash_algorithm": "SHA-256",
        "items": []
    }
    
    sources = []
    
    provenance = {
        "exported_at": "2026-01-18T03:00:00Z",
        "exported_by": "test-user@example.com",
        "request_id": "req-test-123",
        "environment": "testing",
        "app_version": "1.0.0-test"
    }
    
    # Serialize content files
    report_json = serialize_deterministic(report).encode('utf-8')
    sources_json = serialize_deterministic(sources).encode('utf-8')
    provenance_json = serialize_deterministic(provenance).encode('utf-8')
    
    # Build manifest
    content_files = {
        "report.json": report_json,
        "sources.json": sources_json,
        "provenance.json": provenance_json,
    }
    
    manifest = {
        "version": "1.0",
        "createdAt": "2026-01-18T03:00:00",
        "totalFiles": len(content_files),
        "files": []
    }
    
    for filename, content in sorted(content_files.items()):
        manifest["files"].append({
            "path": filename,
            "sizeBytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest()
        })
    
    manifest_json = serialize_deterministic(manifest).encode('utf-8')
    
    # Compute package hash
    package_hash = hashlib.sha256(manifest_json).hexdigest()
    
    # Build integrity document
    integrity = {
        "verified": True,
        "reportHash": report["report_hash"],
        "packageHash": package_hash,
        "algorithm": "SHA-256",
        "generatedAt": "2026-01-18T03:00:00",
        "requestId": "req-test-123",
        "itemCount": 0,
        "sourceCount": 0,
        "deepfakeAnalysesCount": 0
    }
    
    integrity_json = serialize_deterministic(integrity).encode('utf-8')
    
    # Assemble ZIP
    all_files = {
        "integrity.json": integrity_json,
        "manifest.json": manifest_json,
        "provenance.json": provenance_json,
        "report.json": report_json,
        "sources.json": sources_json,
    }
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, content in sorted(all_files.items()):
            zf.writestr(filename, content)
    
    return zip_buffer.getvalue()


def create_tampered_zip() -> bytes:
    """Create a ZIP where report.json has been tampered after manifest generation."""
    # Start with a valid ZIP structure
    report = {
        "id": "RPT-TAMPERED",
        "chain_valid": True,
        "report_hash": "original-hash",
        "hash_algorithm": "SHA-256",
        "items": []
    }
    
    sources = []
    
    provenance = {
        "exported_at": "2026-01-18T03:00:00Z",
        "exported_by": "attacker@example.com",
        "request_id": "req-fake",
        "environment": "testing"
    }
    
    # Serialize content files
    original_report_json = serialize_deterministic(report).encode('utf-8')
    sources_json = serialize_deterministic(sources).encode('utf-8')
    provenance_json = serialize_deterministic(provenance).encode('utf-8')
    
    # Build manifest with hashes of ORIGINAL files
    content_files = {
        "report.json": original_report_json,
        "sources.json": sources_json,
        "provenance.json": provenance_json,
    }
    
    manifest = {
        "version": "1.0",
        "createdAt": "2026-01-18T03:00:00",
        "totalFiles": len(content_files),
        "files": []
    }
    
    for filename, content in sorted(content_files.items()):
        manifest["files"].append({
            "path": filename,
            "sizeBytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest()
        })
    
    manifest_json = serialize_deterministic(manifest).encode('utf-8')
    package_hash = hashlib.sha256(manifest_json).hexdigest()
    
    integrity = {
        "verified": True,
        "reportHash": report["report_hash"],
        "packageHash": package_hash,
        "algorithm": "SHA-256",
        "generatedAt": "2026-01-18T03:00:00",
        "requestId": "req-fake",
        "itemCount": 0,
        "sourceCount": 0,
        "deepfakeAnalysesCount": 0
    }
    
    integrity_json = serialize_deterministic(integrity).encode('utf-8')
    
    # NOW TAMPER: modify report.json AFTER manifest was created
    tampered_report = dict(report)
    tampered_report["id"] = "RPT-HACKED!!!"
    tampered_report_json = serialize_deterministic(tampered_report).encode('utf-8')
    
    # Assemble ZIP with tampered report
    all_files = {
        "integrity.json": integrity_json,
        "manifest.json": manifest_json,
        "provenance.json": provenance_json,
        "report.json": tampered_report_json,  # TAMPERED!
        "sources.json": sources_json,
    }
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, content in sorted(all_files.items()):
            zf.writestr(filename, content)
    
    return zip_buffer.getvalue()


def create_missing_file_zip() -> bytes:
    """Create a ZIP missing the provenance.json file."""
    report = {
        "id": "RPT-INCOMPLETE",
        "chain_valid": True,
        "report_hash": "incomplete-hash",
        "hash_algorithm": "SHA-256",
        "items": []
    }
    
    sources = []
    
    report_json = serialize_deterministic(report).encode('utf-8')
    sources_json = serialize_deterministic(sources).encode('utf-8')
    
    manifest = {
        "version": "1.0",
        "createdAt": "2026-01-18T03:00:00",
        "totalFiles": 2,
        "files": [
            {"path": "report.json", "sizeBytes": len(report_json), "sha256": hashlib.sha256(report_json).hexdigest()},
            {"path": "sources.json", "sizeBytes": len(sources_json), "sha256": hashlib.sha256(sources_json).hexdigest()},
        ]
    }
    
    manifest_json = serialize_deterministic(manifest).encode('utf-8')
    package_hash = hashlib.sha256(manifest_json).hexdigest()
    
    integrity = {
        "verified": True,
        "reportHash": "incomplete-hash",
        "packageHash": package_hash,
        "algorithm": "SHA-256",
        "generatedAt": "2026-01-18T03:00:00",
        "requestId": "",
        "itemCount": 0,
        "sourceCount": 0,
        "deepfakeAnalysesCount": 0
    }
    
    integrity_json = serialize_deterministic(integrity).encode('utf-8')
    
    # Assemble ZIP WITHOUT provenance.json
    all_files = {
        "integrity.json": integrity_json,
        "manifest.json": manifest_json,
        "report.json": report_json,
        "sources.json": sources_json,
        # NO provenance.json!
    }
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, content in sorted(all_files.items()):
            zf.writestr(filename, content)
    
    return zip_buffer.getvalue()


# =============================================================================
# TESTS
# =============================================================================

class TestValidPackage:
    """Test that a properly constructed package passes all checks."""
    
    def test_valid_package_passes(self, tmp_path):
        """A correctly constructed package should pass all verifications."""
        zip_path = tmp_path / "valid.zip"
        zip_path.write_bytes(create_valid_zip())
        
        report = verify_package(zip_path)
        
        assert report.overall_passed, f"Expected PASS but got FAIL. Failed checks: {[c.name for c in report.checks if not c.passed]}"
        assert report.pass_count >= 5  # At least 5 checks should pass
        assert report.fail_count == 0
    
    def test_valid_package_format_output(self, tmp_path):
        """Formatted output should contain PASS indicator."""
        zip_path = tmp_path / "valid.zip"
        zip_path.write_bytes(create_valid_zip())
        
        report = verify_package(zip_path)
        output = format_report(report)
        
        assert "OVERALL: ✅ PASS" in output
        assert "valid.zip" in output


class TestTamperedPackage:
    """Test that tampered packages fail verification."""
    
    def test_tampered_file_fails(self, tmp_path):
        """A package with modified content should fail hash verification."""
        zip_path = tmp_path / "tampered.zip"
        zip_path.write_bytes(create_tampered_zip())
        
        report = verify_package(zip_path)
        
        assert not report.overall_passed, "Tampered package should fail"
        assert report.fail_count >= 1
        
        # Find the file hash check
        hash_check = next((c for c in report.checks if c.name == "FILE HASH VERIFICATION"), None)
        assert hash_check is not None
        assert not hash_check.passed, "File hash verification should fail for tampered file"
        assert "MISMATCH" in " ".join(hash_check.details)


class TestMissingFiles:
    """Test that packages with missing files fail verification."""
    
    def test_missing_file_fails(self, tmp_path):
        """A package missing required files should fail structure check."""
        zip_path = tmp_path / "incomplete.zip"
        zip_path.write_bytes(create_missing_file_zip())
        
        report = verify_package(zip_path)
        
        assert not report.overall_passed, "Package with missing files should fail"
        
        # Find the structure check
        structure_check = next((c for c in report.checks if c.name == "STRUCTURE CHECK"), None)
        assert structure_check is not None
        assert not structure_check.passed, "Structure check should fail for missing file"
        assert "provenance.json" in " ".join(structure_check.details).lower() or "missing" in structure_check.message.lower()


class TestHashUtilities:
    """Test low-level hash utilities."""
    
    def test_compute_sha256(self):
        """SHA-256 computation should match known values."""
        content = b"test content"
        result = compute_sha256(content)
        
        assert len(result) == 64  # SHA-256 = 64 hex chars
        assert result == hashlib.sha256(content).hexdigest()
    
    def test_sha256_deterministic(self):
        """Same input should always produce same hash."""
        content = b"deterministic test"
        hash1 = compute_sha256(content)
        hash2 = compute_sha256(content)
        
        assert hash1 == hash2


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_nonexistent_file(self, tmp_path):
        """Verifying a non-existent file should fail gracefully."""
        fake_path = tmp_path / "does_not_exist.zip"
        
        report = verify_package(fake_path)
        
        assert not report.overall_passed
        assert report.fail_count >= 1
    
    def test_not_a_zip(self, tmp_path):
        """Verifying a non-ZIP file should fail gracefully."""
        not_zip = tmp_path / "not_a_zip.zip"
        not_zip.write_text("This is not a ZIP file")
        
        report = verify_package(not_zip)
        
        assert not report.overall_passed
        assert any("not a valid ZIP" in c.message for c in report.checks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

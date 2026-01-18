#!/usr/bin/env python3
"""
Offline Evidence Package Verifier

Validates Evidence Package ZIP files without requiring external services.
Designed for legal/compliance staff with human-readable output.

Usage:
    python verify_evidence_package.py <path-to-evidence-package.zip>

Exit codes:
    0 = PASS (all verifications succeeded)
    1 = FAIL (one or more verifications failed)
    2 = ERROR (could not process the file)
"""

import argparse
import hashlib
import json
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# CONSTANTS
# =============================================================================

REQUIRED_FILES = [
    "report.json",
    "sources.json",
    "provenance.json",
    "manifest.json",
    "integrity.json",
]

PROVENANCE_REQUIRED_FIELDS = [
    "exported_at",
    "exported_by",
    "request_id",
    "environment",
]

VERSION = "1.0.0"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class CheckResult:
    """Result of a single verification check."""
    name: str
    passed: bool
    message: str
    details: List[str] = field(default_factory=list)


@dataclass
class VerificationReport:
    """Complete verification report."""
    package_path: str
    verified_at: str
    checks: List[CheckResult] = field(default_factory=list)
    
    @property
    def overall_passed(self) -> bool:
        return all(c.passed for c in self.checks)
    
    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)
    
    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)


# =============================================================================
# HASH UTILITIES
# =============================================================================

def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hash of bytes, returning 64-char hex string."""
    return hashlib.sha256(data).hexdigest()


# =============================================================================
# VERIFICATION LOGIC
# =============================================================================

def verify_structure(zf: zipfile.ZipFile) -> CheckResult:
    """Check that all required files exist in the ZIP."""
    file_list = zf.namelist()
    missing = [f for f in REQUIRED_FILES if f not in file_list]
    
    if missing:
        return CheckResult(
            name="STRUCTURE CHECK",
            passed=False,
            message=f"Missing {len(missing)} required file(s)",
            details=[f"Missing: {f}" for f in missing]
        )
    
    return CheckResult(
        name="STRUCTURE CHECK",
        passed=True,
        message=f"All {len(REQUIRED_FILES)} required files present",
        details=[f"Found: {f}" for f in REQUIRED_FILES]
    )


def verify_file_hashes(zf: zipfile.ZipFile) -> CheckResult:
    """Verify SHA-256 hashes of files listed in manifest.json."""
    try:
        manifest_bytes = zf.read("manifest.json")
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except Exception as e:
        return CheckResult(
            name="FILE HASH VERIFICATION",
            passed=False,
            message="Could not read manifest.json",
            details=[str(e)]
        )
    
    files_list = manifest.get("files", [])
    if not files_list:
        return CheckResult(
            name="FILE HASH VERIFICATION",
            passed=False,
            message="manifest.json contains no file entries",
            details=[]
        )
    
    details = []
    all_passed = True
    
    for file_entry in files_list:
        file_path = file_entry.get("path", "")
        expected_hash = file_entry.get("sha256", "")
        
        if not file_path or not expected_hash:
            details.append(f"⚠️  {file_path}: invalid manifest entry")
            continue
        
        try:
            file_bytes = zf.read(file_path)
            actual_hash = compute_sha256(file_bytes)
            
            if actual_hash == expected_hash:
                details.append(f"✅ {file_path}: MATCH ({actual_hash[:12]}...)")
            else:
                details.append(f"❌ {file_path}: MISMATCH")
                details.append(f"   Expected: {expected_hash}")
                details.append(f"   Actual:   {actual_hash}")
                all_passed = False
        except KeyError:
            details.append(f"❌ {file_path}: FILE NOT FOUND IN ZIP")
            all_passed = False
        except Exception as e:
            details.append(f"❌ {file_path}: ERROR - {e}")
            all_passed = False
    
    return CheckResult(
        name="FILE HASH VERIFICATION",
        passed=all_passed,
        message="All file hashes match" if all_passed else "One or more file hashes do not match",
        details=details
    )


def verify_package_hash(zf: zipfile.ZipFile) -> CheckResult:
    """Verify packageHash = SHA256(manifest.json bytes)."""
    try:
        manifest_bytes = zf.read("manifest.json")
        computed_hash = compute_sha256(manifest_bytes)
    except Exception as e:
        return CheckResult(
            name="PACKAGE HASH VERIFICATION",
            passed=False,
            message="Could not compute manifest hash",
            details=[str(e)]
        )
    
    try:
        integrity_bytes = zf.read("integrity.json")
        integrity = json.loads(integrity_bytes.decode("utf-8"))
        expected_hash = integrity.get("packageHash", "")
    except Exception as e:
        return CheckResult(
            name="PACKAGE HASH VERIFICATION",
            passed=False,
            message="Could not read integrity.json",
            details=[str(e)]
        )
    
    if not expected_hash:
        return CheckResult(
            name="PACKAGE HASH VERIFICATION",
            passed=False,
            message="integrity.json missing packageHash field",
            details=[]
        )
    
    if computed_hash == expected_hash:
        return CheckResult(
            name="PACKAGE HASH VERIFICATION",
            passed=True,
            message="Package hash matches manifest",
            details=[
                f"Computed: {computed_hash}",
                f"Expected: {expected_hash}",
                "Result: MATCH"
            ]
        )
    else:
        return CheckResult(
            name="PACKAGE HASH VERIFICATION",
            passed=False,
            message="Package hash does not match manifest",
            details=[
                f"Computed: {computed_hash}",
                f"Expected: {expected_hash}",
                "Result: MISMATCH - package may have been tampered with"
            ]
        )


def verify_report_hash(zf: zipfile.ZipFile) -> CheckResult:
    """Verify integrity.reportHash matches report.json.report_hash (if present)."""
    try:
        integrity_bytes = zf.read("integrity.json")
        integrity = json.loads(integrity_bytes.decode("utf-8"))
        integrity_report_hash = integrity.get("reportHash", "")
    except Exception as e:
        return CheckResult(
            name="REPORT HASH CHECK",
            passed=False,
            message="Could not read integrity.json",
            details=[str(e)]
        )
    
    try:
        report_bytes = zf.read("report.json")
        report = json.loads(report_bytes.decode("utf-8"))
        report_hash = report.get("report_hash", "")
    except Exception as e:
        return CheckResult(
            name="REPORT HASH CHECK",
            passed=False,
            message="Could not read report.json",
            details=[str(e)]
        )
    
    # If neither has a hash, that's acceptable (may be an older format)
    if not integrity_report_hash and not report_hash:
        return CheckResult(
            name="REPORT HASH CHECK",
            passed=True,
            message="No report hash present (acceptable for this package version)",
            details=["Neither integrity.json nor report.json contain a report hash"]
        )
    
    # If only one has a hash, that's a warning but not failure
    if not integrity_report_hash or not report_hash:
        return CheckResult(
            name="REPORT HASH CHECK",
            passed=True,
            message="Report hash partially present",
            details=[
                f"integrity.reportHash: {integrity_report_hash or '(empty)'}",
                f"report.report_hash: {report_hash or '(empty)'}",
                "Note: One field is empty; cross-validation skipped"
            ]
        )
    
    if integrity_report_hash == report_hash:
        return CheckResult(
            name="REPORT HASH CHECK",
            passed=True,
            message="Report hash matches across files",
            details=[
                f"integrity.reportHash: {integrity_report_hash[:16]}...",
                f"report.report_hash: {report_hash[:16]}...",
                "Result: MATCH"
            ]
        )
    else:
        return CheckResult(
            name="REPORT HASH CHECK",
            passed=False,
            message="Report hash mismatch",
            details=[
                f"integrity.reportHash: {integrity_report_hash}",
                f"report.report_hash: {report_hash}",
                "Result: MISMATCH - data integrity compromised"
            ]
        )


def verify_provenance(zf: zipfile.ZipFile) -> CheckResult:
    """Verify provenance.json has required fields."""
    try:
        provenance_bytes = zf.read("provenance.json")
        provenance = json.loads(provenance_bytes.decode("utf-8"))
    except Exception as e:
        return CheckResult(
            name="PROVENANCE VALIDATION",
            passed=False,
            message="Could not read provenance.json",
            details=[str(e)]
        )
    
    missing = [f for f in PROVENANCE_REQUIRED_FIELDS if f not in provenance]
    
    if missing:
        return CheckResult(
            name="PROVENANCE VALIDATION",
            passed=False,
            message=f"Missing {len(missing)} required field(s)",
            details=[f"Missing: {f}" for f in missing]
        )
    
    details = [
        f"exported_at: {provenance.get('exported_at', '(empty)')}",
        f"exported_by: {provenance.get('exported_by', '(empty)')}",
        f"request_id: {provenance.get('request_id', '(empty)')}",
        f"environment: {provenance.get('environment', '(empty)')}",
    ]
    
    if "app_version" in provenance:
        details.append(f"app_version: {provenance.get('app_version')}")
    
    return CheckResult(
        name="PROVENANCE VALIDATION",
        passed=True,
        message="All required provenance fields present",
        details=details
    )


def verify_evidence_chain(zf: zipfile.ZipFile) -> CheckResult:
    """Report on evidence chain status (limited offline verification)."""
    try:
        integrity_bytes = zf.read("integrity.json")
        integrity = json.loads(integrity_bytes.decode("utf-8"))
    except Exception as e:
        return CheckResult(
            name="EVIDENCE CHAIN",
            passed=False,
            message="Could not read integrity.json",
            details=[str(e)]
        )
    
    verified = integrity.get("verified", False)
    algorithm = integrity.get("algorithm", "unknown")
    item_count = integrity.get("itemCount", 0)
    source_count = integrity.get("sourceCount", 0)
    deepfake_count = integrity.get("deepfakeAnalysesCount", 0)
    
    status_str = "VALID" if verified else "INVALID"
    
    return CheckResult(
        name="EVIDENCE CHAIN",
        passed=True,  # This is informational - real chain validation requires backend
        message=f"Chain reported as {status_str} (verified at export time)",
        details=[
            f"Status: {'✅ VALID' if verified else '⚠️ INVALID'} (as recorded during export)",
            f"Algorithm: {algorithm}",
            f"Items: {item_count}",
            f"Sources: {source_count}",
            f"Deepfake analyses: {deepfake_count}",
            "",
            "⚠️ Note: Full cryptographic chain verification requires the original",
            "   backend system. This tool verifies only the file integrity and",
            "   package hashes, not the full evidence chain signature."
        ]
    )


# =============================================================================
# MAIN VERIFIER
# =============================================================================

def verify_package(zip_path: Path) -> VerificationReport:
    """Run all verification checks on an evidence package."""
    report = VerificationReport(
        package_path=str(zip_path),
        verified_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            report.checks.append(verify_structure(zf))
            report.checks.append(verify_file_hashes(zf))
            report.checks.append(verify_package_hash(zf))
            report.checks.append(verify_report_hash(zf))
            report.checks.append(verify_provenance(zf))
            report.checks.append(verify_evidence_chain(zf))
    except zipfile.BadZipFile:
        report.checks.append(CheckResult(
            name="ZIP VALIDITY",
            passed=False,
            message="File is not a valid ZIP archive",
            details=[]
        ))
    except FileNotFoundError:
        report.checks.append(CheckResult(
            name="FILE ACCESS",
            passed=False,
            message=f"File not found: {zip_path}",
            details=[]
        ))
    except Exception as e:
        report.checks.append(CheckResult(
            name="UNEXPECTED ERROR",
            passed=False,
            message=str(e),
            details=[]
        ))
    
    return report


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def format_report(report: VerificationReport) -> str:
    """Format verification report for human-readable console output."""
    lines = []
    width = 66
    
    # Header
    lines.append("╔" + "═" * width + "╗")
    lines.append("║" + "EVIDENCE PACKAGE VERIFICATION REPORT".center(width) + "║")
    lines.append("╠" + "═" * width + "╣")
    
    # Package info
    pkg_name = Path(report.package_path).name
    lines.append("║" + f" Package: {pkg_name}".ljust(width) + "║")
    lines.append("║" + f" Verified: {report.verified_at}".ljust(width) + "║")
    lines.append("║" + f" Verifier: v{VERSION}".ljust(width) + "║")
    lines.append("╠" + "═" * width + "╣")
    lines.append("")
    
    # Check results
    for check in report.checks:
        icon = "✅" if check.passed else "❌"
        lines.append(f"{icon} {check.name}")
        lines.append(f"   {check.message}")
        for detail in check.details:
            lines.append(f"   {detail}")
        lines.append("")
    
    # Overall result
    if report.overall_passed:
        result_line = "OVERALL: ✅ PASS"
    else:
        result_line = f"OVERALL: ❌ FAIL ({report.fail_count} check(s) failed)"
    
    lines.append("╔" + "═" * width + "╗")
    lines.append("║" + result_line.center(width) + "║")
    lines.append("╚" + "═" * width + "╝")
    
    return "\n".join(lines)


def format_json_report(report: VerificationReport) -> str:
    """Format verification report as JSON for programmatic consumption."""
    data = {
        "package_path": report.package_path,
        "verified_at": report.verified_at,
        "overall_passed": report.overall_passed,
        "pass_count": report.pass_count,
        "fail_count": report.fail_count,
        "checks": [
            {
                "name": c.name,
                "passed": c.passed,
                "message": c.message,
                "details": c.details
            }
            for c in report.checks
        ]
    }
    return json.dumps(data, indent=2)


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Verify an Evidence Package ZIP file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verify_evidence_package.py evidence-RPT-ABC123.zip
  python verify_evidence_package.py --json evidence-package.zip

Exit codes:
  0 = PASS (all verifications succeeded)
  1 = FAIL (one or more verifications failed)
  2 = ERROR (could not process the file)
        """
    )
    
    parser.add_argument(
        "zip_file",
        type=Path,
        help="Path to the evidence package ZIP file"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of human-readable format"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"verify_evidence_package v{VERSION}"
    )
    
    args = parser.parse_args()
    
    if not args.zip_file.exists():
        print(f"Error: File not found: {args.zip_file}", file=sys.stderr)
        sys.exit(2)
    
    if not args.zip_file.is_file():
        print(f"Error: Not a file: {args.zip_file}", file=sys.stderr)
        sys.exit(2)
    
    try:
        report = verify_package(args.zip_file)
        
        if args.json:
            print(format_json_report(report))
        else:
            print(format_report(report))
        
        sys.exit(0 if report.overall_passed else 1)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

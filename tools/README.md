# Evidence Package Verifier

Standalone offline tool for validating Evidence Package ZIP files.

## Prerequisites

- Python 3.8 or higher
- No external dependencies required (uses only Python standard library)

## Usage

```bash
python verify_evidence_package.py <path-to-zip>
```

### Options

| Flag | Description |
|------|-------------|
| `--json` | Output results as JSON instead of human-readable format |
| `--version` | Show version number |
| `--help` | Show help message |

### Examples

```bash
# Basic verification
python verify_evidence_package.py evidence-RPT-ABC123.zip

# JSON output (for automation)
python verify_evidence_package.py --json evidence-RPT-ABC123.zip > result.json
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | **PASS** – All verifications succeeded |
| 1 | **FAIL** – One or more verifications failed |
| 2 | **ERROR** – Could not process the file (not found, not a ZIP, etc.) |

## Sample Output

### Passing Verification

```
╔══════════════════════════════════════════════════════════════════╗
║            EVIDENCE PACKAGE VERIFICATION REPORT                  ║
╠══════════════════════════════════════════════════════════════════╣
║ Package: evidence-RPT-ABC123.zip                                 ║
║ Verified: 2026-01-18T03:30:00Z                                   ║
║ Verifier: v1.0.0                                                 ║
╠══════════════════════════════════════════════════════════════════╣

✅ STRUCTURE CHECK
   All 5 required files present

✅ FILE HASH VERIFICATION
   All file hashes match
   ✅ report.json: MATCH (abc123def456...)
   ✅ sources.json: MATCH (789abc012...)
   ✅ provenance.json: MATCH (345def678...)

✅ PACKAGE HASH VERIFICATION
   Package hash matches manifest
   Computed: a1b2c3d4e5f6...
   Expected: a1b2c3d4e5f6...
   Result: MATCH

✅ REPORT HASH CHECK
   Report hash matches across files

✅ PROVENANCE VALIDATION
   All required provenance fields present
   exported_at: 2026-01-18T01:15:00Z
   exported_by: user@example.com
   request_id: req-abc123
   environment: prod

✅ EVIDENCE CHAIN
   Chain reported as VALID (verified at export time)
   ⚠️ Note: Full chain verification requires original backend

╔══════════════════════════════════════════════════════════════════╗
║                     OVERALL: ✅ PASS                             ║
╚══════════════════════════════════════════════════════════════════╝
```

### Failing Verification (Tampered File)

```
╔══════════════════════════════════════════════════════════════════╗
║            EVIDENCE PACKAGE VERIFICATION REPORT                  ║
╠══════════════════════════════════════════════════════════════════╣
║ Package: tampered-evidence.zip                                   ║
║ Verified: 2026-01-18T03:30:00Z                                   ║
╠══════════════════════════════════════════════════════════════════╣

✅ STRUCTURE CHECK
   All 5 required files present

❌ FILE HASH VERIFICATION
   One or more file hashes do not match
   ❌ report.json: MISMATCH
      Expected: abc123def456...
      Actual:   999999999999...

...

╔══════════════════════════════════════════════════════════════════╗
║              OVERALL: ❌ FAIL (1 check(s) failed)                ║
╚══════════════════════════════════════════════════════════════════╝
```

## What Gets Verified

| Check | Description |
|-------|-------------|
| **Structure** | All 5 required files exist: `report.json`, `sources.json`, `provenance.json`, `manifest.json`, `integrity.json` |
| **File Hashes** | SHA-256 of each file matches what's recorded in `manifest.json` |
| **Package Hash** | `SHA256(manifest.json bytes)` matches `integrity.json.packageHash` |
| **Report Hash** | `integrity.json.reportHash` matches `report.json.report_hash` |
| **Provenance** | Required fields present: `exported_at`, `exported_by`, `request_id`, `environment` |
| **Evidence Chain** | Reports the chain validity status (full verification requires original backend) |

## Troubleshooting

### "File is not a valid ZIP archive"

The file may be corrupted or not a ZIP file. Try:
- Re-download the evidence package
- Check file extension is `.zip`

### "Missing required file(s)"

The ZIP is missing one or more required files. This indicates the package was not generated correctly or was modified after export.

### "Package hash does not match"

The `manifest.json` file has been modified after the package was created. This is a strong indicator of tampering.

### "File hash mismatch"

One or more files have different content than when they were exported. This could indicate:
- Data corruption
- Intentional tampering
- Incorrect re-packaging

### Limited Evidence Chain Verification

The tool reports the chain verification status that was recorded at export time. Full cryptographic chain verification (per-source hashes, per-item hashes) requires the original backend system. This offline tool verifies only file integrity and package hashes.

## Running Tests

From the `tools/` directory:

```bash
python -m pytest test_verify_evidence_package.py -v
```

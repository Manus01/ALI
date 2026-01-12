import copy
import re
from typing import Any, Dict, List, Tuple

CLAIM_PATTERNS = [
    {
        "pattern": r"\bguaranteed\b",
        "replacement": "designed to help",
        "reason": "Absolute guarantee claims require proof.",
    },
    {
        "pattern": r"\b100%\b",
        "replacement": "highly",
        "reason": "Absolute percentage claims require substantiation.",
    },
    {
        "pattern": r"\b#?1\b",
        "replacement": "leading",
        "reason": "Ranking claims require evidence.",
    },
    {
        "pattern": r"\bbest\b",
        "replacement": "top",
        "reason": "Superlative claims require proof.",
    },
]

TEXT_FIELDS = ["caption", "body", "headline", "headlines", "video_script"]


def _verify_claims_text(text: str) -> Dict[str, Any]:
    issues: List[Dict[str, str]] = []
    adjusted_text = text

    for rule in CLAIM_PATTERNS:
        if re.search(rule["pattern"], adjusted_text, re.IGNORECASE):
            issues.append({
                "pattern": rule["pattern"],
                "reason": rule["reason"],
            })
            adjusted_text = re.sub(
                rule["pattern"],
                rule["replacement"],
                adjusted_text,
                flags=re.IGNORECASE,
            )

    adjusted_text = adjusted_text.strip()

    return {
        "original": text,
        "adjusted": adjusted_text,
        "issues": issues,
        "adjusted_flag": adjusted_text != text,
    }


def verify_claims_for_blueprint(blueprint: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    adjusted_blueprint = copy.deepcopy(blueprint)
    channels_report: Dict[str, Any] = {}
    adjusted_fields_total = 0

    for channel, channel_payload in blueprint.items():
        if channel == "theme" or not isinstance(channel_payload, dict):
            continue

        channel_report: Dict[str, Any] = {
            "fields": {},
            "adjusted_fields": 0,
        }

        for field in TEXT_FIELDS:
            if field not in channel_payload:
                continue

            if isinstance(channel_payload[field], list):
                field_results = []
                adjusted_list = []
                for entry in channel_payload[field]:
                    if not isinstance(entry, str):
                        continue
                    result = _verify_claims_text(entry)
                    field_results.append(result)
                    adjusted_list.append(result["adjusted"])
                    if result["adjusted_flag"]:
                        channel_report["adjusted_fields"] += 1
                        adjusted_fields_total += 1
                channel_report["fields"][field] = field_results
                if adjusted_list:
                    adjusted_blueprint[channel][field] = adjusted_list
            elif isinstance(channel_payload[field], str):
                result = _verify_claims_text(channel_payload[field])
                channel_report["fields"][field] = result
                if result["adjusted_flag"]:
                    channel_report["adjusted_fields"] += 1
                    adjusted_fields_total += 1
                    adjusted_blueprint[channel][field] = result["adjusted"]

        if channel_report["fields"]:
            channels_report[channel] = channel_report

    summary = {
        "adjusted_fields_total": adjusted_fields_total,
        "channels_with_adjustments": len(
            [
                channel
                for channel, report in channels_report.items()
                if report.get("adjusted_fields")
            ]
        ),
    }

    return adjusted_blueprint, {"channels": channels_report, "summary": summary}


def run_qc_rubric(blueprint: Dict[str, Any], channel_specs: Dict[str, Any]) -> Dict[str, Any]:
    channels_report: Dict[str, Any] = {}
    total_issues = 0

    for channel, channel_payload in blueprint.items():
        if channel == "theme" or not isinstance(channel_payload, dict):
            continue

        text_limit = channel_specs.get(channel, {}).get("text_limit")
        text_value = (
            channel_payload.get("caption")
            or channel_payload.get("body")
            or " ".join(channel_payload.get("headlines", []) or [])
            or channel_payload.get("video_script")
            or ""
        )
        text_length = len(text_value)

        issues: List[str] = []
        status = "pass"

        if text_limit and text_length > text_limit:
            status = "warn"
            issues.append(
                f"Text length {text_length} exceeds limit {text_limit}. Consider shortening copy."
            )

        if not text_value.strip():
            status = "warn"
            issues.append("No copy was generated for this channel.")

        total_issues += len(issues)

        channels_report[channel] = {
            "status": status,
            "text_length": text_length,
            "text_limit": text_limit,
            "issues": issues,
        }

    summary = {
        "total_channels": len(channels_report),
        "issues_total": total_issues,
        "channels_with_issues": len(
            [channel for channel, report in channels_report.items() if report["issues"]]
        ),
    }

    return {"channels": channels_report, "summary": summary}

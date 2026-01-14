import re
from typing import Dict, List, Tuple

RISKY_PHRASES = [
    "guaranteed",
    "100%",
    "best",
    "number one",
    "#1",
    "cure",
    "instant",
    "perfect",
    "never",
    "always"
]

SAFE_REPLACEMENTS = {
    "guaranteed": "designed to help",
    "100%": "highly",
    "best": "leading",
    "number one": "top",
    "#1": "top",
    "cure": "support",
    "instant": "fast",
    "perfect": "polished",
    "never": "rarely",
    "always": "often"
}


def _collect_blocked_terms(claims_policy: Dict) -> List[str]:
    if not claims_policy:
        return []
    blocked = claims_policy.get("blocked_terms") or []
    banned = claims_policy.get("banned_phrases") or []
    return list({*blocked, *banned})


def verify_claims(text: str, claims_policy: Dict = None) -> Tuple[str, Dict]:
    if not text:
        return text, {
            "original_text": text,
            "rewritten_text": text,
            "flags": [],
            "blocked_terms": [],
            "changes_made": False
        }

    flags = []
    rewritten = text

    for phrase in RISKY_PHRASES:
        # Handle phrases with special characters (like "100%") that don't work well with \b
        escaped = re.escape(phrase)
        # If phrase contains non-word chars at boundaries, use lookahead/lookbehind or simpler match
        if not phrase[0].isalnum() or not phrase[-1].isalnum():
            pattern = escaped
        else:
            pattern = rf"\b{escaped}\b"
        if re.search(pattern, rewritten, flags=re.IGNORECASE):
            flags.append(phrase)
            replacement = SAFE_REPLACEMENTS.get(phrase, "designed to help")
            rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)

    blocked_terms = _collect_blocked_terms(claims_policy)
    for blocked in blocked_terms:
        if re.search(rf"\b{re.escape(blocked)}\b", rewritten, flags=re.IGNORECASE):
            flags.append(blocked)
            rewritten = re.sub(rf"\b{re.escape(blocked)}\b", "", rewritten, flags=re.IGNORECASE).strip()

    report = {
        "original_text": text,
        "rewritten_text": rewritten,
        "flags": flags,
        "blocked_terms": blocked_terms,
        "changes_made": rewritten != text
    }

    return rewritten, report

from typing import Dict, List


def _get_banned_phrases(brand_dna: Dict) -> List[str]:
    tone = brand_dna.get("tone_of_voice") or {}
    return tone.get("banned_phrases") or brand_dna.get("banned_phrases") or []


def evaluate_copy(channel: str, text: str, brand_dna: Dict, channel_spec: Dict) -> Dict:
    text = text or ""
    text_limit = channel_spec.get("text_limit") if channel_spec else None
    length_ok = True
    if text_limit:
        length_ok = len(text) <= text_limit

    banned_phrases = _get_banned_phrases(brand_dna)
    banned_hits = [phrase for phrase in banned_phrases if phrase.lower() in text.lower()]

    checks = {
        "text_length": {
            "limit": text_limit,
            "actual": len(text),
            "passes": length_ok
        },
        "banned_phrases": {
            "hits": banned_hits,
            "passes": len(banned_hits) == 0
        },
        "contrast": {
            "status": "not_evaluated",
            "passes": True
        },
        "text_fit": {
            "status": "not_evaluated",
            "passes": True
        }
    }

    requires_review = not (checks["text_length"]["passes"] and checks["banned_phrases"]["passes"])

    return {
        "channel": channel,
        "checks": checks,
        "requires_review": requires_review
    }

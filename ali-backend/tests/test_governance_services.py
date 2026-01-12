import pytest

from app.services.claims_verifier import verify_claims
from app.services.qc_rubric import evaluate_copy


def test_verify_claims_rewrites_and_flags():
    text = "Guaranteed 100% results, the best in class"
    claims_policy = {"blocked_terms": ["results"]}

    rewritten, report = verify_claims(text, claims_policy)

    assert "guaranteed" in report["flags"]
    assert "100%" in report["flags"]
    assert "best" in report["flags"]
    assert "results" in report["flags"]
    assert report["changes_made"] is True
    assert "guaranteed" not in rewritten.lower()
    assert "100%" not in rewritten
    assert "best" not in rewritten.lower()
    assert "results" not in rewritten.lower()


def test_verify_claims_handles_empty_text():
    rewritten, report = verify_claims("", {})

    assert rewritten == ""
    assert report["flags"] == []
    assert report["changes_made"] is False


@pytest.mark.parametrize(
    "text,limit,expected_pass",
    [
        ("short copy", 20, True),
        ("this copy is too long", 10, False),
    ],
)
def test_evaluate_copy_length_checks(text, limit, expected_pass):
    brand_dna = {"tone_of_voice": {"banned_phrases": []}}
    channel_spec = {"text_limit": limit}

    report = evaluate_copy("linkedin", text, brand_dna, channel_spec)

    assert report["checks"]["text_length"]["passes"] is expected_pass
    assert report["requires_review"] is (not expected_pass)


def test_evaluate_copy_banned_phrases():
    brand_dna = {"tone_of_voice": {"banned_phrases": ["free trial"]}}
    channel_spec = {"text_limit": 50}

    report = evaluate_copy("linkedin", "Get a free trial now", brand_dna, channel_spec)

    assert report["checks"]["banned_phrases"]["hits"] == ["free trial"]
    assert report["checks"]["banned_phrases"]["passes"] is False
    assert report["requires_review"] is True

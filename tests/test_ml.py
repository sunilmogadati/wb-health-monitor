"""Smoke tests for spec 002 that need no DB, no LLM key, and no modeling deps.

They guard the two things that must not regress: the brief is schema-valid, and its framing stays
honest (value-for-money, no blame language — spec SC-006 / Principle V).
"""
from __future__ import annotations

from ml.brief import CountryHealthBrief, Performance, build_brief, classify


def test_classify_bands() -> None:
    assert classify(2.0) is Performance.above
    assert classify(0.0) is Performance.near
    assert classify(-2.0) is Performance.below


def test_brief_fallback_is_valid_and_honest(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    brief = build_brief(
        country_code="NGA",
        country_name="Nigeria",
        year=2020,
        indicators={
            "health_spend_pct_gdp": 3.4,
            "gdp_per_capita": 2000.0,
            "internet_pct": 35.0,
            "fertility_rate": 5.2,
        },
        predicted=54.0,
        actual=53.1,
    )
    assert isinstance(brief, CountryHealthBrief)
    assert brief.residual == -0.9
    assert brief.performance_vs_spend is Performance.near
    # honest-modeling framing present; no blame/causal language
    assert "value-for-money" in brief.summary.lower()
    assert "fail" not in brief.summary.lower()

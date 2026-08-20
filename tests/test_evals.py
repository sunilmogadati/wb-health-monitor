"""Unit tests for the spec-008 deterministic checks + gate logic.

Pure and keyless — no DB, no LLM, no live stack (the same split as test_ml.py / test_insights.py):
these exercise the checkers with crafted fixtures so the free CI gate is itself tested (Principle
II). The live end-to-end run (evals.run against a populated API) runs in the stack, not here.
"""

from __future__ import annotations

from typing import Any

from evals import checks, run

# --- fixtures ---------------------------------------------------------------------------------

VALID_BRIEF: dict[str, Any] = {
    "country_code": "KEN",
    "country_name": "Kenya",
    "year": 2019,
    "indicators": {"health_spend_pct_gdp": 4.6},
    "predicted_life_expectancy": 62.0,
    "actual_life_expectancy": 66.0,
    "residual": 4.0,  # 66 - 62, band 1.5 -> "above"
    "performance_vs_spend": "above",
    "summary": "Kenya's outcome is above what its spending predicts.",
}

ASK_GROUNDED: dict[str, Any] = {
    "answer": "Based on the published mart: Kenya 2019 health_spend_pct_gdp=4.6.",
    "citations": [
        {"country_name": "Kenya", "year": 2019, "indicator": "health_spend_pct_gdp", "value": 4.6}
    ],
    "caveats": "Association with spending, not causation.",
}

ASK_DECLINE: dict[str, Any] = {
    "answer": "I can't answer that from the published data — no matching rows were found.",
    "citations": [],
    "caveats": "Association with spending, not causation.",
}

BANNED = ["failing", "worst", "to blame"]
LIFE_RANGE: dict[str, Any] = {"life_expectancy": [20.0, 95.0]}


# --- honest framing (Principle V) -------------------------------------------------------------

def test_no_banned_language_passes_on_clean_text() -> None:
    result = checks.no_banned_language("above what spending predicts", BANNED)
    assert result.passed


def test_no_banned_language_fails_on_blame() -> None:
    result = checks.no_banned_language("Kenya has the worst, failing health system", BANNED)
    assert not result.passed
    assert "worst" in result.detail and "failing" in result.detail


def test_find_banned_terms_is_case_insensitive() -> None:
    assert checks.find_banned_terms("A FAILING system", ["failing"]) == ["failing"]


# --- /ask -------------------------------------------------------------------------------------

def test_has_citations_passes_when_grounded() -> None:
    assert checks.has_citations(ASK_GROUNDED).passed


def test_has_citations_fails_on_decline() -> None:
    assert not checks.has_citations(ASK_DECLINE).passed


def test_decline_behaviour_matches_expectation() -> None:
    assert checks.decline_behaviour(ASK_DECLINE, should_decline=True).passed
    assert checks.decline_behaviour(ASK_GROUNDED, should_decline=False).passed


def test_decline_behaviour_flags_mismatch() -> None:
    # answered when it should have declined (out-of-scope) -> fail
    assert not checks.decline_behaviour(ASK_GROUNDED, should_decline=True).passed
    # declined when it should have answered -> fail
    assert not checks.decline_behaviour(ASK_DECLINE, should_decline=False).passed


# --- /brief schema + numbers ------------------------------------------------------------------

def test_brief_schema_valid_passes() -> None:
    assert checks.brief_schema_valid(VALID_BRIEF).passed


def test_brief_schema_valid_flags_missing_field() -> None:
    broken = {k: v for k, v in VALID_BRIEF.items() if k != "summary"}
    result = checks.brief_schema_valid(broken)
    assert not result.passed and "summary" in result.detail


def test_brief_schema_valid_rejects_bool_as_number() -> None:
    broken = {**VALID_BRIEF, "residual": True}
    assert not checks.brief_schema_valid(broken).passed


def test_brief_schema_valid_rejects_bad_band() -> None:
    broken = {**VALID_BRIEF, "performance_vs_spend": "best"}
    assert not checks.brief_schema_valid(broken).passed


def test_numbers_consistent_passes() -> None:
    assert checks.numbers_consistent(VALID_BRIEF, tolerance=0.02, band=1.5).passed


def test_numbers_consistent_fails_on_invented_residual() -> None:
    lying = {**VALID_BRIEF, "residual": 10.0}  # 10 != 66 - 62
    assert not checks.numbers_consistent(lying, tolerance=0.02, band=1.5).passed


def test_numbers_consistent_fails_on_wrong_band() -> None:
    # residual 0.5 is within the 1.5 band -> "near", but the payload claims "above"
    off = {**VALID_BRIEF, "predicted_life_expectancy": 65.5, "residual": 0.5}
    assert not checks.numbers_consistent(off, tolerance=0.02, band=1.5).passed


# --- data-quality gate ------------------------------------------------------------------------

def _rows(n: int, life: float = 60.0) -> list[dict[str, Any]]:
    return [{"life_expectancy": life, "fertility_rate": 4.0} for _ in range(n)]


def test_data_quality_passes_clean_pull() -> None:
    config = {"min_rows": 3, "max_null_rate": 0.0, "value_ranges": LIFE_RANGE}
    results = checks.data_quality(_rows(5), config)
    assert all(r.passed for r in results)


def test_data_quality_fails_too_few_rows() -> None:
    config = {"min_rows": 100, "max_null_rate": 0.0, "value_ranges": {}}
    results = checks.data_quality(_rows(5), config)
    assert any(r.name == "row_count" and not r.passed for r in results)


def test_data_quality_fails_out_of_range() -> None:
    config = {"min_rows": 1, "max_null_rate": 0.0, "value_ranges": LIFE_RANGE}
    results = checks.data_quality(_rows(3, life=300.0), config)
    assert any(r.name == "range:life_expectancy" and not r.passed for r in results)


def test_data_quality_fails_high_null_rate() -> None:
    config = {"min_rows": 1, "max_null_rate": 0.0, "value_ranges": LIFE_RANGE}
    rows = [{"life_expectancy": None}, {"life_expectancy": 60.0}]
    results = checks.data_quality(rows, config)
    assert any(r.name == "null_rate:life_expectancy" and not r.passed for r in results)


# --- champion / challenger --------------------------------------------------------------------

def test_should_promote_first_run_no_champion() -> None:
    assert checks.should_promote(challenger_rmse=5.0, champion_rmse=None, tolerance=0.3).passed


def test_should_promote_accepts_within_tolerance() -> None:
    assert checks.should_promote(challenger_rmse=3.5, champion_rmse=3.3, tolerance=0.3).passed


def test_should_promote_rejects_regression() -> None:
    assert not checks.should_promote(challenger_rmse=4.0, champion_rmse=3.3, tolerance=0.3).passed


# --- the runner's case wiring (no network) ----------------------------------------------------

def test_evaluate_case_grounded_ask_passes() -> None:
    thresholds = checks.load_thresholds()
    case = {"id": "x", "target": "ask", "expect": {"decline": False}}
    results = run.evaluate_case(ASK_GROUNDED, case, thresholds)
    assert all(r.passed for r in results)


def test_evaluate_case_flags_blame_in_brief() -> None:
    thresholds = checks.load_thresholds()
    blamey = {**VALID_BRIEF, "summary": "Kenya's failing system is the worst."}
    case = {"id": "y", "target": "brief", "expect": {}}
    results = run.evaluate_case(blamey, case, thresholds)
    assert not all(r.passed for r in results)


def test_load_thresholds_has_expected_keys() -> None:
    thresholds = checks.load_thresholds()
    for key in ("banned_language", "numbers_tolerance", "brief_band", "data_quality"):
        assert key in thresholds


def test_load_cases_are_wellformed() -> None:
    cases = run.load_cases()
    assert cases, "expected at least one eval case"
    for case in cases:
        assert case["target"] in {"ask", "brief"}
        assert "id" in case

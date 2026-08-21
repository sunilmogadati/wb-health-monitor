"""Unit tests for the spec-008 deterministic checks + gate logic.

Pure and keyless — no DB, no LLM, no live stack (the same split as test_ml.py / test_insights.py):
these exercise the checkers with crafted fixtures so the free CI gate is itself tested (Principle
II). The live end-to-end run (evals.run against a populated API) runs in the stack, not here.
"""

from __future__ import annotations

from typing import Any

from evals import checks, judge, run, select_model

# --- fixtures ---------------------------------------------------------------------------------

VALID_BRIEF: dict[str, Any] = {
    "country_code": "KEN",
    "country_name": "Kenya",
    "year": 2019,
    "indicators": {"health_spend_pct_gdp": 4.6},
    "predicted_life_expectancy": 62.0,
    "actual_life_expectancy": 66.0,
    "residual": 4.0,  # 66 - 62, band 1.5 -> "above_expected"
    "performance_vs_spend": "above_expected",
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


# --- statistical anomaly detection (domain-agnostic) ------------------------------------------

CAF_LE = [
    (2015, 51.9), (2016, 51.0), (2017, 45.2), (2018, 52.3),
    (2019, 31.5), (2020, 50.6), (2021, 40.3), (2022, 18.8),  # corrupted WB series (sawtooth)
]
KEN_LE = [
    (2015, 62.3), (2016, 62.5), (2017, 62.7), (2018, 62.8),
    (2019, 62.9), (2020, 61.6), (2021, 61.2), (2022, 63.5),  # smooth, real
]


def _series(code: str, pairs: list[tuple[int, float]]) -> list[dict[str, Any]]:
    return [{"country_code": code, "year": y, "life_expectancy": v} for y, v in pairs]


def test_robust_z_flags_far_outlier() -> None:
    vals = [62.0, 62.5, 63.0, 61.0, 62.8, 18.8]  # the last is the CAR-like error
    assert checks.robust_z_outliers(vals, threshold=3.5) == [5]


def test_robust_z_ignores_smooth_series() -> None:
    assert checks.robust_z_outliers([62.3, 62.5, 62.7, 62.8, 62.9, 63.5], threshold=3.5) == []


def test_robust_z_short_series_returns_empty() -> None:
    assert checks.robust_z_outliers([1.0, 2.0], threshold=3.5) == []


def test_detect_anomalies_flags_corrupted_country_only() -> None:
    rows = _series("CAF", CAF_LE) + _series("KEN", KEN_LE)
    config = {
        "columns": ["life_expectancy"],
        "robust_z_threshold": 3.5,
        "max_yoy_change": {"life_expectancy": 5.0},
    }
    flagged = checks.detect_anomalies(rows, config)
    assert {f["entity"] for f in flagged} == {"CAF"}  # never the clean control country
    assert "yoy_jump" in {f["reason"] for f in flagged}  # the sawtooth caught by volatility
    assert any(f["reason"] == "robust_z" and f["value"] == 18.8 for f in flagged)  # 18.8 caught too


def test_detect_anomalies_clean_data_no_flags() -> None:
    smooth = [(2015 + i, round(60.0 + 0.2 * i, 1)) for i in range(8)]  # 60.0..61.4, tiny steps
    rows = _series("KEN", smooth) + _series("TZA", [(y, round(v + 0.1, 1)) for y, v in smooth])
    config = {
        "columns": ["life_expectancy"],
        "robust_z_threshold": 3.5,
        "max_yoy_change": {"life_expectancy": 5.0},
    }
    assert checks.detect_anomalies(rows, config) == []


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


# --- LLM-as-judge (groundedness) --------------------------------------------------------------

def test_result_from_score_passes_above_floor() -> None:
    assert judge.result_from_score(0.9, 0.7, "supported").passed


def test_result_from_score_fails_below_floor() -> None:
    result = judge.result_from_score(0.4, 0.7, "unsupported")
    assert not result.passed
    assert "0.40" in result.detail


def test_judge_available_reflects_env(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert judge.judge_available() is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert judge.judge_available() is True


def test_judge_never_vacuous_pass_when_unavailable(monkeypatch) -> None:
    # No key → the judge can't run, but it must FAIL "not evaluated", never silently pass (FR-004).
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = judge.judge_groundedness("q", "an answer", [], floor=0.7)
    assert not result.passed
    assert "not evaluated" in result.detail


def test_run_judge_off_by_default() -> None:
    # evaluate_case with run_judge=False (the free PR gate) adds no groundedness check.
    thresholds = checks.load_thresholds()
    case = {"id": "x", "target": "ask", "expect": {"decline": False}}
    results = run.evaluate_case(ASK_GROUNDED, case, thresholds)
    assert all(r.name != "groundedness" for r in results)


# --- FR-012 expected key-facts (deterministic) ------------------------------------------------

def test_answer_contains_any_passes_when_a_key_fact_is_present() -> None:
    result = checks.answer_contains_any("Kenya's life expectancy is increasing.", ["increas"])
    assert result.passed


def test_answer_contains_any_fails_on_a_grounded_row_dump() -> None:
    # The exact regression: a grounded dump with none of the direction words → fails (SC-008).
    dump = "Based on the published mart: Kenya 2015 life_expectancy=62.3; Kenya 2022 =63.5."
    result = checks.answer_contains_any(dump, ["increas", "rising", "rose"])
    assert not result.passed


def test_answer_contains_any_empty_options_is_a_pass() -> None:
    assert checks.answer_contains_any("anything", []).passed


def test_ask_case_with_missing_key_fact_fails_the_case() -> None:
    thresholds = checks.load_thresholds()
    expect = {"decline": False, "contains_any": ["increas"]}
    case = {"id": "trend", "target": "ask", "expect": expect}
    dump = {"answer": "Kenya 2015 =62.3; 2022 =63.5.", "citations": [{"x": 1}], "caveats": ""}
    # run_judge=True = the "a real model answered" regime where key-facts are asserted (FR-012).
    results = run.evaluate_case(dump, case, thresholds, run_judge=True)
    assert any(r.name == "answer_contains" and not r.passed for r in results)


# --- FR-013 helpfulness judge -----------------------------------------------------------------

def test_helpfulness_result_carries_its_dimension() -> None:
    result = judge.result_from_score(0.9, 0.7, "direct answer", dimension="helpfulness")
    assert result.name == "helpfulness"
    assert result.passed


def test_judge_helpfulness_never_vacuous_pass_when_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = judge.judge_helpfulness("q", "a row dump", floor=0.7)
    assert not result.passed
    assert "not evaluated" in result.detail


# --- FR-014 LLM champion/challenger selection rule --------------------------------------------

def test_select_prefers_lowest_cost_among_qualified() -> None:
    rows = [
        {"model": "cheap", "quality": 0.9, "price_out": 5.0, "latency_s": 3.0},
        {"model": "pricey", "quality": 0.95, "price_out": 25.0, "latency_s": 1.0},
    ]
    assert select_model.select(rows, quality_floor=0.8)["model"] == "cheap"


def test_select_breaks_ties_on_latency() -> None:
    rows = [
        {"model": "slow", "quality": 0.9, "price_out": 5.0, "latency_s": 4.0},
        {"model": "fast", "quality": 0.9, "price_out": 5.0, "latency_s": 1.0},
    ]
    assert select_model.select(rows, quality_floor=0.8)["model"] == "fast"


def test_select_falls_back_to_best_quality_when_none_clear_the_floor() -> None:
    rows = [
        {"model": "a", "quality": 0.5, "price_out": 1.0, "latency_s": 1.0},
        {"model": "b", "quality": 0.7, "price_out": 25.0, "latency_s": 9.0},
    ]
    assert select_model.select(rows, quality_floor=0.8)["model"] == "b"

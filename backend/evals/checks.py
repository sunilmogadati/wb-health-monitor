"""Deterministic evaluation checks (spec 008) — the free CI gate.

Pure functions over response payloads (plain dicts as returned by the API). No DB, no LLM, no
network — so they run on every PR with no key and are unit-testable with crafted fixtures. Each
checker returns a :class:`CheckResult`; a case passes when every applicable checker passes.

Scope here is *deterministic* only: schema/shape, citations, decline behaviour,
numbers-match-source, and the honest-framing (no causal/blame) rule (Principle V, FR-003).
Groundedness — the one fuzzy dimension — is the throttled LLM-as-judge, kept out of this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

THRESHOLDS_PATH = Path(__file__).resolve().parent / "thresholds.json"

# The contract every /brief payload must satisfy (mirrors ml.brief.CountryHealthBrief without
# importing it, so the checker stays dependency-free for the keyless CI gate).
BRIEF_REQUIRED: dict[str, type | tuple[type, ...]] = {
    "country_code": str,
    "country_name": str,
    "year": int,
    "indicators": dict,
    "predicted_life_expectancy": (int, float),
    "actual_life_expectancy": (int, float),
    "residual": (int, float),
    "performance_vs_spend": str,
    "summary": str,
}
# Matches ml.brief.Performance enum values (the /brief schema).
PERFORMANCE_BANDS = {"above_expected", "near_expected", "below_expected"}


@dataclass(frozen=True)
class CheckResult:
    """One deterministic check's outcome. ``passed`` gates; ``detail`` explains a failure."""

    name: str
    passed: bool
    detail: str


def load_thresholds(path: Path = THRESHOLDS_PATH) -> dict[str, Any]:
    """Load the single thresholds/config file (FR-010)."""
    data: dict[str, Any] = json.loads(path.read_text())
    return data


# --- honest framing (Principle V) -------------------------------------------------------------

def find_banned_terms(text: str, banned: list[str]) -> list[str]:
    """Return the banned terms present in ``text`` (case-insensitive)."""
    low = text.lower()
    return sorted({term for term in banned if term.lower() in low})


def no_banned_language(text: str, banned: list[str]) -> CheckResult:
    """No causal/blame or judgement wording in model-facing text (Principle V, FR-003/SC-004)."""
    hits = find_banned_terms(text, banned)
    if hits:
        return CheckResult("no_banned_language", False, f"banned terms present: {', '.join(hits)}")
    return CheckResult("no_banned_language", True, "no banned terms")


# --- /ask (InsightResponse: answer, citations[], caveats) -------------------------------------

def is_decline(ask_response: dict[str, Any]) -> bool:
    """A /ask answer is a decline when it is grounded in zero citations."""
    citations = ask_response.get("citations") or []
    return len(citations) == 0


def has_citations(ask_response: dict[str, Any]) -> CheckResult:
    """A grounded /ask answer must cite at least one mart row (FR-002)."""
    if is_decline(ask_response):
        return CheckResult("has_citations", False, "no citations (answer is a decline)")
    return CheckResult("has_citations", True, f"{len(ask_response['citations'])} citation(s)")


def answer_contains_any(text: str, options: list[str]) -> CheckResult:
    """The answer must contain at least one expected key-fact substring (FR-012).

    Catches a *grounded-but-empty/wrong* answer that the citation/decline checks miss: a trend
    question whose answer is a raw row dump never contains "increasing"/"rising". Case-insensitive
    substring match; empty ``options`` is a pass (nothing asserted).
    """
    if not options:
        return CheckResult("answer_contains", True, "no key-facts asserted")
    low = text.lower()
    hits = [o for o in options if o.lower() in low]
    if hits:
        return CheckResult("answer_contains", True, f"found {hits[0]!r}")
    return CheckResult("answer_contains", False, f"none of {options} present in the answer")


def decline_behaviour(ask_response: dict[str, Any], should_decline: bool) -> CheckResult:
    """Assert /ask declines exactly when the case says it should (out-of-scope/unanswerable)."""
    declined = is_decline(ask_response)
    if declined == should_decline:
        verb = "declined" if declined else "answered"
        return CheckResult("decline_behaviour", True, f"{verb} as expected")
    expected = "a decline" if should_decline else "an answer"
    got = "a decline" if declined else "an answer"
    return CheckResult("decline_behaviour", False, f"expected {expected}, got {got}")


# --- /brief (CountryHealthBrief) --------------------------------------------------------------

def brief_schema_valid(brief: dict[str, Any]) -> CheckResult:
    """The /brief payload matches the required contract (fields present + typed) (FR-002)."""
    missing = [key for key in BRIEF_REQUIRED if key not in brief]
    if missing:
        return CheckResult("brief_schema_valid", False, f"missing fields: {', '.join(missing)}")
    wrong = [
        key
        for key, expected in BRIEF_REQUIRED.items()
        # bool is an int subclass; reject it where a number is expected via the isinstance below.
        if not isinstance(brief[key], expected) or isinstance(brief[key], bool)
    ]
    if wrong:
        return CheckResult("brief_schema_valid", False, f"wrong type: {', '.join(wrong)}")
    band = brief["performance_vs_spend"]
    if band not in PERFORMANCE_BANDS:
        return CheckResult("brief_schema_valid", False, f"performance_vs_spend '{band}' not a band")
    return CheckResult("brief_schema_valid", True, "schema valid")


def _band_for(residual: float, band: float) -> str:
    if residual > band:
        return "above_expected"
    if residual < -band:
        return "below_expected"
    return "near_expected"


def numbers_consistent(brief: dict[str, Any], tolerance: float, band: float) -> CheckResult:
    """residual == actual - predicted (±tol) and the band matches the residual (FR-002).

    Catches an LLM that invents numbers instead of echoing the model's output.
    """
    try:
        predicted = float(brief["predicted_life_expectancy"])
        actual = float(brief["actual_life_expectancy"])
        residual = float(brief["residual"])
    except (KeyError, TypeError, ValueError) as exc:
        return CheckResult("numbers_consistent", False, f"unreadable numbers: {exc}")

    if abs(residual - (actual - predicted)) > tolerance:
        return CheckResult(
            "numbers_consistent",
            False,
            f"residual {residual} != actual {actual} - predicted {predicted}",
        )
    expected_band = _band_for(residual, band)
    got_band = brief.get("performance_vs_spend")
    if got_band != expected_band:
        return CheckResult(
            "numbers_consistent",
            False,
            f"band '{got_band}' != '{expected_band}' for residual {residual}",
        )
    return CheckResult("numbers_consistent", True, "numbers echo the model")


# --- data-quality gate (pipeline, FR-007) -----------------------------------------------------

def data_quality(rows: list[dict[str, Any]], config: dict[str, Any]) -> list[CheckResult]:
    """Gate the incoming pull before it reaches the mart: row count, value ranges, null rate.

    ``rows`` are feature rows (country-year dicts). Returns one result per rule; any failure should
    halt the pipeline (SC-003).
    """
    results: list[CheckResult] = []

    min_rows = int(config.get("min_rows", 0))
    results.append(
        CheckResult("row_count", len(rows) >= min_rows, f"{len(rows)} rows (min {min_rows})")
    )

    ranges: dict[str, list[float]] = config.get("value_ranges", {})
    max_null_rate = float(config.get("max_null_rate", 0.0))
    for column, (low, high) in ranges.items():
        values = [r.get(column) for r in rows]
        present = [v for v in values if v is not None]
        null_rate = 1.0 - (len(present) / len(values)) if values else 1.0
        if null_rate > max_null_rate:
            results.append(
                CheckResult(f"null_rate:{column}", False, f"{null_rate:.2%} > {max_null_rate:.2%}")
            )
            continue
        out_of_range = [v for v in present if not (low <= float(v) <= high)]
        detail = "in range" if not out_of_range else f"{len(out_of_range)} outside [{low}, {high}]"
        results.append(CheckResult(f"range:{column}", not out_of_range, detail))
    return results


# --- statistical anomaly detection (domain-agnostic, no hand-set ranges) ----------------------

def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def robust_z_outliers(values: list[float], threshold: float = 3.5) -> list[int]:
    """Indices of values whose robust z-score exceeds ``threshold`` (median + MAD).

    Robust z = 0.6745 * (x - median) / MAD, MAD = median(|x - median|); no distribution assumed. It
    flags values far from the bulk **without any hand-set range** — the domain-agnostic catch for
    features nobody has intuition about. Falls back to standard z when MAD is 0.
    """
    if len(values) < 3:
        return []
    med = _median(values)
    mad = _median([abs(v - med) for v in values])
    if mad > 0:
        scores = [0.6745 * (v - med) / mad for v in values]
    else:
        mean = sum(values) / len(values)
        std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
        if std == 0:
            return []
        scores = [(v - mean) / std for v in values]
    return [i for i, s in enumerate(scores) if abs(s) > threshold]


def detect_anomalies(rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Flag anomalous cells with two domain-agnostic detectors (spec 008, question-4 upgrade).

    1. **Population robust-z** — a value far from the column's bulk. Apply only to
       **bounded/unimodal** columns (``robust_z_columns``); on a skewed level variable like GDP it
       false-positives on genuinely rich/poor entities, so leave those out.
    2. **Per-entity year-over-year volatility** — a value that jumps implausibly vs its OWN history
       (catches a smoothed series that sawtooths, regardless of the absolute magnitude).

    Returns one record per flag: ``{entity, year, column, value, reason}``. Used to *filter* bad
    rows and to drive the systemic *tripwire* (halt only when the flagged fraction is large).
    """
    entity_key = config.get("entity_key", "country_code")
    year_key = config.get("year_key", "year")
    z_threshold = float(config.get("robust_z_threshold", 3.5))
    flagged: list[dict[str, Any]] = []

    for col in config.get("robust_z_columns", config.get("columns", [])):
        present = [(r, float(r[col])) for r in rows if r.get(col) is not None]
        vals = [v for _, v in present]
        for i in robust_z_outliers(vals, z_threshold):
            row = present[i][0]
            flagged.append(
                {
                    "entity": row.get(entity_key),
                    "year": row.get(year_key),
                    "column": col,
                    "value": present[i][1],
                    "reason": "robust_z",
                }
            )

    for col, limit in config.get("max_yoy_change", {}).items():
        by_entity: dict[Any, list[dict[str, Any]]] = {}
        for r in rows:
            if r.get(col) is not None:
                by_entity.setdefault(r.get(entity_key), []).append(r)
        for entity, ent_rows in by_entity.items():
            ordered = sorted(ent_rows, key=lambda r: r[year_key])
            prev: float | None = None
            for r in ordered:
                value = float(r[col])
                if prev is not None and abs(value - prev) > float(limit):
                    flagged.append(
                        {
                            "entity": entity,
                            "year": r[year_key],
                            "column": col,
                            "value": value,
                            "reason": "yoy_jump",
                        }
                    )
                prev = value
    return flagged


def range_flags(rows: list[dict[str, Any]], ranges: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-row static range violations (the hand-set bounds), as anomaly records (spec 008)."""
    flagged: list[dict[str, Any]] = []
    for row in rows:
        for col, bounds in ranges.items():
            value = row.get(col)
            if value is not None and not (float(bounds[0]) <= float(value) <= float(bounds[1])):
                flagged.append(
                    {
                        "entity": row.get("country_code"),
                        "year": row.get("year"),
                        "column": col,
                        "value": value,
                        "reason": "range",
                    }
                )
    return flagged


# --- champion / challenger (model promotion gate, FR-006) -------------------------------------

def should_promote(
    challenger_rmse: float, champion_rmse: float | None, tolerance: float
) -> CheckResult:
    """Promote the challenger only if its CV RMSE is not worse than the champion past ``tolerance``.

    First run (no champion) always promotes. Lower RMSE is better, so a challenger is acceptable
    when ``challenger_rmse <= champion_rmse + tolerance`` (SC-002).
    """
    if champion_rmse is None:
        return CheckResult("should_promote", True, "no champion yet — challenger becomes champion")
    if challenger_rmse <= champion_rmse + tolerance:
        return CheckResult(
            "should_promote",
            True,
            f"challenger {challenger_rmse:.3f} <= champion {champion_rmse:.3f} + {tolerance:.3f}",
        )
    return CheckResult(
        "should_promote",
        False,
        f"regressed: {challenger_rmse:.3f} > {champion_rmse:.3f} + {tolerance:.3f}",
    )

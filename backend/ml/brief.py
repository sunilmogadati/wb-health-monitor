"""Country Health Brief — structured LLM output (spec 002, FR-007/008/009).

``CountryHealthBrief`` is the validated Pydantic contract. ``build_brief()`` fills it: with an
Anthropic API key it asks Claude for the summary (STUDENT TODO), otherwise it falls back to a
deterministic template so tests and offline dev pass. Framing is value-for-money — an association
with spending, NOT causation or blame (Principle V). Do not add causal/ranking language.
"""
from __future__ import annotations

import os
from enum import Enum

from pydantic import BaseModel, Field


class Performance(str, Enum):
    above = "above_expected"
    near = "near_expected"
    below = "below_expected"


class CountryHealthBrief(BaseModel):
    """The validated shape every brief must take — no free-text-only responses (FR-007)."""

    country_code: str
    country_name: str
    year: int
    indicators: dict[str, float | None]
    predicted_life_expectancy: float
    actual_life_expectancy: float
    residual: float = Field(
        description="actual - predicted life expectancy; the value-for-money signal (association, not causal)"
    )
    performance_vs_spend: Performance
    summary: str


def classify(residual: float, band: float = 1.5) -> Performance:
    """Above/near/below what spending + context predict — a benchmark band, not a grade."""
    if residual > band:
        return Performance.above
    if residual < -band:
        return Performance.below
    return Performance.near


def _template_summary(name: str, year: int, perf: Performance, residual: float) -> str:
    direction = {
        Performance.above: "above",
        Performance.near: "about at",
        Performance.below: "below",
    }[perf]
    return (
        f"In {year}, {name}'s life expectancy is {direction} what its health spending and context "
        f"would predict (residual {residual:+.1f} years). This is a value-for-money benchmark — an "
        f"association with spending, not a causal or performance judgement."
    )


def build_brief(
    *,
    country_code: str,
    country_name: str,
    year: int,
    indicators: dict[str, float | None],
    predicted: float,
    actual: float,
) -> CountryHealthBrief:
    """Assemble a validated brief. Deterministic by default; LLM-narrated when a key is set."""
    residual = actual - predicted
    perf = classify(residual)
    summary = _template_summary(country_name, year, perf, residual)

    if os.getenv("ANTHROPIC_API_KEY"):
        # STUDENT TODO (FR-007): call Claude with STRUCTURED OUTPUT validated against
        # CountryHealthBrief (anthropic SDK `.parse` / tool schema). Ground every number in
        # `indicators` / `predicted` / `actual`; keep the value-for-money framing; make no causal or
        # blame claim. On ANY error, keep the deterministic `summary` below (FR-008 — never crash CI).
        pass

    return CountryHealthBrief(
        country_code=country_code,
        country_name=country_name,
        year=year,
        indicators=indicators,
        predicted_life_expectancy=round(predicted, 1),
        actual_life_expectancy=round(actual, 1),
        residual=round(residual, 1),
        performance_vs_spend=perf,
        summary=summary,
    )

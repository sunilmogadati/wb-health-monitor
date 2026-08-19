"""Country Health Brief — structured LLM output (spec 002, FR-007/008/009).

``CountryHealthBrief`` is the validated Pydantic contract. ``build_brief()`` fills it: with an
Anthropic API key it asks Claude for the summary (STUDENT TODO), otherwise it falls back to a
deterministic template so tests and offline dev pass. Framing is value-for-money — an association
with spending, NOT causation or blame (Principle V). Do not add causal/ranking language.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

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
        description=(
            "actual - predicted life expectancy; the value-for-money signal "
            "(association, not causal)"
        )
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


def _fallback_brief(
    *,
    country_code: str,
    country_name: str,
    year: int,
    indicators: dict[str, float | None],
    predicted: float,
    actual: float,
    residual: float,
    perf: Performance,
    summary: str,
) -> CountryHealthBrief:
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


def _contains_unsafe_framing(summary: str) -> bool:
    banned = ("caused by", "causes", "because of", "failed", "failing", "blame")
    lower = summary.lower()
    return any(term in lower for term in banned)


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
        try:
            from langchain_anthropic import ChatAnthropic

            model = ChatAnthropic(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
                temperature=0,
            )
            structured_model = model.with_structured_output(CountryHealthBrief)
            result: Any = structured_model.invoke(
                [
                    (
                        "system",
                        "You write concise, data-grounded country health briefs. Use only "
                        "the supplied numbers. Frame residuals as value-for-money "
                        "benchmarks: association, not causation or blame.",
                    ),
                    (
                        "human",
                        "\n".join(
                            [
                                "Build a schema-valid CountryHealthBrief.",
                                f"country_code: {country_code}",
                                f"country_name: {country_name}",
                                f"year: {year}",
                                f"indicators: {indicators}",
                                f"predicted_life_expectancy: {predicted:.4f}",
                                f"actual_life_expectancy: {actual:.4f}",
                                f"residual: {residual:.4f}",
                                f"performance_vs_spend: {perf.value}",
                                "The summary must be one sentence and include the phrase "
                                "value-for-money.",
                            ]
                        ),
                    ),
                ]
            )
            llm_brief = (
                result
                if isinstance(result, CountryHealthBrief)
                else CountryHealthBrief.model_validate(result)
            )
            if not _contains_unsafe_framing(llm_brief.summary):
                summary = llm_brief.summary
        except Exception:
            summary = _template_summary(country_name, year, perf, residual)

    return _fallback_brief(
        country_code=country_code,
        country_name=country_name,
        year=year,
        indicators=indicators,
        predicted=predicted,
        actual=actual,
        residual=residual,
        perf=perf,
        summary=summary,
    )

"""Multi-step agent over the governed mart (spec 011) — LangGraph + LangSmith.

Where ``/ask`` (spec 004) is a *single-round* tool-caller, this is a **multi-step LangGraph agent**:
it plans, calls whitelisted tools in sequence, observes, loops, and synthesizes. Three modes share
one graph + tools — ``analyze`` (user-facing planner), ``investigate`` (a data-quality-flagged
country-year), ``report`` (a multi-country briefing).

Grounding + honesty are **inherited, not re-derived**: the tools are the same whitelisted,
parameterized queries ``/ask`` uses, and they build the ``citations`` list, so grounding is a
property of the code. A self-check gates the final answer — an empty answer, no citations, or
causal/blame wording falls back to the deterministic template (Principle V). It does NOT gate on
strict number-matching (a *derived* figure isn't a citation value; ``/ask``'s lesson).

LangSmith tracing turns on purely by env (``LANGSMITH_TRACING=true`` + ``LANGSMITH_API_KEY``); no
code, no committed secret. With no ``ANTHROPIC_API_KEY`` the agent step is skipped and a
deterministic fallback keeps the endpoints runnable offline (FR-006).
"""

from __future__ import annotations

import os
from typing import Any

from ml.features import country_history
from ml.forecast import forecast_features
from pydantic import BaseModel

from ai.insights import (
    CAVEAT,
    Citation,
    connect,
    get_country_year,
    has_causal_language,
    is_grounded,
    latest_year,
    resolve_ask_model,
    template_answer,
    top_by_value_for_money,
)

MODES = ("analyze", "investigate", "report")

PROMPTS: dict[str, str] = {
    "analyze": (
        "You are a Sub-Saharan African health-data analyst. Break the question into steps and call "
        "the tools to get REAL numbers for every figure. Then answer every part in plain prose in "
        "value-for-money / 'above or below what spending predicts' framing — never 'best/worst', "
        "never blame or causation. Cite via the tools; if the tools return nothing, say so."
    ),
    "investigate": (
        "You are a data-quality investigator. For that country-year, use the tools to pull the "
        "country's history and compare years; judge whether the value is a REAL signal or a likely "
        "DATA ARTIFACT. Give a keep-or-flag disposition with reasoning grounded in the numbers. "
        "Never a blame or performance claim — this is about data quality, not the country."
    ),
    "report": (
        "You are a briefing writer. For EACH requested country, use the tools to fetch the numbers "
        "and write one short grounded section in value-for-money framing (never best/worst/blame). "
        "Compose the sections into one multi-country briefing."
    ),
}


class AgentStep(BaseModel):
    tool: str
    summary: str


class AgentResponse(BaseModel):
    mode: str
    answer: str
    steps: list[AgentStep]
    citations: list[Citation]
    grounded: bool
    caveat: str


# Blame/judgement words (a subset of the causal ban) that are NEVER acceptable — even in the
# investigate mode, which otherwise reasons causally about the DATA ("likely an artifact because the
# prior year…"). The full causal ban applies to the user-facing analyze/report modes.
_BLAME_TERMS = (
    "failing",
    "failed",
    "worst",
    "incompetent",
    "corrupt",
    "mismanaged",
    "negligent",
    "to blame",
    "at fault",
    "disgrace",
    "blame",
)


def prompt_for(mode: str) -> str:
    """The system prompt for a mode; unknown modes fall back to the analyst prompt."""
    return PROMPTS.get(mode, PROMPTS["analyze"])


def _disallowed(mode: str, text: str) -> bool:
    """Honest-framing guard. investigate reasons about DATA causally (allowed) but never blames a
    country; analyze/report get the full causal+blame ban (Principle V)."""
    if mode == "investigate":
        lowered = text.lower()
        return any(term in lowered for term in _BLAME_TERMS)
    return has_causal_language(text)


def build_response(
    mode: str, answer: str, steps: list[AgentStep], sink: list[Citation]
) -> AgentResponse:
    """Assemble the response, applying the honest-framing self-check (FR-004).

    Fallback to the deterministic template when the draft is empty, has no citations, or breaks the
    mode's honest-framing guard — NOT on strict number-matching (a derived figure isn't a citation
    value). ``grounded`` reports whether the draft also passed the strict check, for transparency.
    """
    use_template = (not answer) or (not sink) or _disallowed(mode, answer)
    final = template_answer(sink) if use_template else answer
    grounded = (not use_template) and is_grounded(answer, sink)
    return AgentResponse(
        mode=mode, answer=final, steps=steps, citations=sink, grounded=grounded, caveat=CAVEAT
    )


def _load_model() -> Any:
    """Load the trained model from the artifact store (local or S3), or None if not trained yet."""
    data = None
    try:
        import io

        import joblib
        from ml import artifacts

        data = artifacts.get_bytes(artifacts.MODEL_FILENAME)
        if data is None:
            return None
        return joblib.load(io.BytesIO(data))
    except Exception:
        return None


def _run_graph(
    mode: str, user_input: str, conn: Any, sink: list[Citation], model: str
) -> tuple[str | None, list[AgentStep]]:
    """Run the LangGraph ReAct agent; return (answer, steps). Broad except → fallback (FR-006)."""
    try:
        from langchain_core.tools import tool
        from langgraph.prebuilt import create_react_agent

        @tool  # type: ignore[misc]  # langchain ships no type stubs (mypy override in pyproject.toml)
        def country_indicators(country_code: str, year: int) -> str:
            """Every published indicator for one country + year. country_code = ISO3 (e.g. KEN)."""
            rows = get_country_year(conn, country_code, year)
            sink.extend(rows)
            return "; ".join(f"{c.indicator}={c.value}" for c in rows) or "No data."

        @tool  # type: ignore[misc]
        def value_for_money(indicator: str, year: int, n: int = 5) -> str:
            """Rank countries by an indicator per unit of health spending for a year (VfM leaders).
            indicator ∈ life_expectancy, under5_mortality, health_spend_pct_gdp, gdp_per_capita,
            internet_pct, fertility_rate."""
            rows = top_by_value_for_money(conn, indicator, year, n)
            sink.extend(rows)
            return "; ".join(f"{c.country_name} {c.indicator}={c.value}" for c in rows) or "None."

        @tool  # type: ignore[misc]
        def forecast_life_expectancy(country: str, year: int) -> str:
            """Forecast a FUTURE year's life expectancy by projecting the model's inputs forward.
            country = name or ISO code; year beyond the data (e.g. 2027)."""
            projected = forecast_features(country_history(conn, country), year)
            model_obj = _load_model()
            if projected is None or model_obj is None:
                return f"Can't forecast {country} {year} (insufficient history or no model)."
            import pandas as pd
            from ml.features import FEATURES

            frame = pd.DataFrame([projected], columns=FEATURES)
            value = round(float(model_obj.predict(frame)[0]), 1)
            return f"Forecast life expectancy for {country} in {year}: {value} yrs (projected)."

        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(model_name=model, timeout=60, stop=None)
        graph = create_react_agent(
            llm,
            tools=[country_indicators, value_for_money, forecast_life_expectancy],
            prompt=prompt_for(mode),
        )
        result = graph.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            {"recursion_limit": 12},
        )
        steps: list[AgentStep] = []
        for message in result["messages"]:
            for call in getattr(message, "tool_calls", None) or []:
                steps.append(AgentStep(tool=str(call["name"]), summary=str(call.get("args", {}))))
        content = result["messages"][-1].content
        answer = content if isinstance(content, str) else None
        return answer, steps
    except Exception:
        return None, []


def run_agent(mode: str, user_input: str, model: str | None = None) -> AgentResponse:
    """Run the agent for a mode over a natural-language input, grounded in the published mart."""
    resolved = resolve_ask_model(model)
    with connect() as conn:
        if not os.getenv("ANTHROPIC_API_KEY"):
            citations = top_by_value_for_money(conn, "life_expectancy", latest_year(conn))
            return build_response(mode, "", [], citations)
        sink: list[Citation] = []
        answer, steps = _run_graph(mode, user_input, conn, sink, resolved)
    return build_response(mode, answer or "", steps, sink)

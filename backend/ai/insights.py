"""AI Insights — natural-language Q&A over the published mart (spec 004).

A Claude SQL-tool agent turns a plain-English question into calls against a small set of fixed,
parameterized query tools over ``published.country_year_indicators`` (FR-001) — never free-form SQL.
Every number the agent states must come back out of those tool calls; the tools themselves (not the
LLM) build the ``citations`` list, so grounding is a property of the code, not something we hope the
model got right. If the model's prose can't be verified against the retrieved rows, or reads as a
causal/blame claim instead of value-for-money framing, a deterministic template built from the same
rows is used instead (FR-002/003/004) — mirrors the fallback discipline in ``ml/brief.py``.

With no ``ANTHROPIC_API_KEY`` the whole agent step is skipped: a canned query + the same template
answer keep this runnable offline (FR-006).
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence
from typing import Any

import psycopg
from pydantic import BaseModel

# Same indicator codes the published mart exposes (backend/scripts/pull_wdi.py, spec 001).
INDICATORS = (
    "life_expectancy",
    "under5_mortality",
    "health_spend_pct_gdp",
    "gdp_per_capita",
    "internet_pct",
    "fertility_rate",
)

CAVEAT = (
    "Framed as value-for-money / association with health spending, not a causal or performance "
    "judgement (some data may be missing for a given country-year)."
)

DECLINE = "I can't answer that from the published data — no matching rows were found."

_CAUSAL_TERMS = (
    "causes",
    "caused by",
    "because of",
    "due to",
    "leads to",
    "results in",
    "is failing",
    "are failing",
    "failure",
    "blame",
    "responsible for",
    "at fault",
)

SYSTEM_PROMPT = (
    "You answer questions about Sub-Saharan African health indicators using ONLY the query "
    "tools provided — never invent a number. Every figure you state must come from a tool "
    "result, and you must name the country, year, and indicator for each one. Frame "
    "comparisons as value-for-money / association with health spending — never as a causal "
    "claim or as a country 'failing'. If the tools return nothing useful, say plainly that "
    "the data can't answer the question."
)


class InsightRequest(BaseModel):
    question: str


class Citation(BaseModel):
    country_code: str
    country_name: str
    year: int
    indicator: str
    value: float


class InsightResponse(BaseModel):
    answer: str
    citations: list[Citation]
    caveats: str


def connect() -> psycopg.Connection:
    """Connect to Postgres.

    Unlike ``ml.features.connect`` (a host-only script), this is called from the FastAPI endpoint,
    which runs INSIDE the api container — so it must honor ``POSTGRES_HOST`` (compose's `env_file:
    .env` sets it to ``db`` there), not default straight to ``localhost``.
    """
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "wb_health_monitor"),
        user=os.getenv("POSTGRES_USER", "wb_health_monitor"),
        password=os.getenv("POSTGRES_PASSWORD", "localdevpassword"),
    )


def _query(conn: psycopg.Connection, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        assert cur.description is not None, "expected a SELECT with a result set"
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def _row_to_citations(row: dict[str, Any]) -> list[Citation]:
    return [
        Citation(
            country_code=row["country_code"],
            country_name=row["country_name"],
            year=row["year"],
            indicator=indicator,
            value=float(row[indicator]),
        )
        for indicator in INDICATORS
        if row.get(indicator) is not None
    ]


def get_country_year(conn: psycopg.Connection, country_code: str, year: int) -> list[Citation]:
    """All published indicators for one country and year (FR-001)."""
    rows = _query(
        conn,
        """SELECT country_code, country_name, year, life_expectancy, under5_mortality,
               health_spend_pct_gdp, gdp_per_capita, internet_pct, fertility_rate
           FROM published.country_year_indicators
           WHERE country_code = %s AND year = %s""",
        (country_code.upper(), year),
    )
    return [c for row in rows for c in _row_to_citations(row)]


def top_by_value_for_money(
    conn: psycopg.Connection,
    indicator: str,
    year: int | None,
    n: int = 5,
    spend_indicator: str = "health_spend_pct_gdp",
) -> list[Citation]:
    """Top-N countries by ``indicator`` per unit of ``spend_indicator``, for a year (FR-001).

    Value-for-money = indicator / spend — an association with spending, not a causal or
    performance claim (Principle V). ``indicator``/``spend_indicator`` are checked against the
    fixed ``INDICATORS`` allowlist before being placed in SQL — never free-form/user-supplied SQL.
    """
    if indicator not in INDICATORS or spend_indicator not in INDICATORS or year is None:
        return []
    rows = _query(
        conn,
        f"""SELECT country_code, country_name, year, {indicator} AS target_value,
               {spend_indicator} AS spend_value
           FROM published.country_year_indicators
           WHERE year = %s AND {indicator} IS NOT NULL AND {spend_indicator} > 0
           ORDER BY ({indicator} / {spend_indicator}) DESC
           LIMIT %s""",
        (year, n),
    )
    citations = []
    for row in rows:
        code, name, year_ = row["country_code"], row["country_name"], row["year"]
        citations.append(
            Citation(
                country_code=code,
                country_name=name,
                year=year_,
                indicator=indicator,
                value=float(row["target_value"]),
            )
        )
        citations.append(
            Citation(
                country_code=code,
                country_name=name,
                year=year_,
                indicator=spend_indicator,
                value=float(row["spend_value"]),
            )
        )
    return citations


def latest_year(conn: psycopg.Connection) -> int | None:
    with conn.cursor() as cur:
        cur.execute("SELECT max(year) FROM published.country_year_indicators")
        row = cur.fetchone()
        value = row[0] if row is not None else None
        return int(value) if value is not None else None


def is_grounded(text: str, citations: Sequence[Citation]) -> bool:
    """Every number the answer states must match a retrieved citation value or year (FR-003)."""
    numbers = [float(n) for n in re.findall(r"-?\d+\.?\d*", text)]
    if not numbers:
        return True
    known = {round(c.value, 1) for c in citations} | {float(c.year) for c in citations}
    return all(round(n, 1) in known for n in numbers)


def has_causal_language(text: str) -> bool:
    """SC-004: association/value-for-money only, never causal or blame framing."""
    lowered = text.lower()
    return any(term in lowered for term in _CAUSAL_TERMS)


def template_answer(citations: Sequence[Citation]) -> str:
    """Deterministic, always-grounded, always-honest answer built straight from retrieved rows."""
    if not citations:
        return DECLINE
    lines = [f"{c.country_name} {c.year} {c.indicator}={c.value}" for c in citations]
    return "Based on the published mart: " + "; ".join(lines) + "."


def _run_agent(conn: psycopg.Connection, question: str, sink: list[Citation]) -> str | None:
    """Let Claude pick and call the query tools; return its prose, or None on any failure.

    Deliberately broad ``except``: this is a live external API call (FR-005/FR-006 — never let an
    LLM/network failure take the endpoint down; fall back to the deterministic template instead, the
    same discipline ``ml/brief.py`` uses for its Claude call).
    """
    try:
        from langchain.agents import create_agent
        from langchain.tools import tool

        @tool  # type: ignore[misc]  # langchain ships no type stubs (see mypy override in pyproject.toml)
        def get_country_year_tool(country_code: str, year: int) -> str:
            """Look up every published indicator for one country and year. Use this for a
            specific-country question, e.g. "What was Kenya's life expectancy in 2020?".
            country_code is the 3-letter ISO code (e.g. KEN)."""
            rows = get_country_year(conn, country_code, year)
            sink.extend(rows)
            if not rows:
                return f"No published data for {country_code} in {year}."
            return "; ".join(f"{c.indicator}={c.value}" for c in rows)

        @tool  # type: ignore[misc]
        def top_by_value_for_money_tool(
            indicator: str, year: int, n: int = 5, spend_indicator: str = "health_spend_pct_gdp"
        ) -> str:
            """Rank countries by an indicator per unit spent on another indicator, for a year —
            the best 'value for money' countries. Use for comparison/ranking questions, e.g. "which
            countries get the most life expectancy for their health spending?". indicator and
            spend_indicator must each be one of: life_expectancy, under5_mortality,
            health_spend_pct_gdp, gdp_per_capita, internet_pct, fertility_rate."""
            rows = top_by_value_for_money(conn, indicator, year, n, spend_indicator)
            sink.extend(rows)
            if not rows:
                return "No matching rows."
            by_country: dict[str, list[Citation]] = {}
            for c in rows:
                by_country.setdefault(c.country_code, []).append(c)
            return "; ".join(
                f"{group[0].country_name} ({group[0].country_code}, {group[0].year}): "
                + ", ".join(f"{c.indicator}={c.value}" for c in group)
                for group in by_country.values()
            )

        agent = create_agent(
            model="anthropic:claude-sonnet-4-5",
            tools=[get_country_year_tool, top_by_value_for_money_tool],
            system_prompt=SYSTEM_PROMPT,
        )
        result = agent.invoke({"messages": [{"role": "user", "content": question}]})
        content = result["messages"][-1].content
        return content if isinstance(content, str) else None
    except Exception:
        return None


def answer_question(question: str) -> InsightResponse:
    """Answer a plain-English question, grounded in ``published.country_year_indicators``."""
    with connect() as conn:
        if not os.getenv("ANTHROPIC_API_KEY"):
            citations = top_by_value_for_money(conn, "life_expectancy", latest_year(conn))
            return InsightResponse(
                answer=template_answer(citations), citations=citations, caveats=CAVEAT
            )

        sink: list[Citation] = []
        answer = _run_agent(conn, question, sink)

    if not sink:
        return InsightResponse(answer=DECLINE, citations=[], caveats=CAVEAT)
    if not answer or not is_grounded(answer, sink) or has_causal_language(answer):
        answer = template_answer(sink)
    return InsightResponse(answer=answer, citations=sink, caveats=CAVEAT)

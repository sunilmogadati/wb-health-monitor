"""Tests for spec 004 (ai-insights).

Split like test_ml.py: guardrail/schema logic needs no DB, no LLM key, and no `ai` extra (langchain
is imported lazily inside `ai.insights._run_agent`, only reached when ANTHROPIC_API_KEY is set) —
these run in plain CI. The mart-backed tests need a live Postgres with the published view migrated
and populated (`make up && make migrate && make ingest`); they skip themselves when that isn't
available, the same way `make test` (inside the stack) is the only place spec-002's `ml.train` gets
exercised end to end.
"""

from __future__ import annotations

import psycopg
import pytest

from ai.insights import (
    DECLINE,
    Citation,
    InsightResponse,
    answer_question,
    connect,
    has_causal_language,
    is_grounded,
    latest_year,
    template_answer,
    top_by_value_for_money,
)


def _pg_available() -> bool:
    try:
        with connect():
            return True
    except psycopg.OperationalError:
        return False


NEEDS_DB = pytest.mark.skipif(
    not _pg_available(), reason="Postgres not reachable (run inside the stack)"
)


def _citation(**overrides) -> Citation:
    fields = {
        "country_code": "KEN",
        "country_name": "Kenya",
        "year": 2020,
        "indicator": "life_expectancy",
        "value": 61.4,
    }
    fields.update(overrides)
    return Citation(**fields)


# --- Guardrails (FR-002/003/004) — no DB, no LLM key ------------------------------------------


def test_is_grounded_accepts_numbers_from_citations() -> None:
    citations = [_citation(value=61.4), _citation(indicator="health_spend_pct_gdp", value=4.9)]
    text = "Kenya spent 4.9% of GDP on health with a life expectancy of 61.4 years."
    assert is_grounded(text, citations)


def test_is_grounded_rejects_an_invented_number() -> None:
    citations = [_citation(value=61.4)]
    assert not is_grounded("Kenya's life expectancy is 99.9 years.", citations)


def test_is_grounded_true_with_no_numbers_in_text() -> None:
    assert is_grounded("The data does not cover that indicator.", [])


def test_has_causal_language_flags_blame_words() -> None:
    assert has_causal_language("Kenya's health spending causes its longer life expectancy.")
    assert has_causal_language("Country X is failing its citizens.")


def test_has_causal_language_allows_value_for_money_framing() -> None:
    text = "Kenya shows strong value-for-money: high life expectancy relative to health spending."
    assert not has_causal_language(text)


def test_template_answer_declines_with_no_citations() -> None:
    assert template_answer([]) == DECLINE


def test_template_answer_cites_every_row_and_stays_grounded() -> None:
    citations = [
        _citation(value=61.4),
        _citation(country_code="NGA", country_name="Nigeria", value=54.5),
    ]
    answer = template_answer(citations)
    assert "Kenya" in answer and "Nigeria" in answer
    assert is_grounded(answer, citations)
    assert not has_causal_language(answer)


def test_insight_response_schema_round_trips() -> None:
    citations = [_citation()]
    response = InsightResponse(
        answer=template_answer(citations), citations=citations, caveats="value-for-money"
    )
    assert response.citations[0].country_code == "KEN"
    assert response.model_dump()["citations"][0]["indicator"] == "life_expectancy"


# --- Mart-backed (needs a live, migrated Postgres) --------------------------------------------


@NEEDS_DB
def test_top_by_value_for_money_matches_a_direct_query() -> None:
    with connect() as conn:
        year = latest_year(conn)
        citations = top_by_value_for_money(conn, "life_expectancy", year, n=3)
        if not citations:
            pytest.skip("published mart has no data yet — run `make ingest`")
        with conn.cursor() as cur:
            cur.execute(
                "SELECT life_expectancy FROM published.country_year_indicators "
                "WHERE country_code = %s AND year = %s",
                (citations[0].country_code, citations[0].year),
            )
            (actual,) = cur.fetchone()
    assert citations[0].value == actual


@NEEDS_DB
def test_offline_fallback_runs_with_no_api_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    question = "Which countries get the most life expectancy for their health spending?"
    response = answer_question(question)
    assert isinstance(response, InsightResponse)
    assert not has_causal_language(response.answer)
    if response.citations:
        assert is_grounded(response.answer, response.citations)

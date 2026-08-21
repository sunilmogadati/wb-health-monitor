"""Tests for the agentic-analysis feature (spec 011).

Pure parts (prompt selection, response assembly, the self-check gate) are unit-tested; the LangGraph
run itself is not exercised here (needs a live LLM) — the endpoint contract uses a fake run_agent.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from ai import agent
from ai.agent import AgentResponse, AgentStep, build_response, prompt_for
from ai.insights import Citation
from app import agent as app_agent
from app.main import app


def _cite(value: float = 61.4, year: int = 2020) -> Citation:
    return Citation(
        country_code="KEN",
        country_name="Kenya",
        year=year,
        indicator="life_expectancy",
        value=value,
    )


# --- prompts (FR-003) --------------------------------------------------------------------------


def test_each_mode_has_a_distinct_prompt() -> None:
    prompts = {prompt_for(m) for m in ("analyze", "investigate", "report")}
    assert len(prompts) == 3


def test_unknown_mode_falls_back_to_analyst_prompt() -> None:
    assert prompt_for("nonsense") == prompt_for("analyze")


# --- self-check gate (FR-004, SC-004) ----------------------------------------------------------


def test_grounded_answer_is_kept() -> None:
    resp = build_response("analyze", "Kenya 2020 life_expectancy=61.4.", [], [_cite()])
    assert resp.answer == "Kenya 2020 life_expectancy=61.4."
    assert resp.grounded is True


def test_causal_answer_falls_back_to_template() -> None:
    resp = build_response("analyze", "Low spending causes shorter lives.", [], [_cite()])
    assert resp.answer.startswith("Based on the published mart")
    assert resp.grounded is False


def test_investigate_allows_data_causal_reasoning_but_not_blame() -> None:
    # "because" is data-quality reasoning (kept in investigate)...
    draft = "2017 is likely an artifact because it breaks the smooth trend."
    kept = build_response("investigate", draft, [], [_cite()])
    assert kept.answer.startswith("2017 is likely an artifact")
    # ...but a blame word still falls back to the template, even in investigate.
    blamed = build_response("investigate", "This country is failing its people.", [], [_cite()])
    assert blamed.answer.startswith("Based on the published mart")


def test_analyze_still_bans_causal_language() -> None:
    draft = "Life expectancy rose because of higher spending."
    resp = build_response("analyze", draft, [], [_cite()])
    assert resp.answer.startswith("Based on the published mart")


def test_empty_citations_declines_via_template() -> None:
    resp = build_response("analyze", "some answer", [], [])
    assert resp.grounded is False
    assert resp.citations == []


def test_empty_answer_falls_back_to_template() -> None:
    resp = build_response("report", "", [], [_cite()])
    assert resp.answer.startswith("Based on the published mart")


# --- no-key fallback (FR-006) ------------------------------------------------------------------


class _FakeConn:
    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_run_agent_without_key_returns_deterministic_fallback(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(agent, "connect", lambda: _FakeConn())
    monkeypatch.setattr(agent, "latest_year", lambda conn: 2022)
    monkeypatch.setattr(agent, "top_by_value_for_money", lambda conn, indicator, year: [_cite()])

    resp = agent.run_agent("analyze", "anything")
    assert resp.answer.startswith("Based on the published mart")
    assert resp.steps == []
    assert len(resp.citations) == 1


# --- endpoint contract (FR-007) ----------------------------------------------------------------


def test_analyze_endpoint_returns_the_agent_shape(monkeypatch) -> None:
    fake = AgentResponse(
        mode="analyze",
        answer="Kenya's life expectancy is rising and sits above what its spending predicts.",
        steps=[AgentStep(tool="value_for_money", summary="{'indicator': 'life_expectancy'}")],
        citations=[_cite()],
        grounded=True,
        caveat="value-for-money framing",
    )
    monkeypatch.setattr(app_agent, "run_agent", lambda mode, user_input: fake)

    response = TestClient(app).get("/api/v1/agent/analyze?q=is+kenya+improving")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "analyze"
    assert len(body["steps"]) == 1
    assert body["steps"][0]["tool"] == "value_for_money"

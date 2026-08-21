"""Agentic analysis endpoints (spec 011) — three modes over one LangGraph agent.

Each endpoint shapes a natural-language task, runs the multi-step agent, and returns the answer, the
steps it took (tool calls), citations, a groundedness flag, and the honest caveat.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from ai.agent import AgentResponse, run_agent

router = APIRouter(tags=["agent"], prefix="/agent")


@router.get("/analyze", response_model=AgentResponse, summary="Multi-step analysis of a question")
def analyze(
    q: str = Query(..., min_length=1, description="A plain-English, possibly multi-part question"),
) -> AgentResponse:
    return run_agent("analyze", q)


@router.get(
    "/investigate", response_model=AgentResponse, summary="Investigate a flagged country-year"
)
def investigate(country: str, year: int) -> AgentResponse:
    task = (
        f"Investigate the data-quality-flagged value(s) for {country} in {year}. Pull the "
        f"history, compare years, and judge whether it is a real signal or a data artifact. "
        f"Give a keep-or-flag disposition with reasoning."
    )
    return run_agent("investigate", task)


@router.get("/report", response_model=AgentResponse, summary="Multi-country briefing")
def report(
    countries: str = Query(..., description="Comma-separated country names or ISO codes"),
    year: int = 2022,
) -> AgentResponse:
    names = [c.strip() for c in countries.split(",") if c.strip()]
    task = (
        f"Build a briefing for {year} covering these countries: {', '.join(names)}. One grounded, "
        f"cited section each, in value-for-money framing."
    )
    return run_agent("report", task)

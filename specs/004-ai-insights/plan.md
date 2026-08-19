# Implementation Plan: AI Insights (spec 004)

**Status**: For review · **Spec**: `spec.md` (Accepted) · **Author**: maintainer

## Summary

A natural-language question about the health data returns a **grounded, cited** answer, produced by a
**SQL-tool agent** (Claude) that queries only the `published` mart. Every number traces to a retrieved
row; with no API key, a deterministic fallback keeps it running.

## Technical context

- **Deps**: `backend[warehouse,ai]` (dbt for the mart; anthropic/langchain-anthropic for the agent).
  No `ml` (no training here).
- **Read surface**: `published.country_year_indicators` (+ `published.model_residual` if present).
- **LLM**: Claude via `langchain-anthropic`.
- **Serve**: `GET /api/v1/ask` in `backend/app/`.

## Constitution check (gate)

- **III Governed pipeline** ✅ reads only `published`.
- **V Honest modeling** ✅ answers framed as value-for-money / association; never causal/blame.
- **II Test-backed** ✅ grounding, citation, and offline-fallback tests.
- **I Public data** ✅; no keys in code (Anthropic key via env).

## Design decisions

1. **Retrieval = SQL-tool agent, NOT free-form SQL.** Expose a small set of **safe, parameterized
   query tools** (e.g. `get_country_year(country, year)`, `top_by_value_for_money(indicator, year, n)`)
   that run fixed `SELECT`s over the mart. This prevents SQL injection and hallucinated columns, and
   makes every result a real mart row. (FR-001/FR-003)
2. **Grounding guardrail** — the agent may only state numbers returned by a tool; each is a citation
   `{country, year, indicator, value}`. If tools return nothing, the answer declines. (FR-002/FR-003)
3. **Output** — `InsightResponse` (Pydantic): `answer`, `citations[]`, `caveats` (states the
   value-for-money framing / any data gaps).
4. **Fallback** — no API key → run a canned tool query (e.g. top-N by residual) and return a template
   answer + real citations, so CI passes offline. (FR-006)
5. **Endpoint** — `GET /api/v1/ask?q=...` returns `InsightResponse`.

## Data flow

`question → agent picks a query tool → tool runs a parameterized SELECT on published → Claude composes a grounded, cited answer → InsightResponse`

## Files

- add `backend/ai/insights.py` (query tools + `InsightResponse` + the agent + fallback)
- add a router under `backend/app/` for `/ask`
- add tests in `tests/`

## Testing

- Grounding: every number in the answer equals a mart value (assert against a direct query).
- Citations present for each figure.
- Offline fallback runs with no `ANTHROPIC_API_KEY`.
- No causal/blame language (SC-004).

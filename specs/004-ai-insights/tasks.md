# Tasks: AI Insights (spec 004)

**Status**: For review · **Plan**: `plan.md` · Work these in order; each maps to a spec FR / SC.

## Phase 1 — Safe data access
- [ ] **T001** `backend/ai/insights.py`: parameterized query tools over `published.country_year_indicators` (e.g. `get_country_year`, `top_by_value_for_money`). Fixed `SELECT`s only — no free-form SQL. (FR-001)

## Phase 2 — Response contract
- [ ] **T002** `InsightResponse` (Pydantic): `answer`, `citations[] {country, year, indicator, value}`, `caveats`. (FR-002)

## Phase 3 — Agent
- [ ] **T003** Wire a Claude SQL-tool agent (`langchain-anthropic`) to the query tools. (FR-005)
- [ ] **T004** Grounding guardrail: numbers in the answer must come from tool output, each cited; if tools return nothing, decline. (FR-003)
- [ ] **T005** Honest framing in the prompt: value-for-money / association, never causal or "failing". (FR-004)

## Phase 4 — Offline fallback
- [ ] **T006** No-`ANTHROPIC_API_KEY` path: run a canned tool query + template answer with real citations. (FR-006)

## Phase 5 — API
- [ ] **T007** `backend/app/`: `GET /api/v1/ask?q=...` → `InsightResponse`. (FR-007)

## Phase 6 — Tests & gate
- [ ] **T008** Tests: grounding (numbers match the mart), citations present, offline fallback runs; no causal/blame language. (SC-001..005)
- [ ] **T009** `make test` green.

## Phase 7 — Ship
- [ ] **T010** PR into `develop`; maintainer reviews against the spec's Success Criteria.

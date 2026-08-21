# Tasks: Agentic Analysis (spec 011) · TDD

- [x] **T001** `tests/test_agent.py`: pure tests — mode→prompt selection; AgentResponse assembly from a
      fake graph result; self-check gate (grounded vs causal → template). *(FR-003, FR-004)*
- [x] **T002** `backend/ai/agent.py`: tools (query/forecast/value-for-money over the mart, citations
      sink), `create_react_agent` graph, `run_agent(mode, **inputs)` with self-check + fallback. *(FR-001..006)*
- [x] **T003** `backend/app/agent.py`: `GET /agent/analyze|investigate|report` → `AgentResponse`. *(FR-007)*
- [x] **T004** `main.py`: include the agent router.
- [x] **T005** `tests/test_agent.py`: endpoint contract (shape; no-key fallback; causal→template). *(FR-006, SC-004)*
- [x] **T006** `pyproject.toml`: pin `langgraph` + `langsmith` in the `ai` extra (already transitive).
- [x] **T007** `frontend`: `getAgent` + `AgentPanel` (analyze) on the dashboard. *(FR-007)*
- [x] **T008** Verify live: `analyze` two-part Kenya question → ≥2 tool steps + grounded answer;
      `investigate`/`report` run; update `docs/PROJECT_BRIEF.md`.

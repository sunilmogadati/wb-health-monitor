# Implementation Plan: Agentic Analysis

**Spec**: `specs/011-agentic-analysis/spec.md` · **Branch**: `agent-011`

## Constitution Check
- I — public data via whitelisted tools only. ✅  II — eval judges (008) score agent answers;
  unit-tested pure parts. ✅  V — groundedness self-check + honest-framing fallback. ✅  VI —
  deterministic tools; no-key fallback. ✅  Change Traceability — new capability → this spec. ✅

## Approach
Reuse everything grounded that already exists; add the *orchestration*.
1. **`backend/ai/agent.py`**: build the tools (wrap spec-004/010 queries + forecast + value-for-money,
   each appending to a citations sink), then a **LangGraph** agent via `create_react_agent(model,
   tools, prompt)` — the prebuilt ReAct graph gives the multi-step plan→act→observe loop. A thin
   `run_agent(mode, **inputs)` shapes the prompt per mode (`analyze`/`investigate`/`report`), invokes
   the graph, collects the tool-call steps + citations, runs the **groundedness self-check**
   (`insights.is_grounded` + `has_causal_language`), and falls back to the deterministic template on
   failure or no key. LangSmith turns on purely by env (`LANGSMITH_TRACING`), no code.
2. **`backend/app/agent.py`**: `GET /agent/analyze|investigate|report`, each → `AgentResponse`.
3. **`main.py`**: include the router.
4. **Frontend**: an `AgentPanel` (analyze mode) + `getAgent` in `lib/api.ts`, surfaced on the dashboard.

## Test strategy
- Pure/unit: mode→prompt selection; the AgentResponse assembly from a fake graph result; the
  self-check gate (grounded vs causal → template).
- Contract (TestClient, monkeypatched graph + conn): each endpoint returns the shape; no-key →
  deterministic fallback (FR-006); causal draft → template (SC-004).
- Live: `analyze` a two-part Kenya question shows ≥2 tool steps; `investigate`/`report` run.

## Notes
- Keep the agent's tools identical in spirit to `/ask` so grounding + honesty are inherited, not
  re-derived. The *only* new risk surface is the multi-step loop — bounded by a recursion limit.

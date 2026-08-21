# Feature Specification: Agentic Analysis (LangGraph + LangSmith)

**Feature Branch**: `011-agentic-analysis`

**Created**: 2026-08-21

**Status**: Accepted & implemented (2026-08-21). Clarify folded in (the three modes + tool set were
the design decisions); live-verified — `analyze` chains 6 tool calls on a two-part question,
`investigate` returns a data-quality disposition, mode-scoped honest-framing preserved.

**Depends on**: spec 004 (`/ask` tool-agent, the grounding discipline), spec 002 (`/predict`,
`/brief`), spec 010 (`/forecast`), spec 008 (the eval gate + judges that also score these answers).

**Input**: Today's `/ask` is a **single-round** tool-caller. Some questions need **multiple steps**
that depend on each other — "forecast Kenya's life expectancy, then say how that compares to its
peers, and whether it's above what its spending predicts." Build a **multi-step agent** on
**LangGraph** (plan → act with tools → observe → loop → synthesize → self-check), traced with
**LangSmith**, exposing **three use cases** over the same governed data + tools.

> **Constitution alignment:** Principle I (public data; the agent only reads the governed mart via
> whitelisted tools — never free-form SQL), Principle II (tests before code; the eval gate from 008
> also scores agent answers), Principle V (**Honest Modeling** — value-for-money framing, citations,
> and a groundedness self-check; the agent declines rather than invents), Principle VI (deterministic
> tools; the LLM step degrades to a safe fallback with no key).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Analysis planner (Priority: P1)

A user asks a multi-part question. The agent **plans**, calls the right tools in sequence, and
synthesizes a grounded answer — showing the steps it took.

**Acceptance**:
1. **Given** "Is Kenya's life expectancy improving, and is it above what its spending predicts?",
   **When** the agent runs, **Then** it calls a trend tool AND the value-for-money/benchmark tool and
   answers both parts, with citations, in value-for-money framing.
2. **Given** any answer, **Then** every figure traces to a tool result (a groundedness self-check runs;
   a failing check falls back to the deterministic template, mirroring `/ask`).

### User Story 2 — Anomaly investigator (Priority: P2)

A governance user points the agent at a **data-quality-flagged** country-year. The agent pulls the
country's history + neighbors, checks the source value, and proposes **keep vs. flag** with reasoning.

**Acceptance**:
1. **Given** a flagged country-year, **When** the agent investigates, **Then** it returns a reasoned
   disposition (real signal vs. likely artifact) grounded in the retrieved history — never a blame claim.

### User Story 3 — Report builder (Priority: P2)

**Acceptance**:
1. **Given** a set of countries, **When** the agent builds a report, **Then** it produces one briefing
   with a grounded, cited section per country (reusing the `/brief` discipline), honest framing throughout.

## Requirements *(mandatory)*

- **FR-001** — A **LangGraph** agent (a `StateGraph`, or `create_react_agent` wrapped with a
  synthesis + self-check step) drives a **multi-step** tool loop, unlike `/ask`'s single round.
- **FR-002** — Tools are **whitelisted, parameterized** functions over `published.country_year_indicators`
  (reuse spec 004/010 query + forecast + value-for-money tools) — never free-form SQL; the tools build
  the citations, so grounding is a property of the code.
- **FR-003** — **Three modes**, one graph + shared tools: `analyze` (US1), `investigate` (US2),
  `report` (US3), each with a mode-specific prompt and input shape.
- **FR-004** — A **groundedness self-check** on the final answer (reuse `insights.is_grounded` /
  `has_causal_language`); a failure falls back to a deterministic, grounded template (Principle V).
- **FR-005** — **LangSmith tracing** is on when `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` are set
  (project `wb-health-monitor`); absent, the agent runs untraced. No secret committed.
- **FR-006** — With **no `ANTHROPIC_API_KEY`**, the agent step is skipped and a deterministic fallback
  answer keeps the endpoints runnable offline (mirrors `/ask` FR-006).
- **FR-007** — Endpoints under `/api/v1/agent/*`: `analyze`, `investigate`, `report`. Each returns the
  answer, the **steps taken** (tool calls), citations, a `grounded` flag, and the honest caveat.
- **FR-008** — The response text obeys the **banned-language / honest-framing** rule (spec 008); agent
  answers are scored by the same eval judges (groundedness + helpfulness).

### Key Entities

- **AgentResponse**: `mode, answer, steps[] (tool + summary), citations[], grounded, caveat`.

## Success Criteria *(mandatory)*

- **SC-001**: A two-part question triggers ≥2 distinct tool calls and both parts are answered, cited.
- **SC-002**: `investigate` on a flagged country-year returns a reasoned keep/flag disposition, grounded.
- **SC-003**: `report` returns one section per requested country, each grounded + cited.
- **SC-004**: No answer contains causal/blame language; a non-grounded draft is replaced by the template.
- **SC-005**: With `LANGSMITH_*` set, runs appear as traces; unset, the agent still works.
- **SC-006**: With no Anthropic key, the endpoints return a deterministic fallback, not an error.

## Out of Scope

- Autonomous write actions (the agent only reads; it never mutates the mart or triggers the pipeline).
- A general chat agent — the three modes are bounded to the health-data domain + governed tools.

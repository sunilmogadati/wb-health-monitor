# Tasks: Continuous Evaluation & Quality Gates (spec 008)

**Status**: Draft · **Plan**: `plan.md` · **Owner**: maintainer / advanced · Work in order; each maps to a spec FR / SC.

> Run `/speckit.clarify` first to settle the open choice (hybrid deterministic + LLM-judge vs
> deterministic-only) before building the judge.

## Phase 1 — The eval set + config
- [ ] **T001** `evals/cases/` — a small versioned eval set (public-data only): `/ask` cases (grounded,
  cites, declines-when-unanswerable, out-of-scope refusal), `/brief` cases (schema-valid, numbers echo
  the model, honest framing), and model/data expectations. (FR-001/FR-002)
- [ ] **T002** `evals/thresholds.yaml` — RMSE-regression tolerance, groundedness floor, banned-language
  list, data-quality bounds; one documented config. (FR-010)

## Phase 2 — Deterministic checks (the free gate) — tests first
- [ ] **T003** `evals/checks/` with unit tests: schema-valid, citation-present, correct-decline,
  numbers-match-source, and **banned-language** (causal/blame) checkers. Each proven on crafted fixtures.
  (FR-003/SC-004)
- [ ] **T004** `evals/run.py` — load cases, call the target (`/ask` / `/brief` / model), apply
  deterministic checks, write a **scored report**, exit non-zero on failure. `--deterministic-only`
  mode for PRs. (FR-003/FR-005/FR-011)

## Phase 3 — LLM-as-judge (groundedness)
- [ ] **T005** `evals/judge.py` — pinned model + fixed rubric, returns score + rationale; a low score
  fails, judge-unavailable marks "not evaluated" (never a vacuous pass). Wire into `run.py` as the
  throttled full mode. (FR-004)

## Phase 4 — Model & data gates (pipeline)
- [ ] **T006** **Champion/challenger** in the train step: compare challenger CV RMSE to the stored
  champion; promote only within threshold, else keep champion + flag; record the decision in metadata.
  (FR-006/SC-002)
- [ ] **T007** **Data-quality gate** on the pull (row-count range, value ranges, null rate) before dbt
  builds; **halt** on failure so bad data never reaches `published`. (FR-007/SC-003)

## Phase 5 — Wire into CI/CD + schedule (spec 007)
- [ ] **T008** CI job: run the **deterministic** eval suite on changes to model/AI/eval code; **block
  merge** on failure. (FR-008/SC-001/SC-007)
- [ ] **T009** Merge + **scheduled** workflow: run the **full** suite (with judge), record scores, and
  **alert** on a regression past threshold — including the no-code-change drift case. (FR-009/SC-006)
- [ ] **T010** Persist the **scored report** as a trend (durable location — RDS/S3 per 007), queryable
  over time. (FR-005/SC-005)

## Phase 6 — Document + ship
- [ ] **T011** `docs/EVALUATION.md` — what's measured, thresholds, how to add a case, how the gates fire.
- [ ] **T012** PR into `develop`; maintainer reviews against Success Criteria.

## v2.0.0 — LLM output evaluation & selection (FR-012/013/014, this amendment)

- [x] **T013** Golden regression cases: `ask_trend_kenya`, `ask_value_for_money`, `ask_roi` +
      `checks.answer_contains_any` (expected key-facts) wired into the runner. (FR-012, SC-008)
- [x] **T014** Helpfulness judge: `judge.judge_helpfulness` + `helpfulness_floor`, wired into
      `_judge_results`; rubric made context-aware (SSA-only data + value-for-money framing are
      correct, not penalised). (FR-013, SC-009)
- [x] **T015** Configurable answer model: `insights.resolve_ask_model` + `ASK_MODEL` env + allowlist;
      `/ask?model=` override. (FR-014)
- [x] **T016** `evals/select_model.py` champion/challenger (quality floor → cost → latency) + price
      table; writes `evals/llm_selection.json`. (FR-014, SC-010)
- [x] **T017** `docs/adr/0009-llm-selection.md` + README. (FR-014)
- [x] **T018** Tests: `answer_contains_any`, helpfulness dimension/unavailable, `select()` rule.
- [x] **T019** Verify live: eval suite 6/6 with judges; selection run picks a champion (haiku, 0.96 ≥
      floor, cheaper+faster than sonnet). Update `docs/PROJECT_BRIEF.md`.

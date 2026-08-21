# Implementation Plan: Continuous Evaluation & Quality Gates (spec 008)

**Status**: Draft · **Spec**: `spec.md` · **Owner**: maintainer / advanced

## Summary

A versioned eval set + a runner that scores the model and the two LLM features, wired into two gates:
**CI** (deterministic, on every relevant change) and the **scheduled pipeline** (champion/challenger +
data-quality + periodic LLM re-eval). Thresholds are config. The honest-modeling rule becomes an
automated check.

## The two loops

```
 CI  (fast, deterministic, free)                 PIPELINE / SCHEDULE (continuous)
 ─────────────────────────────                   ───────────────────────────────
 change to model/AI/eval code                    scheduled retrain / cron
        │                                                 │
        ▼                                                 ▼
 run eval set ── deterministic checks            data-quality gate ─ halt if bad pull
   • schema valid   • cites   • declines                  │
   • numbers match  • no blame language                   ▼
        │                                        train challenger → 5-fold CV RMSE
   pass? ── no ─► FAIL MERGE                              │
        │                                        vs champion + threshold
   (on merge/schedule only:)                             │
   LLM-as-judge ─ groundedness ≥ floor          promote? ─ no ─► keep champion + flag
        │                                                 │
        ▼                                                 ▼
   scored report (trend)                         periodic LLM eval re-run → alert on drift
```

## Constitution check (gate)

- **II Test-backed** ✅ evaluation is the test at the ML/LLM layer; it gates merges + promotion.
- **V Honest modeling** ✅ banned-language check enforces "no causal/blame" automatically (FR-003/SC-004).
- **I Public data / no secrets** ✅ eval cases are public-data only; the judge key comes from Secrets Manager (007).

## Design decisions

1. **Eval set as versioned code** (`evals/cases/`) — each case = input + declared expected properties
   (JSON/YAML). Reviewed like code; a stale set is a known risk (FR-001/FR-002).
2. **Two scoring tiers** — **deterministic** (fast, free, the default gate) and **LLM-as-judge** for
   groundedness only, pinned model + fixed rubric, threshold-based, never a vacuous pass (FR-003/FR-004).
3. **Runner** (`evals/run.py`) — loads cases, calls the target (`/ask`, `/brief`, or the model), applies
   checks, writes a **scored report**; exit non-zero on gate failure. One entry point, two modes
   (`--deterministic-only` for PRs, full for merge/schedule) (FR-005/FR-011).
4. **Model gate in the pipeline** — extend `train.py` (or a thin wrapper) with champion/challenger:
   compare challenger CV RMSE to the stored champion, promote only if within threshold, record the
   decision in metadata (FR-006). A **data-quality gate** runs on the pull before dbt builds (FR-007).
5. **Thresholds in one config** (`evals/thresholds.yaml`) — RMSE tolerance, groundedness floor,
   banned-language list, data-quality bounds (FR-010).
6. **Wiring** — CI job runs the deterministic suite on model/AI/eval changes and blocks merge;
   merge-to-main + a scheduled workflow run the full suite (with judge) and record/alert (FR-008/FR-009).

## Files

- `evals/cases/` — the versioned eval cases (public-data).
- `evals/run.py` — the runner (deterministic + optional judge), writes a scored report.
- `evals/checks/` — deterministic checkers (schema, citations, decline, numbers-match, banned-language).
- `evals/judge.py` — groundedness judge (pinned model + rubric).
- `evals/thresholds.yaml` — all thresholds/config.
- `backend/ml/` — champion/challenger promotion + data-quality gate (extends 002's train step).
- `.github/workflows/` — an evals job in the CI gate + a scheduled eval workflow (integrates with 007).
- `docs/EVALUATION.md` — what's measured, thresholds, how to add a case.

## Testing

- The runner has unit tests: each deterministic checker passes/fails on crafted fixtures (a blame-language
  case must fail; a citation-missing case must fail).
- Champion/challenger: a synthetic worse challenger is **not** promoted; a better one is.
- Data-quality gate: a pull with out-of-range values / high null rate **halts**.
- Judge-unavailable path: deterministic checks still gate; groundedness marked "not evaluated" (not passed).

## Sequencing

- Depends on 002 + 004 existing (they do). **Best built after 005/006** (so the read API/dashboard are
  stable) and **alongside 007** (it plugs into that CI/CD + pipeline). It is not a jr first ticket.

## v2.0.0 amendment — LLM output evaluation & selection (FR-012/013/014)

Three additions, each reusing existing machinery:
- **FR-012 golden regression cases** — new `evals/cases/` files for the answer *types* that regressed
  (trend, value-for-money, ROI) + a deterministic `checks.answer_contains_any` asserting expected
  key-facts. A grounded row dump lacks the direction word → fails. Cheap, on the free gate.
- **FR-013 helpfulness judge** — a second judged dimension (`judge.judge_helpfulness`) beside
  groundedness; same discipline (pinned model, floor, not-evaluated-fail). The rubric is
  **context-aware**: SSA-only data scope and value-for-money framing are correct-by-design and must
  not be penalised (found in the live run — the judge first failed correct answers, so the rubric was
  tightened, then 6/6 passed).
- **FR-014 LLM champion/challenger** — `evals/select_model.py` scores candidate models on the golden
  eval (quality) + price table (cost) + measured latency, selects by quality-floor→cost→latency, and
  writes `evals/llm_selection.json`. The answer model is env-configurable (`ASK_MODEL`), so adopting
  the champion is config, not code. Manual/periodic (paid), never a per-PR gate. Mirrors `train.py`.

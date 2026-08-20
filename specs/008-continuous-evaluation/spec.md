# Feature Specification: Continuous Evaluation & Quality Gates

**Feature Branch**: `008-continuous-evaluation`

**Created**: 2026-08-19

**Status**: Draft — needs `/speckit.clarify` review before Accepted

**Depends on**: spec 002 (model + `/brief`), spec 004 (`/ask` agent). **Integrates with**: spec 007
(runs inside the CI/CD gate and the scheduled pipeline).

**Input**: Make the model and the two LLM features **measurably trustworthy** by evaluating them
automatically — in **CI** (catch regressions you cause) and **continuously in the pipeline** (catch
drift you didn't). Evaluation results **gate**: a worse model is not promoted; an AI regression fails
the merge. This turns quality — including the honest-modeling rule — from reviewer vigilance into an
enforced contract.

> **Constitution alignment:** Principle II (tests before code — evaluation *is* the test at the
> ML/LLM layer), Principle V (**honest modeling** — "no causal/blame language" becomes an automated
> gate, not a checklist), Principle I (the eval set uses only public data; no secrets committed).

## Why this is its own spec

You ship **two kinds of AI that fail differently**: a **regression model** (fails by silently
regressing or by input drift) and **two LLM features** (fail by hallucinating numbers, not citing,
answering when they should decline, or emitting blame language). They need different scores and gate at
different points — the model at **promotion time** in the pipeline, the LLM features at **merge time**
in CI. Bundling this into deployment would hide a first-class concern.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A regression can't ship (Priority: P1)

**Acceptance**:
1. **Given** a change to the AI code (prompts, agent, model config), **When** CI runs the eval set,
   **Then** a drop past the configured thresholds **fails the check** and blocks merge.
2. **Given** a passing change, **Then** the eval scores are recorded so the trend is visible.

### User Story 2 — A worse model is not promoted (Priority: P1)

**Acceptance**:
1. **Given** a scheduled retrain, **When** the challenger's cross-validated RMSE is worse than the
   current champion by more than the threshold, **Then** the pipeline **keeps the champion** and flags
   it — it does not publish the regressed model.
2. **Given** the incoming data fails a data-quality check (row count, ranges, null rate), **Then** the
   pipeline **halts before** the bad data reaches the mart.

### User Story 3 — Drift is caught even when nothing changed (Priority: P1)

**Acceptance**: on a schedule, the LLM eval set re-runs against the live model tier; a regression (e.g.
from a Claude version change) is recorded and **alerts**, even with no code change.

### User Story 4 — Honest framing is enforced (Priority: P1)

**Acceptance**: an eval case asserts that `/brief` and `/ask` outputs contain **no causal/blame
language** ("failing", "worst", "best/worst" rankings-as-judgement); a violation **fails** the eval
(Principle V).

### Edge Cases

- The judge model is unavailable → deterministic checks still run and gate; the groundedness score is
  marked "not evaluated" rather than silently passing.
- The eval set can't reach the mart/API → the eval **errors** (red), never passes vacuously.
- First run / no champion yet → the challenger becomes the champion (no gate to compare against).

## Requirements *(mandatory)*

### The eval set
- **FR-001** — A **versioned eval set** lives in the repo (`evals/`): a small, curated set of cases
  built from **public data only** — no secrets, no PII. Each case declares its expected properties.
- **FR-002** — Cases cover: **`/ask`** (grounded, cites, declines-when-unanswerable, refuses
  out-of-scope), **`/brief`** (schema-valid, numbers echo the model's predicted/actual/residual, honest
  framing), and the **model** (a held-out metric check + data-quality expectations).

### Scoring
- **FR-003** — **Deterministic checks** (the fast, free gate): schema validity, citation presence,
  correct decline behavior, numbers-match-source, and a **banned-language** check for causal/blame
  wording (Principle V).
- **FR-004** — **LLM-as-judge** for the one fuzzy dimension — **groundedness** (do the answer's claims
  trace to actual mart rows?). The judge runs against a **pinned model + fixed rubric**, returns a
  score + rationale, and is **only advisory-plus-threshold** (a low groundedness score fails; the judge
  never *invents* a pass). *(Deterministic-only is an accepted fallback — resolve in `/speckit.clarify`.)*
- **FR-005** — Every run writes a **scored report** (per-case pass/fail + aggregate) to a durable
  location, so scores are a **trend over time**, not a single boolean.

### Model gate (pipeline)
- **FR-006** — **Champion/challenger**: the pipeline compares the retrained model's **5-fold CV RMSE**
  to the stored champion's; it **promotes only if not worse** than the threshold, else keeps the
  champion and flags it. The decision is recorded in the model metadata.
- **FR-007** — **Data-quality gate**: before the mart is rebuilt, the incoming pull is checked (expected
  row count range, indicator value ranges, null rate); a failure **halts** the pipeline (no bad data in
  `published`).

### Wiring (into spec 007)
- **FR-008** — **CI gate**: the deterministic eval suite (and, when enabled, the judge) runs in the
  GitHub Actions workflow on changes to the model/AI/eval code and **blocks merge** on failure.
- **FR-009** — **Continuous run**: the eval set re-runs on a **schedule** against the live stack; results
  are recorded and a regression past threshold **alerts** (even with no code change).
- **FR-010** — **Thresholds are config, not magic numbers**: RMSE-regression tolerance, groundedness
  floor, banned-language list, and data-quality bounds live in one documented config file.

### Cost & determinism
- **FR-011** — The **default CI gate is deterministic and free**; the judge (paid, non-deterministic) is
  a **separate, throttled** step (e.g. on merge to `develop`/`main` and on the schedule), so PR feedback
  is fast and cheap.

## Success Criteria *(mandatory)*

- **SC-001**: A prompt/agent change that breaks citing or grounding **fails CI** and cannot merge.
- **SC-002**: A retrain that regresses CV RMSE past the threshold is **not promoted**; the champion stays.
- **SC-003**: A pull that violates data-quality bounds **halts** before reaching `published`.
- **SC-004**: A `/brief` or `/ask` output containing causal/blame language **fails** an eval case.
- **SC-005**: Eval scores are **recorded over time** (a trend is queryable), not just pass/fail.
- **SC-006**: The scheduled run catches a model-tier-induced regression with **no code change**.
- **SC-007**: The deterministic gate runs with **no paid model calls**; the judge is opt-in/throttled.

## Out of Scope

- Human-labeling UI / annotation tooling (the eval set is curated in-repo).
- A/B testing in production, online experimentation, user-feedback capture.
- Replacing the model-selection logic in 002 (this **gates** it; it doesn't redesign it).
- Full observability/tracing platform (a scored report + alert is enough; deep tracing is a stretch).

## Dependencies & risks (for the plan phase)

- **Judge cost/flakiness** — keep the judge off the fast PR path (FR-011); pin its model + rubric so its
  own drift doesn't masquerade as a regression.
- **Champion storage** — the champion's metrics (and, per 007, the artifact) must persist between runs
  (metadata in RDS / artifact in S3) for the gate to compare against.
- **Eval-set maintenance** — a stale eval set gives false confidence; treat it as versioned code with
  its own review.

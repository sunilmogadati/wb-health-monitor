# ADR-0009: LLM selection criteria (champion/challenger)

**Status:** Accepted

**Date:** 2026-08-20

## Context

ADR-0005 decided *"use Anthropic Claude via the API"* but not **which model** for **which task**, and
we had no way to compare candidates. In practice the models were pinned ad hoc — `/ask` on
`claude-sonnet-4-5`, the judge on `claude-sonnet-4-5`, `/brief` on an `ANTHROPIC_MODEL` env that was
silently 404ing on a haiku default until it was fixed. That is exactly the un-governed drift the ML
side does *not* have: the trained model is chosen by a 5-fold CV-RMSE **champion/challenger** with the
rationale written to metadata. The LLM deserves the same discipline.

## Decision

Select the `/ask` answer model by a **champion/challenger** scored on the **golden eval**, not a hunch
(`evals/select_model.py`, spec 008 FR-014):

1. Run the answerable golden `/ask` cases through each **candidate model** (via `/ask?model=`).
2. Score **quality** with the *same* checks as the gate — deterministic (decline, citations,
   key-facts) **+ groundedness + helpfulness** judges — as a pass fraction.
3. Record **cost** (output $/1M from a documented price table) and **latency** (measured wall-clock).
4. **Select by rule:** models at/above a **quality floor** first, then **lowest cost**, then
   **latency**. If none clear the floor, take the highest quality (never a vacuous pick).
5. Write the candidates, scores, champion, and rationale to `evals/llm_selection.json` (mirrors the ML
   model's `selection_rationale`).

The answer model is **configurable** (`ASK_MODEL` env, bounded by an allowlist): adopting the champion
is a **config change, not a code edit**. The harness makes paid calls across models, so it is a
**manual/periodic** tool (like retraining), never a per-PR gate.

## Alternatives considered

- **Pin the biggest model always** — simplest, but pays Opus prices where Sonnet/Haiku clear the
  quality bar; no evidence, no record.
- **Pick by latency/price alone** — cheap, but a cheaper model that fails groundedness/helpfulness is
  worse than useless. Quality must gate first.
- **A separate bespoke benchmark** — the golden eval already encodes what "good" means (grounded,
  helpful, honest, declines correctly); reusing it keeps one definition of quality.

## Consequences

- **+** The LLM choice is evidence-based, recorded, and re-runnable when models or prices change —
  symmetric with the ML champion/challenger.
- **+** Quality is the same bar the gate enforces, so a "cheaper" pick can't quietly regress answers.
- **+** Switching champions is one env var.
- **−** The selection run costs paid calls across candidates; mitigated by keeping it manual/periodic
  and the candidate list small.
- **−** The price table is a **list-price proxy** for cost, not a measured per-question spend; good
  enough for a relative ranking, and documented as such.

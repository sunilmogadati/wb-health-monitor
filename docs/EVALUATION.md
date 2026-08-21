# Evaluation — how we keep the model and the AI trustworthy

Spec **008** turns quality — including the honest-modeling rule — from *reviewer vigilance* into an
**enforced contract**. Two things are evaluated automatically: the **trained model** (a regression
metric gate) and the **LLM features** (`/ask`, `/brief`, the agent). Everything lives in
`backend/evals/` + `backend/ml/train.py`, and the bounds live in one file: `backend/evals/thresholds.json`.

## The two-tier scoring

| Tier | What | Cost | When |
|---|---|---|---|
| **Deterministic checks** | schema validity, citations present, correct decline behavior, numbers-match-source, **banned-language** (no causal/blame — Principle V), and **expected key-facts** per case | free, no LLM | every PR (CI) |
| **LLM-as-judge** | **groundedness** (do the answer's claims trace to the cited rows?) + **helpfulness** (does it actually answer, not just dump rows?) | paid, throttled | on merge/schedule, not the PR path |

The judge runs against a **pinned model + fixed rubric**, returns a score + rationale against a floor,
and a judge that can't run is a **not-evaluated FAIL — never a vacuous pass**. Groundedness alone
passes a grounded-but-useless row dump; **helpfulness** is the dimension that catches it. The
helpfulness rubric is **context-aware**: the Sub-Saharan-Africa data scope and the value-for-money
framing are correct-by-design and are not penalised.

## The golden set (regression cases)

`backend/evals/cases/*.json` — a small, versioned set of cases over public data only. Each answerable
case asserts **expected key-facts** (a `contains_any` on the answer), so a grounded-but-wrong answer
fails. The set includes **regression cases for bugs we actually fixed** — a trend question that once
dumped rows instead of stating the trend, and a value-for-money question that once wrongly declined —
so those regressions can't re-merge green.

## Champion / challenger (two of them)

- **ML model** (`train.py`, FR-006): a retrained model is promoted only if its **5-fold CV RMSE** is
  **not worse** than the current champion by more than the tolerance; the decision + rationale are
  written to the model metadata.
- **LLM** (`evals/select_model.py`, FR-014 / ADR-0009): the choice of `/ask` model is made by the
  **golden eval**, not a hunch — candidate models are scored on quality (deterministic + both judges),
  **cost** (a price table), and **latency**, and selected by *quality-floor → cost → latency*. The
  champion is recorded in `evals/llm_selection.json`; adopting it is a config change (`ASK_MODEL`), not
  a code edit. *(Live example run: Haiku cleared the quality floor at ~3× lower cost + ~2× faster than
  Sonnet.)*

## Data-quality gate (feeds the same discipline)

Before the mart is rebuilt, the incoming pull is checked (row-count range, indicator value ranges, null
rate) and anomalies are flagged (robust-z on bounded columns + year-over-year volatility). A breach
past the tripwire **halts** the pipeline (no bad data in `published`); flagged cells are nulled in the
mart, not silently kept. See **ADR-0004** (filter + tripwire) and **ADR-0007** (detect at the staging
boundary — shift-left).

## Where it runs

- **CI** — the deterministic checkers are unit-tested on every PR (`tests/test_evals.py`); a failure
  blocks merge.
- **Scheduled / on-merge** — `python -m evals.run` runs the full suite against the live stack
  (`.github/workflows/evals.yml`, weekly cron + dispatch); the judge runs if `ANTHROPIC_API_KEY` is
  set, else it gates on the deterministic checks alone and says so.

## Try it

```bash
# deterministic gate against the local stack (no key needed):
cd backend && python -m evals.run --deterministic-only
# with the judges (needs ANTHROPIC_API_KEY):
cd backend && python -m evals.run
# LLM champion/challenger (paid; needs a key + the stack up):
cd backend && python -m evals.select_model
```

Full requirements + success criteria: `specs/008-continuous-evaluation/spec.md`.

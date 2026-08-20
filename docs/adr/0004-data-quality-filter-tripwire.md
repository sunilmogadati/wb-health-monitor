# ADR-0004: Data quality — filter + tripwire gate with anomaly detection

- **Status:** Accepted
- **Date:** 2026-08-20

## Context
Public, authoritative sources contain real errors. This platform hit one: the World Bank API returns an
impossible life expectancy (`18.8`) for a country-year, and the model was silently training on it. A
model trained on bad data fails silently — the worst failure mode.

## Decision
Validate model-ready data with a **filter + tripwire** gate (spec 008), run before training/publishing:
- **Detect** with three complementary methods: static ranges, **robust-z** (median + MAD, for
  bounded/unimodal columns), and **year-over-year volatility** (a value that breaks its own history).
- **Respond proportionally:** drop a few flagged rows (isolated source noise); **halt** only if the
  flagged *fraction* exceeds a threshold (systemic break).

## Alternatives considered
- **Trust the source:** rejected — it demonstrably ships errors.
- **Hard-halt on any bad value:** too brittle — one bad source cell would block the whole pipeline for
  data we don't control.
- **Static ranges only:** needs domain knowledge for every feature; misses anomalies in features nobody
  has intuition about. The statistical detectors catch those with no hand-set bounds.
- **Great Expectations / Pandera now:** good production tools, but the hand-rolled detectors keep the
  logic transparent and dependency-light; adopt a framework if the checks grow.

## Consequences
- Bad rows are excluded, not silently trained on; removing 7 corrupted rows **improved the model
  (RMSE 3.27 → 2.72)**.
- **Method must fit the feature:** robust-z on a skewed *level* variable (GDP) false-positives on
  genuinely rich/poor entities — so robust-z runs only on bounded/unimodal columns; skewed variables
  use YoY or a log transform. A flag is a *candidate*, confirmed by a human or an independent source.

# Implementation Plan: Country Health Model & Brief (spec 002)

**Status**: For review · **Spec**: `spec.md` (Accepted) · **Author**: maintainer

## Summary

Implement the country-health model as a governed, tested slice that reads the **`published`** mart,
trains and compares four models, persists residuals as the value-for-money signal, generates a
Claude-backed `CountryHealthBrief`, and serves both over the API.

## Technical context

- **Language/deps**: Python; `backend[ml,warehouse,ai]` (pandas, scikit-learn, xgboost, joblib; dbt for
  the mart; anthropic/langchain-anthropic for the brief).
- **Read surface**: `published.country_year_indicators` (built by `make dbt-build`). No pivoting of
  `staging` in app code.
- **Artifacts**: winning model → `backend/models/life_expectancy.joblib` (gitignored). Residuals →
  a Postgres table (below).
- **Serve**: FastAPI endpoints in `backend/app/`.

## Constitution check (gate)

- **I Public data only** ✅ WB indicators via the governed pipeline. No keys in code.
- **II Spec-driven, test-backed** ✅ tests accompany the code (`make test`).
- **III Governed pipeline** ✅ reads only `published`; residuals written to a declared table.
- **IV Conformed model** ✅ consumes the star's mart, does not re-shape raw.
- **V Honest modeling** ✅ residual = actual − predicted = **value-for-money** signal; language is
  association, never causal/blame. No "failing" countries.
- **VI Reproducible** ✅ `make train` deterministic (fixed seed); DB containerized.

## Design decisions

1. **Feature source** — `features.py` selects from `published.country_year_indicators` (target +
   4 features). Drop rows missing the target; document the null policy for features.
2. **Models** — Linear, DecisionTree, RandomForest, XGBoost on one seeded 80/20 split; metrics
   R²/MAE/RMSE; select the winner by lowest RMSE, record the rationale.
3. **Residuals** — predict with the winner over **all** rows; write
   `country_code, year, actual, predicted, residual` to **`published.model_residual`** (a table the
   dashboard/insights can read). Framed as value-for-money.
4. **Model artifact** — `joblib.dump` to `backend/models/life_expectancy.joblib`.
5. **Brief** — fill `brief.py`'s Claude call with `langchain-anthropic` `with_structured_output`
   against `CountryHealthBrief`; keep the deterministic no-key fallback.
6. **API** — `backend/app/`: `GET /api/v1/predict?country=&year=` and `GET /api/v1/brief?country=&year=`;
   load the model once at startup; read the row from the mart.

## Data flow

`published.country_year_indicators → features → train (4 models) → winner.joblib + published.model_residual → API (predict / brief)`

## Files

- edit `backend/ml/features.py`, `backend/ml/train.py`, `backend/ml/brief.py`
- add a router under `backend/app/` for `/predict` and `/brief`
- add/extend tests in `tests/`

## Testing

- Existing `tests/test_ml.py` (brief schema + honest framing) stays green.
- Add a smoke test: features returns rows from the mart; `/predict` returns a number for a known
  country-year.
- `make train` and `make test` green; honest-framing check (SC-006).

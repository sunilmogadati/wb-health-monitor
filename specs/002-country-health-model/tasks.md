# Tasks: Country Health Model & Brief (spec 002)

**Status**: For review · **Plan**: `plan.md` · Work these in order; each maps to a spec FR / SC.

## Phase 1 — Feature table (from the mart)
- [ ] **T001** `features.py`: read features from `published.country_year_indicators` (target + 4 features); drop rows missing the target. (FR-002)
- [ ] **T002** Verify: `feature_rows()` returns rows sourced from the mart (not a staging pivot).

## Phase 2 — Train & compare
- [ ] **T003** `train.py`: add **XGBoost** to `candidate_models()`. (FR-003)
- [ ] **T004** `train.py`: fit all four on one seeded 80/20 split; print R²/MAE/RMSE comparison; select winner by RMSE + record rationale. (FR-003/FR-004)
- [ ] **T005** `train.py`: save the winner to `backend/models/life_expectancy.joblib`. (FR-006)
- [ ] **T006** `train.py`: predict over all rows; write `country_code, year, actual, predicted, residual` to `published.model_residual`. Value-for-money framing. (FR-005/FR-009)

## Phase 3 — Brief
- [ ] **T007** `brief.py`: implement the Claude structured-output call (`langchain-anthropic`) filling `CountryHealthBrief`; keep the deterministic no-key fallback. (FR-007/FR-008)

## Phase 4 — API
- [ ] **T008** `backend/app/`: `GET /api/v1/predict?country=&year=` — load model, read the mart row, return the prediction.
- [ ] **T009** `backend/app/`: `GET /api/v1/brief?country=&year=` — return the `CountryHealthBrief`.

## Phase 5 — Tests & gate
- [ ] **T010** Add a smoke test: features returns mart rows; `/predict` returns a number for a known country-year. (FR-010)
- [ ] **T011** `make train` and `make test` green; confirm no causal/blame language (SC-006).

## Phase 6 — Ship
- [ ] **T012** PR into `develop`; maintainer reviews against the spec's Success Criteria.

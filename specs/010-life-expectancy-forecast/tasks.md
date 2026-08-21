# Tasks: Life-Expectancy Forecast

**Spec** 010 · **Plan** `plan.md` · TDD — tests land before/with the code they cover.

## v1.0.0 — forecast capability (done, PR #26)

- [x] **T001** — `tests/test_forecast.py`: pure-projection unit tests (recover a known slope; clamp
      internet ≤ 100 and fertility ≥ floor; `< MIN_POINTS` → `None`). *(FR-002, FR-003, FR-005)*
- [x] **T002** — `backend/ml/forecast.py`: `FEATURE_BOUNDS`, `MIN_POINTS`, `_project_linear`,
      `_clamp`, `forecast_features`. *(FR-001, FR-002, FR-003, FR-005)*
- [x] **T003** — `backend/ml/features.py`: `country_history(conn, country)` + `max_year(conn)`.
- [x] **T004** — `tests/test_forecast.py`: endpoint contract (future year → forecast + `is_forecast`
      + projected inputs + caveat; year ≤ latest → 400 → `/predict`; sparse history → 422).
      *(FR-001, FR-004, FR-005, FR-006)*
- [x] **T005** — `backend/app/main.py`: `ForecastResponse` + `GET /forecast` wiring. *(FR-001, FR-004,
      FR-006)*
- [x] **T006** — `frontend/src/lib/api.ts`: `ForecastResponse` type + `getForecast(country, year)`.
- [x] **T007** — `frontend/src/components/PredictionPanel.tsx`: future years (2023–2028); on a future
      year call `/forecast` and render the forecast card (projected inputs + caveat + badge). *(FR-007)*
- [x] **T008** — `frontend/src/components/__tests__/PredictionPanel.test.tsx`: forecast-mode render. *(FR-007)*
- [x] **T009** — Verify live: `make up && make train`; `/forecast?country=KEN&year=2028`; dashboard
      future-year path. Updated `docs/PROJECT_BRIEF.md` build status.

## v1.1.0 — indicative interval (FR-009, this amendment)

- [x] **T010** — `tests/test_forecast.py`: `indicative_interval` unit tests (low ≤ point ≤ high; band
      **widens** with horizon; low clamped ≥ 0). *(FR-009, SC-005)*
- [x] **T011** — `backend/ml/forecast.py`: `indicative_interval(point, cv_rmse, horizon_years)`.
- [x] **T012** — `backend/app/main.py`: read the selected model's `cv_rmse` from metadata; add
      `forecast_low`, `forecast_high`, `interval_method` to `ForecastResponse`. *(FR-009)*
- [x] **T013** — `frontend`: `getForecast` type + `PredictionPanel` render the range next to the
      point (e.g. "60.9 yrs · indicative 55–66"). Update the forecast-mode test. *(FR-009, SC-005)*
- [x] **T014** — Verify live + update `docs/PROJECT_BRIEF.md`.

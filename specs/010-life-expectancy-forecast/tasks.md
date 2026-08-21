# Tasks: Life-Expectancy Forecast

**Spec** 010 · **Plan** `plan.md` · TDD — tests land before/with the code they cover.

- [ ] **T001** — `tests/test_forecast.py`: pure-projection unit tests (recover a known slope; clamp
      internet ≤ 100 and fertility ≥ floor; `< MIN_POINTS` → `None`). *(FR-002, FR-003, FR-005)*
- [ ] **T002** — `backend/ml/forecast.py`: `FEATURE_BOUNDS`, `MIN_POINTS`, `_project_linear`,
      `_clamp`, `forecast_features`. *(FR-001, FR-002, FR-003, FR-005)*
- [ ] **T003** — `backend/ml/features.py`: `country_history(conn, country)` + `max_year(conn)`.
- [ ] **T004** — `tests/test_forecast.py`: endpoint contract (future year → forecast + `is_forecast`
      + projected inputs + caveat; year ≤ latest → 400 → `/predict`; sparse history → 422).
      *(FR-001, FR-004, FR-005, FR-006)*
- [ ] **T005** — `backend/app/main.py`: `ForecastResponse` + `GET /forecast` wiring. *(FR-001, FR-004,
      FR-006)*
- [ ] **T006** — `frontend/src/lib/api.ts`: `ForecastResponse` type + `getForecast(country, year)`.
- [ ] **T007** — `frontend/src/components/PredictionPanel.tsx`: future years (2023–2028); on a future
      year call `/forecast` and render the forecast card (projected inputs + caveat + badge). *(FR-007)*
- [ ] **T008** — `frontend/src/components/__tests__`: PredictionPanel forecast-mode render test. *(FR-007)*
- [ ] **T009** — Verify live: `make up && make train`; `/forecast?country=KEN&year=2028`; dashboard
      future-year path. Update `docs/PROJECT_BRIEF.md` build status.

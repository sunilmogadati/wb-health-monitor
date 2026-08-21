# Implementation Plan: Life-Expectancy Forecast

**Spec**: `specs/010-life-expectancy-forecast/spec.md` · **Branch**: `forecast-feature`

## Constitution Check

- **I — Public data only**: reuses the published mart; no new data source, no keys. ✅
- **II — Tests first**: `tests/test_forecast.py` (pure projection unit tests + endpoint contract) is
  written before wiring. ✅
- **V — Honest Modeling**: `is_forecast` flag, projected inputs surfaced, qualitative caveat, plausible
  clamps. No causal/best-worst language. ✅
- **VI — Deterministic/containerized**: least-squares trend is deterministic; no RNG; runs in the
  existing api container. ✅
- **Change Traceability**: New-capability lane → this spec is the artifact. ✅

## Approach

Keep the *projection* logic pure and DB/model-free so it is trivially testable; wire DB + model in
the endpoint.

1. **`backend/ml/forecast.py`** (pure): `forecast_features(history, target_year) -> dict|None`.
   - Per feature: collect `(year, value)` observed points, fit a least-squares line, evaluate at
     `target_year`, clamp to `FEATURE_BOUNDS`. Return `None` if any feature has `< MIN_POINTS` points.
2. **`backend/ml/features.py`**: add `country_history(conn, country)` (all rows for a country) and
   `max_year(conn)` (latest observed year, for the ≤-guard).
3. **`backend/app/main.py`**: add `ForecastResponse` + `GET /forecast`. Reuses `_load_model`,
   `_feature_frame`, `_model_name`. 400 for `year <= max_year`; 404 no history; 422 too little history.
4. **Frontend**: `getForecast()` in `lib/api.ts`; `PredictionPanel` gains future years (2023–2028) and
   renders a forecast card (projected inputs + caveat + "forecast" badge) when a future year is chosen.

## Method choice (why linear trend)

8 annual points per feature. A linear least-squares trend is the honest, inspectable baseline — it
won't overfit the way a higher-order extrapolator would, it's deterministic, and returning the
projected inputs lets a reader sanity-check them. Bounds stop it leaving the physically possible.
Deliberately **not** modelling feature interactions or a stochastic forecast — that is FR-008 scope.

## Test strategy

- Unit (pure): trend on a known line recovers the slope; clamps hold (internet ≤ 100); `< MIN_POINTS`
  → `None`.
- Contract (TestClient, monkeypatched conn + model): future year → forecast + `is_forecast`; year 2022
  → 400; sparse history → 422.

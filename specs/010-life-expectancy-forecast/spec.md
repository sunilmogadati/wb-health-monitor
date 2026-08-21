# Feature Specification: Life-Expectancy Forecast (project inputs → predict future years)

**Feature Branch**: `010-life-expectancy-forecast`

**Created**: 2026-08-20

**Status**: Accepted & implemented (2026-08-20) — merged in PR #26.

**Version**: 1.1.0

**Amendment history**:
- **1.1.0 (2026-08-20)** — spec-miss/scope amendment: promoted the deferred confidence-interval item
  (was FR-008 "out of scope") to an **in-scope requirement, FR-009** — an *indicative* range around
  the forecast. Reason: the point-forecast reads as more precise than it is; a range makes the
  uncertainty legible. Downstream `plan.md`/`tasks.md` re-run for the touched FR (see below).
- **1.0.0 (2026-08-20)** — initial forecast capability (FR-001–FR-008); clarify was folded into the
  spec (the `out of scope` boundary on FR-008 *was* the clarification), accepted, implemented.

**Input**: The model (`/predict`, spec 002) scores one country-year using that year's **observed**
features, so it stops at the last data year (2022). Users reasonably ask "what will life expectancy
be in 2028?". This spec adds a **forecast**: project each model input forward from its own history,
then score the projected inputs with the existing trained model — clearly labelled as a forecast,
not an observation.

> **Constitution alignment:** Principle I (public WB data only), Principle II (tests before code),
> Principle V (**Honest Modeling** — a forecast is a *scenario under "if current trends hold"*, never
> a certainty; uncertainty is surfaced, not hidden), Principle VI (deterministic — a linear trend is
> reproducible, no randomness), **Change Traceability** (this is a *new capability* → full lifecycle,
> not an ad-hoc edit).

## Why a new spec (not a bug or amendment)

`/predict` behaves exactly as spec 002 says — it is not broken. Forecasting future years is **new
behavior** (new inputs, new endpoint, new UI affordance, a new honesty obligation). Per the
Change-Traceability router that is the **New capability** lane → its own spec.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Forecast a future year for one country (Priority: P1)

A user selects a country and a year beyond the data (2023–2028) and gets a forecast life expectancy
with the projected inputs shown, plainly marked as a forecast.

**Why this priority**: this is the whole point — turn "predict what we already know" into "project
what we don't."

**Acceptance**:
1. **Given** a country with enough history, **When** the user requests year 2028, **Then** the
   response returns a `forecast_life_expectancy`, the **projected inputs** used, `is_forecast: true`,
   and the years the projection was fit on.
2. **Given** a year within the observed data (≤ 2022), **When** `/forecast` is called, **Then** it
   returns 400 and points the caller to `/predict` (forecasting an observed year is a category error).
3. **Given** a country with too little history to fit a trend, **When** a forecast is requested,
   **Then** it returns 422 with a clear reason (never a fabricated number).

### User Story 2 — Honesty of the forecast (Priority: P1)

**Acceptance**:
1. **Given** any forecast, **When** it is returned, **Then** it carries a caveat that the inputs are
   themselves projected ("if current trends hold") and that uncertainty grows with distance from 2022.
2. **Given** a projected input, **When** it is computed, **Then** it is **clamped to a physically
   plausible range** (e.g. internet penetration can't exceed 100%), so extrapolation never produces
   an impossible input.
3. **Given** the UI, **When** a future year is chosen, **Then** the result is visually distinguished
   from an observed prediction (a "forecast" label + the projected inputs are shown) — never presented
   as a measured value.

### User Story 3 — Surface it in the dashboard (Priority: P2)

**Acceptance**:
1. **Given** the prediction panel, **When** the user picks a year 2023–2028, **Then** the panel calls
   `/forecast` (instead of `/predict`+`/brief`) and renders the forecast + projected inputs + caveat.

## Requirements *(mandatory)*

- **FR-001**: A `/forecast?country=&year=` endpoint MUST project each model feature to the requested
  year and return the trained model's prediction on those projected features.
- **FR-002**: Feature projection MUST use a **deterministic, inspectable method** (a per-feature
  least-squares linear trend over that feature's observed history). No randomness (Principle VI).
- **FR-003**: Each projected feature MUST be **clamped to a documented plausible range**.
- **FR-004**: `/forecast` MUST reject years within the observed data (≤ latest mart year) with a 400
  that names `/predict` as the correct endpoint.
- **FR-005**: A country with fewer than the minimum required observed points for any feature MUST get
  a 422 (a forecast is declined, never faked).
- **FR-006**: Every forecast response MUST include `is_forecast: true`, the `projected_indicators`
  used, the `based_on_years`, and a caveat framing it as a trend scenario (Principle V).
- **FR-007**: The dashboard MUST offer future years and render forecasts distinctly from observed
  predictions, showing the projected inputs and the caveat.
- **FR-009 (added in v1.1.0)**: Every forecast MUST include an **indicative range**
  (`forecast_low`, `forecast_high`) around the point forecast, derived from the selected model's own
  out-of-sample error (`cv_rmse` in the model metadata) **widened with the forecast horizon** (inputs
  are extrapolated, so error compounds with distance). It MUST be labelled *indicative* (an
  `interval_method` string), NOT a formal statistical confidence interval — the input-projection
  uncertainty is not rigorously modelled, so over-claiming a 95% CI would be dishonest (Principle V).
  Deterministic: same inputs → same range (Principle VI). The dashboard MUST show the range with the
  point forecast.

  *(Superseded FR-008, "no interval — qualitative caveat only", from v1.0.0.)*

### Key Entities

- **ForecastResponse**: `country_code, country_name, year, projected_indicators{feature→value},
  forecast_life_expectancy, is_forecast, based_on_years[], caveat, model`.

## Success Criteria *(mandatory)*

- **SC-001**: `/forecast?country=KEN&year=2028` returns a plausible life expectancy with projected
  inputs and `is_forecast: true`.
- **SC-002**: `/forecast` for 2022 returns 400 pointing to `/predict`.
- **SC-003**: Projected `internet_pct` never exceeds 100; `fertility_rate` never below its floor.
- **SC-004**: The dashboard, on a future year, shows a forecast labelled as such with its projected
  inputs and caveat — no user could mistake it for a measured value.
- **SC-005 (v1.1.0)**: Every forecast response carries `forecast_low` ≤ `forecast_life_expectancy` ≤
  `forecast_high`, the band **widens** as the target year moves further past the last data year, and
  it is labelled *indicative* (not a 95% CI). The dashboard renders the range next to the point.

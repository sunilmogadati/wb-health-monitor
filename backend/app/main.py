"""FastAPI application factory.

Built at import time (`app = create_app()`) so that a missing required configuration value stops the
process before uvicorn binds a port, rather than failing on the first request. The module-level
`app` is what the container command imports: `uvicorn app.main:app`.
"""

from __future__ import annotations

import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ml.brief import CountryHealthBrief, build_brief
from ml.features import FEATURES, TARGET, connect, country_history, country_year_row, max_year
from ml.forecast import INTERVAL_METHOD, forecast_features, indicative_interval
from pydantic import BaseModel

from app.analytics import router as analytics_router
from app.ask import router as ask_router

API_V1_PREFIX = "/api/v1"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "life_expectancy.joblib"
METADATA_PATH = MODELS_DIR / "life_expectancy_metadata.json"

router = APIRouter(tags=["health"])


class PredictionResponse(BaseModel):
    country_code: str
    country_name: str
    year: int
    indicators: dict[str, float | None]
    predicted_life_expectancy: float
    actual_life_expectancy: float | None
    model: str


FORECAST_CAVEAT = (
    "Forecast, not an observation. The model's inputs for this future year are themselves "
    "projected from each indicator's recent trend, so read this as a scenario — 'if current trends "
    "hold' — not a measurement. Uncertainty grows the further past the last data year you go."
)


class ForecastResponse(BaseModel):
    country_code: str
    country_name: str
    year: int
    projected_indicators: dict[str, float]
    forecast_life_expectancy: float
    forecast_low: float
    forecast_high: float
    interval_method: str
    is_forecast: bool
    based_on_years: list[int]
    caveat: str
    model: str


# The three honest projection bases for a trend-chart continuation (FR-010).
_SERIES_CAVEATS = {
    "model": (
        "Forecast: life expectancy from the model on projected inputs — a scenario, not a "
        "measurement. Uncertainty grows with the horizon."
    ),
    "trend": (
        "Projected by extrapolating this indicator's own recent trend. This indicator is a model "
        "*input*, so this is a trend projection, not a model prediction — a scenario, not a "
        "measurement."
    ),
    "none": "No forecast: this indicator is neither the model's target nor one of its inputs.",
}
MAX_FORECAST_YEAR = 2028


class ForecastPoint(BaseModel):
    year: int
    value: float


class ForecastSeriesResponse(BaseModel):
    country_code: str
    country_name: str
    indicator: str
    basis: str  # "model" | "trend" | "none"
    points: list[ForecastPoint]
    caveat: str


@router.get("/health", summary="Process status and the server's own clock")
def health() -> dict[str, Any]:
    """Liveness with the server clock. No dependency calls."""
    return {"status": "alive", "server_time_epoch": int(time.time())}


@router.get("/health/live", summary="Liveness probe")
def liveness() -> dict[str, str]:
    """200 whenever the process can execute this handler. No dependency calls."""
    return {"status": "alive"}


@router.get("/health/ready", summary="Readiness probe")
def readiness() -> dict[str, Any]:
    """Reports whether the service can serve. Extend with real dependency probes as they are added.

    Readiness always answers 200 when it can evaluate; a degraded dependency is a fact this endpoint
    reports (in the payload), not a failure of the endpoint itself.
    """
    return {"status": "healthy", "dependencies": {}}


@lru_cache
def _load_model() -> Any:
    if not MODEL_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Model artifact not found. Run `make train` before using predictions.",
        )
    try:
        import joblib
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Prediction dependencies are not installed. Install `backend[ml]`.",
        ) from exc
    return joblib.load(MODEL_PATH)


def _model_name() -> str:
    if not METADATA_PATH.exists():
        return MODEL_PATH.name
    try:
        import json

        metadata = json.loads(METADATA_PATH.read_text())
        return str(metadata.get("selected_model", MODEL_PATH.name))
    except (OSError, ValueError, TypeError):
        return MODEL_PATH.name


def _selected_cv_rmse() -> float:
    """The selected model's cross-validated RMSE from metadata — the width of the forecast interval.

    Falls back to a conservative default if metadata is absent/unreadable so a forecast still ships
    a (wider, honest) band rather than failing. Reuses the ``models`` table ``train.py`` writes.
    """
    default = 3.0
    if not METADATA_PATH.exists():
        return default
    try:
        import json

        metadata = json.loads(METADATA_PATH.read_text())
        selected = metadata.get("selected_model")
        for model in metadata.get("models", []):
            if model.get("model") == selected and model.get("cv_rmse") is not None:
                return float(model["cv_rmse"])
    except (OSError, ValueError, TypeError):
        return default
    return default


def _fetch_mart_row(country: str, year: int) -> dict[str, Any]:
    with connect() as conn:
        row = country_year_row(conn, country, year)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No published mart row found for {country} in {year}.",
        )
    return row


def _feature_frame(indicators: dict[str, float | None]) -> Any:
    try:
        import pandas as pd

        return pd.DataFrame([indicators], columns=FEATURES)
    except ImportError:
        return type("FeatureFrame", (), {"columns": FEATURES, "row": indicators})()


def _predict_from_row(row: dict[str, Any]) -> PredictionResponse:
    missing = [feature for feature in FEATURES if row.get(feature) is None]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient feature data for prediction: {', '.join(missing)}.",
        )

    indicators = {feature: row.get(feature) for feature in FEATURES}
    prediction = float(_load_model().predict(_feature_frame(indicators))[0])
    actual = row.get(TARGET)

    return PredictionResponse(
        country_code=str(row["country_code"]),
        country_name=str(row["country_name"]),
        year=int(row["year"]),
        indicators=indicators,
        predicted_life_expectancy=round(prediction, 2),
        actual_life_expectancy=None if actual is None else round(float(actual), 2),
        model=_model_name(),
    )


@router.get("/predict", response_model=PredictionResponse)
def predict(country: str, year: int) -> PredictionResponse:
    """Predict life expectancy for one country-year from the published mart."""
    row = _fetch_mart_row(country, year)
    return _predict_from_row(row)


@router.get("/brief", response_model=CountryHealthBrief)
def brief(country: str, year: int) -> CountryHealthBrief:
    """Return a schema-valid country health brief grounded in the mart and model output."""
    row = _fetch_mart_row(country, year)
    prediction = _predict_from_row(row)
    if prediction.actual_life_expectancy is None:
        raise HTTPException(
            status_code=422,
            detail="Actual life expectancy is required to compute the brief residual.",
        )
    return build_brief(
        country_code=prediction.country_code,
        country_name=prediction.country_name,
        year=prediction.year,
        indicators=prediction.indicators,
        predicted=prediction.predicted_life_expectancy,
        actual=prediction.actual_life_expectancy,
    )


@router.get("/forecast", response_model=ForecastResponse)
def forecast(country: str, year: int) -> ForecastResponse:
    """Forecast a *future* year by projecting the model's inputs forward, then scoring (spec 010).

    Unlike ``/predict`` (which needs an observed mart row), this works past the data: each feature
    is extrapolated from its own history, then the trained model scores the projected inputs. The
    result is explicitly a forecast — inputs are estimates, uncertainty grows with distance (V).
    """
    with connect() as conn:
        latest = max_year(conn)
        if latest is not None and year <= latest:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"/forecast is for future years only (> {latest}). "
                    f"Use /predict for observed years like {year}."
                ),
            )
        history = country_history(conn, country)

    if not history:
        raise HTTPException(
            status_code=404, detail=f"No published history found for {country}."
        )

    projected = forecast_features(history, year)
    if projected is None:
        raise HTTPException(
            status_code=422,
            detail=f"Not enough history to project all model inputs for {country} to {year}.",
        )

    prediction = float(_load_model().predict(_feature_frame(dict(projected)))[0])
    based_on_years = sorted({int(row["year"]) for row in history})
    horizon = year - (latest if latest is not None else based_on_years[-1])
    low, high = indicative_interval(prediction, _selected_cv_rmse(), horizon)
    first = history[0]
    return ForecastResponse(
        country_code=str(first["country_code"]),
        country_name=str(first["country_name"]),
        year=year,
        projected_indicators=projected,
        forecast_life_expectancy=round(prediction, 2),
        forecast_low=low,
        forecast_high=high,
        interval_method=INTERVAL_METHOD,
        is_forecast=True,
        based_on_years=based_on_years,
        caveat=FORECAST_CAVEAT,
        model=_model_name(),
    )


@router.get("/forecast/series", response_model=ForecastSeriesResponse)
def forecast_series(
    country: str, indicator: str, to_year: int = MAX_FORECAST_YEAR
) -> ForecastSeriesResponse:
    """Projected FUTURE points for one indicator, continuing the trend chart past the data (FR-010).

    Only three projection bases exist, and each is disclosed honestly (Principle V):
    - ``life_expectancy`` (the model's target) → ``basis="model"``: project the inputs, predict.
    - a model **input** indicator → ``basis="trend"``: the projected input value itself (NOT a model
      output).
    - anything else (e.g. ``under5_mortality``) → ``basis="none"``: no points; never fabricated.

    Returns future points only; the observed series comes from ``/timeseries``.
    """
    with connect() as conn:
        latest = max_year(conn)
        history = country_history(conn, country)

    if not history:
        raise HTTPException(status_code=404, detail=f"No published history found for {country}.")

    first = history[0]
    base = ForecastSeriesResponse(
        country_code=str(first["country_code"]),
        country_name=str(first["country_name"]),
        indicator=indicator,
        basis="none",
        points=[],
        caveat=_SERIES_CAVEATS["none"],
    )
    if indicator != TARGET and indicator not in FEATURES:
        return base  # not projectable — honest empty result, not an error

    start = (latest if latest is not None else int(history[-1]["year"])) + 1
    end = min(to_year, MAX_FORECAST_YEAR)
    is_target = indicator == TARGET
    model = _load_model() if is_target else None

    points: list[ForecastPoint] = []
    for year in range(start, end + 1):
        projected = forecast_features(history, year)
        if projected is None:
            break  # not enough history to project — stop rather than fake later years
        if is_target and model is not None:
            value = float(model.predict(_feature_frame(dict(projected)))[0])
        else:
            value = projected[indicator]
        points.append(ForecastPoint(year=year, value=round(value, 2)))

    basis = "model" if is_target else "trend"
    return base.model_copy(
        update={"basis": basis, "points": points, "caveat": _SERIES_CAVEATS[basis]}
    )


def create_app() -> FastAPI:
    """Build the application."""
    app = FastAPI(
        title="wb-health-monitor API",
        version="1.0.0",
        description=(
            "wb-health-monitor platform API. Every endpoint is served under the versioned "
            "base path."
        ),
        docs_url=f"{API_V1_PREFIX}/docs",
        redoc_url=f"{API_V1_PREFIX}/redoc",
        openapi_url=f"{API_V1_PREFIX}/openapi.json",
    )
    # CORS so the Next.js dashboard (spec 006) can call the read API (spec 005) from its origin.
    origins = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET"],
            allow_headers=["*"],
        )

    app.include_router(router, prefix=API_V1_PREFIX)
    app.include_router(analytics_router, prefix=API_V1_PREFIX)
    app.include_router(ask_router, prefix=API_V1_PREFIX)
    return app


app = create_app()

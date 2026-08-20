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
from ml.features import FEATURES, TARGET, connect, country_year_row
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
    # CORS so the Next.js/React dashboard (spec 006) can call the read API (spec 005)
    # from its origin.
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

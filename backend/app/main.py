"""FastAPI application factory.

Built at import time (`app = create_app()`) so that a missing required configuration value stops the
process before uvicorn binds a port, rather than failing on the first request. The module-level
`app` is what the container command imports: `uvicorn app.main:app`.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, FastAPI

from app.ask import router as ask_router

API_V1_PREFIX = "/api/v1"

router = APIRouter(tags=["health"])


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


def create_app() -> FastAPI:
    """Build the application."""
    app = FastAPI(
        title="wb-health-monitor API",
        version="1.0.0",
        description="wb-health-monitor platform API. Every endpoint is served under the versioned base path.",
        docs_url=f"{API_V1_PREFIX}/docs",
        redoc_url=f"{API_V1_PREFIX}/redoc",
        openapi_url=f"{API_V1_PREFIX}/openapi.json",
    )
    app.include_router(router, prefix=API_V1_PREFIX)
    app.include_router(ask_router, prefix=API_V1_PREFIX)
    return app


app = create_app()

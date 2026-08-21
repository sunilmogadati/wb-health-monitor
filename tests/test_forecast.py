"""Forecast tests for spec 010 — project inputs forward, then predict a future year.

Split in two: the projection math is pure (no DB, no model) and unit-tested directly; the endpoint
contract is exercised through the FastAPI TestClient with the DB + model monkeypatched out.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from ml.features import FEATURES
from ml.forecast import MIN_POINTS, _project_linear, forecast_features

from app import main as app_main

# --- pure projection (FR-002, FR-003, FR-005) ---------------------------------------------------


def test_project_linear_recovers_a_known_slope() -> None:
    # y = 2*year - 4000 → at 2028 should be 56.0
    points = [(2018, 36.0), (2019, 38.0), (2020, 40.0), (2021, 42.0)]
    assert _project_linear(points, 2028) == 56.0


def test_project_linear_declines_with_too_few_points() -> None:
    assert _project_linear([(2020, 40.0), (2021, 42.0)], 2028) is None


def _history(**overrides: list[float | None]) -> list[dict[str, Any]]:
    """8 country-years 2015-2022 with linearly-rising features; override any feature's series."""
    years = list(range(2015, 2023))
    base = {
        "health_spend_pct_gdp": [4.0 + 0.1 * i for i in range(8)],
        "gdp_per_capita": [1000.0 + 100.0 * i for i in range(8)],
        "internet_pct": [20.0 + 8.0 * i for i in range(8)],  # rising toward/over 100
        "fertility_rate": [5.0 - 0.1 * i for i in range(8)],
        "life_expectancy": [60.0 + 0.3 * i for i in range(8)],
    }
    base.update(overrides)
    return [
        {"country_code": "KEN", "country_name": "Kenya", "year": y, **{f: base[f][i] for f in base}}
        for i, y in enumerate(years)
    ]


def test_forecast_features_projects_every_feature() -> None:
    projected = forecast_features(_history(), 2028)
    assert projected is not None
    assert set(projected) == set(FEATURES)


def test_forecast_features_clamps_internet_to_100() -> None:
    # internet rises 8pts/yr from 20% → the 2028 trend overshoots 100; must clamp (FR-003).
    projected = forecast_features(_history(), 2028)
    assert projected is not None
    assert projected["internet_pct"] == 100.0


def test_forecast_features_declines_when_a_feature_is_too_sparse() -> None:
    # Only two observed internet points → can't project that feature → whole forecast declines.
    sparse = [None] * 8
    sparse[0], sparse[1] = 20.0, 28.0
    assert forecast_features(_history(internet_pct=sparse), 2028) is None
    assert MIN_POINTS == 3  # documents the threshold the test relies on


# --- endpoint contract (FR-001, FR-004, FR-005, FR-006) -----------------------------------------


class _FakeConn:
    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _FakeModel:
    def predict(self, frame: object) -> list[float]:
        assert list(frame.columns) == FEATURES  # type: ignore[attr-defined]
        return [64.7]


def _wire(monkeypatch, latest: int, history: list[dict[str, Any]]) -> TestClient:
    monkeypatch.setattr(app_main, "connect", lambda: _FakeConn())
    monkeypatch.setattr(app_main, "max_year", lambda conn: latest)
    monkeypatch.setattr(app_main, "country_history", lambda conn, country: history)
    monkeypatch.setattr(app_main, "_load_model", lambda: _FakeModel())
    monkeypatch.setattr(app_main, "_model_name", lambda: "fake_model")
    return TestClient(app_main.app)


def test_forecast_future_year_returns_labelled_forecast(monkeypatch) -> None:
    client = _wire(monkeypatch, latest=2022, history=_history())
    response = client.get("/api/v1/forecast?country=KEN&year=2028")

    assert response.status_code == 200
    body = response.json()
    assert body["is_forecast"] is True
    assert body["year"] == 2028
    assert body["forecast_life_expectancy"] == 64.7
    assert set(body["projected_indicators"]) == set(FEATURES)
    assert body["based_on_years"] == list(range(2015, 2023))
    assert "if current trends hold" in body["caveat"]


def test_forecast_rejects_observed_year_and_points_to_predict(monkeypatch) -> None:
    client = _wire(monkeypatch, latest=2022, history=_history())
    response = client.get("/api/v1/forecast?country=KEN&year=2022")

    assert response.status_code == 400
    assert "/predict" in response.json()["detail"]


def test_forecast_declines_when_history_too_sparse(monkeypatch) -> None:
    sparse = [None] * 8
    sparse[0], sparse[1] = 20.0, 28.0
    client = _wire(monkeypatch, latest=2022, history=_history(internet_pct=sparse))
    response = client.get("/api/v1/forecast?country=KEN&year=2028")

    assert response.status_code == 422


def test_forecast_unknown_country_returns_404(monkeypatch) -> None:
    client = _wire(monkeypatch, latest=2022, history=[])
    response = client.get("/api/v1/forecast?country=ZZZ&year=2028")

    assert response.status_code == 404

"""Analytics read API contract tests for spec 005."""

from __future__ import annotations

from typing import Any

import psycopg
from fastapi.testclient import TestClient

from app import analytics
from app.main import app


class _Description:
    def __init__(self, name: str) -> None:
        self.name = name


class _Cursor:
    def __init__(
        self,
        columns: list[str],
        rows: list[tuple[Any, ...]],
        error: Exception | None = None,
    ) -> None:
        self.description = [_Description(column) for column in columns]
        self.rows = rows
        self.error = error
        self.sql = ""
        self.params: tuple[Any, ...] | None = None

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.sql = sql
        self.params = params
        if self.error is not None:
            raise self.error

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self.rows


class _Connection:
    def __init__(self, cursor: _Cursor) -> None:
        self.cursor_obj = cursor

    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def cursor(self) -> _Cursor:
        return self.cursor_obj


def _client_with_cursor(monkeypatch, cursor: _Cursor) -> TestClient:
    monkeypatch.setattr(analytics, "connect", lambda: _Connection(cursor))
    return TestClient(app)


def _assert_published_only(sql: str) -> None:
    lowered = sql.lower()
    assert "published.country_year_indicators" in lowered or "published.model_residual" in lowered
    assert "staging." not in lowered
    assert "warehouse." not in lowered
    assert "raw." not in lowered


def test_countries_returns_country_list_from_published(monkeypatch) -> None:
    cursor = _Cursor(
        ["country_code", "country_name"],
        [("KEN", "Kenya"), ("NGA", "Nigeria")],
    )
    response = _client_with_cursor(monkeypatch, cursor).get("/api/v1/countries")

    assert response.status_code == 200
    assert response.json() == [
        {"country_code": "KEN", "country_name": "Kenya"},
        {"country_code": "NGA", "country_name": "Nigeria"},
    ]
    _assert_published_only(cursor.sql)


def test_timeseries_returns_indicator_values_by_year(monkeypatch) -> None:
    cursor = _Cursor(
        ["year", "indicator", "value"],
        [(2019, "life_expectancy", 60.4), (2020, "life_expectancy", None)],
    )
    response = _client_with_cursor(monkeypatch, cursor).get(
        "/api/v1/timeseries?country=KEN&indicator=life_expectancy"
    )

    assert response.status_code == 200
    assert response.json() == [
        {"year": 2019, "indicator": "life_expectancy", "value": 60.4},
        {"year": 2020, "indicator": "life_expectancy", "value": None},
    ]
    assert cursor.params == ("life_expectancy", "life_expectancy", "KEN", "KEN")
    _assert_published_only(cursor.sql)


def test_timeseries_unknown_indicator_returns_empty_result(monkeypatch) -> None:
    cursor = _Cursor(["year", "indicator", "value"], [])
    response = _client_with_cursor(monkeypatch, cursor).get(
        "/api/v1/timeseries?country=KEN&indicator=unknown"
    )

    assert response.status_code == 200
    assert response.json() == []
    assert cursor.sql == ""


def test_compare_returns_selected_countries_for_one_indicator(monkeypatch) -> None:
    cursor = _Cursor(
        ["country_code", "country_name", "year", "indicator", "value"],
        [
            ("KEN", "Kenya", 2020, "health_spend_pct_gdp", 4.3),
            ("NGA", "Nigeria", 2020, "health_spend_pct_gdp", 3.4),
        ],
    )
    response = _client_with_cursor(monkeypatch, cursor).get(
        "/api/v1/compare?countries=KEN,NGA&indicator=health_spend_pct_gdp"
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "country_code": "KEN",
            "country_name": "Kenya",
            "year": 2020,
            "indicator": "health_spend_pct_gdp",
            "value": 4.3,
        },
        {
            "country_code": "NGA",
            "country_name": "Nigeria",
            "year": 2020,
            "indicator": "health_spend_pct_gdp",
            "value": 3.4,
        },
    ]
    assert cursor.params == (
        "health_spend_pct_gdp",
        "health_spend_pct_gdp",
        ["ken", "nga"],
        ["ken", "nga"],
    )
    _assert_published_only(cursor.sql)


def test_benchmark_returns_residual_rankings_with_bands(monkeypatch) -> None:
    cursor = _Cursor(
        ["country_code", "country_name", "year", "actual", "predicted", "residual"],
        [
            ("KEN", "Kenya", 2020, 61.4, 58.0, 3.4),
            ("GHA", "Ghana", 2020, 64.0, 63.4, 0.6),
            ("NGA", "Nigeria", 2020, 54.5, 57.1, -2.6),
        ],
    )
    response = _client_with_cursor(monkeypatch, cursor).get("/api/v1/benchmark?year=2020")

    assert response.status_code == 200
    assert response.json() == {
        "model_built": True,
        "rows": [
            {
                "country_code": "KEN",
                "country_name": "Kenya",
                "year": 2020,
                "actual": 61.4,
                "predicted": 58.0,
                "residual": 3.4,
                "band": "above",
            },
            {
                "country_code": "GHA",
                "country_name": "Ghana",
                "year": 2020,
                "actual": 64.0,
                "predicted": 63.4,
                "residual": 0.6,
                "band": "near",
            },
            {
                "country_code": "NGA",
                "country_name": "Nigeria",
                "year": 2020,
                "actual": 54.5,
                "predicted": 57.1,
                "residual": -2.6,
                "band": "below",
            },
        ],
    }
    assert cursor.params == (2020,)
    _assert_published_only(cursor.sql)


def test_benchmark_degrades_when_residual_table_is_absent(monkeypatch) -> None:
    cursor = _Cursor(
        ["country_code", "country_name", "year", "actual", "predicted", "residual"],
        [],
        error=psycopg.errors.UndefinedTable("published.model_residual"),
    )
    response = _client_with_cursor(monkeypatch, cursor).get("/api/v1/benchmark")

    assert response.status_code == 200
    assert response.json() == {"model_built": False, "rows": []}
    _assert_published_only(cursor.sql)

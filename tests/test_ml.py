"""Smoke tests for spec 002 that need no DB, no LLM key, and no modeling deps.

They guard the two things that must not regress: the brief is schema-valid, and its framing stays
honest (value-for-money, no blame language — spec SC-006 / Principle V).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from ml import features
from ml.brief import CountryHealthBrief, Performance, build_brief, classify
from ml.features import FEATURES, TARGET

from app import main as app_main


def test_classify_bands() -> None:
    assert classify(2.0) is Performance.above
    assert classify(0.0) is Performance.near
    assert classify(-2.0) is Performance.below


def test_brief_fallback_is_valid_and_honest(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    brief = build_brief(
        country_code="NGA",
        country_name="Nigeria",
        year=2020,
        indicators={
            "health_spend_pct_gdp": 3.4,
            "gdp_per_capita": 2000.0,
            "internet_pct": 35.0,
            "fertility_rate": 5.2,
        },
        predicted=54.0,
        actual=53.1,
    )
    assert isinstance(brief, CountryHealthBrief)
    assert brief.residual == -0.9
    assert brief.performance_vs_spend is Performance.near
    # honest-modeling framing present; no blame/causal language
    assert "value-for-money" in brief.summary.lower()
    assert "fail" not in brief.summary.lower()


class _Description:
    def __init__(self, name: str) -> None:
        self.name = name


class _Cursor:
    def __init__(self) -> None:
        self.sql = ""
        self.description = [_Description(column) for column in features.FEATURE_COLUMNS]

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: object | None = None) -> None:
        self.sql = sql

    def fetchall(self) -> list[tuple[object, ...]]:
        return [("NGA", "Nigeria", 2020, 53.1, 3.4, 2000.0, 35.0, 5.2)]


class _Connection:
    def __init__(self, cursor: _Cursor) -> None:
        self.cursor_obj = cursor

    def cursor(self) -> _Cursor:
        return self.cursor_obj


def test_feature_rows_read_from_published_mart() -> None:
    cursor = _Cursor()
    rows = features.feature_rows(_Connection(cursor))

    assert "published.country_year_indicators" in cursor.sql
    assert "staging." not in cursor.sql.lower()
    assert rows == [
        {
            "country_code": "NGA",
            "country_name": "Nigeria",
            "year": 2020,
            TARGET: 53.1,
            "health_spend_pct_gdp": 3.4,
            "gdp_per_capita": 2000.0,
            "internet_pct": 35.0,
            "fertility_rate": 5.2,
        }
    ]


def test_predict_endpoint_returns_numeric_prediction(monkeypatch) -> None:
    class FakeModel:
        def predict(self, frame: object) -> list[float]:
            assert list(frame.columns) == FEATURES
            return [54.321]

    monkeypatch.setattr(
        app_main,
        "_fetch_mart_row",
        lambda country, year: {
            "country_code": "NGA",
            "country_name": "Nigeria",
            "year": year,
            TARGET: 53.1,
            "health_spend_pct_gdp": 3.4,
            "gdp_per_capita": 2000.0,
            "internet_pct": 35.0,
            "fertility_rate": 5.2,
        },
    )
    monkeypatch.setattr(app_main, "_load_model", lambda: FakeModel())
    monkeypatch.setattr(app_main, "_model_name", lambda: "fake_model")

    response = TestClient(app_main.app).get("/api/v1/predict?country=NGA&year=2020")

    assert response.status_code == 200
    body = response.json()
    assert body["country_code"] == "NGA"
    assert body["predicted_life_expectancy"] == 54.32
    assert isinstance(body["predicted_life_expectancy"], float)

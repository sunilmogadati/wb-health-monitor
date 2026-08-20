"""Analytics read API over the published mart (spec 005)."""

from __future__ import annotations

from typing import Any, Literal

import psycopg
from fastapi import APIRouter, Query
from ml.features import connect
from pydantic import BaseModel

router = APIRouter(tags=["analytics"])

INDICATORS = (
    "life_expectancy",
    "under5_mortality",
    "health_spend_pct_gdp",
    "gdp_per_capita",
    "internet_pct",
    "fertility_rate",
)
BAND_THRESHOLD = 1.5
Band = Literal["above", "near", "below"]

_TIMESERIES_SQL = """
    SELECT
        year,
        %s AS indicator,
        CASE %s
            WHEN 'life_expectancy' THEN life_expectancy
            WHEN 'under5_mortality' THEN under5_mortality
            WHEN 'health_spend_pct_gdp' THEN health_spend_pct_gdp
            WHEN 'gdp_per_capita' THEN gdp_per_capita
            WHEN 'internet_pct' THEN internet_pct
            WHEN 'fertility_rate' THEN fertility_rate
            ELSE NULL
        END AS value
    FROM published.country_year_indicators
    WHERE lower(country_code) = lower(%s)
       OR lower(country_name) = lower(%s)
    ORDER BY year
"""

_COMPARE_SQL = """
    SELECT
        country_code,
        country_name,
        year,
        %s AS indicator,
        CASE %s
        WHEN 'life_expectancy' THEN life_expectancy
        WHEN 'under5_mortality' THEN under5_mortality
        WHEN 'health_spend_pct_gdp' THEN health_spend_pct_gdp
        WHEN 'gdp_per_capita' THEN gdp_per_capita
        WHEN 'internet_pct' THEN internet_pct
        WHEN 'fertility_rate' THEN fertility_rate
        ELSE NULL
        END AS value
    FROM published.country_year_indicators
    WHERE lower(country_code) = ANY(%s)
       OR lower(country_name) = ANY(%s)
    ORDER BY country_name, year
"""


class CountrySummary(BaseModel):
    country_code: str
    country_name: str


class TimeSeriesPoint(BaseModel):
    year: int
    indicator: str
    value: float | None


class ComparePoint(TimeSeriesPoint):
    country_code: str
    country_name: str


class BenchmarkRow(BaseModel):
    country_code: str
    country_name: str
    year: int
    actual: float
    predicted: float
    residual: float
    band: Band


class BenchmarkResponse(BaseModel):
    model_built: bool
    rows: list[BenchmarkRow]


def _query(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        assert cur.description is not None, "expected a SELECT with a result set"
        columns = [description.name for description in cur.description]
        return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]


def _as_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _band(residual: float) -> Band:
    if residual > BAND_THRESHOLD:
        return "above"
    if residual < -BAND_THRESHOLD:
        return "below"
    return "near"


def _country_tokens(countries: str) -> list[str]:
    return [country.strip().lower() for country in countries.split(",") if country.strip()]


@router.get("/countries", response_model=list[CountrySummary])
def countries() -> list[CountrySummary]:
    """List countries that exist in the published mart."""
    rows = _query(
        """
        SELECT DISTINCT country_code, country_name
        FROM published.country_year_indicators
        ORDER BY country_name
        """
    )
    return [CountrySummary(**row) for row in rows]


@router.get("/timeseries", response_model=list[TimeSeriesPoint])
def timeseries(
    country: str = Query(..., min_length=1),
    indicator: str = Query(..., min_length=1),
) -> list[TimeSeriesPoint]:
    """Return one country's published indicator values by year."""
    if indicator not in INDICATORS:
        return []
    rows = _query(
        _TIMESERIES_SQL,
        (indicator, indicator, country, country),
    )
    return [
        TimeSeriesPoint(
            year=int(row["year"]),
            indicator=str(row["indicator"]),
            value=_as_float(row["value"]),
        )
        for row in rows
    ]


@router.get("/compare", response_model=list[ComparePoint])
def compare(
    countries: str = Query(..., min_length=1),
    indicator: str = Query(..., min_length=1),
) -> list[ComparePoint]:
    """Return selected countries' published values for one indicator."""
    tokens = _country_tokens(countries)
    if indicator not in INDICATORS or not tokens:
        return []
    rows = _query(
        _COMPARE_SQL,
        (indicator, indicator, tokens, tokens),
    )
    return [
        ComparePoint(
            country_code=str(row["country_code"]),
            country_name=str(row["country_name"]),
            year=int(row["year"]),
            indicator=str(row["indicator"]),
            value=_as_float(row["value"]),
        )
        for row in rows
    ]


@router.get("/benchmark", response_model=BenchmarkResponse)
def benchmark(year: int | None = None) -> BenchmarkResponse:
    """Rank countries by actual-minus-predicted residual from the published model output."""
    try:
        rows = _query(
            """
            SELECT country_code, country_name, year, actual, predicted, residual
            FROM published.model_residual
            WHERE year = COALESCE(%s, (SELECT max(year) FROM published.model_residual))
            ORDER BY residual DESC, country_name
            """,
            (year,),
        )
    except psycopg.errors.UndefinedTable:
        return BenchmarkResponse(model_built=False, rows=[])

    return BenchmarkResponse(
        model_built=True,
        rows=[
            BenchmarkRow(
                country_code=str(row["country_code"]),
                country_name=str(row["country_name"]),
                year=int(row["year"]),
                actual=float(row["actual"]),
                predicted=float(row["predicted"]),
                residual=float(row["residual"]),
                band=_band(float(row["residual"])),
            )
            for row in rows
        ],
    )

"""Build the model-ready feature table from the published mart (spec 002).

Reads ``published.country_year_indicators``: one row per country-year with the target + context
features already shaped by dbt. Pure psycopg + SQL — no pandas needed here, so it is cheap to import
and test. ``train.py`` turns these rows into a DataFrame.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import psycopg

TARGET = "life_expectancy"
FEATURES = ["health_spend_pct_gdp", "gdp_per_capita", "internet_pct", "fertility_rate"]
FEATURE_COLUMNS = ["country_code", "country_name", "year", TARGET, *FEATURES]


def _load_dotenv_defaults() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _running_in_container() -> bool:
    return Path("/.dockerenv").exists()


def _pg_host() -> str:
    if os.getenv("PGHOST"):
        return os.environ["PGHOST"]
    if _running_in_container():
        return os.getenv("POSTGRES_HOST", "db")
    return "localhost"


def _pg_port() -> str:
    if os.getenv("PGPORT"):
        return os.environ["PGPORT"]
    if _running_in_container():
        return "5432"
    return os.getenv("POSTGRES_PORT", "5432")


def connect() -> psycopg.Connection:
    """Connect to Postgres.

    Works from the host (``localhost:${POSTGRES_PORT}``) or inside the container
    (set ``PGHOST=db``).
    Local-dev credentials come from the environment, defaulting to the repo's ``.env`` values.
    """
    _load_dotenv_defaults()
    return psycopg.connect(
        host=_pg_host(),
        port=_pg_port(),
        dbname=os.getenv("POSTGRES_DB", "wbhealth"),
        user=os.getenv("POSTGRES_USER", "wbhealth"),
        password=os.getenv("POSTGRES_PASSWORD", "wbhealth_local_dev"),
    )


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Return stable Python primitives for model/API consumers."""
    out = dict(row)
    out["year"] = int(out["year"])
    for column in [TARGET, *FEATURES]:
        if out.get(column) is not None:
            out[column] = float(out[column])
    return out


def _rows_from_cursor(
    colnames: Iterable[str], rows: Iterable[tuple[Any, ...]]
) -> list[dict[str, Any]]:
    return [_normalize_row(dict(zip(colnames, row, strict=True))) for row in rows]


def feature_rows(conn: psycopg.Connection, drop_incomplete: bool = True) -> list[dict]:
    """One row per country-year: ``country_code, country_name, year``, target, and FEATURES.

    Reads the published dbt mart directly. Rows missing the target are always excluded; when
    ``drop_incomplete`` (the default), rows missing ANY feature are excluded too — the simplest
    honest null policy. If you change it (e.g. impute), document why (spec FR-002).
    """
    sql = """
        SELECT
            country_code,
            country_name,
            year,
            life_expectancy,
            health_spend_pct_gdp,
            gdp_per_capita,
            internet_pct,
            fertility_rate
        FROM published.country_year_indicators
        ORDER BY country_code, year
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        assert cur.description is not None
        colnames = [d.name for d in cur.description]
        rows = _rows_from_cursor(colnames, cur.fetchall())

    out: list[dict] = []
    for r in rows:
        if r[TARGET] is None:
            continue
        if drop_incomplete and any(r[f] is None for f in FEATURES):
            continue
        out.append(r)
    return out


def country_year_row(conn: psycopg.Connection, country: str, year: int) -> dict[str, Any] | None:
    """Fetch one mart row by case-insensitive country code or country name."""
    sql = """
        SELECT
            country_code,
            country_name,
            year,
            life_expectancy,
            health_spend_pct_gdp,
            gdp_per_capita,
            internet_pct,
            fertility_rate
        FROM published.country_year_indicators
        WHERE year = %s
          AND (lower(country_code) = lower(%s) OR lower(country_name) = lower(%s))
        ORDER BY CASE WHEN lower(country_code) = lower(%s) THEN 0 ELSE 1 END
        LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(sql, (year, country, country, country))
        row = cur.fetchone()
        if row is None:
            return None
        assert cur.description is not None
        colnames = [d.name for d in cur.description]
    return _rows_from_cursor(colnames, [row])[0]

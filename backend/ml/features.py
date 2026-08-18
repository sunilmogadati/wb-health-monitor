"""Build the model-ready feature table from the governed staging data (spec 002).

Reads ``staging.wdi_observation`` (long: one row per country-year-indicator) and pivots it to one
row per country-year with the target + context features. Pure psycopg + SQL — no pandas needed here,
so it is cheap to import and test. ``train.py`` turns these rows into a DataFrame.
"""
from __future__ import annotations

import os

import psycopg

TARGET = "life_expectancy"
FEATURES = ["health_spend_pct_gdp", "gdp_per_capita", "internet_pct", "fertility_rate"]


def connect() -> psycopg.Connection:
    """Connect to Postgres.

    Works from the host (``localhost:${POSTGRES_PORT}``) or inside the container (set ``PGHOST=db``).
    Local-dev credentials come from the environment, defaulting to the repo's ``.env`` values.
    """
    return psycopg.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "wbhealth"),
        user=os.getenv("POSTGRES_USER", "wbhealth"),
        password=os.getenv("POSTGRES_PASSWORD", "wbhealth_local_dev"),
    )


def feature_rows(conn: psycopg.Connection, drop_incomplete: bool = True) -> list[dict]:
    """One row per country-year: ``country_code, country_name, year``, target, and FEATURES.

    Pivots the long staging table with conditional aggregation. Rows missing the target are always
    excluded; when ``drop_incomplete`` (the default), rows missing ANY feature are excluded too — the
    simplest honest null policy. If you change it (e.g. impute), document why (spec FR-002).
    """
    cols = [TARGET, *FEATURES]
    # `cols` are controlled constants (not user input), so inlining them is safe here.
    selects = ",\n            ".join(
        f"max(value) FILTER (WHERE indicator = '{c}') AS {c}" for c in cols
    )
    sql = f"""
        SELECT country_code, max(country_name) AS country_name, year,
            {selects}
        FROM staging.wdi_observation
        GROUP BY country_code, year
        ORDER BY country_code, year
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        colnames = [d.name for d in cur.description]
        rows = [dict(zip(colnames, r)) for r in cur.fetchall()]

    out: list[dict] = []
    for r in rows:
        if r[TARGET] is None:
            continue
        if drop_incomplete and any(r[f] is None for f in FEATURES):
            continue
        out.append(r)
    return out

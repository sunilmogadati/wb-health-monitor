"""create published.country_year_indicators

Revision ID: 0002_published_mart
Revises: 0001_pull_log
Create Date: 2026-08-19

The published mart spec 004 (ai-insights) reads from. Spec 003 (warehouse star schema) is still
Draft and unimplemented, so this is a minimal, honest stand-in for its FR-007 — a `published` view
pivoted straight from `staging.wdi_observation` — not the full conformed dimensional model (dims +
fact table) spec 003 actually scopes. It still holds zone discipline (Principle III): nothing
user-facing reads `staging` directly, only this view.

`staging.wdi_observation` is normally created by `backend/scripts/load_wdi.py` on first ingest, not
by a migration, so `make migrate` can run before `make ingest` on a fresh DB. Guard with the same
`CREATE TABLE IF NOT EXISTS` DDL load_wdi.py uses so the view always has something to select from.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_published_mart"
down_revision: str | None = "0001_pull_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Same indicator codes backend/scripts/pull_wdi.py ingests (spec 001).
_INDICATORS = (
    "life_expectancy",
    "under5_mortality",
    "health_spend_pct_gdp",
    "uhc_index",
    "gdp_per_capita",
    "internet_pct",
    "fertility_rate",
)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS staging")
    op.execute(
        """CREATE TABLE IF NOT EXISTS staging.wdi_observation (
               country_code text NOT NULL,
               country_name text,
               year         int  NOT NULL,
               indicator    text NOT NULL,
               value        double precision,
               PRIMARY KEY (country_code, year, indicator))"""
    )

    op.execute("CREATE SCHEMA IF NOT EXISTS published")
    pivot_cols = ",\n            ".join(
        f"max(value) FILTER (WHERE indicator = '{c}') AS {c}" for c in _INDICATORS
    )
    op.execute(
        f"""CREATE VIEW published.country_year_indicators AS
            SELECT country_code, max(country_name) AS country_name, year,
                {pivot_cols}
            FROM staging.wdi_observation
            GROUP BY country_code, year"""
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS published.country_year_indicators")
    op.execute("DROP SCHEMA IF EXISTS published")

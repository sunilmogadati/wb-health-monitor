"""Data-quality gate at the staging boundary (spec 008, ADR-0007).

Runs AFTER staging is loaded and BEFORE dbt builds the mart, so anomaly detection happens ONCE,
early — every downstream zone (warehouse, mart, model, API) inherits clean data. Reshapes the long
staging rows to wide, runs the same detectors (static ranges + robust-z + year-over-year), writes
flagged country-year-indicators to ``ingestion.data_quality_flag`` (which the published dbt model
nulls), and halts on a large flagged fraction (the tripwire). ``raw`` stays immutable.

Runs in the api container via ``make flag`` (``python /workspace/backend/scripts/flag_quality.py``).
"""

from __future__ import annotations

from typing import Any

import psycopg
from evals import checks
from ml.features import connect


def wide_staging_rows(conn: psycopg.Connection) -> list[dict[str, Any]]:
    """Reshape long staging (country, year, indicator, value) into wide country-year rows."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT country_code, country_name, year, indicator, value FROM staging.wdi_observation"
        )
        raw = cur.fetchall()
    wide: dict[tuple[str, int], dict[str, Any]] = {}
    for country_code, country_name, year, indicator, value in raw:
        row = wide.setdefault(
            (country_code, int(year)),
            {"country_code": country_code, "country_name": country_name, "year": int(year)},
        )
        row[indicator] = None if value is None else float(value)
    return list(wide.values())


def persist_flags(conn: psycopg.Connection, flags: list[dict[str, Any]]) -> int:
    """Write the flagged country-year-indicators; always ensures the table exists (dbt reads it)."""
    records = sorted({(str(f["entity"]), int(f["year"]), str(f["column"])) for f in flags})
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ingestion.data_quality_flag (
                country_code text NOT NULL,
                year integer NOT NULL,
                indicator text NOT NULL,
                PRIMARY KEY (country_code, year, indicator)
            )
            """
        )
        cur.execute("TRUNCATE ingestion.data_quality_flag")
        cur.executemany(
            "INSERT INTO ingestion.data_quality_flag (country_code, year, indicator) "
            "VALUES (%s, %s, %s)",
            records,
        )
    return len(records)


def main() -> None:
    thresholds = checks.load_thresholds()
    dq = thresholds["data_quality"]
    with connect() as conn:
        rows = wide_staging_rows(conn)
        flags = checks.range_flags(rows, dq.get("value_ranges", {}))
        flags += checks.detect_anomalies(rows, thresholds["anomaly_detection"])

        flagged_keys = {(f["entity"], f["year"]) for f in flags}
        fraction = len(flagged_keys) / len(rows) if rows else 0.0
        for f in sorted(flags, key=lambda x: (str(x["entity"]), x["year"]))[:25]:
            print(f"  flag  {f['entity']} {f['year']}  {f['column']}={f['value']}  ({f['reason']})")

        max_bad = float(dq.get("max_bad_fraction", 0.05))
        if fraction > max_bad:
            raise SystemExit(
                f"data-quality tripwire: {fraction:.1%} of country-years flagged (> {max_bad:.0%}) "
                "— halting; the pull looks systemically broken (ADR-0007)"
            )
        n_flags = persist_flags(conn, flags)
    print(
        f"flagged {n_flags} country-year-indicators -> ingestion.data_quality_flag "
        f"({fraction:.1%} of {len(rows)} country-years); dbt nulls them in the mart"
    )


if __name__ == "__main__":
    main()

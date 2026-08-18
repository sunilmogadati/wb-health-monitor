"""Load the tidy WDI CSV into Postgres and record the run in ingestion.pull_log.

Runs INSIDE the api container (has psycopg + DB access):
    docker compose exec -T api python /workspace/backend/scripts/load_wdi.py
Reads /workspace/backend/data/wdi_observation.csv produced by pull_wdi.py.
"""
import csv
import os
from pathlib import Path

import psycopg

CSV = Path("/workspace/backend/data/wdi_observation.csv")
YEAR_FROM, YEAR_TO = 2015, 2022


def main() -> None:
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg", "postgresql")
    rows = list(csv.DictReader(CSV.open()))
    if not rows:
        raise SystemExit(f"no rows in {CSV} — run pull_wdi.py on the host first")

    indicators = sorted({r["indicator"] for r in rows})
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO ingestion.pull_log
                 (indicators, economies, object_keys, year_from, year_to,
                  rows_fetched, status, started_at)
               VALUES (%s, %s, %s, %s, %s, %s, 'running', now())
               RETURNING pull_id""",
            (indicators, ["SSF"], [str(CSV)], YEAR_FROM, YEAR_TO, len(rows)),
        )
        pull_id = cur.fetchone()[0]

        cur.execute("CREATE SCHEMA IF NOT EXISTS staging")
        cur.execute(
            """CREATE TABLE IF NOT EXISTS staging.wdi_observation (
                   country_code text NOT NULL,
                   country_name text,
                   year         int  NOT NULL,
                   indicator    text NOT NULL,
                   value        double precision,
                   PRIMARY KEY (country_code, year, indicator))"""
        )
        cur.execute("TRUNCATE staging.wdi_observation")
        cur.executemany(
            """INSERT INTO staging.wdi_observation
                 (country_code, country_name, year, indicator, value)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (country_code, year, indicator) DO UPDATE
                 SET value = EXCLUDED.value, country_name = EXCLUDED.country_name""",
            [(r["country_code"], r["country_name"], int(r["year"]),
              r["indicator"], float(r["value"])) for r in rows],
        )
        cur.execute(
            "UPDATE ingestion.pull_log SET status='succeeded', finished_at=now() WHERE pull_id=%s",
            (pull_id,),
        )
        conn.commit()

        cur.execute(
            "SELECT count(*), count(distinct country_code), count(distinct indicator) "
            "FROM staging.wdi_observation"
        )
        n, countries, inds = cur.fetchone()
        print(f"pull_id={pull_id}  loaded {n} rows  {countries} countries  {inds} indicators")


if __name__ == "__main__":
    main()

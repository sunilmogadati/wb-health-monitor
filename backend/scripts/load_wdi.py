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
RAW_BUCKET = os.environ.get("S3_BUCKET_RAW", "raw")


def s3_client_kwargs() -> dict[str, str]:
    """boto3 client kwargs, driven by env so the SAME code hits MinIO locally and real S3 in prod.

    Only pass what's set: with ``S3_ENDPOINT_URL`` unset (prod) boto3 uses AWS's default endpoint;
    with the access keys unset (prod) boto3 falls back to the IAM task-role credential chain. Local
    dev provides all three via ``.env`` (MinIO). No cloud/local branch in the code — just config.
    """
    kwargs: dict[str, str] = {}
    endpoint = os.environ.get("S3_ENDPOINT_URL")
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    access_key = os.environ.get("S3_ACCESS_KEY")
    secret_key = os.environ.get("S3_SECRET_KEY")
    if access_key and secret_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key
    return kwargs


def _land_raw(csv_path: Path, pull_id: int) -> str:
    """Upload the raw pull to the `raw` zone (immutable bronze); return its s3:// key."""
    import boto3

    s3 = boto3.client("s3", **s3_client_kwargs())
    try:
        s3.head_bucket(Bucket=RAW_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=RAW_BUCKET)
    key = f"world_bank_wdi/pull_{pull_id}/wdi_observation.csv"
    s3.upload_file(str(csv_path), RAW_BUCKET, key)
    return f"s3://{RAW_BUCKET}/{key}"


def main() -> None:
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg", "postgresql")
    rows = list(csv.DictReader(CSV.open()))
    if not rows:
        raise SystemExit(f"no rows in {CSV} — run pull_wdi.py on the host first")

    indicators = sorted({r["indicator"] for r in rows})
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        # Ingestion is driven by the registry: resolve the registered, active source first.
        cur.execute(
            "SELECT source_id FROM ingestion.data_sources WHERE name = %s AND is_active",
            ("world_bank_wdi",),
        )
        src = cur.fetchone()
        if src is None:
            raise SystemExit(
                "source 'world_bank_wdi' is not registered/active in ingestion.data_sources"
                " - run `make migrate`"
            )
        source_id = src[0]

        cur.execute(
            """INSERT INTO ingestion.pull_log
                 (source_id, indicators, economies, year_from, year_to,
                  rows_fetched, status, started_at)
               VALUES (%s, %s, %s, %s, %s, %s, 'running', now())
               RETURNING pull_id""",
            (source_id, indicators, ["SSF"], YEAR_FROM, YEAR_TO, len(rows)),
        )
        pull_row = cur.fetchone()
        assert pull_row is not None
        pull_id = pull_row[0]

        # Land the raw pull in the MinIO `raw` zone (bronze), then record its object key.
        object_key = _land_raw(CSV, pull_id)
        cur.execute(
            "UPDATE ingestion.pull_log SET object_keys = %s WHERE pull_id = %s",
            ([object_key], pull_id),
        )

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
        summary_row = cur.fetchone()
        assert summary_row is not None
        n, countries, inds = summary_row
        print(f"pull_id={pull_id}  loaded {n} rows  {countries} countries  {inds} indicators")


if __name__ == "__main__":
    main()

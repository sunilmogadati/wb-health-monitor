"""wb-health-monitor batch pipeline as an Airflow DAG (spec 012, alternative track).

Reference DAG — Airflow is not installed/run in this repo (it lives under infra/, outside the
backend package). It runs the SAME governed steps as ``backend/scripts/run_pipeline.py`` (ingest →
flag → dbt build → train), but as ordered Airflow tasks with explicit dependencies, retries, and a
UI — the managed-orchestrator value over the EventBridge→Fargate default (ADR-0002). One
orchestrator, not both.

Deployed by uploading this file to the MWAA DAG S3 bucket (infra/mwaa/main.tf does that). The tasks
shell out to the same commands the container runs; DB/S3 come from env/Secrets Manager, as in the
Fargate path.
"""

from __future__ import annotations

from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

DEFAULT_ARGS = {
    "owner": "wb-health-monitor",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "depends_on_past": False,
}

with DAG(
    dag_id="wb_health_pipeline",
    description="ingest -> flag -> dbt build -> train (the governed batch pipeline)",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 6 * * *",  # daily 06:00 UTC, matching the EventBridge default
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["wb-health-monitor", "batch"],
) as dag:
    ingest = BashOperator(
        task_id="ingest",
        bash_command=(
            "cd $PROJECT_DIR/backend && python scripts/pull_wdi.py && python scripts/load_wdi.py"
        ),
    )
    flag = BashOperator(
        task_id="flag",
        bash_command="cd $PROJECT_DIR/backend && python scripts/flag_quality.py",
    )
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="cd $PROJECT_DIR/backend/dbt && dbt build --profiles-dir .",
    )
    train = BashOperator(
        task_id="train",
        bash_command="cd $PROJECT_DIR/backend && python -m ml.train",
    )

    # Explicit dependencies — a failed task halts everything downstream (SC-001).
    ingest >> flag >> dbt_build >> train

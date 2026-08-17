"""create ingestion.pull_log

Revision ID: 0001_pull_log
Revises:
Create Date: 2026-08-17

The ingest run log (spec 001-wdi-ingestion). One row per WDI ingest run: what was pulled, where it
landed in object storage, and whether it succeeded. This is the lineage anchor the rest of the
pipeline is built on.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_pull_log"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ingestion")
    op.create_table(
        "pull_log",
        sa.Column("pull_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("indicators", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("economies", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("year_from", sa.Integer, nullable=False),
        sa.Column("year_to", sa.Integer, nullable=False),
        sa.Column("rows_fetched", sa.Integer, nullable=True),
        sa.Column("object_keys", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="pull_log_status_check",
        ),
        schema="ingestion",
    )


def downgrade() -> None:
    op.drop_table("pull_log", schema="ingestion")
    op.execute("DROP SCHEMA IF EXISTS ingestion")

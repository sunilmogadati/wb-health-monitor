"""create ingestion.data_sources registry and link pull_log to it

Revision ID: 0002_data_sources
Revises: 0001_pull_log
Create Date: 2026-08-18

The source registry (spec 001). Every ingest is driven by a registered, active source, and every
pull_log row references the source it came from — the provenance anchor. One seeded source today
(World Bank WDI); the pattern lets a second public source be added as a row, not code.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_data_sources"
down_revision: str | None = "0001_pull_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_WB_INDICATORS = (
    "SP.DYN.LE00.IN,SH.DYN.MORT,SH.XPD.CHEX.GD.ZS,SH.UHC.SRVS.CV.XD,"
    "NY.GDP.PCAP.CD,IT.NET.USER.ZS,SP.DYN.TFRT.IN"
)


def upgrade() -> None:
    op.create_table(
        "data_sources",
        sa.Column("source_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("base_url", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("kind IN ('rest-api', 'file-drop', 'database')", name="data_sources_kind_check"),
        schema="ingestion",
    )

    # Seed the one source this platform ingests today (public, keyless).
    op.execute(
        """
        INSERT INTO ingestion.data_sources (name, kind, base_url, description, config)
        VALUES (
            'world_bank_wdi',
            'rest-api',
            'https://api.worldbank.org/v2',
            'World Bank World Development Indicators via wbgapi (public, no auth).',
            jsonb_build_object(
                'region', 'SSF',
                'year_from', 2015,
                'year_to', 2022,
                'indicators', string_to_array('%s', ',')
            )
        )
        """
        % _WB_INDICATORS
    )

    # Link every pull to its source. Backfill existing rows, then enforce NOT NULL + FK.
    op.add_column(
        "pull_log",
        sa.Column("source_id", sa.BigInteger, nullable=True),
        schema="ingestion",
    )
    op.execute(
        """
        UPDATE ingestion.pull_log
        SET source_id = (SELECT source_id FROM ingestion.data_sources WHERE name = 'world_bank_wdi')
        WHERE source_id IS NULL
        """
    )
    op.create_foreign_key(
        "pull_log_source_id_fkey",
        "pull_log",
        "data_sources",
        ["source_id"],
        ["source_id"],
        source_schema="ingestion",
        referent_schema="ingestion",
    )
    op.alter_column("pull_log", "source_id", nullable=False, schema="ingestion")


def downgrade() -> None:
    op.drop_constraint(
        "pull_log_source_id_fkey", "pull_log", schema="ingestion", type_="foreignkey"
    )
    op.drop_column("pull_log", "source_id", schema="ingestion")
    op.drop_table("data_sources", schema="ingestion")

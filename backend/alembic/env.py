"""Alembic migration environment.

Points at an empty history. The root revision `0001_baseline` is authored in-project; there is
deliberately nothing in `versions/` yet.

There is exactly one migration history with exactly one head at all times. Every later revision,
from any feature, descends from the baseline directly or transitively.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Target metadata
#
# None until the first declarative model exists. The baseline migration is written by hand
# (autogenerate cannot emit CREATE SCHEMA / CREATE EXTENSION). A later feature sets this to its
# metadata once it has one.
# ---------------------------------------------------------------------------
target_metadata = None

# Alembic records applied revisions in `public` by default. Pinned explicitly so it cannot drift.
VERSION_TABLE_SCHEMA = "public"


def _database_url() -> str:
    """Resolve the database URL from the environment.

    One configuration path, shared with the application, so a migration and the app can never
    disagree about which database they mean, and no credential is committed.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set; refusing to migrate an unknown database.")
    return url


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live connection, so a reviewer can read what will run."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=VERSION_TABLE_SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against a live connection."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        # NullPool: a migration run is a short-lived process that opens one connection and exits.
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=VERSION_TABLE_SCHEMA,
            compare_type=True,
            compare_server_default=True,
            # Wrap each migration in its own transaction so a failure leaves no partially applied
            # revision.
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

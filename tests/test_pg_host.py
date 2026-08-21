"""Regression test for DB-host resolution (spec 007 FR-005 - pipeline must reach the cloud DB).

The bug: `ml.features._pg_host` detected "in a container" via `/.dockerenv`, which does NOT exist on
The bug: `ml.features._pg_host` used `/.dockerenv` to detect a container, which does NOT exist
an explicit `POSTGRES_HOST` first, on any runtime.
"""

from __future__ import annotations

from ml import features


def test_pg_host_honors_postgres_host_env(monkeypatch) -> None:
    monkeypatch.delenv("PGHOST", raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "my-rds.example.aws")
    assert features._pg_host() == "my-rds.example.aws"


def test_pg_host_pghost_takes_precedence(monkeypatch) -> None:
    monkeypatch.setenv("PGHOST", "override-host")
    monkeypatch.setenv("POSTGRES_HOST", "my-rds.example.aws")
    assert features._pg_host() == "override-host"


def test_pg_host_defaults_localhost_off_host(monkeypatch) -> None:
    monkeypatch.delenv("PGHOST", raising=False)
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.setattr(features, "_running_in_container", lambda: False)
    assert features._pg_host() == "localhost"

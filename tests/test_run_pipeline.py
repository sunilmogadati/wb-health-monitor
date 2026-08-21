"""Structural test for the deploy pipeline entrypoint (spec 007 FR-005).

It orchestrates subprocesses, so we don't run it here — we assert the governed sequence is wired
in order (ingest → load → flag → dbt build → train), the contract the scheduled task depends on.
"""

from __future__ import annotations

from scripts import run_pipeline


def test_pipeline_runs_the_governed_sequence_in_order() -> None:
    labels = [label for label, _argv, _cwd in run_pipeline.STEPS]
    assert labels == ["pull WDI", "load WDI", "flag quality", "dbt build", "train"]


def test_train_is_the_last_step() -> None:
    # train writes the model artifact — it must run after ingest + dbt build have produced the mart.
    assert run_pipeline.STEPS[-1][0] == "train"

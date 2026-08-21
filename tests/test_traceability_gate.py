"""Tests for the Change-Traceability CI gate's pure decision function.

The gate lives at repo-root ``scripts/check_traceability.py`` (a governance script, not app code),
so it is loaded by path rather than imported as a package.
"""

from __future__ import annotations

import importlib.util
import pathlib

_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_traceability.py"
_spec = importlib.util.spec_from_file_location("check_traceability", _SCRIPT)
assert _spec is not None and _spec.loader is not None
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def test_no_behavior_change_passes() -> None:
    ok, _ = gate.decide(["README.md", "docs/PROJECT_BRIEF.md"], "")
    assert ok


def test_test_only_change_passes() -> None:
    files = ["tests/test_forecast.py", "frontend/src/components/__tests__/X.test.tsx"]
    ok, _ = gate.decide(files, "")
    assert ok


def test_behavior_with_spec_passes() -> None:
    ok, _ = gate.decide(["backend/app/main.py", "specs/010-forecast/spec.md"], "")
    assert ok


def test_behavior_with_adr_passes() -> None:
    ok, _ = gate.decide(["backend/ml/train.py", "docs/adr/0009-something.md"], "")
    assert ok


def test_bug_lane_passes_with_test_and_named_fr() -> None:
    ok, _ = gate.decide(
        ["backend/app/analytics.py", "tests/test_analytics_api.py"],
        "Fixes the gap logic. Regression test for FR-003.",
    )
    assert ok


def test_bug_lane_blocks_without_named_fr() -> None:
    # A behavior fix + test but no FR named, no spec/ADR → orphan, blocks.
    ok, _ = gate.decide(
        ["backend/app/analytics.py", "tests/test_analytics_api.py"],
        "Fixes the gap logic.",
    )
    assert not ok


def test_skip_marker_passes() -> None:
    body = "Rename a private var. [skip-traceability: pure rename, no behavior]"
    ok, reason = gate.decide(["backend/app/main.py"], body)
    assert ok
    assert "skip-traceability" in reason


def test_orphan_behavior_change_blocks() -> None:
    ok, _ = gate.decide(["backend/app/main.py"], "Quietly changed the endpoint.")
    assert not ok

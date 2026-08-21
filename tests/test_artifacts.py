"""Tests for the model-artifact store (spec 007 FR-006).

The local branch is exercised end-to-end (round-trip through a tmp dir); the S3 branch is boto3 and
mypy-checked but not run here (no AWS). The pure S3 key-parsing is unit-tested directly.
"""

from __future__ import annotations

from ml import artifacts


def test_local_round_trip(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MODEL_ARTIFACT_DIR", str(tmp_path))
    uri = artifacts.put_bytes("m.joblib", b"\x00\x01model")
    assert uri.endswith("m.joblib")
    assert artifacts.get_bytes("m.joblib") == b"\x00\x01model"
    assert artifacts.exists("m.joblib") is True


def test_get_bytes_returns_none_when_absent(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MODEL_ARTIFACT_DIR", str(tmp_path))
    assert artifacts.get_bytes("nope.json") is None
    assert artifacts.exists("nope.json") is False


def test_default_base_is_the_local_models_dir(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_ARTIFACT_DIR", raising=False)
    assert artifacts.artifact_base().endswith("/models")
    assert artifacts._is_s3(artifacts.artifact_base()) is False


def test_s3_base_is_detected_and_parsed() -> None:
    base = "s3://my-bucket/models/prod"
    assert artifacts._is_s3(base) is True
    bucket, key = artifacts._s3_parts(base, "life_expectancy.joblib")
    assert bucket == "my-bucket"
    assert key == "models/prod/life_expectancy.joblib"


def test_s3_base_without_prefix_keys_at_root() -> None:
    bucket, key = artifacts._s3_parts("s3://just-bucket", "meta.json")
    assert bucket == "just-bucket"
    assert key == "meta.json"

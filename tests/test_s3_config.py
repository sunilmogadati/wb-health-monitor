"""Tests for the env-driven S3 client config (spec 007 FR-004/FR-008).

The point: one code path, config per environment. Local sets the MinIO env; prod leaves it unset so
boto3 uses AWS's default endpoint + the IAM role. We test the kwargs builder, not a live client.
"""

from __future__ import annotations

from scripts.load_wdi import s3_client_kwargs


def test_prod_env_uses_aws_default_endpoint_and_iam(monkeypatch) -> None:
    for var in ("S3_ENDPOINT_URL", "S3_ACCESS_KEY", "S3_SECRET_KEY"):
        monkeypatch.delenv(var, raising=False)
    # Nothing set → boto3 gets no endpoint override and no static keys (AWS default + IAM chain).
    assert s3_client_kwargs() == {}


def test_local_env_targets_minio_with_static_keys(monkeypatch) -> None:
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://minio:9000")
    monkeypatch.setenv("S3_ACCESS_KEY", "wbhealth")
    monkeypatch.setenv("S3_SECRET_KEY", "local-dev-secret")
    kwargs = s3_client_kwargs()
    assert kwargs["endpoint_url"] == "http://minio:9000"
    assert kwargs["aws_access_key_id"] == "wbhealth"
    secret = kwargs["aws_secret_access_key"]
    assert secret == "local-dev-secret"  # noqa: S105 (test fixture, not a real key)


def test_partial_keys_are_ignored(monkeypatch) -> None:
    # Only one of the pair set → don't pass static creds (avoid a half-configured client).
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)
    monkeypatch.setenv("S3_ACCESS_KEY", "only-access")
    monkeypatch.delenv("S3_SECRET_KEY", raising=False)
    assert "aws_access_key_id" not in s3_client_kwargs()

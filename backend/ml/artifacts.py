"""Model-artifact store (spec 007 FR-006): local files locally, S3 in the cloud — env-switched.

The trained model + metadata must be shared between two **independently-deployed** containers: the
batch pipeline that *writes* them (a scheduled Fargate task) and the API that *reads* them. Locally
that shared store is the filesystem; in the cloud it is S3. One env var, ``MODEL_ARTIFACT_DIR``,
picks which — a plain path (default, so ``make train`` + local dev are unchanged) or ``s3://…``.

boto3 honors IAM/instance credentials in AWS, so the swap is **config, not code** (FR-004/FR-006):
nothing here changes between local and cloud except that env var. Kept to a tiny bytes-in/bytes-out
surface so the two callers (``train.py`` save, ``app.main`` load) don't each grow an S3 branch.
"""

from __future__ import annotations

import os
from pathlib import Path

# Artifact names — the shared contract between the writer (train) and the reader (API).
MODEL_FILENAME = "life_expectancy.joblib"
METADATA_FILENAME = "life_expectancy_metadata.json"

_DEFAULT_DIR = Path(__file__).resolve().parent.parent / "models"
_S3_SCHEME = "s3://"


def artifact_base() -> str:
    """The artifact location: ``MODEL_ARTIFACT_DIR`` env, else the local ``backend/models`` dir."""
    return os.getenv("MODEL_ARTIFACT_DIR", str(_DEFAULT_DIR))


def _is_s3(base: str) -> bool:
    return base.startswith(_S3_SCHEME)


def _s3_parts(base: str, name: str) -> tuple[str, str]:
    """Split ``s3://bucket/prefix`` + ``name`` into ``(bucket, key)``."""
    rest = base[len(_S3_SCHEME) :].strip("/")
    bucket, _, prefix = rest.partition("/")
    key = f"{prefix}/{name}" if prefix else name
    return bucket, key


def put_bytes(name: str, data: bytes) -> str:
    """Write an artifact; return its resolved URI/path. Creates local parents as needed."""
    base = artifact_base()
    if _is_s3(base):
        import boto3

        bucket, key = _s3_parts(base, name)
        boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=data)
        return f"{_S3_SCHEME}{bucket}/{key}"
    path = Path(base) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)


def get_bytes(name: str) -> bytes | None:
    """Read an artifact's bytes, or ``None`` if absent yet (first run degrades gracefully)."""
    base = artifact_base()
    if _is_s3(base):
        import boto3
        from botocore.exceptions import ClientError

        bucket, key = _s3_parts(base, name)
        try:
            obj = boto3.client("s3").get_object(Bucket=bucket, Key=key)
            body: bytes = obj["Body"].read()
            return body
        except ClientError:
            return None
    path = Path(base) / name
    return path.read_bytes() if path.exists() else None


def exists(name: str) -> bool:
    """Whether an artifact is present (a HEAD on S3, a stat locally) — no full download."""
    base = artifact_base()
    if _is_s3(base):
        import boto3
        from botocore.exceptions import ClientError

        bucket, key = _s3_parts(base, name)
        try:
            boto3.client("s3").head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False
    return (Path(base) / name).exists()

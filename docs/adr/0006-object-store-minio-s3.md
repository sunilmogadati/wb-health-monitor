# ADR-0006: Object store — MinIO local → S3 cloud

- **Status:** Accepted
- **Date:** 2026-08-20

## Context
The `raw` zone must hold each pull as an **immutable object** (bronze) for replay and audit, both on a
laptop and in the cloud. We want one code path across environments and no rewrite when we deploy.

## Decision
Use an **S3-compatible object store**: **MinIO** locally (Docker) and **Amazon S3** in the cloud
(spec 007). The code uses **`boto3`**, so moving from MinIO to S3 is an **endpoint/credentials env
change — no code rewrite**. The trained model artifact travels the same way (S3) so the batch job and
the API can share it.

## Alternatives considered
- **Local filesystem for raw:** simple, but no clean cloud parity and weaker durability/audit story.
- **Google Cloud Storage:** would require a client swap or an S3-compat shim; S3 is the zero-change path
  given `boto3`.

## Consequences
- Identical object semantics locally and in production; the `raw` zone is immutable and replayable.
- The S3-compatibility is what makes AWS the least-change deploy target (see the deployment spec).
- The API loads the model artifact from the object store (not a baked-in local file), so independently
  deployed containers share one model.

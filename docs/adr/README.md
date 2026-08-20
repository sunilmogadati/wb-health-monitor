# Architecture Decision Records

An **ADR** captures one architecturally-significant decision: its **context**, the **decision**, the
**alternatives** weighed, and the **consequences**. ADRs are the *why* behind the system; the
[reference architecture](../ARCHITECTURE.md) diagrams are the *what*. They complement each other — a
reader asking "why Postgres, not Mongo? why not Spark? why not managed Airflow?" finds the answer here.

ADRs are **append-only**: don't edit a decided one; supersede it with a new record and mark the old
`Superseded by ADR-000N`.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-datastore-postgres-medallion.md) | PostgreSQL with medallion zones | Accepted |
| [0002](0002-orchestration-eventbridge-fargate.md) | Orchestration: EventBridge + scheduled Fargate task | Accepted |
| [0003](0003-compute-engine-single-node.md) | Compute engine: single-node (Postgres/dbt/pandas) | Accepted |
| [0004](0004-data-quality-filter-tripwire.md) | Data quality: filter + tripwire gate with anomaly detection | Accepted |
| [0005](0005-llm-claude.md) | LLM: Anthropic Claude via API | Accepted |
| [0006](0006-object-store-minio-s3.md) | Object store: MinIO local → S3 cloud | Accepted |

**Template:** Title · Status · Date · Context · Decision · Alternatives considered · Consequences.

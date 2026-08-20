# Reference Architecture

The WB Health-Systems Performance Monitor, described in the standard architecture **views**. Each view
answers a different question; together they are the reference architecture. Diagrams are Mermaid so they
live in git and render on GitHub. Views marked *(planned)* describe the target deployment (spec 007).

- [1. System context](#1-system-context) — who and what the system talks to
- [2. Container / application](#2-container--application) — the running pieces
- [3. Data architecture](#3-data-architecture) — how data flows through the zones
- [4. Deployment *(planned)*](#4-deployment-planned) — the runtime on AWS
- [5. Network *(planned)*](#5-network-planned) — VPC, subnets, trust boundaries

---

## 1. System context

Who uses it, and which external systems it depends on.

```mermaid
flowchart TB
    analyst["World Bank analyst<br/>(economist / country team)"]
    wb[("World Bank<br/>Open Data API<br/>wbgapi")]
    claude[("Anthropic<br/>Claude API")]
    system["<b>WB Health-Systems<br/>Performance Monitor</b><br/>ingest · warehouse · model · AI · dashboard"]

    analyst -->|"explores benchmarks,<br/>trends, plain-English Q&A"| system
    wb -->|"health & economic<br/>indicators (public)"| system
    system -->|"grounded questions"| claude
    claude -->|"cited answers +<br/>country briefs"| system
```

## 2. Container / application

The independently-deployable pieces and how they talk. The read path never touches anything but the
`published` zone (Constitution III).

```mermaid
flowchart TB
    subgraph client["Client"]
      web["Dashboard<br/>Next.js + Tailwind<br/>(spec 006)"]
    end
    subgraph svc["Service"]
      api["FastAPI<br/>/predict · /brief · /ask · read API<br/>(specs 002/004/005)"]
      pipe["Batch pipeline<br/>ingest → dbt-build → train<br/>(specs 001/002/003)"]
    end
    subgraph stores["Data stores"]
      pg[("PostgreSQL<br/>staging · warehouse · published")]
      obj[("Object store<br/>MinIO → S3<br/>raw zone")]
    end
    wb[("World Bank API")]
    claude[("Claude API")]

    web -->|"HTTPS / JSON (CORS)"| api
    api -->|"reads published only"| pg
    api -->|"grounded prompts"| claude
    pipe -->|"pulls"| wb
    pipe -->|"raw objects"| obj
    pipe -->|"staging → warehouse → published"| pg
```

## 3. Data architecture

The medallion zones — raw is immutable; each zone is derived from the one before; the model and API
read only the published mart. This is the governance spine.

```mermaid
flowchart LR
    wb[("World Bank<br/>wbgapi")] --> raw
    subgraph zones["Governed zones"]
      direction LR
      raw[["<b>raw</b> (S3/MinIO)<br/>immutable pull, replay/audit"]]
      staging[["<b>staging</b><br/>tidy long rows +<br/>data-quality checks"]]
      wh[["<b>warehouse</b> (dbt)<br/>star schema:<br/>dim_* + fact_indicator"]]
      pub[["<b>published</b> (dbt)<br/>country_year_indicators<br/>+ model_residual"]]
      raw --> staging --> wh --> pub
    end
    reg[("ingestion.data_sources<br/>+ pull_log — provenance")] -.-> staging
    pub --> model["ML model<br/>(train + residuals)"]
    pub --> api["read API + AI"]
    model --> pub
```

## 4. Deployment *(planned)*

Target runtime on AWS (spec 007): everything as Terraform + CI/CD. The batch pipeline is a **scheduled
task**, not a long-running service.

```mermaid
flowchart TB
    users["Users (HTTPS)"]
    subgraph aws["AWS"]
      alb["Application Load Balancer<br/>/api/* · /*"]
      subgraph ecs["ECS Fargate"]
        apisvc["api service"]
        websvc["web service"]
        job["pipeline task<br/>(EventBridge schedule)"]
      end
      rds[("RDS<br/>PostgreSQL")]
      s3[("S3<br/>raw + model artifact")]
      sm["Secrets Manager<br/>ANTHROPIC_API_KEY, DB creds"]
    end
    claude[("Claude API")]

    users --> alb --> apisvc & websvc
    apisvc --> rds & s3 & claude
    job --> rds & s3
    apisvc -.reads.-> sm
    job -.reads.-> sm
```

## 5. Network *(planned)*

Trust boundaries (spec 007): only the ALB is public; compute and data sit in private subnets.

```mermaid
flowchart TB
    inet(["Internet"])
    subgraph vpc["VPC"]
      subgraph pub["Public subnet"]
        alb["ALB (443)"]
      end
      subgraph priv["Private subnets"]
        fargate["Fargate tasks<br/>(api · web · pipeline)"]
        rds[("RDS")]
      end
    end
    inet -->|"443 only"| alb
    alb -->|"SG: ALB → app"| fargate
    fargate -->|"SG: app → db (5432)"| rds
    fargate -->|"VPC endpoint / NAT"| s3ext[("S3 · Secrets Manager")]
```

---

## Key decisions (ADR-style summary)

| Decision | Choice | Why |
|---|---|---|
| Data governance | Medallion zones, read-only `published` | provenance + a single clean read surface |
| Object store | MinIO locally → **S3** in cloud | S3-compatible, zero `boto3` code change |
| Batch pipeline | **scheduled task**, not a service | it runs and exits; no idle compute |
| LLM | Anthropic **Claude** (API/Bedrock) | grounded, cited; not self-hosted |
| Model serving | in-process artifact from S3 | tiny model; a real-time endpoint is overkill |
| Data quality | filter + tripwire gate (spec 008) | public data has real errors; validate, don't trust |

*Full detail lives in the specs (`specs/001`–`009`); this is the map, not the territory.*

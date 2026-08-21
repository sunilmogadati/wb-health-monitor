# Reference Architecture

The WB Health-Systems Performance Monitor, described in the standard architecture **views**. Each view
answers a different question; together they are the reference architecture. Diagrams are Mermaid so they
live in git and render on GitHub. The Deployment + Network views are the **built** AWS infra (spec 007),
`terraform apply`-verified live on 2026-08-21.

- [1. System context](#1-system-context) — who and what the system talks to
- [2. Container / application](#2-container--application) — the running pieces
- [3. Data architecture](#3-data-architecture) — how data flows through the zones
- [4. Deployment (AWS)](#4-deployment-aws) — the runtime on AWS
- [5. Network](#5-network) — VPC, subnets, trust boundaries

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

## 4. Deployment (AWS)

Built for spec 007 (v1.2.0) — `terraform apply`-verified live on AWS (2026-08-21), then torn down.
The whole platform as Terraform (`infra/`) + CI/CD. The **dashboard is a static export on S3 +
CloudFront** (no web container); CloudFront routes `/api/*` to the ALB so the browser hits the API
**same-origin**. The batch pipeline is a **scheduled Fargate task**, not a service. Every top-level
resource is tagged `Project=wb-health-monitor` (see `infra/RESOURCES.md`). Diagram = the 60 resources
a `terraform apply` creates.

```mermaid
flowchart TB
    users["Users (browser)"]
    gh["GitHub Actions<br/>OIDC deploy role"]
    claude[("Anthropic Claude API")]
    subgraph aws["AWS · us-east-1"]
      waf["WAFv2 web ACL<br/>managed rules + rate-limit"]
      cf["CloudFront<br/>default → S3 · /api/* → ALB"]
      s3web[("S3: web<br/>static export, private/OAC")]
      alb["ALB (:80)"]
      ecr["ECR: api image"]
      evt["EventBridge Scheduler<br/>daily cron"]
      subgraph ecsc["ECS Fargate"]
        api["api service<br/>FastAPI :8000"]
        pipe["pipeline task<br/>ingest→dbt→train"]
      end
      rds[("RDS PostgreSQL<br/>warehouse · mart · residuals")]
      s3raw[("S3: raw zone")]
      s3art[("S3: model artifacts<br/>versioned")]
      sm["Secrets Manager<br/>DB creds · ANTHROPIC_API_KEY"]
    end

    users --> waf --> cf
    cf --> s3web
    cf -->|/api/*| alb --> api
    gh -->|build + push| ecr
    gh -->|apply · s3 sync · alembic| aws
    ecr --> api & pipe
    evt --> pipe
    api --> rds & s3art & claude
    api -.reads.-> sm
    pipe --> rds & s3raw & s3art
    pipe -.reads.-> sm
```

**Alternative tracks (separate Terraform roots, documented reference — not applied):**
`infra/sagemaker/` (spec 009, managed model lifecycle) and `infra/mwaa/` (spec 012, managed Airflow
orchestration) each replace one slice of the above; adopt deliberately, not by default.

## 5. Network

Only CloudFront/ALB are internet-facing; compute + data sit in **private subnets**. Security groups
chain ALB → tasks → RDS. **VPC endpoints** keep task↔AWS-service traffic off the NAT (S3 via a free
gateway endpoint; ECR/Secrets/Logs via interface endpoints).

```mermaid
flowchart TB
    inet(["Internet"])
    edge["CloudFront + WAF (edge)"]
    subgraph vpc["VPC 10.20.0.0/16"]
      subgraph pub["Public subnets ×2"]
        alb["ALB"]
        nat["NAT gateway"]
        igw["Internet gateway"]
      end
      subgraph priv["Private subnets ×2"]
        tasks["Fargate tasks<br/>api · pipeline"]
        rds[("RDS")]
        vpce["VPC endpoints<br/>S3(gw) · ECR · Secrets · Logs"]
      end
    end

    inet --> edge --> alb
    alb -->|"SG: ALB→tasks"| tasks
    tasks -->|"SG: tasks→rds :5432"| rds
    tasks -->|"AWS APIs, no NAT"| vpce
    tasks -->|"egress: Claude API"| nat --> igw
```

---

## Key decisions

The *why* behind this structure lives in the [Architecture Decision Records](adr/README.md); the table
below is the summary.

| Decision | Choice | Why |
|---|---|---|
| Data governance | Medallion zones, read-only `published` | provenance + a single clean read surface |
| Object store | MinIO locally → **S3** in cloud | S3-compatible, zero `boto3` code change |
| Batch pipeline | **scheduled task**, not a service | it runs and exits; no idle compute |
| LLM | Anthropic **Claude** (API/Bedrock) | grounded, cited; not self-hosted |
| Model serving | in-process artifact from S3 | tiny model; a real-time endpoint is overkill |
| Data quality | filter + tripwire gate (spec 008) | public data has real errors; validate, don't trust |
| Frontend hosting | static export → **S3 + CloudFront** | client SPA; no web container; same-origin `/api/*` → ALB |
| Edge security | **WAFv2** on CloudFront | managed rules + rate-limit before the ALB |
| API gateway | **none** — ALB + ACM + Route53 | custom domain + TLS without API Gateway |
| Agent | **LangGraph** + LangSmith (spec 011) | multi-step tool loop; grounding inherited from `/ask` |

*Full detail lives in the specs (`specs/001`–`012`); this is the map, not the territory. The AWS
deployment above is the built `infra/` — see `docs/DEPLOYMENT.md` (runbook) and `infra/RESOURCES.md`
(the 60 resources + cost + teardown).*

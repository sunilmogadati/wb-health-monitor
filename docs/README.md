# Documentation — start here

The WB Health-Systems Performance Monitor: a spec-driven, test-driven governed data platform on public
World Bank health data — ingestion → warehouse → ML model → AI (grounded Q&A + a LangGraph agent) →
dashboard, deployed on AWS. Read in this order:

| # | Doc | What it answers |
|---|---|---|
| 1 | **[PROJECT_BRIEF.md](PROJECT_BRIEF.md)** | What & why + **authoritative current status** (the Build-status table). Start here. |
| 2 | **[ARCHITECTURE.md](ARCHITECTURE.md)** | The map — system context, containers, data zones, and the **built AWS deployment + network** (Mermaid diagrams). |
| 3 | **[DEPLOYMENT.md](DEPLOYMENT.md)** + **[../infra/RESOURCES.md](../infra/RESOURCES.md)** | The AWS runbook (manual steps vs. Terraform) + the exact resources, cost, and teardown. |
| 4 | **[data-and-storage.md](data-and-storage.md)** | The data layer — zones, schema, provenance. |
| 5 | **[adr/README.md](adr/README.md)** | The *why* behind each significant decision (ADRs 0001–0009). |
| — | [ROADMAP.md](ROADMAP.md) | **Historical** build sequence (specs 001–005 era) — the SDD "how we work" story, not current status. |

## The governance spine (the capstone's method story)

- **Constitution** (`.specify/memory/constitution.md`) — 7 principles, incl. **VII. Change
  Traceability** (every behavior change traces to a spec / amendment / ADR / FR-named test).
- **Specs** (`specs/001`–`012`) — each capability specified → clarified → planned → tasked →
  implemented. 009 (SageMaker) and 012 (MWAA) are **documented alternative tracks**, not required.
- **Enforcement** — a CI **traceability gate** (`scripts/check_traceability.py`, ADR-0008) blocks an
  orphan behavior change; a PR template reconciles spec status/tasks/version in the same PR.

## The build, end to end

Ingestion (001) → warehouse star schema (003) → ML model + brief (002) → AI insights `/ask` (004) →
read API (005) → dashboard (006) → deploy to AWS (007) → continuous evaluation + LLM-judge (008) →
life-expectancy forecast (010) → LangGraph agent (011). Alternatives: managed MLOps on SageMaker (009),
managed Airflow on MWAA (012).

**Verified live on AWS (2026-08-21):** the full stack was `terraform apply`-deployed, seeded on Fargate,
and served real data through CloudFront → ALB → ECS (ARM64) — then torn down (`../infra/teardown.sh`).

# Capstone Roadmap — Step by Step

The one place that tells you **what we're building, how we work, and exactly what to do next.**
Read "How we work" once, then follow the phases in order.

**What we're building:** a *WB Health-Systems Performance Monitor* — a governed data platform on public
World Bank data, with an ML model, an AI layer, and an analytics dashboard on top.

**Legend:** ✅ done · ▶️ do now · ⬜ later ·  👤 each student · 🧑‍🏫 instructor-led

---

## How we work (read once)

1. **Spec-driven.** Every feature is a spec under `specs/NNN-name/`. The loop is:
   **constitution** (the rules) → **specify** (what) → **clarify** (resolve unknowns) →
   **plan** (how + research) → **tasks** (checklist) → **implement** → **review** → **merge**.
2. **Git Flow — branch → PR → merge.** `main` is the released line; **`develop`** is the shared
   integration branch (seeded once from `main`). You work on **your own `XX-Dev` branch** (initials +
   `-Dev`, e.g. `SM-Dev`) cut from `develop` — never commit to `main` or `develop` directly. Open a
   Pull Request **into `develop`**, reviewed against the spec's Success Criteria **and** the
   constitution, then merged. That's how your work becomes part of the capstone.
3. **Two command families:** `/speckit.*` drives the spec loop; `make` drives the dev loop
   (see the cheat sheet at the bottom).

---

## Status at a glance

| Phase | What | Who | Status |
|---|---|---|---|
| 0 | Setup — clone, `.env`, `make up` | 👤 | ✅ works |
| 1 | Run the pipeline, load data to Postgres | 👤 | ✅ works (`make ingest`) |
| 2 | Ratify the constitution | 🧑‍🏫 | ✅ v1.0.0 |
| 3 | Accept the specs (001, 002) | 🧑‍🏫 | ▶️ **next** |
| 4 | ML homework → spec 002 (models + brief) | 👤 | ▶️ **now** |
| 5 | Warehouse / star schema (spec 003) | 👤 | ✅ works (`make dbt-build`) |
| 6 | AI layer — RAG / NL query (spec 004) | 👤 | ⬜ |
| 7 | Analytics dashboard (spec 005) | 👤 | ⬜ |

---

## Phase 0 — Setup (👤 once per person)

```bash
git clone https://github.com/sunilmogadati/wb-health-monitor.git
cd wb-health-monitor
cp .env.example .env
make up            # builds + starts api + db + minio, waits for health
```
**Done when:** `curl http://localhost:8000/api/v1/health` returns 200 (or `make ps` shows all healthy).

## Phase 1 — Run the pipeline & load data ✅ (demo / repeat any time)

```bash
make migrate       # creates the ingestion.pull_log lineage table
make ingest        # pull WB indicators -> CSV -> load into Postgres -> log the run
```
Verify the data landed:
```bash
docker compose exec db psql -U wbhealth -d wbhealth \
  -c "select indicator, count(*) from staging.wdi_observation group by 1 order by 1;" \
  -c "select pull_id, rows_fetched, status from ingestion.pull_log;"
```
**What it does:** `source (World Bank) → raw pull → staging.wdi_observation → sync-log`. Currently 6
indicators, ~2271 rows, 48 Sub-Saharan Africa countries, 2015–2022.
**Done when:** `staging.wdi_observation` is populated and `pull_log` shows a `succeeded` row.

## Phase 2 — Ratify the constitution ✅

Read `.specify/memory/constitution.md` — the 6 principles that gate every PR (public data only;
spec-driven + test-backed; governed pipeline; conformed dimensional model; **honest modeling**;
reproducible/containerized). **Ratified v1.0.0.** To change it later: PR with rationale + version bump.

## Phase 3 — Accept the specs 🧑‍🏫 ▶️ NEXT

Two specs exist: `001-wdi-ingestion` (the pipeline) and `002-country-health-model` (the ML slice).
Each has `[NEEDS CLARIFICATION]` markers to resolve together, then mark `Status: Accepted`.
```
/speckit.clarify   002-country-health-model     # resolve: model artifact location (local vs MinIO)
/speckit.plan      002-country-health-model     # generates research.md + plan.md
/speckit.tasks     002-country-health-model     # generates the tasks.md checklist
```
**Done when:** the `[NEEDS CLARIFICATION]` items are answered and the spec status is `Accepted`.

## Phase 4 — ML homework → spec 002 👤 ▶️ NOW

Your homework (predict `life_expectancy` from spending + context; compare LR/DT/RF/XGBoost;
"Country Health Brief" via Pydantic) becomes a real contribution here.

```bash
git checkout develop && git pull                    # shared integration branch
git checkout -b <YOUR-INITIALS>-Dev                 # your branch off develop, e.g. SM-Dev
#   already have your branch?  git checkout <YOUR-INITIALS>-Dev && git merge develop
pip install -e "backend[ml]"          # pandas / scikit-learn / xgboost / joblib
make ingest                            # ensure the feature indicators are loaded
```
Fill in the scaffold (search for `STUDENT TODO`):
- `backend/ml/train.py` — add **XGBoost**; after picking the winner, compute + persist **residuals**
  (value-for-money signal, *not* causation).
- `backend/ml/brief.py` — implement the **Claude structured-output** call that fills
  `CountryHealthBrief` (keep the deterministic fallback so tests pass with no API key).
```bash
make train                             # trains, prints the metrics comparison, saves the winner
make test                              # schema + honest-framing guards must pass
git add -A && git commit -m "002: country health model + brief"
git push -u origin <YOUR-INITIALS>-Dev
gh pr create --base develop --fill     # PR targets develop (or open it in the GitHub UI)
```
**Done when:** all four models are compared, the brief is schema-valid, `make test` is green, and the
PR is approved (spec Success Criteria + **no blame/causal language**, SC-006) and merged into `develop`.

## Phase 5 — Warehouse / star schema (spec 003) ✅

Turns `staging` into a conformed dimensional model with **dbt**: `dim_country`, `dim_indicator`,
`dim_year`, `fact_indicator` (warehouse schema) and `country_year_indicators` (published mart).

```bash
pip install -e "backend[warehouse]"    # dbt-postgres
make dbt-build                          # builds staging -> warehouse -> published, runs the tests
docker compose exec db psql -U wbhealth -d wbhealth \
  -c "select * from published.country_year_indicators where country_code='NGA' order by year desc limit 5;"
```

dbt project lives in `backend/dbt/` (models under `models/{warehouse,published}/`, tests inline +
`tests/`). The `published` mart is the single read surface for the model (spec 002) and dashboard
(spec 005).

## Phase 6 — AI layer: RAG / natural-language query (spec 004) ⬜

Over the **published** marts: ask "which countries under-perform their health spending?" → an
agent/tool turns it into SQL, returns a **grounded, cited** narrative (no invented numbers).
Reuses `backend/ml/brief.py`'s structured-output pattern. Spec `004-ai-insights`.

## Phase 7 — Analytics dashboard (spec 005) ⬜

Published marts → API → charts: peer-group benchmarks, the residual (over/under-performance) map,
indicator trends. Spec `005-dashboard`.

---

## Command cheat sheet

| Dev loop (`make`) | Spec loop (`/speckit`) | Git flow |
|---|---|---|
| `make up` / `down` | `/speckit.constitution` | `git checkout -b <INITIALS>-Dev` (off `develop`) |
| `make migrate` | `/speckit.specify` | `git commit -m "NNN: ..."` |
| `make ingest` | `/speckit.clarify` | `git push -u origin <INITIALS>-Dev` |
| `make train` | `/speckit.plan` | `gh pr create --base develop --fill` |
| `make test` / `ci` | `/speckit.tasks` | review → **merge into `develop`** |

## Definition of done for ANY spec (the merge gate)

1. Acceptance criteria in the spec are met.
2. `make ci` is green (lint, types, tests).
3. The constitution is honored — especially **honest modeling** (benchmark, association, never
   causation or blame).
4. PR reviewed and approved, then **merged into `develop`** — `main` stays the released, stable line.

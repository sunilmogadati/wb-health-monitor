# WB Health-Systems Performance Monitor — Project Brief

**Project:** World Bank **Health-Systems Performance Monitor**
**Audience:** the engineering team building this project.
**Status:** the *what & why*. The build **method** (spec-driven, test-driven, ticket-owned) is in the companion **Spec-Kit Method** doc.

> **How to read this:** mission → use case → what the model actually claims → dataset → architecture → data model → dev environment → tech stack → deliverables.

---

## Part 0 — What you're building, in one sentence

A **spec-driven, test-driven data platform** that turns **World Bank open health data** into a decision tool: it **ingests** WB indicators, **curates** them through a governed data pipeline, **trains and evaluates several models** to find where countries under-perform on health outcomes *for what they spend*, **serves** it over an API, and presents a **country → region dashboard**.

You build it as a **team**, as a real ticketed project — not a throwaway notebook.

---

## Build status (2026-08-19)

**Repo:** `github.com/sunilmogadati/wb-health-monitor` (**public**). **Git Flow:** `main` (released) ·
`develop` (integration) · per-dev `XX-Dev` branches → PRs into `develop`. Step-by-step: `docs/ROADMAP.md`.

**Specs — 001–006 built + merged; 008 substantially built; 007 + 009 drafted (production track):**

| Spec | Status |
|---|---|
| 001 ingestion (raw→MinIO→staging, source registry) | ✅ built + merged |
| 002 country-health model + serving (`/predict`, `/brief`) | ✅ built + merged |
| 003 warehouse star schema (dbt) | ✅ built + merged |
| 004 AI insights (`/ask`, SQL-tool agent) | ✅ built + merged |
| 005 analytics read API (backend) | ✅ built + merged |
| 006 analytics dashboard (UI, React/Next.js/Tailwind) | ✅ built + merged |
| 008 continuous evaluation & quality gates | 🟩 **built** (v2.0.0): deterministic gate, anomaly detection (robust-z + YoY), filter+tripwire, ML champion/challenger, data-quality serving, LLM-judge (**groundedness + helpfulness**), scheduled/CI wiring, **golden regression cases + expected key-facts**, **LLM champion/challenger** (`select_model.py` → `ADR-0009`, picks by quality→cost→latency) |
| 010 life-expectancy forecast (`/forecast` — project inputs → predict future years) | 🟩 **built** (v1.2.0): per-feature linear trend + clamps, forecast endpoint, UI forecast card (2023–2028) + **indicative interval** (cv_rmse widened by horizon) + **trend-chart projection** (`/forecast/series` — dashed model/trend continuation, honest basis disclosure) |
| 007 deployment — AWS (Terraform IaC + CI/CD) | 🟨 **accepted (v1.1.0) + authored**: model artifact via S3 (FR-006, live-tested); env-driven S3 client + `.env.example`; **dashboard = static export → S3 + CloudFront** (`/api/*`→ALB same-origin, static export **build-verified**); full `infra/` Terraform (VPC/RDS/S3/ECS+ALB/CloudFront/EventBridge/Secrets/IAM+OIDC) + `deploy.yml` + `run_pipeline.py` — **reference IaC, not yet `terraform apply`d** (credentialed session) |
| 009 managed MLOps on SageMaker *(alt. to the 007/008 model slice)* | 🟨 **accepted (alt track) + authored**: `infra/sagemaker/` — Model Registry group, SM roles, Pipeline (quality→train→evaluate→condition→register), `pipeline.py` builder; serving = S3-load default, Registry approval replaces 008 gate. **Reference IaC, not applied** |

Also added since the first cut: an **Ask AI** dashboard panel (grounded, cited `/ask`) and **data-quality serving** (the read API returns a gap for flagged anomalies — the `18.8` no longer reaches the UI).

**Data quality is shift-left (ADR-0007):** detection runs **once**, at the staging boundary (`make flag` / `scripts/flag_quality.py`), writes `ingestion.data_quality_flag`, and the **dbt `published` model nulls flagged cells** — so the mart is clean at the source and the model + API inherit it (no re-filtering). Pipeline order: `ingest → (flag) → dbt-build → train`. `raw` stays immutable.

Constitution ratified v1.0.0. Details in the walkthrough below.

**Team research (reference, merged):** each contributor's exploration lands under `research/<name>/`
(models / vector-stores gitignored).

---

## Where we are — end-to-end walkthrough (2026-08-19)

**Status:** specs **001–004 are built and merged**; the last feature — the analytics dashboard — was
**split into two single-owner specs: 005 (read API, backend) + 006 (React/Next.js dashboard, UI)** so
two contributors can build in parallel (API merges first). The app
runs end-to-end today: **ingest → warehouse → model (predict/brief) → AI Q&A (ask)**.

### What we did
A spec-driven, test-driven **governed data platform**: a source registry + ingestion pipeline lands
World Bank data in an object store and Postgres, **dbt** conforms it into a star schema and a published
mart, an **ML model** scores value-for-money and serves predictions + a structured brief, and an **AI
agent** answers plain-English questions over the mart — all behind a **FastAPI** service.

### The DE pipeline, step by step
| # | Step | Command | What it does |
|---|---|---|---|
| 1 | **Pull** | `make ingest` | `wbgapi` fetches the configured indicators from the World Bank API |
| 2 | **Land raw (bronze)** | (in `make ingest`) | writes the exact pull as an **immutable object** to MinIO `raw` |
| 3 | **Load staging** | (in `make ingest`) | loads tidy long rows into `staging.wdi_observation`; logs the run in `ingestion.pull_log` (→ its registered source) |
| 4 | **Build warehouse + mart** | `make dbt-build` | **dbt** conforms staging into the `warehouse` star + the `published` mart |
| 5 | **Train + score** | `make train` | trains/compares models, saves the winner, writes residuals to `published.model_residual` |
| 6 | **Serve** | `make up` (FastAPI) | `/predict`, `/brief`, `/ask` — read **only** `published` |

### Schemas — what populates each, in which step, and what it's for
| Schema.object | Populated in step | Used for |
|---|---|---|
| `raw` (MinIO) | 2 — raw land | immutable "bronze" source of truth; replay / audit |
| `ingestion.data_sources` | migration + seed | the **source registry** — provenance ("which source?") |
| `ingestion.pull_log` | 3 — load | one row per run — lineage ("which run, what landed?") |
| `staging.wdi_observation` | 3 — load | tidy long landing; where **data-quality checks** run |
| `warehouse.dim_country / dim_indicator / dim_year` | 4 — dbt | conformed **dimensions** (shared keys) |
| `warehouse.fact_indicator` | 4 — dbt | the **fact** (grain = country × indicator × year) |
| `published.country_year_indicators` | 4 — dbt | the wide **read mart** — model + API + dashboard read this |
| `published.model_residual` | 5 — train | the **value-for-money** signal (actual − predicted) |

### Data we have now
**6 indicators × 48 Sub-Saharan Africa countries × 2015–2022 ≈ 2,271 rows** in staging; the model
trains on the **~357 complete country-years** (all four features + target present). Indicators:
`life_expectancy` (target), `under5_mortality`, `health_spend_pct_gdp`, `gdp_per_capita`,
`internet_pct`, `fertility_rate` (`uhc_index` is too sparse, so it's dropped).

### From raw data to model-ready features (libraries, cleaning, feature choices)

**The tools we actually use.** **pandas** does the tabular work — the WB pull (`pull_wdi.py`), the
train/compare DataFrames and the metrics table (`train.py`), and the single-row frame the API builds for
a prediction. **scikit-learn** provides three of the four models + the cross-validation and metrics;
**XGBoost** is the fourth. **NumPy** is present underneath (pandas and scikit-learn compute on NumPy
arrays — e.g. RMSE is `mse ** 0.5` over an array) but we rarely call it directly. **We do *not* use
Matplotlib**: charts are rendered in the **browser** by the React/Next.js dashboard (Recharts/Tremor),
not as server-side PNGs — the platform serves data, the client draws it. A lot of the "reshaping" that
would otherwise be pandas lives in **SQL/dbt** instead (tidy long WDI rows → one wide country-year row).

**Data cleaning — what we did, honestly.**
- **Missing values → complete-case, no imputation.** Two passes: the pull drops rows with no
  value/year (`dropna`), and the feature builder (`feature_rows`, `drop_incomplete=True`) excludes any
  country-year missing the **target or any feature**. That's why **~357 of ~2,271** rows train — the
  *simplest honest null policy*: we'd rather train on real rows than **invent** values. Imputation
  (mean/kNN/model-based) is a documented, deliberate *next* option, not a silent default.
- **Sparse column dropped.** `uhc_index` is excluded entirely — too many gaps to be useful.
- **Outliers → not removed, on purpose.** We do **no** outlier trimming. The selected family —
  **tree ensembles** — is robust to outliers by construction (splits, not distances), which is part of
  why it beats linear regression here. Explicit outlier handling is a candidate improvement, not a gap
  we're hiding.
- **Normalization / scaling → not needed here.** Decision Tree, Random Forest and XGBoost are
  **scale-invariant**, so we don't standardize. The one model that *would* benefit — Linear Regression —
  we left unscaled, and it was the weakest anyway; if we leaned on linear/distance models we'd add a
  `StandardScaler`. Knowing *when scaling matters* is the point.

**Feature engineering — how the features were chosen.** Selection here is **domain-driven and
deliberately small/interpretable**, not automated. The four predictors are health-economics levers:
**health spending (% GDP)** — the value-for-money lever itself; **GDP per capita** — wealth/development;
**internet %** — an infrastructure/development proxy; **fertility rate** — a demographic health-transition
proxy. Two deliberate *exclusions* are the real teaching points: `uhc_index` (too sparse, above), and —
importantly — **`under5_mortality` is pulled but *not* used as a predictor**: it's so tightly coupled to
life expectancy that it would act as a **near-restatement of the target** (leakage-flavoured), inflating
accuracy without adding insight. We did **not** run automated selection (RFE/Lasso) or build derived
features (interactions, `log(GDP)`) — both are honest next steps. The empirical check that the small set
is reasonable comes from the model comparison below (tree ensembles fit it well).

### Data quality in practice — a real anomaly the eval gate caught

Building the continuous-evaluation gate (spec 008) paid off immediately: the **data-quality gate
halted `make train`** because a value was impossible — **Central African Republic (CAF), 2022,
`life_expectancy = 18.818`** (outside the plausible `[20, 95]` band). A newborn life expectancy of 18.8
means the average person dies before 19 — only ever seen in a singular catastrophe (the 1994 Rwandan
genocide, for one year).

**Our bug, or the source?** We traced it: the `staging` value matched, and querying the World Bank API
directly (`SP.DYN.LE00.IN` via `wbgapi`) returned the *same* `18.818` — so **our pipeline is faithful;
the value comes from the World Bank itself.**

**Scope.** Only **2 of 48 countries** are affected — **CAF** and **South Sudan (SSD)**, across 6
country-years; the rest are clean (Kenya: a smooth 62.3 → 63.5). The tell isn't just the low value,
it's the **shape**: CAF *sawtooths* — 51.9 → 51.0 → 45.2 → 52.3 → **31.5** → 50.6 → **40.3** → **18.8**.
Life expectancy at birth is a smoothed, modelled measure; it does not oscillate ±15–20 years year to
year, even in conflict. That signature is a data/modelling error, not real mortality.

**Could it be real — war or calamity?** CAF and SSD are conflict-affected, so we tested against an
**independent source**: the **WHO Global Health Observatory** (WHO's own life tables, which also model
fragile states):

| Year | CAF — World Bank | CAF — WHO | SSD — World Bank | SSD — WHO |
|---|---|---|---|---|
| 2015 | 51.9 | 51.0 | 39.8 | 59.3 |
| 2017 | 45.2 | 51.3 | 35.4 | 58.9 |
| 2019 | **31.5** | 52.9 | 58.1 | 59.0 |
| 2021 | **40.3** | 52.3 | 57.0 | 58.6 |

WHO shows both countries **smooth and stable** (CAF ~51–53, SSD ~59). A control country (Kenya) agrees
closely between the two sources — so this is **not** a WHO-vs-World-Bank methodology offset; it is a
World-Bank-specific error in a few fragile-state cells.

**Verdict (evidence-backed).** The World Bank values for CAF and SSD are **confirmed source-data
errors**, not war or calamity — WHO, which also accounts for conflict, shows stable values. The model
had been silently training on `18.8` until the gate caught it.

**How we handle it — filter + tripwire.** Because the source is authoritative-but-flawed and we cannot
fix the World Bank, the pipeline (1) **drops implausible rows** from training (an extension of the
complete-case null policy — bad values treated as missing, so CAF/SSD keep only their valid years), and
(2) keeps the data-quality gate as a **systemic tripwire** that halts only when the *fraction* of bad
rows is large (isolated source noise → filter and proceed; a broad break → halt). The plausibility
bounds become part of the documented cleaning.

**Beyond common sense — statistical anomaly detection.** The `[20, 95]` range only worked because a
human *knew* 18.8 was impossible. For features where nobody has that intuition (GDP, fertility,
internet %), the gate also runs two **domain-agnostic** detectors with no hand-set ranges:
**robust-z** (median + MAD — values far from the column's bulk) and **year-over-year volatility**
(values that jump implausibly vs their own history). Run on the real data they caught all of CAF/SSD
*and surfaced a candidate the range check missed* — Botswana 2022, a >5-year one-year jump, flagged for
review (plausibly a real post-COVID rebound — the detector finds *candidates*; a human or an independent
source confirms).

**The lesson.** Even an authoritative public source contains real errors. A production pipeline must
*validate*, not trust — and the eval gate turned "silently training on garbage" into a caught,
explained, evidence-backed decision.

### The model — selection, evaluation, and what we chose

**How we select.** The pipeline trains four candidates — Linear Regression, Decision Tree, Random
Forest, XGBoost — and **selects by 5-fold cross-validated RMSE**, *not* a single train/test split. On a
small dataset (~357 rows) one split is noisy — which model "wins" swings with the split — so
cross-validation (averaging RMSE over five folds) gives a **robust** choice. A held-out test split is
also reported for context. The winner, metrics, and rationale are written to
`models/life_expectancy_metadata.json`.

**Results (current mart: 357 SSA country-years, 4 features):**

| Model | **CV RMSE** (↓ = selection metric) | Held-out test R² |
|---|---|---|
| **Random Forest** ← selected | **3.27 ± 0.81** | 0.565 |
| Decision Tree | 3.85 ± 0.51 | 0.725 |
| XGBoost | 3.86 ± 0.77 | 0.480 |
| Linear Regression | 4.23 ± 0.78 | 0.432 |

**What we chose and why — Random Forest:** lowest cross-validated RMSE (3.27), clearly ahead of the
field, matching the exploration's finding that **tree ensembles** fit this data best. The teaching
point: the Decision Tree had the **best single-split test R² (0.72)** yet a **worse CV RMSE** — it got
*lucky on one split*. Selecting on that single number picks the wrong model; **cross-validation corrects
it.** (An earlier run did exactly that — picked `decision_tree` on split-luck — which is why selection
now uses CV.)

**Honest framing.** Absolute accuracy is modest (4 features, ~357 rows) — and that's fine, because the
model isn't the product: the **residual (actual − predicted)** is the **value-for-money** signal — a
country above/below what its spending predicts — an *association*, never a causal or "failing" claim.

### The APIs we have (FastAPI)
| Endpoint | Spec | Returns |
|---|---|---|
| `GET /api/v1/health` (+ live/ready) | 001+ | service status |
| `GET /api/v1/predict?country=&year=` | 002 | predicted life expectancy for a country-year |
| `GET /api/v1/brief?country=&year=` | 002 | a validated **Country Health Brief** (Claude structured output; deterministic fallback) |
| `GET /api/v1/ask?q=…` | 004 | a **grounded, cited** answer over the mart (SQL-tool agent; declines when the data can't answer) |

### The LLM — which model, and why

Both AI features use **Anthropic Claude** (via `langchain-anthropic`), the project's standard LLM
(spec 004 FR-005 mandates Claude). Two tiers, matched to the job:

| Feature | Model | Why this tier |
|---|---|---|
| `/brief` (Country Health Brief) | **Claude 3.5 Haiku** (`ANTHROPIC_MODEL`, default `claude-3-5-haiku-latest`), temp 0 | a structured, low-creativity fill (Pydantic `with_structured_output`) — cheap + fast is enough |
| `/ask` (AI insights) | **Claude Sonnet 4.5** (`anthropic:claude-sonnet-4-5`) | agentic tool-use + grounded reasoning needs the stronger tier |

**Why Claude (vs OpenAI GPT / Google Gemini):**
- **Structured output + tool use** — the brief is a validated Pydantic object and the Q&A is a
  tool-calling agent; Claude does both natively and reliably.
- **Instruction-following for grounding** — the hard rule is *no invented numbers* + honest
  (value-for-money) framing; Claude follows the "use only retrieved rows / cite everything" contract well.
- **Stack standard** — one provider, one SDK, one key; the constitution keeps the platform Claude-native.

**Config + graceful degradation:**
- `ANTHROPIC_API_KEY` in `.env` enables the live LLM; `ANTHROPIC_MODEL` overrides the brief's model.
- **No key → deterministic fallback:** `/brief` returns the template brief and `/ask` runs a canned
  query + template answer, so tests and offline dev pass with no LLM at all (FR-006 / FR-008).

> **Consistency note (worth a small follow-up):** the brief's model is env-configurable but `/ask`'s is
> hardcoded, and the two tiers differ. Standardize both behind `ANTHROPIC_MODEL` on one current tier
> (e.g. a single Sonnet/Haiku choice) so the model is one config, not two code paths.

### Next → the read API + dashboard (specs 005 + 006)
The remaining feature is split into two single-owner specs so two contributors build in parallel:

- **Spec 005 — analytics read API (backend, #11):** a thin, parameterized read API over the
  `published` mart + `model_residual` — `/countries`, `/timeseries`, `/compare`, `/benchmark`
  (`/benchmark` degrades gracefully to `model_built: false` when residuals are absent). **Merges first.**
- **Spec 006 — analytics dashboard (UI, #12, depends on 005):** a **React / Next.js
  (App Router) + Tailwind** app in `frontend/` that consumes the 005 API and renders three charts
  (**value-for-money benchmark**, **indicator trends**, **country comparison**).

Each has its own accepted spec + plan + tasks. Contract (Key Entities) lives in the 005 spec, so 006
can build against mocks and integrate once 005 lands.

### Then → the production track (specs 007–009, drafted)
Once the app is complete, three drafted specs make it production-grade:

- **Spec 007 — Deployment (AWS):** the whole platform as **Terraform IaC + GitHub Actions CI/CD** —
  ECS Fargate (API + dashboard) behind an ALB, RDS, S3 (a drop-in for the object store), the batch
  pipeline as a scheduled task, secrets in Secrets Manager.
- **Spec 008 — Continuous evaluation & quality gates:** evals in **CI** (grounding, citations, decline,
  schema, and the honest-framing rule as an automated check) + **continuous** in the pipeline
  (**champion/challenger** on the model, a **data-quality gate**, and periodic re-eval for drift).
- **Spec 009 — Managed MLOps on SageMaker** *(optional alternative)*: the model's lifecycle
  (train → register → gate → serve → monitor) on managed SageMaker primitives instead of the DIY
  007/008 model slice — the managed way, shown alongside the hand-rolled one.

These build **after** 005/006 land; 009 is an alternative to the 007/008 *model* slice, not additive.

---

## Part 1 — Mission & purpose (why the World Bank cares)

The World Bank supports **health-systems strengthening** and progress toward **Universal Health Coverage (UHC)** across developing countries. A recurring analytical question: *which countries get weak health outcomes relative to what they spend and to their peers — i.e., where is the health system under-performing?*

This platform answers that from public data. Purpose: **help World Bank teams see, rank, and explore health-system performance** — so analysts know where to look first.

**Who uses it**
- **WB health economists** — benchmarking and analysis.
- **Country / sector teams** — situational awareness before designing support.
- **Government health-ministry counterparts** — a shared, plain view.

**The decisions it supports**
1. **Benchmarking** — how does a country's outcome compare to peers at similar spending?
2. **Efficiency / value-for-money** — which countries get **poor outcomes despite high spending**?
3. **Progress monitoring** — who is on- or off-track for **SDG-3** (child mortality, life expectancy, UHC)?
4. **Prioritization** — where should analysts and technical support focus?

---

## Part 2 — The use case, as one concrete scenario

> A WB country economist opens the dashboard, filters to **Sub-Saharan Africa**, and sorts by **performance gap**. Three countries stand out: relatively high health spending, but life expectancy and UHC coverage well below what the model *expects* at that spending level. She drills into one, sees the 10-year trend flat, and reads the model's explanation of which factors drive the gap. She exports the ranking as evidence for a sector note.

Every layer of the platform exists to make that scenario work.

---

## Part 3 — What "under-performance" means (and how WB gets the data)

This matters — be precise about what the model claims.

**It is a *value-for-money* benchmark, not an investment tracker.** The model asks: *given a country's health spending and context, what health outcome would we expect — and how far below (or above) that is the actual outcome?* That residual is the **performance gap**.

- **Measured against national spending, not WB's investments.** WB *open* data (the World Development Indicators) exposes **total national health expenditure** — all sources combined (government, private, external/donor) — **not** a per-country ledger of the World Bank's own loans/projects. Attributing an outcome change to a specific WB investment is a causal-impact question far beyond public indicators, so we don't claim it. The platform benchmarks *systems*, not *operations*.
- **How WB gets the data.** WDI is a **compilation** — the Bank republishes indicators sourced from specialist agencies:
  - **Health spending** → WHO **Global Health Expenditure Database** (built from national health accounts that governments report).
  - **Life expectancy / under-5 mortality** → UN Population Division / UN **IGME**.
  - **UHC service coverage** → WHO / World Bank UHC monitoring.
  - These are **annual, compiled national statistics** (with reporting lags), pulled programmatically via the official **`wbgapi`** client — no scraping, no keys.
- **Honesty rule (teach this):** this is **correlational benchmarking**, not impact evaluation. It flags *where* to look, not *why*, and not the effect of any single intervention. The model-evaluation report must state this limitation plainly.

---

## Part 4 — The dataset (public World Bank data only)

**Source:** World Bank **World Development Indicators (WDI)** via **`wbgapi`**. Core indicators — the platform's "vital signs":

| Indicator | WB code | Role |
|---|---|---|
| Life expectancy at birth | `SP.DYN.LE00.IN` | outcome |
| Under-5 mortality rate | `SH.DYN.MORT` | outcome |
| Current health expenditure (% of GDP) | `SH.XPD.CHEX.GD.ZS` | input / spend |
| UHC service coverage index | `SH.UHC.SRVS.CV.XD` | outcome |

Context features (GDP per capita, population, etc.) support the model. **Scope: country and WB-region level** (Sub-Saharan Africa, LAC, …) — no sub-national data (a known WB-API limit, out of scope).

> **Fence:** public World Bank data only. No personal, patient, or private data of any kind.

---

## Part 5 — Architecture (a governed data platform)

A full pipeline — ingest → curate → model → serve → present — modeled on a **zone architecture** (raw data is never read by anything user-facing; data earns its way to "published"):

```mermaid
flowchart TB
    WB["World Bank WDI\n(wbgapi)"] --> RAW["raw — MinIO\n(immutable NDJSON,\nobject store)"]
    RAW --> STG["staging\n(clean, typed — Postgres)"]
    STG --> WH["warehouse\n(conformed star: facts + dims)"]
    WH --> PUB["published\n(aggregated report tables)"]
    WH --> MOD["model\n(train & evaluate several;\nperformance gap = residual)"]
    PUB --> API["FastAPI\n/api + /health + /metrics"]
    MOD --> API
    API --> WEB["Dashboard\ncountry → region drill-down + ranking"]
    QA["data-quality tests\n(block promotion)"] -.gate.-> STG
    QA -.gate.-> WH
```

**The layers, and what each teaches**
- **Ingest → raw** — pull WDI via `wbgapi` as batches; store the exact pull. *(idempotent ingestion, sync logs.)*
- **Staging** — clean/type; **data-quality tests** (nulls, ranges, freshness) must pass to promote. *(ELT, data quality.)*
- **Warehouse** — a **conformed star schema** (Part 6): a fact table + shared dimensions. *(dimensional modelling.)*
- **Published** — aggregated report tables the dashboard reads (nothing user-facing reads `raw`). *(serving/curated layer, lineage.)*
- **Model** — **train and evaluate several models** (linear/tree/forest/boosting), compare with proper metrics, pick the best; the **residual = performance gap** that ranks countries. *(this is where Weeks 1–2 land — multiple models + an evaluation report.)*
- **Serving** — FastAPI with `/api`, `/health`, `/metrics`; the model behind an endpoint. *(model serving, train/serve split, monitoring.)*
- **Dashboard** — country → region drill-down on the four indicators + the performance-gap ranking. *(deployment as a dashboard.)*

*(This mirrors a real governed-data-platform pattern — zones, star schema, ELT with tests, lineage — scaled to a teaching project.)*

### The ingestion pipeline, step by step

Each stage is one `make` target; data only moves forward when its quality tests pass. This is the sequence a team member runs (and what the tickets cover):

| Step | Command | What happens |
|---|---|---|
| 1. Create schemas | `make migrate` | create the `raw` / `staging` / `warehouse` / `published` schemas + tables |
| 2. Seed reference data | `make seed` | load the dimension registries: the 4 indicators (code, unit, polarity) → `dim_indicator`; the region→country tree → `dim_entity` (from `wbgapi` region metadata) |
| 3. Ingest | `make ingest` | pull WDI via `wbgapi` for the chosen indicators/economies/years → `raw.wdi_observation` + one row in `raw.pull_log`. **Idempotent** — safe to re-run |
| 4. Build | `make build` | run the transforms: `raw → staging` (clean/type + **DQ tests**) → `warehouse` (dims + fact) → `published` (report marts). A blocking test failure **halts promotion** |
| 5. Train | `make train` | train & evaluate several models on the warehouse; write predictions → `published.rpt_performance_gap` |
| 6. Verify | `make status` · `curl /health` | confirm the stack is healthy and the marts have rows **before** opening the UI |

*(`make ingest` + `make build` are the `wbgapi`-pull and the dbt-style transform.)*

---

## Part 6 — Schemas, tables & views (the data model)

**One object store (`raw`, in MinIO) + four Postgres schemas, one per zone.** Data flows forward only;
nothing user-facing reads anything but `published`.

**`raw` — the MinIO object store (bronze), *not* a Postgres schema.** Each `make ingest` writes the
exact pull as an immutable object, keyed by the run:
```
s3://raw/world_bank_wdi/pull_<pull_id>/wdi_observation.csv     -- immutable copy of what the API returned
```

**`ingestion` (Postgres) — governance & lineage.** The source registry + the run log:
```sql
ingestion.data_sources(source_id PK, name UNIQUE, kind, base_url, description,
                       config JSONB, is_active, created_at)          -- the source registry (provenance)
ingestion.pull_log(pull_id PK, source_id FK, indicators[], economies[], object_keys[],
                   year_from, year_to, rows_fetched, status, started_at, finished_at)  -- one row / run
```

**`staging` (Postgres) — the tidy long landing** (loaded from the raw objects; where data-quality
checks run):
```sql
staging.wdi_observation(country_code, country_name, year INT, indicator, value,
                        PRIMARY KEY (country_code, year, indicator))   -- one row / country-year-indicator
```

**`warehouse` (Postgres) — the conformed Kimball star (built by dbt, `make dbt-build`):**
```sql
warehouse.dim_country(country_key PK, country_code UNIQUE, country_name)
warehouse.dim_indicator(indicator_key PK, indicator_code UNIQUE, indicator_name)
warehouse.dim_year(year_key PK, year UNIQUE)
warehouse.fact_indicator(country_key FK, indicator_key FK, year_key FK, value,
                         UNIQUE(country_key, indicator_key, year_key))   -- grain = one measurement
```

![Warehouse star schema](figures/star_schema.png)
*The star: one **fact** in the center (`fact_indicator`, grain = one country×indicator×year measurement),
three **conformed dimensions** around it. Every FK on the fact points to a dimension's PK, so any measure
slices by any dimension. The `published` mart is built **from** this star.*

**`published` (Postgres) — the read surface (the *only* zone the API/UI read):**
```sql
published.country_year_indicators(country_code, country_name, year,
    life_expectancy, under5_mortality, health_spend_pct_gdp,
    gdp_per_capita, internet_pct, fertility_rate)              -- pivoted: one row / country-year (dbt view)
published.model_residual(country_code, year, actual, predicted, residual)   -- the model output (spec 002)
```

**What each zone is *for*:**

| Zone | Where | Holds | Used for |
|---|---|---|---|
| **raw** | MinIO | immutable API pulls (CSV) | replayable "bronze" source of truth |
| **ingestion** | Postgres | `data_sources`, `pull_log` | provenance — which source, which run, what landed |
| **staging** | Postgres | `wdi_observation` (long) | typed landing; where data-quality checks run |
| **warehouse** | Postgres | star (3 dims + fact) | conformed dimensional model — slice any measure by any dim |
| **published** | Postgres | `country_year_indicators`, `model_residual` | the read API, dashboard, and model consume **only** this |

---

## Part 7 — The dev environment: what's in the compose + how to run it

Stamped from the project starter, so everyone runs an **identical** stack.

**What's in `docker-compose.yml`:**

| Service | Image / build | Ports (host→container) | Volumes | Notes |
|---|---|---|---|---|
| `app` | build `./backend` (FastAPI) | `${API_PORT}:8000` | `./backend → /workspace/backend`, `./tests → /workspace/tests` (bind, live-reload) | `uvicorn --reload`; `depends_on: db healthy`; reads `.env` |
| `db` | `postgres:16` | `${POSTGRES_PORT}:5432` | named volume `…-db-data → /var/lib/postgresql/data` | healthcheck `pg_isready`; holds the 4 schemas / warehouse |
| `web` *(stretch)* | build `./frontend` (Next.js) | `${WEB_PORT}:3000` | `./frontend` bind | the dashboard, if built as Next.js |

`.env` (copied from `.env.example`) sets ports + Postgres creds. **Remap host ports into a private range** (e.g. `1x000`) so nothing on your machine clashes:
```
API_PORT=18000
POSTGRES_PORT=15432
WEB_PORT=13000
POSTGRES_DB=wbhealth
POSTGRES_USER=wbhealth
POSTGRES_PASSWORD=wbhealth_local_dev
```

**The local run flow (from a clean clone):**
```bash
cp .env.example .env          # set the ports + creds above
make up                       # build + start app + db, wait for health
make migrate                  # create raw / staging / warehouse / published
make seed                     # load dim_indicator + dim_entity (region→country)
make ingest                   # pull WDI via wbgapi → raw
make build                    # raw → staging (DQ tests) → warehouse → published
make train                    # train/eval models → published.rpt_performance_gap

# verify BEFORE opening a browser:
curl -s localhost:18000/health     # expect {"status":"ok"} + model_loaded:true
curl -s localhost:18000/api/meta   # model card + row counts

open http://localhost:18000/docs   # API (Swagger)
open http://localhost:13000        # dashboard (if the web service is built)
```

> **Note — auth is stretch.** If the team adds Auth0 later, a common trick: a commented `DEV_LOGIN_BYPASS=true` in `.env.example` gives a password-less local sign-in (dev personas) so you don't need a real identity provider to develop. **Not needed for the core (public-data) build.**

*(Same shape as a production data platform's local stack: mounted `/workspace` + warehouse DB + a one-command dev loop + a pre-browser health check.)*

---

## Part 7½ — Operating the pipeline, end to end (with a manual check at every step)

The operator's runbook: build the stack, land the data, transform it, and **verify each stage before
moving to the next**. Some steps work today (`make up`, `make migrate`); others are the specs the
team builds (`make seed`, `make ingest`, `make dbt-build`) — the commands and checks below are the
**target shape** they're building toward.

**What MinIO is.** MinIO is **S3-compatible object storage that runs in Docker** — you `PUT`/`GET`
files ("objects") into "buckets" over the *same API* as Amazon S3. We use it as the immutable **`raw`
landing zone**: every `wbgapi` pull is written there untouched, so we always have the exact source to
replay from. Nothing user-facing reads `raw`. Console: `http://localhost:9001`; S3 API:
`http://localhost:9000`. The curated data (`staging → warehouse → published`) lives in **Postgres** —
object store for the lake, warehouse for the queries.

### The stages

| # | Stage | Command | Manual check (verify before continuing) |
|---|---|---|---|
| 1 | **Build & start the stack** | `make up` | `make ps` → `api`, `db`, `minio` all **healthy**; `curl localhost:8000/api/v1/health` → `{"status":"alive"}`; open the MinIO console `:9001` |
| 2 | **Create schemas, tables & views** | `make migrate` | `psql -c "\dn"` (schemas), `\dt ingestion.* warehouse.* published.*` (tables), `\dv published.*` (views) |
| 3 | **Register the data source** | `make seed` | `psql -c "select * from ingestion.data_sources"` → the WB WDI source with its indicators, economies, year range |
| 4 | **Get the dataset (ingest → raw)** | `make ingest` | MinIO console → objects under `raw/wdi/<date>/`; `psql -c "select status, rows_fetched from ingestion.pull_log order by started_at desc limit 1"` → `succeeded` |
| 5 | **Transform (dbt: raw → staging → warehouse → published)** | `make dbt-build` | dbt prints model **+ test** results (all pass); `psql -c "select count(*) from warehouse.fact_indicator"` and `select * from published.rpt_country_year limit 5` |
| 6 | **Update the tables (refresh)** | re-run `make ingest` then `make dbt-build` | a **new** `pull_log` row; `max(year)` / row counts in `published.*` reflect the new pull; prior `raw` objects unchanged (immutable) |

### The commands, one level deeper

- **`make up`** — `docker compose up --build --wait`: builds the API image, starts `api` + `db` + `minio`, waits for health. Re-run after changing dependencies (it rebuilds the image).
- **`make migrate`** — `alembic upgrade head` inside the api container: applies every migration in `backend/alembic/versions/` to the DB, creating the `ingestion` / `warehouse` / `published` schemas + their tables and views. Reverse the last one with `make migrate-down`.
- **`make seed`** — loads *config*, not data: the **datasource registry** (`ingestion.data_sources` — which indicators, economies, and years to pull) and the dimension seeds (`dim_indicator` codes/units/polarity, `dim_entity` region→country tree).
- **`make ingest`** — runs the ingestion job: `wbgapi` pulls the registered indicators → writes immutable NDJSON to `raw/…` in MinIO → writes an `ingestion.pull_log` row. Idempotent (a repeat is a *new* pull, never an edit).
- **`make dbt-build`** — runs **dbt**: loads `raw` (from MinIO) into `staging`, conforms into the `warehouse` star schema, aggregates into `published` marts — and runs **dbt tests** (uniqueness, not-null, ranges, freshness) that **block** promotion on failure.
- **`make train`** — trains/compares models, applies the **data-quality gate** (filter + tripwire), writes `published.model_residual` **and** `published.data_quality_flag` (so the read API can gap anomalies).

### Running the dashboard (frontend)

The dashboard is a separate **Next.js + Tailwind** app in `frontend/` (spec 006) that calls the read API. It runs on its own dev server — bring the **backend up first** (`make up && make ingest && make dbt-build && make train`), then:

```bash
nvm use 22                  # Next.js needs Node 18+; the machine default may be older (check: node -v)
cd frontend
cp .env.example .env.local  # optional — defaults to NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
npm install
npm run dev
```

**Which port?** Next serves on **`http://localhost:3000`** by default. If 3000 is already taken it **auto-increments to 3001** — and **prints the real URL in the terminal**, so always read that line (e.g. `- Local: http://localhost:3001`). The API's CORS already allows both 3000 and 3001; if you ever land on another port, add it to `CORS_ALLOWED_ORIGINS` in `.env` and recreate the container (`docker compose up -d api`).

**Ask AI** needs `ANTHROPIC_API_KEY` in `.env` for real Claude answers; without it, `/ask` returns a grounded, cited *template* (no crash). Frontend checks: `npm run lint`, `npm test` (vitest).

### Manual-verification cheat-sheet (any DB client, or `make shell` for a container shell)

```bash
DB="postgresql://wbhealth:wbhealth_local_dev@localhost:5432/wbhealth"

psql "$DB" -c "\dn"                                       # schemas
psql "$DB" -c "\dt ingestion.* warehouse.* published.*"   # tables
psql "$DB" -c "\dv published.*"                           # views

psql "$DB" -c "select source, indicators, economies, year_from, year_to from ingestion.data_sources;"
psql "$DB" -c "select pull_id, status, rows_fetched, started_at from ingestion.pull_log order by started_at desc;"

# raw landing: browse the 'raw' bucket in the MinIO console at http://localhost:9001

psql "$DB" -c "select count(*) from warehouse.fact_indicator;"
psql "$DB" -c "select * from published.rpt_country_year order by year desc limit 5;"

make shell   # then inside the container:  dbt test
```

> **Build status:** `make up` + `make migrate` (the `ingestion.pull_log` migration) work today.
> `make seed`, `make ingest`, and `make dbt-build` are delivered by specs `001`–`002` — the table
> above is the flow the team is building toward.

---

## Part 8 — Tech stack

| Layer | Stack |
|---|---|
| Ingest / warehouse / transform / model / API | **FastAPI · Python**, **Postgres** (warehouse), `wbgapi`, pandas, scikit-learn, `pytest`, `ruff`, Makefile, **Docker Compose** |
| Dashboard | **Next.js · TypeScript**, Tremor (charts), Tailwind, `vitest` — *or* a Python dashboard (Streamlit/Dash) if the team prefers "deploy as dashboard" the lighter way |
| Data quality / transforms | SQL transforms with **data-quality tests** (a lightweight dbt-style layer) |

> **Note:** the exact scaffold (profile files, compose service names, command prefix) comes from the project starter at stamp time.

---

## Part 9 — Deliverables

The project produces four deliverables, each a natural by-product:

| Deliverable | Where it comes from here |
|---|---|
| **Clean, well-documented code notebooks** | the ingest + preprocessing + model-training notebooks (Weeks 1–2 style), committed and documented |
| **Model evaluation reports** | the model layer trains **several** models and reports metrics (RMSE/R² for the gap regression, or accuracy/precision/recall/F1/ROC for a classification framing) + the honesty caveat from Part 3 |
| **Deployed prototype model** (local or cloud) | FastAPI serving the model (`/api`, `/health`, `/metrics`) — and/or the dashboard |
| **Final presentation & technical documentation** | the team demo + the README/architecture docs |

Plus **"train and evaluate *multiple* models"** and **"deploy as an API *or* dashboard"** — both are built in.

---

## Part 10 — What to reuse (don't build from scratch)

| Need | Reuse | License |
|---|---|---|
| Repo skeleton & project hygiene | `worldbank/template` | MIT |
| WB data client | `tgherzog/wbgapi` + its quickstart notebook | MIT |
| Dashboard-on-WB patterns | `mirbehroznoor/World-Bank-API-Python-DashBoard` (patterns only) | MIT |
| Tabular-indicator ML reference | `drivendataorg/pover-t-tests` | MIT |
| Health chart *recipes* | `TaranKhan/global-health-dashboard` — **reproduce the idea, write your own code, cite it** | (no license — ideas only) |

**Rule on unlicensed repos:** ideas/methods are free to reproduce; the *code text* isn't. Rewrite recipes yourself (you're learning to write them anyway) and cite the source. Copy code only from the MIT/Apache items.

---

## Part 11 — Scope: core vs. stretch

As a **team** you can go further; scope so the **core** always ships:

- **Core (must ship — hits every deliverable):** ingest → clean → warehouse → **multiple models + evaluation report** → deploy (API and/or dashboard) → docs + presentation.
- **Stretch (if the team has capacity):** the published/aggregation zone, richer data-quality tests, a natural-language query layer over the indicators, role-based access. *(Advanced — don't let it block the core.)*

---

## Part 12 — Fences & non-negotiables

1. **Public WB data only** — no personal/private data.
2. **Spec-driven + test-driven** — every feature has a spec and passing tests before "done" (see the Spec-Kit Method doc).
3. **Reuse cleanly** — permissive-licensed code only; reproduce unlicensed *ideas* in your own code.
4. **Country/region scope** — no sub-national data.
5. **Honest claims** — the model benchmarks systems (correlational); it does not attribute outcomes to any investment.

---

*A spec-driven, test-driven WB **Health-Systems Performance Monitor**: ingest (`wbgapi`) → governed Postgres warehouse (raw→staging→warehouse→published, star schema, data-quality tests) → train & evaluate several models (performance gap = outcome vs. spending residual) → FastAPI (+ dashboard). Docker Compose with a `/workspace` mount + `make up`. Maps to every deliverable; benchmarks systems, not investments.*

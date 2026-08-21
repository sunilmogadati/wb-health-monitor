# Capstone Q&A — talking points

Presenter reference. Each answer is grounded in what was **actually built** (honest framing where we
used domain reasoning vs. a formal algorithm), with a pointer to the source doc for deeper questions.

---

### 1. Purpose / outcome (in business language)
A **"value-for-money" scorecard for national health systems.** From public World Bank data it answers:
*given what a country spends on health (and its wealth, development, demographics), is it getting the
life expectancy you'd expect — or more, or less?* The model's **residual** (predicted − actual) is the
product: it flags where spending appears to over- or under-deliver. **Framed as association, not blame**
("above/below what spending predicts", never "best/worst"). Outcome: a governed pipeline + dashboard +
grounded AI Q&A that turns raw indicators into a decision aid.
→ `docs/PROJECT_BRIEF.md` Parts 0–2.

### 2. Which World Bank mission is served
WB **health-systems strengthening** and **Universal Health Coverage (UHC)**; monitoring **SDG-3** (child
mortality, life expectancy). It surfaces **allocative efficiency** — where the same health dollar buys
more or less outcome — for WB health economists, country teams, and ministry counterparts. Public data
only.
→ `docs/PROJECT_BRIEF.md` Part 1 ("why the World Bank cares").

### 3. How were the features selected? (not just intuition)
**Honest answer: domain-driven, deliberately small + interpretable — not an automated algorithm.** The
4 predictors of life expectancy are defensible health-economics levers: **health spend (% GDP)** (the
value-for-money lever), **GDP/capita** (wealth), **internet %** (development/infrastructure), **fertility
rate** (demographic transition). Two *exclusions* are the real teaching points: `uhc_index` (too sparse)
and **`under5_mortality` deliberately NOT a predictor** — it's a near-restatement of the target
(**leakage**), which would inflate accuracy without insight.

**Is information gain relevant? Yes — it's the rigorous upgrade** (a great feature-engineering exercise):
- **Mutual information** (`mutual_info_regression`) — the regression form of *information gain*; captures
  non-linear dependence correlation misses.
- **Permutation importance / RandomForest `feature_importances_`** — does the trained model actually rely
  on each feature? (RF exposes this for free — a post-hoc validation.)
- **Correlation / VIF** — prune redundancy (GDP vs internet%).

*Lead with:* "We chose an interpretable, domain-justified set for an **honest, explainable** model;
mutual-information ranking is the natural next step to make selection *measured*, not *expert-judged*."
→ `docs/PROJECT_BRIEF.md` "Feature engineering — how the features were chosen."

### 4. Data cleanup / dedup / outliers — automated as a gate (this is rigorous)
Runs at the **raw→staging boundary (shift-left, ADR-0007)** so bad data never reaches the mart
(`scripts/flag_quality.py` + `evals/checks.py`, bounds in `evals/thresholds.json`). **Algorithms:**
- **Static range checks** — plausible bounds per indicator (life exp ∈ [20,95], internet% ∈ [0,100]).
- **Robust z-score (median + MAD, threshold 3.5)** — outlier-resistant; applied **only to
  `life_expectancy`** (bounded/unimodal).
- **Year-over-year volatility** (max Δ 5.0 yrs) — catches implausible jumps.
- **Filter + tripwire** — flagged cells are **nulled** in the mart (not deleted, not trusted); if **>5%
  of rows** are bad the pipeline **halts**.
- **Dedup** — staging is `TRUNCATE`d + reloaded per pull (idempotent) — no duplicate country-years.

**Key lesson:** robust-z is applied **only to bounded/unimodal columns** — it *false-positived* on skewed
level variables (GDP, fertility — Mauritius' low fertility is real), so those use YoY + ranges. We tuned
the detector to the data's shape.
→ `docs/EVALUATION.md`, `docs/adr/0004-*`, `docs/adr/0007-*`, spec 008.

### 5. Model evaluation & selection — dynamic + continuous
- **Selection:** 4 candidates (linear, decision tree, **random forest**, XGBoost) compared on **5-fold
  cross-validated RMSE** (robust to a single split). RF won.
- **Champion/challenger (dynamic):** a retrained model is promoted **only if its CV-RMSE isn't worse**
  than the champion by more than a tolerance; the decision + rationale are written to model metadata.
- **Continuous evaluation (spec 008):** the suite runs in **CI** (regressions you cause) and on a
  **weekly schedule** vs. the live stack (drift you didn't) — catches a bad model/data change with no
  code change.
→ spec 002, spec 008, `docs/EVALUATION.md`.

### 6. DE orchestration / DAG / Airflow — did we implement it?
**What runs: EventBridge Scheduler → a scheduled Fargate task** (ADR-0002) executing `run_pipeline.py`
(`ingest → flag → dbt build → train`) on a **daily cron**. On the live AWS deploy, EventBridge fires it
automatically. **Right-sized for one linear daily batch.**

**Airflow?** A **documented alternative track (spec 012, MWAA)** with a real **Airflow DAG**
(`infra/mwaa/dags/wb_pipeline.py`, explicit task deps + retries) + MWAA Terraform — authored,
`terraform validate`-clean, **not applied** (MWAA ~$350/mo idle). *Lead with:* "EventBridge→Fargate is
correctly-sized; Airflow/MWAA is the documented path for when the pipeline becomes a real multi-task DAG
(backfills, SLAs, a UI) — over-provisioning it for one linear job would be a weakness, not a strength."
→ `docs/adr/0002-*`, spec 007 (FR-005), spec 012, `infra/mwaa/`.

### 7. LLM evaluation
Two-tier: **deterministic checks** (citations present, correct decline, banned-language/honest-framing,
expected key-facts) on every PR — free; **LLM-as-judge** for the fuzzy dimensions — **groundedness** (do
claims trace to cited rows?) + **helpfulness** (does it answer, not dump rows?) — pinned model, fixed
rubric, judge-unavailable = FAIL (never a vacuous pass). Plus **golden regression cases** (incl. bugs we
fixed) and an **LLM champion/challenger** (`select_model.py`) picking the `/ask` model by
quality→cost→latency (ADR-0009).
→ `docs/EVALUATION.md`, spec 008.

### 8. Infrastructure
CloudFront + **WAF** → S3 (static dashboard) / ALB → **ECS Fargate (ARM64)** API; **RDS** Postgres; **S3**
(raw + versioned model artifacts); **Secrets Manager**; **VPC** (public/private subnets, NAT, 5 VPC
endpoints); **EventBridge** scheduled pipeline task; **GitHub OIDC** CI/CD. Terraform IaC (`infra/`),
**deployed + verified live on AWS**. ~$100–110/mo running, ~$0 after `./infra/teardown.sh`.
→ `docs/ARCHITECTURE.md` §4–5, `docs/DEPLOYMENT.md`, `infra/RESOURCES.md`.

---

**The through-line for the whole talk:** every capability is a **spec** (001–012), carried through
`constitution → specify → clarify → plan → tasks → implement`, with a **CI traceability gate** that
blocks any behavior change lacking a spec/ADR/FR-named test (Constitution VII + ADR-0008). The method is
the product as much as the platform is.

# AR — Life Expectancy Prediction

Independent exploration of spec 002 (country health model), built outside the `backend/ml/`
scaffold — CSV/local-file driven rather than Postgres-driven. Kept here as reference; the
reviewed, shipped implementation lives in `backend/ml/`.

## Approach

1. **Data collection & prep** (`data_collection.py`, `data_prep.py`) — pull World Bank indicators
   and assemble a country-year feature table: `health_spend_pct_gdp`, `gdp_per_capita`,
   `internet_pct`, `fertility_rate`, target `life_expectancy`.
2. **Model comparison** (`train_models.py`) — train and evaluate six regressors on a shared split:
   Linear Regression, Decision Tree, KNN, AdaBoost, Random Forest, XGBoost.
3. **Reporting** (`llm_report.py`) — feed the model-comparison metrics to Claude with a
   structured-output schema (`ProjectReport` in `llm_report.py`) to generate a plain-language
   summary. Grounded in the provided metrics only ("do not invent numbers"); no country-level
   causal or performance claims are made.
4. **RAG explorer** (`rag_query.py`, `agent.py`, `predict_tool.py`) — a Chroma-based
   retrieval agent over the World Bank data for ad-hoc Q&A (not part of the model pipeline).

## Model comparison results

| Model | R² | RMSE (years) |
|---|---|---|
| Random Forest | 0.839 | 3.05 |
| KNN | 0.824 | 3.19 |
| AdaBoost | 0.816 | 3.26 |
| Linear Regression | 0.812 | 3.29 |
| XGBoost | 0.773 | 3.62 |
| Decision Tree | 0.702 | 4.15 |

**Best model:** Random Forest — leads on every error metric, needs no feature scaling.

**Top predictive features:** fertility rate (46.5% importance) and GDP per capita (35.5%)
dominate; health spending as % of GDP contributes only ~5%.

**Caveat:** small test set (42 countries) — results should be cross-validated before treating
Random Forest's edge over plain Linear Regression as meaningful.

## What's not here

Trained model binaries (`*.joblib`), the Chroma vector store, and the large intermediate CSVs are
gitignored and not committed — they regenerate by running the scripts above. Only the code and the
small result files (`model_comparison_results.csv`, `run_summary.json`, `final_report.json`) are
kept.

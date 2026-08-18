"""Train & compare models for life expectancy, then (STUDENT TODO) persist residuals + a brief.

Runs on the HOST — where scikit-learn / xgboost / pandas are installed, the same place the homework
ran:  ``make train``  (or ``cd backend && python -m ml.train``). Reads the governed feature table
from Postgres, trains models on a shared seeded split, prints a metrics comparison, and saves the
winner. Fill in the STUDENT TODO sections with your homework (XGBoost, residuals, the brief).

Honest modeling (Principle V): residuals are a value-for-money benchmark — association, not
causation. No country is "failing"; it is above/below what its spending + context predict.
"""
from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor

from ml.features import FEATURES, TARGET, connect, feature_rows

SEED = 42
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


def load_frame() -> pd.DataFrame:
    with connect() as conn:
        rows = feature_rows(conn)
    if not rows:
        raise SystemExit("no feature rows — run `make ingest` first (needs the extended indicators)")
    return pd.DataFrame(rows)


def candidate_models() -> dict:
    # STUDENT TODO (FR-003): add XGBoost — `from xgboost import XGBRegressor` — and any tuning you did.
    return {
        "linear_regression": LinearRegression(),
        "decision_tree": DecisionTreeRegressor(random_state=SEED),
        "random_forest": RandomForestRegressor(random_state=SEED),
    }


def main() -> None:
    df = load_frame()
    X, y = df[FEATURES], df[TARGET]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=SEED)

    rows, fitted = [], {}
    for name, model in candidate_models().items():
        model.fit(X_tr, y_tr)
        pred = model.predict(X_te)
        rows.append({
            "model": name,
            "r2": round(r2_score(y_te, pred), 3),
            "mae": round(mean_absolute_error(y_te, pred), 2),
            "rmse": round(mean_squared_error(y_te, pred) ** 0.5, 2),
        })
        fitted[name] = model

    table = pd.DataFrame(rows).sort_values("rmse").reset_index(drop=True)
    print(table.to_string(index=False))

    winner = table.iloc[0]["model"]
    print(f"\nselected: {winner}  (lowest RMSE; weigh accuracy vs interpretability, FR-004)")

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(fitted[winner], MODELS_DIR / "life_expectancy.joblib")
    print(f"saved -> {MODELS_DIR / 'life_expectancy.joblib'}")

    # STUDENT TODO (FR-005): with the winning model, predict over ALL rows, compute residuals
    #   (actual - predicted), and persist them (e.g. published.model_residual) — value-for-money,
    #   never causal. Then build a CountryHealthBrief (ml.brief.build_brief) for a chosen country.


if __name__ == "__main__":
    main()

"""Train & compare models for life expectancy and persist residuals + artifacts.

Runs on the HOST — where scikit-learn / xgboost / pandas are installed:  ``make train``  (or
``cd backend && python -m ml.train``). Reads the governed feature table
from Postgres, trains models on a shared seeded split, prints a metrics comparison, and saves the
winner. Fill in the TODO sections (XGBoost, residuals, the brief).

Honest modeling (Principle V): residuals are a value-for-money benchmark — association, not
causation. No country is "failing"; it is above/below what its spending + context predict.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor

from ml.features import FEATURES, TARGET, connect, feature_rows

SEED = 42
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "life_expectancy.joblib"
METADATA_PATH = MODELS_DIR / "life_expectancy_metadata.json"


def load_frame() -> pd.DataFrame:
    with connect() as conn:
        rows = feature_rows(conn)
    if not rows:
        raise SystemExit(
            "no feature rows — run `make ingest` first (needs the extended indicators)"
        )
    return pd.DataFrame(rows)


def candidate_models() -> dict:
    return {
        "linear_regression": LinearRegression(),
        "decision_tree": DecisionTreeRegressor(random_state=SEED, max_depth=8),
        "random_forest": RandomForestRegressor(
            random_state=SEED,
            n_estimators=300,
            min_samples_leaf=2,
            n_jobs=1,
        ),
        "xgboost": XGBRegressor(
            objective="reg:squarederror",
            random_state=SEED,
            n_estimators=300,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            n_jobs=1,
        ),
    }


def persist_residuals(
    df: pd.DataFrame, predictions: pd.Series | list[float], model_name: str
) -> int:
    """Publish actual - predicted residuals as the value-for-money benchmark signal."""
    residuals = df[["country_code", "country_name", "year", TARGET]].copy()
    residuals["predicted"] = [round(float(p), 4) for p in predictions]
    residuals["actual"] = residuals[TARGET].astype(float).round(4)
    residuals["residual"] = (residuals["actual"] - residuals["predicted"]).round(4)
    records = [
        (
            row.country_code,
            row.country_name,
            int(row.year),
            float(row.actual),
            float(row.predicted),
            float(row.residual),
            model_name,
        )
        for row in residuals.itertuples(index=False)
    ]

    with connect() as conn, conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS published")
        cur.execute("DROP TABLE IF EXISTS published.model_residual")
        cur.execute(
            """
            CREATE TABLE published.model_residual (
                country_code text NOT NULL,
                country_name text NOT NULL,
                year integer NOT NULL,
                actual double precision NOT NULL,
                predicted double precision NOT NULL,
                residual double precision NOT NULL,
                model_name text NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY (country_code, year)
            )
            """
        )
        cur.executemany(
            """
            INSERT INTO published.model_residual (
                country_code, country_name, year, actual, predicted, residual, model_name
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            records,
        )
    return len(records)


def save_metadata(comparison: pd.DataFrame, winner: str) -> None:
    payload = {
        "target": TARGET,
        "features": FEATURES,
        "seed": SEED,
        "selected_model": winner,
        "selection_rationale": (
            "lowest held-out RMSE on the shared seeded split; residuals are a "
            "value-for-money benchmark, not a causal claim"
        ),
        "models": comparison.to_dict(orient="records"),
    }
    METADATA_PATH.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    df = load_frame()
    feature_frame, target = df[FEATURES], df[TARGET]
    features_train, features_test, target_train, target_test = train_test_split(
        feature_frame, target, test_size=0.2, random_state=SEED
    )

    rows, fitted = [], {}
    for name, model in candidate_models().items():
        model.fit(features_train, target_train)
        pred = model.predict(features_test)
        rows.append(
            {
                "model": name,
                "r2": round(r2_score(target_test, pred), 3),
                "mae": round(mean_absolute_error(target_test, pred), 2),
                "rmse": round(mean_squared_error(target_test, pred) ** 0.5, 2),
            }
        )
        fitted[name] = model

    table = pd.DataFrame(rows).sort_values("rmse").reset_index(drop=True)
    print(table.to_string(index=False))

    winner = table.iloc[0]["model"]
    print(f"\nselected: {winner}  (lowest RMSE; weigh accuracy vs interpretability, FR-004)")

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(fitted[winner], MODEL_PATH)
    save_metadata(table, winner)
    print(f"saved -> {MODEL_PATH}")
    print(f"metadata -> {METADATA_PATH}")

    all_predictions = fitted[winner].predict(feature_frame)
    residual_count = persist_residuals(df, all_predictions, winner)
    print(f"published residuals -> published.model_residual ({residual_count} rows)")


if __name__ == "__main__":
    main()

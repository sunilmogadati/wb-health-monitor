"""Train & compare models for life expectancy and persist residuals + artifacts.

Runs on the HOST — where scikit-learn / xgboost / pandas are installed:  ``make train``  (or
``cd backend && python -m ml.train``). Reads the governed feature table
from Postgres, trains models on a shared seeded split, prints a metrics comparison, and saves the
winner. Fill in the TODO sections (XGBoost, residuals, the brief).

Honest modeling (Principle V): residuals are a value-for-money benchmark — association, not
causation. No country is "failing"; it is above/below what its spending + context predict.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from evals import checks
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import mutual_info_regression
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor

from ml import artifacts
from ml.features import FEATURES, TARGET, connect, feature_rows

SEED = 42
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


def load_frame() -> pd.DataFrame:
    with connect() as conn:
        rows = feature_rows(conn)
    if not rows:
        raise SystemExit(
            "no feature rows — run `make ingest` first (needs the extended indicators)"
        )
    return pd.DataFrame(rows)


def _champion_rmse() -> float | None:
    """The current champion's CV RMSE from saved metadata, or None on the first run."""
    raw = artifacts.get_bytes(artifacts.METADATA_FILENAME)
    if raw is None:
        return None
    try:
        meta = json.loads(raw)
        selected = meta.get("selected_model")
        for model in meta.get("models", []):
            if model.get("model") == selected:
                return float(model["cv_rmse"])
    except (OSError, ValueError, TypeError, KeyError):
        return None
    return None


def candidate_models() -> dict[str, Any]:
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


def feature_analysis(
    feature_frame: pd.DataFrame, target: pd.Series, importances: Any
) -> dict[str, dict[str, float | None]]:
    """Feature-importance evidence (FR-011) — makes feature choice measured, not just expert-judged.

    Two signals per feature: mutual information (mutual_info_regression = the regression form of
    information gain; captures non-linear dependence correlation misses) and the winning model's
    importances (RandomForest feature_importances_). It does NOT auto-select features (the set stays
    domain-chosen for interpretability) — it validates that choice with data. Deterministic (seeded
    MI). importances may be None if the winning model exposes none.
    """
    mi = mutual_info_regression(feature_frame, target, random_state=SEED)
    imp = list(importances) if importances is not None else [None] * len(FEATURES)
    return {
        feature: {
            "mutual_info": round(float(mi[i]), 4),
            "model_importance": (round(float(imp[i]), 4) if imp[i] is not None else None),
        }
        for i, feature in enumerate(FEATURES)
    }


def save_metadata(
    comparison: pd.DataFrame,
    winner: str,
    analysis: dict[str, dict[str, float | None]] | None = None,
) -> None:
    payload = {
        "target": TARGET,
        "features": FEATURES,
        "seed": SEED,
        "selected_model": winner,
        "selection_rationale": (
            "lowest 5-fold cross-validated RMSE (robust to a single split); residuals are a "
            "value-for-money benchmark, not a causal claim"
        ),
        "models": comparison.to_dict(orient="records"),
        "feature_analysis": analysis or {},
    }
    body = (json.dumps(payload, indent=2) + "\n").encode()
    artifacts.put_bytes(artifacts.METADATA_FILENAME, body)


def main() -> None:
    df = load_frame()

    # Data quality is handled upstream now (spec 008 / ADR-0007): the flag step + dbt null anomalies
    # in the mart, so `load_frame` already returns clean rows — no filtering needed here.
    thresholds = checks.load_thresholds()
    feature_frame, target = df[FEATURES], df[TARGET]

    # Model SELECTION uses 5-fold cross-validated RMSE — robust to a single lucky/unlucky split,
    # which matters on a small dataset (~357 rows). A held-out split is also reported for context.
    cv = KFold(n_splits=5, shuffle=True, random_state=SEED)
    features_train, features_test, target_train, target_test = train_test_split(
        feature_frame, target, test_size=0.2, random_state=SEED
    )

    rows = []
    for name, model in candidate_models().items():
        neg_mse = cross_val_score(
            model, feature_frame, target, cv=cv, scoring="neg_mean_squared_error", n_jobs=1
        )
        cv_rmse = (-neg_mse) ** 0.5
        model.fit(features_train, target_train)
        pred = model.predict(features_test)
        rows.append(
            {
                "model": name,
                "cv_rmse": round(float(cv_rmse.mean()), 2),
                "cv_rmse_std": round(float(cv_rmse.std()), 2),
                "test_r2": round(r2_score(target_test, pred), 3),
                "test_rmse": round(mean_squared_error(target_test, pred) ** 0.5, 2),
            }
        )

    table = pd.DataFrame(rows).sort_values("cv_rmse").reset_index(drop=True)
    print(table.to_string(index=False))

    winner = table.iloc[0]["model"]
    winner_rmse = float(table.iloc[0]["cv_rmse"])
    print(f"\nselected: {winner}  (lowest 5-fold CV RMSE — robust to a single split, FR-004)")

    # Champion/challenger gate (spec 008 FR-006): promote only if the challenger's CV RMSE is not
    # worse than the current champion past tolerance — a regressed retrain must not overwrite it.
    tolerance = float(thresholds["rmse_regression_tolerance"])
    promotion = checks.should_promote(winner_rmse, _champion_rmse(), tolerance)
    print(f"promotion: {promotion.detail}")
    if not promotion.passed:
        print("keeping the current champion — challenger NOT promoted (spec 008 FR-006)")
        return

    # Fit the winner on ALL rows for the deployed artifact + residuals (best use of a small set).
    final_model = candidate_models()[winner]
    final_model.fit(feature_frame, target)

    # Feature-importance evidence (FR-011): mutual information + the winner's importances.
    importances = getattr(final_model, "feature_importances_", None)
    analysis = feature_analysis(feature_frame, target, importances)
    print("\nfeature importance (mutual info = information gain | model importance):")
    for feature, scores in sorted(analysis.items(), key=lambda kv: -(kv[1]["mutual_info"] or 0.0)):
        model_imp = scores["model_importance"]
        model_str = f"{model_imp:.4f}" if model_imp is not None else "n/a"
        print(f"  {feature:24} MI={scores['mutual_info']:.4f}  model={model_str}")

    buffer = io.BytesIO()
    joblib.dump(final_model, buffer)
    model_uri = artifacts.put_bytes(artifacts.MODEL_FILENAME, buffer.getvalue())
    save_metadata(table, winner, analysis)
    print(f"saved -> {model_uri}")
    print(f"metadata -> {artifacts.artifact_base()}/{artifacts.METADATA_FILENAME}")

    all_predictions = final_model.predict(feature_frame)
    residual_count = persist_residuals(df, all_predictions, winner)
    print(f"published residuals -> published.model_residual ({residual_count} rows)")


if __name__ == "__main__":
    main()

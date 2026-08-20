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
from typing import Any

import joblib
import pandas as pd
from evals import checks
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
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


def _range_flags(rows: list[dict[str, Any]], ranges: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-row static range violations (the hand-set bounds), as anomaly records."""
    flagged: list[dict[str, Any]] = []
    for r in rows:
        for col, bounds in ranges.items():
            v = r.get(col)
            if v is not None and not (float(bounds[0]) <= float(v) <= float(bounds[1])):
                flagged.append(
                    {
                        "entity": r.get("country_code"),
                        "year": r.get("year"),
                        "column": col,
                        "value": v,
                        "reason": "range",
                    }
                )
    return flagged


def data_quality_gate(df: pd.DataFrame, thresholds: dict[str, Any]) -> pd.DataFrame:
    """Filter anomalous rows; halt only if too many are bad — spec-008 filter + tripwire (FR-007).

    Flags each country-year with (a) static range violations and (b) domain-agnostic detection
    (robust-z + year-over-year volatility). A large flagged FRACTION means the pull is systemically
    broken → halt (SC-003); otherwise drop the flagged rows (isolated source errors, e.g. the WB's
    CAF/SSD life-expectancy glitches) and train on the clean remainder. Returns the cleaned frame.
    """
    rows: list[dict[str, Any]] = df.to_dict("records")
    dq = thresholds["data_quality"]
    flags = _range_flags(rows, dq.get("value_ranges", {}))
    flags += checks.detect_anomalies(rows, thresholds["anomaly_detection"])

    flagged_keys = {(f["entity"], f["year"]) for f in flags}
    fraction = len(flagged_keys) / len(rows) if rows else 0.0
    for f in sorted(flags, key=lambda x: (str(x["entity"]), x["year"]))[:25]:
        print(f"  flag  {f['entity']} {f['year']}  {f['column']}={f['value']}  ({f['reason']})")

    max_bad = float(dq.get("max_bad_fraction", 0.05))
    if fraction > max_bad:
        raise SystemExit(
            f"data-quality tripwire: {fraction:.1%} of rows flagged (> {max_bad:.0%}) — halting; "
            "the pull looks systemically broken (spec 008 FR-007)"
        )

    clean = df[~df.apply(lambda r: (r["country_code"], r["year"]) in flagged_keys, axis=1)]
    clean = clean.reset_index(drop=True)
    min_rows = int(dq.get("min_rows", 0))
    if len(clean) < min_rows:
        raise SystemExit(f"only {len(clean)} clean rows (< {min_rows}) — halting (spec 008 FR-007)")
    print(
        f"data-quality: dropped {len(flagged_keys)} anomalous country-years "
        f"({fraction:.1%}); training on {len(clean)} of {len(rows)}"
    )
    return clean


def _champion_rmse() -> float | None:
    """The current champion's CV RMSE from saved metadata, or None on the first run."""
    if not METADATA_PATH.exists():
        return None
    try:
        meta = json.loads(METADATA_PATH.read_text())
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


def save_metadata(comparison: pd.DataFrame, winner: str) -> None:
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
    }
    METADATA_PATH.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    df = load_frame()

    # Spec 008 FR-007: filter anomalous rows (tripwire halts only if too many) before training.
    thresholds = checks.load_thresholds()
    df = data_quality_gate(df, thresholds)

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

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(final_model, MODEL_PATH)
    save_metadata(table, winner)
    print(f"saved -> {MODEL_PATH}")
    print(f"metadata -> {METADATA_PATH}")

    all_predictions = final_model.predict(feature_frame)
    residual_count = persist_residuals(df, all_predictions, winner)
    print(f"published residuals -> published.model_residual ({residual_count} rows)")


if __name__ == "__main__":
    main()

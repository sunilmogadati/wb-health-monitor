"""Tests for feature-importance evidence (spec 002 FR-011).

Mutual information (= information gain, non-linear) + the winning model's importances validate the
domain-chosen feature set with data. Pure function — no DB, no live model needed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from ml.features import FEATURES
from ml.train import feature_analysis


def test_ranks_the_informative_feature_highest() -> None:
    rng = np.random.RandomState(0)
    n = 300
    frame = pd.DataFrame({f: rng.normal(size=n) for f in FEATURES}, columns=FEATURES)
    # The target is driven almost entirely by the FIRST feature.
    target = pd.Series(3.0 * frame[FEATURES[0]] + 0.01 * rng.normal(size=n))
    importances = [0.7, 0.1, 0.1, 0.1]

    out = feature_analysis(frame, target, importances)

    assert set(out) == set(FEATURES)
    top_mi = max(v["mutual_info"] for v in out.values() if v["mutual_info"] is not None)
    assert out[FEATURES[0]]["mutual_info"] == top_mi  # the driver has the highest MI
    assert out[FEATURES[0]]["model_importance"] == 0.7


def test_handles_a_model_with_no_importances() -> None:
    rng = np.random.RandomState(1)
    n = 100
    frame = pd.DataFrame({f: rng.normal(size=n) for f in FEATURES}, columns=FEATURES)
    target = pd.Series(rng.normal(size=n))

    out = feature_analysis(frame, target, None)

    assert all(v["model_importance"] is None for v in out.values())
    assert all(v["mutual_info"] is not None for v in out.values())

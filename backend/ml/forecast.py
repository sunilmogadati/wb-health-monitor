"""Project the model's inputs forward, so life expectancy can be forecast past the data (spec 010).

``/predict`` (spec 002) scores a country-year using that year's *observed* features, so it stops at
the last data year. To answer "what will life expectancy be in 2028?" we first **project each
input** from its own history — a per-feature least-squares trend line — then let the existing
trained model score those projected inputs. This is a *forecast*, not an observation: the inputs are
estimates, so the caller must surface the uncertainty and the ``is_forecast`` flag (FR-006).

Deliberately simple and honest (Principle V, FR-002): a linear trend on ~8 annual points is
inspectable and deterministic — no RNG (Principle VI), no over-fit extrapolator — and every
projected input is **clamped to a physically plausible range** (FR-003) so extrapolation never
leaves the possible (you can't have >100% internet penetration). The projected inputs are returned
so a reader can sanity-check them.
"""

from __future__ import annotations

from typing import Any

from ml.features import FEATURES

# Physically plausible bounds for each projected feature (FR-003). Extrapolation is clamped here
# so a runaway trend line can't produce an impossible input.
FEATURE_BOUNDS: dict[str, tuple[float, float]] = {
    "health_spend_pct_gdp": (0.0, 30.0),
    "gdp_per_capita": (0.0, 1_000_000.0),
    "internet_pct": (0.0, 100.0),
    "fertility_rate": (0.5, 9.0),
}

# Fewer observed points than this and a trend line isn't trustworthy — decline rather than fake it.
MIN_POINTS = 3


def _project_linear(points: list[tuple[int, float]], target_year: int) -> float | None:
    """Least-squares line through ``(year, value)`` points, evaluated at ``target_year``.

    Returns ``None`` when there are too few points to fit a trustworthy trend (FR-005). A vertical
    spread of zero years (degenerate) falls back to the mean rather than dividing by zero.
    """
    if len(points) < MIN_POINTS:
        return None
    n = len(points)
    xs = [float(year) for year, _ in points]
    ys = [value for _, value in points]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return mean_y
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / denom
    intercept = mean_y - slope * mean_x
    return slope * float(target_year) + intercept


def _clamp(feature: str, value: float) -> float:
    low, high = FEATURE_BOUNDS.get(feature, (float("-inf"), float("inf")))
    return max(low, min(high, value))


def forecast_features(
    history: list[dict[str, Any]], target_year: int
) -> dict[str, float] | None:
    """Project every model feature to ``target_year`` from a country's history.

    ``history`` is the mart rows for one country (each has ``year`` + the FEATURES; nulls allowed).
    Returns the projected, clamped feature dict, or ``None`` if *any* feature lacks enough observed
    points to project (FR-005) — a forecast is all-or-nothing because the model needs every feature.
    """
    projected: dict[str, float] = {}
    for feature in FEATURES:
        points = sorted(
            (int(row["year"]), float(row[feature]))
            for row in history
            if row.get(feature) is not None and row.get("year") is not None
        )
        value = _project_linear(points, target_year)
        if value is None:
            return None
        projected[feature] = round(_clamp(feature, value), 4)
    return projected

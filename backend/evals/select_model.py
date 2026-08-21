"""LLM champion/challenger (spec 008 FR-014): pick the /ask model by the golden eval, not a hunch.

Runs the answerable golden `/ask` cases through each CANDIDATE model (via `/ask?model=`), scores
quality with the *same* checks as the gate (deterministic + groundedness + helpfulness judges),
measures latency, and reads cost from a documented price table. Selects by rule — a quality
**floor** first, then lowest cost, then latency — and writes selection metadata (mirroring the ML
model's `selection_rationale`). This is the LLM analogue of `train.py`'s champion/challenger.

Paid + non-deterministic → a **manual/periodic** tool, never a per-PR gate. Adopting the champion
is a config change (`ASK_MODEL=<model>`), not a code edit.

Usage (from backend/, stack up, ANTHROPIC_API_KEY set):
    python -m evals.select_model
    python -m evals.select_model --candidates claude-haiku-4-5,claude-sonnet-4-5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from evals import checks, run

# USD per 1M tokens (input, output) — from the model card; keep in sync when prices change.
PRICE_TABLE: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
}
DEFAULT_CANDIDATES = ["claude-haiku-4-5", "claude-sonnet-4-5"]
QUALITY_FLOOR = 0.8
SELECTION_PATH = Path(__file__).resolve().parent / "llm_selection.json"


def price_out(model: str) -> float:
    """Output $/1M — the cost dimension (a documented list-price proxy, not a measured spend)."""
    return PRICE_TABLE.get(model, (0.0, 999.0))[1]


def select(rows: list[dict[str, Any]], quality_floor: float) -> dict[str, Any]:
    """Pure selection rule (FR-014): among models at/above the quality floor, lowest cost, then
    latency. If none clear the floor, take the highest-quality — never crash, never a vacuous pick.
    """
    qualified = [r for r in rows if r["quality"] >= quality_floor]
    if qualified:
        return min(qualified, key=lambda r: (r["price_out"], r["latency_s"]))
    return max(rows, key=lambda r: r["quality"])


def _call_ask(base_url: str, query: str, model: str) -> dict[str, Any]:
    import httpx

    resp = httpx.get(
        f"{base_url}/api/v1/ask", params={"q": query, "model": model}, timeout=120
    )
    resp.raise_for_status()
    body: dict[str, Any] = resp.json()
    return body


def _score_candidate(
    base_url: str, model: str, cases: list[dict[str, Any]], thresholds: dict[str, Any]
) -> dict[str, Any]:
    """Quality = fraction of checks passed on answerable /ask cases; latency = mean wall-clock."""
    passed = total = 0
    latencies: list[float] = []
    for case in cases:
        if case["target"] != "ask" or case.get("expect", {}).get("decline", False):
            continue  # only answerable /ask cases exercise the model's answer quality
        started = time.monotonic()
        payload = _call_ask(base_url, str(case["query"]), model)
        latencies.append(time.monotonic() - started)
        results = run.evaluate_case(payload, case, thresholds, run_judge=True)
        passed += sum(1 for r in results if r.passed)
        total += len(results)
    return {
        "model": model,
        "quality": round(passed / total, 3) if total else 0.0,
        "price_out": price_out(model),
        "latency_s": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "checks": total,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LLM champion/challenger (spec 008 FR-014).")
    parser.add_argument("--base-url", default=os.getenv("EVAL_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--candidates", default=",".join(DEFAULT_CANDIDATES))
    parser.add_argument("--floor", type=float, default=QUALITY_FLOOR)
    parser.add_argument("--out", default=str(SELECTION_PATH))
    args = parser.parse_args(argv)

    from evals import judge

    if not judge.judge_available():
        print("error: selection needs ANTHROPIC_API_KEY (judges score quality).", file=sys.stderr)
        return 2

    thresholds = checks.load_thresholds()
    cases = run.load_cases()
    candidates = [c.strip() for c in args.candidates.split(",") if c.strip()]

    rows: list[dict[str, Any]] = []
    for model in candidates:
        print(f"scoring {model} …")
        rows.append(_score_candidate(args.base_url, model, cases, thresholds))

    champion = select(rows, args.floor)
    rationale = (
        f"Highest-quality model at/above the {args.floor:.0%} quality floor with the lowest output "
        "price, tie-broken by latency; scored on the golden /ask eval (deterministic + "
        "groundedness + helpfulness)."
    )
    metadata = {
        "selected_model": champion["model"],
        "quality_floor": args.floor,
        "rationale": rationale,
        "candidates": sorted(rows, key=lambda r: -r["quality"]),
    }
    Path(args.out).write_text(json.dumps(metadata, indent=2) + "\n")

    print(f"\n{'model':22} {'quality':>8} {'$out/M':>8} {'latency_s':>10}")
    for r in sorted(rows, key=lambda r: -r["quality"]):
        mark = "  <- champion" if r["model"] == champion["model"] else ""
        print(
            f"{r['model']:22} {r['quality']:>8.2f} {r['price_out']:>8.1f} "
            f"{r['latency_s']:>10.2f}{mark}"
        )
    print(f"\nselected: {champion['model']}  → {args.out}")
    print(f"adopt with:  ASK_MODEL={champion['model']}  (config change, not code)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

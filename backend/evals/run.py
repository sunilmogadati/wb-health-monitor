"""Eval runner (spec 008): load cases → call the API → apply deterministic checks → scored report.

Runs against a live stack (the API must be up with the mart populated). The deterministic checks
here are free; the LLM-as-judge (groundedness) is a later, throttled add-on (``--judge``, FR-004).

Usage (from ``backend/``):
    python -m evals.run                       # deterministic gate against http://localhost:8000
    python -m evals.run --base-url URL --out report.json
    python -m evals.run --deterministic-only  # explicit: skip the judge (default today)

Exit code is non-zero if any case fails, so CI can gate on it (FR-008).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path
from typing import Any

from evals import checks

CASES_DIR = Path(__file__).resolve().parent / "cases"
API_PREFIX = "/api/v1"


def load_cases(cases_dir: Path = CASES_DIR) -> list[dict[str, Any]]:
    cases = [json.loads(Path(p).read_text()) for p in sorted(glob.glob(str(cases_dir / "*.json")))]
    return cases


def _text_blob(payload: dict[str, Any], target: str) -> str:
    """The model-facing text a case's honest-language check should scan."""
    if target == "ask":
        return f"{payload.get('answer', '')} {payload.get('caveats', '')}"
    return str(payload.get("summary", ""))


def evaluate_case(
    payload: dict[str, Any],
    case: dict[str, Any],
    thresholds: dict[str, Any],
    run_judge: bool = False,
) -> list[checks.CheckResult]:
    """Apply the deterministic checks (+ the LLM-as-judge when enabled) for this case's target."""
    target = case["target"]
    expect = case.get("expect", {})
    blob = _text_blob(payload, target)
    results = [checks.no_banned_language(blob, thresholds["banned_language"])]

    if target == "ask":
        declined = bool(expect.get("decline", False))
        results.append(checks.decline_behaviour(payload, declined))
        if not declined:
            results.append(checks.has_citations(payload))
            # Key-facts test the LLM's answer content, which exists only when a real model
            # answered (keyless, /ask returns a fixed template). Assert it in the same regime as
            # the judges, or a no-key scheduled run would falsely fail on the template text.
            if run_judge and expect.get("contains_any"):
                results.append(
                    checks.answer_contains_any(
                        str(payload.get("answer", "")), list(expect["contains_any"])
                    )
                )
    elif target == "brief":
        results.append(checks.brief_schema_valid(payload))
        tol = thresholds["numbers_tolerance"]
        band = thresholds["brief_band"]
        results.append(checks.numbers_consistent(payload, tol, band))

    if run_judge:
        results.extend(_judge_results(payload, case, thresholds))
    return results


def _judge_results(
    payload: dict[str, Any], case: dict[str, Any], thresholds: dict[str, Any]
) -> list[checks.CheckResult]:
    """Groundedness judge for the answerable cases (skips a case expected to decline)."""
    from evals import judge

    floor = float(thresholds.get("groundedness_floor", 0.7))
    help_floor = float(thresholds.get("helpfulness_floor", 0.7))
    target = case["target"]
    if target == "ask" and not case.get("expect", {}).get("decline", False):
        query = str(case.get("query", ""))
        answer = str(payload.get("answer", ""))
        return [
            judge.judge_groundedness(query, answer, list(payload.get("citations", [])), floor),
            # Groundedness alone passes a grounded-but-useless row dump; helpfulness catches it.
            judge.judge_helpfulness(query, answer, help_floor),
        ]
    if target == "brief":
        cite = [
            {
                "predicted": payload.get("predicted_life_expectancy"),
                "actual": payload.get("actual_life_expectancy"),
                "residual": payload.get("residual"),
                "indicators": payload.get("indicators"),
            }
        ]
        question = f"Country health brief for {case.get('country')} {case.get('year')}"
        return [judge.judge_groundedness(question, str(payload.get("summary", "")), cite, floor)]
    return []


def _call_api(base_url: str, case: dict[str, Any]) -> dict[str, Any]:
    import httpx  # dev/runtime dep; only needed for a live run

    target = case["target"]
    if target == "ask":
        resp = httpx.get(f"{base_url}{API_PREFIX}/ask", params={"q": case["query"]}, timeout=60)
    elif target == "brief":
        resp = httpx.get(
            f"{base_url}{API_PREFIX}/brief",
            params={"country": case["country"], "year": case["year"]},
            timeout=60,
        )
    else:
        raise ValueError(f"unknown target: {target}")
    resp.raise_for_status()
    body: dict[str, Any] = resp.json()
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the spec-008 deterministic eval gate.")
    parser.add_argument("--base-url", default=os.getenv("EVAL_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--out", default=None, help="write the scored report JSON here")
    parser.add_argument("--deterministic-only", action="store_true", help="skip the judge")
    args = parser.parse_args(argv)

    thresholds = checks.load_thresholds()
    cases = load_cases()
    report: list[dict[str, Any]] = []
    failed = 0

    from evals import judge

    run_judge = not args.deterministic_only and judge.judge_available()
    if not args.deterministic_only and not judge.judge_available():
        print("note: LLM-as-judge skipped — no ANTHROPIC_API_KEY (deterministic gate only)")

    for case in cases:
        try:
            payload = _call_api(args.base_url, case)
            results = evaluate_case(payload, case, thresholds, run_judge=run_judge)
        except Exception as exc:  # a call/eval error is a red case, never a vacuous pass
            results = [checks.CheckResult("error", False, str(exc))]
        case_passed = all(r.passed for r in results)
        failed += 0 if case_passed else 1
        check_rows = [{"name": r.name, "passed": r.passed, "detail": r.detail} for r in results]
        report.append(
            {
                "id": case["id"],
                "target": case["target"],
                "passed": case_passed,
                "checks": check_rows,
            }
        )
        mark = "PASS" if case_passed else "FAIL"
        print(f"[{mark}] {case['id']}")
        for r in results:
            if not r.passed:
                print(f"        ✗ {r.name}: {r.detail}")

    summary = {"total": len(cases), "failed": failed, "cases": report}
    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2) + "\n")
    print(f"\n{len(cases) - failed}/{len(cases)} cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

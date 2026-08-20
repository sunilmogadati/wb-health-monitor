"""LLM-as-judge for groundedness (spec 008 FR-004) — the fuzzy dimension the deterministic checks
can't score.

Pinned model + fixed rubric: given a question, an answer, and its citations, score how well every
factual claim traces back to the citations. Below the floor **fails**; a judge that can't run (no
key / API error) returns a **not-evaluated fail** — never a vacuous pass (FR-004). Runs only when a
key is present, so it stays off the free deterministic gate (FR-011).
"""

from __future__ import annotations

import json
import os
from typing import Any

from evals.checks import CheckResult

JUDGE_MODEL = "claude-sonnet-4-5"
RUBRIC = (
    "You are a strict grader. Given a QUESTION, an ANSWER, and CITATIONS (rows from a data mart), "
    "score GROUNDEDNESS from 0.0 to 1.0: to what extent is every factual claim and number in the "
    "ANSWER supported by the CITATIONS? 1.0 = every claim traces to a citation; 0.0 = unsupported. "
    'Reply with JSON only: {"score": <float 0..1>, "reason": "<one short sentence>"}.'
)


def judge_available() -> bool:
    """The judge runs only when a key is configured (throttled off the free deterministic gate)."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def result_from_score(score: float, floor: float, reason: str) -> CheckResult:
    """Pure scoring → CheckResult: pass iff the groundedness score meets the floor."""
    passed = score >= floor
    return CheckResult("groundedness", passed, f"score {score:.2f} (floor {floor:.2f}): {reason}")


def judge_groundedness(
    question: str, answer: str, citations: list[dict[str, Any]], floor: float
) -> CheckResult:
    """Score whether the answer's claims trace to the citations. Never a vacuous pass on failure."""
    try:
        import anthropic

        client = anthropic.Anthropic()
        content = (
            f"QUESTION: {question}\n\nANSWER: {answer}\n\nCITATIONS: {json.dumps(citations)}"
        )
        message = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=200,
            system=RUBRIC,
            messages=[{"role": "user", "content": content}],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        data = json.loads(text[text.index("{") : text.rindex("}") + 1])
        score = float(data.get("score", 0.0))
        reason = str(data.get("reason", ""))[:120]
    except Exception as exc:  # no key, no SDK, bad JSON, API error — all are "not evaluated" fails
        return CheckResult("groundedness", False, f"judge unavailable — not evaluated ({exc})")
    return result_from_score(score, floor, reason)

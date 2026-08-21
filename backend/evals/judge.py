"""LLM-as-judge (spec 008) — the fuzzy dimensions the deterministic checks can't score.

Two dimensions, same discipline (pinned model + fixed rubric, score + rationale, a low score fails):

- **groundedness** (FR-004): do the answer's claims trace back to the citations / mart rows?
- **helpfulness** (FR-013): does the answer *directly and usefully answer the question* — state the
  trend's direction, name the ranking's leader, give the value asked for — rather than merely
  restate grounded rows? This catches a fully-grounded but useless answer (a raw row dump):
  groundedness passes it, helpfulness fails it.

A judge that can't run (no key / API error / bad JSON) returns a **not-evaluated fail** — never a
vacuous pass (FR-004). Runs only when a key is present, so it's off the free deterministic gate.
"""

from __future__ import annotations

import json
import os
from typing import Any

from evals.checks import CheckResult

JUDGE_MODEL = "claude-sonnet-4-5"

GROUNDEDNESS_RUBRIC = (
    "You are a strict grader. Given a QUESTION, an ANSWER, and CITATIONS (rows from a data mart), "
    "score GROUNDEDNESS from 0.0 to 1.0: to what extent is every factual claim and number in the "
    "ANSWER supported by the CITATIONS? 1.0 = every claim traces to a citation; 0.0 = unsupported. "
    'Reply with JSON only: {"score": <float 0..1>, "reason": "<one short sentence>"}.'
)

HELPFULNESS_RUBRIC = (
    "You are a strict grader. Given a QUESTION and an ANSWER, score HELPFULNESS from 0.0 to 1.0: "
    "does the ANSWER directly and usefully answer the QUESTION — stating the conclusion asked for "
    "(a trend's direction and rough size, a ranking's leader, a specific value)? An answer that "
    "restates rows or lists data WITHOUT stating the answer scores LOW (near 0.2); a clear, direct "
    "answer scores high. IMPORTANT CONTEXT, do NOT penalise these — they are correct by design: "
    "(1) the data covers Sub-Saharan Africa only, so an answer scoped to those countries is right, "
    "not a limitation; (2) by policy the system uses value-for-money / 'above or below what "
    "spending predicts' framing and avoids 'best/worst' or blame — an answer that names a leader "
    "with this careful framing is fully helpful. Score whether it answers, not its hedging. "
    'Reply with JSON only: {"score": <float 0..1>, "reason": "<one sentence>"}.'
)


def judge_available() -> bool:
    """The judge runs only when a key is configured (throttled off the free deterministic gate)."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def result_from_score(
    score: float, floor: float, reason: str, dimension: str = "groundedness"
) -> CheckResult:
    """Pure scoring → CheckResult: pass iff the score meets the floor."""
    passed = score >= floor
    return CheckResult(dimension, passed, f"score {score:.2f} (floor {floor:.2f}): {reason}")


def _judge(dimension: str, rubric: str, content: str, floor: float) -> CheckResult:
    """One judged dimension. Any failure to run is a not-evaluated fail, never a vacuous pass."""
    try:
        import anthropic

        client = anthropic.Anthropic()
        message = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=200,
            system=rubric,
            messages=[{"role": "user", "content": content}],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        data = json.loads(text[text.index("{") : text.rindex("}") + 1])
        score = float(data.get("score", 0.0))
        reason = str(data.get("reason", ""))[:120]
    except Exception as exc:  # no key, no SDK, bad JSON, API error — all are "not evaluated" fails
        return CheckResult(dimension, False, f"judge unavailable — not evaluated ({exc})")
    return result_from_score(score, floor, reason, dimension)


def judge_groundedness(
    question: str, answer: str, citations: list[dict[str, Any]], floor: float
) -> CheckResult:
    """Score whether the answer's claims trace to the citations (FR-004)."""
    content = f"QUESTION: {question}\n\nANSWER: {answer}\n\nCITATIONS: {json.dumps(citations)}"
    return _judge("groundedness", GROUNDEDNESS_RUBRIC, content, floor)


def judge_helpfulness(question: str, answer: str, floor: float) -> CheckResult:
    """Score whether the answer directly and usefully answers the question (FR-013)."""
    content = f"QUESTION: {question}\n\nANSWER: {answer}"
    return _judge("helpfulness", HELPFULNESS_RUBRIC, content, floor)

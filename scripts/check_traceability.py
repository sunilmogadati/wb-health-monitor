#!/usr/bin/env python3
"""Change-Traceability CI gate — makes the constitution principle mechanical, not aspirational.

Fails a pull request that changes **behavior** without a **traceable artifact**, routing by the four
lanes the constitution defines:

- **New capability / Spec-miss** → a file under ``specs/`` changed (a new spec, or an amendment +
  version bump). This is the artifact.
- **Refactor** (behavior unchanged, structure improved) → a file under ``docs/adr/`` changed.
- **Bug** (code didn't satisfy an existing spec) → a **test** changed *and* the PR body names the
  violated requirement (``FR-###``). The regression test that names the FR is the artifact.
- **Trivial / non-behavioral** (formatting, comments, docs, config, CI) → not behavior; or, if it
  touches behavior paths for a genuinely non-behavioral reason, an explicit, auditable escape hatch:
  ``[skip-traceability: <reason>]`` in the PR body.

An "orphan" behavior change — none of the above — **blocks**, regardless of code quality (the whole
point of the principle). The decision is a pure function (``decide``) so it is unit-testable without
git or CI; ``main`` only supplies the changed-file list and the PR body.

CI usage:  BASE_REF=origin/develop PR_BODY="$PR_BODY" python scripts/check_traceability.py
Local dry-run:  BASE_REF=origin/develop python scripts/check_traceability.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

# Paths whose change alters system behavior → require a traceable artifact.
BEHAVIOR_PREFIXES: tuple[str, ...] = (
    "backend/app/",
    "backend/ml/",
    "backend/evals/",
    "backend/scripts/",
    "backend/dbt/models/",
    "frontend/src/",
)
# Paths that ARE the traceable artifacts for the spec/refactor lanes.
ARTIFACT_PREFIXES: tuple[str, ...] = ("specs/", "docs/adr/")
# Substrings that mark a file as a test (the bug lane's artifact; a test-only diff can't change
# behavior, so it never needs a spec of its own).
TEST_MARKERS: tuple[str, ...] = ("/__tests__/", "test_", "_test.", ".test.")

FR_RE = re.compile(r"FR-\d+", re.IGNORECASE)
SKIP_RE = re.compile(r"\[skip-traceability:\s*(.+?)\]", re.IGNORECASE)


def is_test(path: str) -> bool:
    return any(marker in path for marker in TEST_MARKERS)


def is_behavior(path: str) -> bool:
    """A behavior change is a non-test file under a behavior prefix."""
    return not is_test(path) and path.startswith(BEHAVIOR_PREFIXES)


def decide(files: list[str], pr_body: str) -> tuple[bool, str]:
    """Pure gate decision. Returns ``(ok, human-readable reason)``.

    Ordered by lane so the reason names *which* lane satisfied (or that none did).
    """
    behavior = [f for f in files if is_behavior(f)]
    if not behavior:
        return True, "No behavior-code changed — nothing to trace."

    if any(f.startswith(ARTIFACT_PREFIXES) for f in files):
        return True, "Behavior change carries a spec/ADR artifact (spec / amendment / refactor)."

    if any(is_test(f) for f in files) and FR_RE.search(pr_body):
        return True, "Bug lane: a test changed and the PR body names the violated FR."

    skip = SKIP_RE.search(pr_body)
    if skip:
        return True, f"Exempted — [skip-traceability: {skip.group(1).strip()}]."

    return False, "ORPHAN behavior change — no spec, no ADR, no FR-named test, no exemption."


def _changed_files(base_ref: str) -> list[str]:
    # Trusted, fixed command (git), no shell, no user-controlled executable — the only variable is a
    # ref name we build ourselves. S603/S607 are false positives here.
    result = subprocess.run(  # noqa: S603
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    base_ref = os.environ.get("BASE_REF", "origin/develop")
    pr_body = os.environ.get("PR_BODY", "")
    files = _changed_files(base_ref)

    ok, reason = decide(files, pr_body)
    if ok:
        print(f"traceability: {reason} ✅")
        return 0

    behavior = [f for f in files if is_behavior(f)]
    print(f"traceability: {reason} ❌\n")
    print("These files change behavior but carry no traceable artifact:")
    for f in behavior:
        print(f"  - {f}")
    print("\nRoute it (Constitution — Change Traceability):")
    print("  • New capability  → a new spec under specs/ (full lifecycle)")
    print("  • Spec-miss       → amend the owning spec + bump its version")
    print("  • Refactor        → an ADR under docs/adr/")
    print("  • Bug             → a regression test + name the FR (FR-###) in the PR body")
    print("  • Trivial         → add `[skip-traceability: <reason>]` to the PR body")
    return 1


if __name__ == "__main__":
    sys.exit(main())

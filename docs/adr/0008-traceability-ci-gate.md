# ADR-0008: Enforce Change-Traceability with a CI gate

**Status:** Accepted

**Date:** 2026-08-20

## Context

The constitution's **Change Traceability** principle says every behavior change must trace to an
approved artifact (a spec, an amendment, or an ADR) — an orphan change is a defect regardless of code
quality. But a principle a human has to *remember to apply* drifts. It already did: spec 010 was
implemented and merged while its `spec.md` still said "Draft" and its `tasks.md` boxes sat unchecked
(reconciled in PR #27). The principle was aspirational, not mechanical.

Two complementary fixes were chosen (the second is this ADR):

1. **Reconcile-in-PR** — a PR template that requires the author to update spec status, check off tasks,
   and bump the version *in the same PR* as the code. Process, human-run.
2. **A CI gate** — automated enforcement, so an orphan behavior change *blocks* rather than relying on
   reviewer vigilance.

## Decision

Add `scripts/check_traceability.py` + `.github/workflows/traceability.yml`. On every PR to `develop`
or `main`, the gate diffs against the base branch and **fails** when a **behavior** file changed with
no **traceable artifact**, routed by the four constitution lanes:

- **New capability / Spec-miss** → a `specs/**` file changed (new spec or amendment + version bump).
- **Refactor** → a `docs/adr/**` file changed.
- **Bug** → a test changed **and** the PR body names the violated `FR-###`.
- **Trivial / non-behavioral** → not a behavior path, or an explicit, auditable
  `[skip-traceability: <reason>]` in the PR body.

Behavior paths are `backend/{app,ml,evals,scripts}/`, `backend/dbt/models/`, `frontend/src/`
(tests excluded — a test-only diff can't change behavior). The decision is a **pure function**
(`decide`), unit-tested in `tests/test_traceability_gate.py` without git or CI.

## Alternatives considered

- **Reviewer discipline only** — the status quo that already drifted. Rejected: not mechanical.
- **Block on a label** (e.g. require a `spec`/`adr` label) — weaker; a label is metadata, not an
  artifact, and doesn't force the spec to actually change.
- **Require a spec change for *every* PR** — too blunt; punishes the bug and refactor lanes the
  constitution explicitly routes elsewhere, and can't exempt genuinely trivial changes.

## Consequences

- **+** The traceability principle is enforced, not hoped for; drift like spec 010's can't merge.
- **+** The four lanes are encoded in one readable, tested function — good teaching artifact.
- **+** The escape hatch is explicit and recorded in the PR (auditable), not a silent bypass.
- **−** A small tax on every behavior PR (name the FR, or touch a spec/ADR). Intended — that *is* the
  discipline.
- **−** Path lists and the `FR-###` convention must be kept current as the repo grows; if they rot,
  the gate mis-fires. Mitigated by the pure-function tests.

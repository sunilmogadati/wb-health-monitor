## What & why

<!-- One or two lines: what this changes and why. -->

## Change-Traceability (required)

Route this change (Constitution: **Change Traceability**) — tick the one lane that applies:

- [ ] **Bug** — code didn't satisfy an existing spec → fix **+ a regression test naming the FR**, and name that `FR-###` in this PR body.
- [ ] **Spec-miss** — a real requirement no spec captured → **amended the owning spec + bumped its version** (amendment history updated).
- [ ] **New capability** — genuinely new behavior → **a new spec** via the full lifecycle (`specs/…`).
- [ ] **Refactor** — behavior unchanged, structure improved → **an ADR** under `docs/adr/`.
- [ ] **Trivial / non-behavioral** — formatting, comments, docs, config, CI → add `[skip-traceability: <reason>]` below.

<!-- For a bug, name the requirement here, e.g.: Regression test for FR-003. -->
<!-- For a trivial behavior-path change, add: [skip-traceability: <why this is non-behavioral>] -->

## Reconcile-in-PR (before merge)

Keep the spec artifacts in sync with reality **in this PR** — never "later":

- [ ] Spec **status** reflects reality (Draft → Accepted / Implemented as appropriate).
- [ ] `tasks.md` boxes **checked** for the work in this PR.
- [ ] Spec **version bumped** if behavior changed (amendment history updated).
- [ ] `plan.md` updated if the approach changed.
- [ ] `docs/PROJECT_BRIEF.md` build status current.

## Verification

<!-- ruff / mypy / pytest / eslint / vitest results; live checks if applicable. -->

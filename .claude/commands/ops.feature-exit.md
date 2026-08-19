---
description: Final development gate for a spec - confidence audit, Definition of Done, doc sync, deferred-dependency gate, PR-ready report
---

## Feature Exit

The last gate before a spec's work ships. Audits how completely the spec was implemented, verifies
the Definition of Done, syncs canonical docs, and confirms nothing was silently deferred.

Run this when a spec's tasks are complete and you are ready to open a PR.

### User Input

```text
$ARGUMENTS
```

Resolve the feature directory from `$ARGUMENTS`, else `$env:SPECIFY_FEATURE`, else the current git
branch name. If it cannot be resolved, list `specs/*/` and ask.

---

### Phase 1: Spec-to-implementation confidence audit

Read `spec.md`, `plan.md`, `tasks.md`, `data-model.md`, `contracts/`, and `checklists/` from the
feature directory.

1. **Task completion** — parse `tasks.md`, count `- [x]` / `- [~]` / `- [ ]`, compute percent complete.
2. **Acceptance scenario coverage** — for each Given/When/Then in `spec.md`, check whether the
   implementing code exists. Score IMPLEMENTED / PARTIAL / MISSING.
3. **Contract coverage** — for each endpoint/interface in `contracts/`, verify an implementation
   registers that method + path (or the equivalent) and that request/response models exist. Score
   IMPLEMENTED / MISSING.
4. **Functional requirements** — for each `FR-*` in `spec.md`, assess by code inspection. Score
   MET / PARTIAL / NOT MET.
5. **Edge cases** — for each edge case in `spec.md`, verify handling exists. Score
   HANDLED / DEFERRED / MISSING.
6. **Checklists** — every file in `checklists/` should be fully checked. Report any unchecked item.

```
Spec-to-Implementation Confidence
=================================
Task completion:      XX/XX (NN%)
Acceptance scenarios: X/X implemented
Contract endpoints:   XX/XX covered
Functional reqs:      XX/XX met
Edge cases:           X/X handled
Checklists:           X/X complete

Overall confidence:   NN% (HIGH >=90 / MEDIUM >=70 / LOW <70)
```

---

### Phase 2: Definition of Done

Per `.specify/memory/constitution.md`, run and report each element of the project's Definition of
Done. Typically: spec satisfied; tasks complete; automated tests green; any constitutionally blocking
suite passed; traceability updated; demoed per affected role. Run the project's actual test commands
and report pass/fail per suite.

**Any suite the constitution marks as blocking (privacy, security, accessibility, or another
invariant) is a constitutional violation when it fails, not a warning. Say so plainly.**

---

### Phase 3: Canonical document sync

Update the real, canonical documents rather than duplicating content. For each, update only if this
spec touched the relevant area:

- **The requirement traceability map** (whatever the constitution names) — every FR in this spec must
  resolve to a row, with Status advanced. This is the step most commonly skipped.
- **Architecture docs** — if this spec made an architectural decision, record it (an ADR or the
  architecture doc set).
- **The API/interface contract** — if this spec added or changed endpoints, reflect them.
- **Design docs** — if API or frontend conventions changed.
- **`CLAUDE.md`** — if a project-wide convention, gotcha, or known gap changed.
- **`specs/README.md`** — update this feature's row and status.
- The spec's own `spec.md` `**Status:**` line.

---

### Phase 3.5: Deferred dependency gate

Ensures no deferral is invisible to the spec that should later fulfill it.

1. Scan `spec.md`, `plan.md`, and `data-model.md` for: "deferred", "out of scope", "future spec",
   "future feature", "later", "pending".
2. Read the deferred-dependencies register (if the project keeps one).
3. For each deferral found, check for a matching Active row. Missing means **UNREGISTERED**.
4. Flag registry rows sourced from this spec whose scope actually shipped — move them to Resolved.
5. Verify any "Waiting for" row naming this feature was addressed; if so, move it to Resolved.

Apply the registry's own decision rule: only **backward-deferred** items belong there. Scope already
assigned to a future feature is **forward-mapped** and belongs in the traceability map, not the
registry. Distinguish both from **open questions** (things only a third party can answer); those live
in the spec's `research.md`.

```
Deferred Dependency Gate
========================
| Deferred item | Source | Registry entry | Status |
|---|---|---|---|

Unregistered deferrals:   N   (MUST be registered before PR)
Stale entries:            N   (move to Resolved)
Upstream obligations met: N   (move to Resolved)

Gate: PASS / FAIL
```

**FAIL** if any deferral lacks a registry entry.

---

### Phase 3.6: Issue-tracker sync validation (optional)

**Only runs if this project mirrors specs to an issue tracker via an installed extension** (e.g. a
Jira Spec Kit extension). If no such extension is configured, **SKIP this phase entirely** and note
that specs are markdown-only here.

When an extension is present, markdown is the source of truth and the tracker is a downstream mirror;
this confirms the mirror has not drifted.

- **Skip** if the spec's tracker-mapping file is absent and the spec has never been mirrored —
  recommend running the extension's "specs to issues" command as a follow-up rather than blocking.
- **Prerequisite:** the extension's credentials file must exist. If it does not, report SKIPPED.
- Otherwise: locate the mapping file, run the extension's sync-status command, and cross-check
  checkbox state (`[x]`→Done, `[~]`→In Progress, `[ ]`→To Do) plus parent roll-up. Report drift.

```
Issue-Tracker Sync Validation
=============================
Gate: PASS / DRIFT / MISSING / SKIPPED (no tracker extension)
```

---

### Phase 4: Issue discovery

Surface anything that should not ship silently: TODO/FIXME added by this work, hardcoded values that
belong in config, missing error handling on new paths, secrets or credentials in source, endpoints
without authorization checks, and any UI that filters data the data layer should have filtered.

---

### Phase 5: Apply and report

Present findings, ask before changing files, then emit a PR-ready summary:

```
Feature Exit: <feature>
=======================
Confidence:         NN% (HIGH/MEDIUM/LOW)
Definition of Done: <suite> PASS · <suite> PASS · ...
Doc sync:           traceability updated · specs/README updated
Deferred gate:      PASS
Tracker gate:       PASS / SKIPPED
Open issues:        N

Verdict: READY FOR PR / BLOCKED (<reasons>)
```

Commit per the project's git conventions.

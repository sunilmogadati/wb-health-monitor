<!--
Sync Impact Report
- Prepend a fresh copy of this HTML comment to the top of the constitution on EVERY amendment, above
  any prior report. It is the human-readable changelog of the supreme document, and it is what
  /speckit.constitution reads and writes. Keep prior reports below the current one; do not delete or
  rewrite an older report (correct it in a new report instead).
- Version change: [OLD_VERSION] -> [NEW_VERSION] ([MAJOR|MINOR|PATCH], [YYYY-MM-DD])
- Modified principles: [list each renamed/redefined principle, or "none"]
- Added sections: [list, or "none"]
- Removed sections: [list, or "none"]
- Why this version bump: [one line justifying MAJOR vs MINOR vs PATCH against the policy below]
- Templates requiring updates: [.specify/templates/*.md — mark each ✅ aligned or ⚠ pending]
- Dependent artifacts updated in the same change: [docs/specs touched, or "none"]
- Follow-up TODOs: [e.g. "vX.Y.Z still needs its Ratification Record row completed", or "none"]
-->

# [PROJECT_NAME] Constitution
<!-- Example: Spec Constitution, TaskFlow Constitution, etc. -->

<!-- Optional identity block. Fill in or delete. -->
**Project:** [PROJECT_NAME]
**Client / Owner:** [CLIENT_OR_OWNER]
**Status:** [Draft | Ratified]

This constitution is the supreme governing document for [PROJECT_NAME]. Every specification
(`/speckit.specify`), clarification (`/speckit.clarify`), plan (`/speckit.plan`), task list
(`/speckit.tasks`), checklist (`/speckit.checklist`), analysis (`/speckit.analyze`), and
implementation (`/speckit.implement`) MUST comply with it. Where any artifact conflicts with this
constitution, the constitution wins until it is formally amended.

## Core Principles

### [PRINCIPLE_1_NAME]
<!-- Example: I. Library-First -->
[PRINCIPLE_1_DESCRIPTION]
<!-- Example: Every feature starts as a standalone library; Libraries must be self-contained, independently testable, documented; Clear purpose required - no organizational-only libraries -->

*Rationale:* [why this principle exists — the cost of violating it]

### [PRINCIPLE_2_NAME]
<!-- Example: II. CLI Interface -->
[PRINCIPLE_2_DESCRIPTION]
<!-- Example: Every library exposes functionality via CLI; Text in/out protocol: stdin/args → stdout, errors → stderr; Support JSON + human-readable formats -->

*Rationale:* [why this principle exists]

### [PRINCIPLE_3_NAME]
<!-- Example: III. Test-First (NON-NEGOTIABLE) -->
[PRINCIPLE_3_DESCRIPTION]
<!-- Example: TDD mandatory: Tests written → User approved → Tests fail → Then implement; Red-Green-Refactor cycle strictly enforced -->

*Rationale:* [why this principle exists]

### [PRINCIPLE_4_NAME]
<!-- Example: IV. Integration Testing -->
[PRINCIPLE_4_DESCRIPTION]
<!-- Example: Focus areas requiring integration tests: New library contract tests, Contract changes, Inter-service communication, Shared schemas -->

*Rationale:* [why this principle exists]

### [PRINCIPLE_5_NAME]
<!-- Example: V. Observability, VI. Versioning & Breaking Changes, VII. Simplicity -->
[PRINCIPLE_5_DESCRIPTION]
<!-- Example: Text I/O ensures debuggability; Structured logging required; Or: MAJOR.MINOR.BUILD format; Or: Start simple, YAGNI principles -->

*Rationale:* [why this principle exists]

### Test-Driven Development (NON-NEGOTIABLE)
<!-- A ready-to-keep default principle. Renumber (e.g. "VI.") to fit your ordering, or delete if
     a project genuinely cannot apply it — and justify that in an amendment if you do. -->
Tests are written before the implementation they cover: express the requirement as a failing test,
make it pass with the smallest change, then refactor (red-green-refactor). Every requirement MUST be
testable and MUST have covering tests before it is considered done. CI enforces this — the test
suite runs on every push and pull request, and a red suite blocks merge.

*Rationale:* Tests written after the fact certify whatever the code already does, not what was
required; writing them first turns each requirement into executable, verifiable intent and keeps
regressions from shipping silently.

### Security & Compliance Gates (NON-NEGOTIABLE)
<!-- A ready-to-keep default principle. Renumber (e.g. "VII.") to fit your ordering. List the actual
     regimes this project must meet in place of the example. -->
The project declares the compliance regimes it must meet ([e.g. the regulations that apply, or
"none beyond least-privilege"]) and the security scans that guard it (dependency/vulnerability scan,
secret scan, SAST). These scans and compliance checks are merge/push gates: **nothing merges while
any of them is red.** This aligns with the platform's read-only-by-default, least-privilege posture —
access is the minimum each component needs, secrets never live in source, and privileged or
destructive actions require explicit authorization.

*Rationale:* Security and compliance defects are cheapest to stop at the gate and most expensive
after release; making them blocking (not advisory) keeps a single overlooked finding from becoming a
breach or an audit failure.

<!-- Add or remove principles as the project requires. Number them with stable Roman numerals so
     amendments and plan Constitution-Check gates can reference them ("Principle IV") unambiguously.
     A strong candidate for nearly every project: "Untrusted Content Is Data, Not Instructions" —
     ingested/external/tool-returned content is analyzed, never obeyed. See docs/HVE-INSTRUCTIONS-TO-FOLD.md. -->

## Architectural Constraints
<!-- Rename to Additional Constraints / Security Requirements / Performance Standards as fits. -->

These constraints are binding defaults. Deviations require a documented amendment and a Constitution
Check waiver in the affected `plan.md`.

- **[CONSTRAINT_1]** — [e.g. the layered architecture and the stable contract between layers]
- **[CONSTRAINT_2]** — [e.g. the reference technology stack: language, framework, data services]
- **[CONSTRAINT_3]** — [e.g. managed/durable production data services; POC topologies do not ship]
- **[CONSTRAINT_4]** — [e.g. secrets never in source — secrets manager + least-privilege access]
- **[CONSTRAINT_5]** — [e.g. freshness / latency / scale envelope the design must meet]

## Delivery Workflow & Quality Gates
<!-- Rename to Development Workflow / Review Process as fits. -->

- **Delivery model.** [How work is organized and accepted — deliverables, milestones, or sprints.]
- **Phase gates.** [Any hard dates or ordering constraints on what must ship before what.]
- **Definition of Done (every feature):** [spec satisfied; tasks complete; tests green; docs/traceability updated; reviewed; demoed — tailor to the project.]
- **Staging mirrors production.** [Where and how changes are validated before release.]
- **Change control.** [How scope changes are proposed, estimated, and approved.]

## Governance

- **Authority.** This constitution supersedes all other project practices. In a conflict between this
  document and a spec, plan, task, or code comment, this document governs.
- **Amendments.** Amendments require: (1) a written rationale, (2) an updated version per the policy
  below, (3) propagation to dependent templates and docs, and (4) documented approval by
  [APPROVING_ROLES — e.g. the technical lead and product owner], recorded in the **Ratification
  Record** at the foot of this file. A Sync Impact Report is prepended to this file on every change.
  An amendment whose Ratification Record row is incomplete is **in force but unratified**: it governs
  day-to-day work, and it remains reversible without a further amendment until every required approval
  is recorded.
- **Versioning policy (semantic):**
  - **MAJOR**: remove or redefine a principle, or make a change that invalidates existing specs/plans.
  - **MINOR**: add a principle or section, or materially expand guidance.
  - **PATCH**: clarify wording, fix typos, or make non-semantic refinements.
- **Compliance review.** Every `plan.md` MUST include a Constitution Check that passes before Phase 0
  research and again before implementation. Every pull request is reviewed for compliance; violations
  block merge. Complexity that appears to violate a principle MUST be justified in the plan's
  Complexity Tracking section, or the design MUST be simplified.

## Ratification Record

The Governance section requires documented approval from [APPROVING_ROLES] for every amendment. This
table is where that approval is recorded. An amendment is **ratified** only when every required
approval column carries a name and a date; otherwise it is **in force but unratified**. State any
caveat (a self-approval, or a ratification conditional on an external decision) in a note beneath the
table rather than hiding it.

| Version | Type / date / summary | Author | [APPROVER_ROLE_1] | [APPROVER_ROLE_2] | Status |
|---|---|---|---|---|---|
| [VERSION] | [MAJOR\|MINOR\|PATCH], [YYYY-MM-DD]. [one-line summary] | [name] | [name + date, or *Pending*] | [name + date, or *Pending*] | [**Ratified** / **In force, unratified**] |

---

**Version:** [CONSTITUTION_VERSION] | **Ratified:** [RATIFICATION_DATE] | **Last Amended:** [LAST_AMENDED_DATE]
<!-- Example: Version: 2.1.1 | Ratified: 2025-06-13 | Last Amended: 2025-07-16 -->

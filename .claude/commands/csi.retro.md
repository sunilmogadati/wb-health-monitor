---
description: Run a session retrospective to capture lessons learned, update docs, and improve processes
---

## Session Retrospective

Conduct a structured retrospective on the current work session. Analyze what happened, identify
improvements, and persist the valuable parts in the right file.

### Step 1: Gather context

Review the session for: bugs hit, workarounds applied, time sinks, surprises, and patterns that
worked well.

### Step 2: Categorize

**Technical issues** — bugs, misconfigurations, runtime failures. Note the root cause and whether a
fix landed or is still open.

**Process gaps** — where the workflow broke down: missing validation, incomplete docs, manual steps
that should be automated.

**What worked well** — patterns, tools, or approaches worth reinforcing.

**Documentation gaps** — information that was missing or hard to find.

**Doc contradictions** — places where two committed documents disagree. These are high-value retro
output, because the constitution makes docs authoritative; a contradiction between two authoritative
docs is a latent defect.

### Step 3: Propose actions

Route each finding to the correct home. Prefer updating an existing doc over creating a new one.

| Finding type | Goes to |
|---|---|
| Architecture, data, security, deployment | the relevant architecture doc / ADR |
| API or frontend design | the relevant design doc |
| Product requirement or persona | the relevant product doc |
| Project-wide agent guidance | `CLAUDE.md` |
| Process or principle change | `.specify/memory/constitution.md` **with a version bump and Sync Impact Report** |
| Requirement traceability | the traceability map |
| Obligation pushed to a later spec | the deferred-dependencies register |
| Harness or command improvement | `.claude/commands/` or `.specify/` |

**Constitution changes are not casual.** Per its Governance section, an amendment needs the versioning
rules applied (MAJOR/MINOR/PATCH) and dependent templates re-checked. Propose, do not apply
unilaterally.

### Before appending to any doc, check for an existing home

This is a hard step, not a nicety. **Grep the target file's `##` headings for the topic first.** If a
section already covers it, extend that section. Only add a new heading when nothing covers the topic.

Why this is enforced: instruction files rot by accretion. It is common for a `CLAUDE.md` to grow past
500 lines and dozens of headings, some of them exact duplicates, precisely because additions were
appended without anyone checking for an existing home. Preventing that is cheap while the file is
small and expensive once it is large.

Also check size. Guidance is to keep an agent instruction file concise, because every line is re-read
on every turn. If `CLAUDE.md` approaches ~200 lines, the retro's job is to propose *moving* detail
into an appropriate doc and leaving a pointer, not to keep growing it.

### Step 4: Present and confirm

Present a table: Finding · Category · Proposed action · Target file. Ask for confirmation before
changing anything.

### Step 5: Apply

After approval, make the changes and commit per the project's git conventions:

```
docs: session retro - <brief summary>
```

### Guidelines

- Be specific about root causes, not symptoms
- Capture only what will be useful in a future session
- Do not record what is already documented or obvious from the code
- Keep it concise and actionable

---
description: Show project status: branch, changes, spec progress, harness health, and dev-loop services
---

## Project Status

Quick overview of the current project state. Useful at the start of a session or when
context-switching.

> **Note.** Sections that exercise application code or infrastructure report "not yet scaffolded"
> (rather than failing) until the code or config they target exists. That is the expected state for
> an early, docs-stage repo, not an error.

### User Input

```text
$ARGUMENTS
```

If the user provides "verbose" or "full", also run the test and typecheck sections.

### Gather and Report

**1. Git**
- Current branch and tracking info; ahead/behind remote
- Uncommitted changes (staged and unstaged)
- Last 5 commits on the current branch

**2. Spec progress** (the primary signal for a docs-stage repo)
- List `specs/*/` directories with each spec's `**Status:**` line from its `spec.md`
- For each spec with a `tasks.md`, count `- [x]` / `- [~]` / `- [ ]` to show completion
- Note any spec missing its issue-tracker mapping (only relevant if a tracker extension is installed)

**3. Harness health**
- `.claude/commands/` count, `.specify/templates/` count, `.specify/scripts/` count
- Whether the governing docs exist: `.specify/memory/constitution.md`, and (if this project mirrors
  to an issue tracker) whatever credentials file that integration requires

**4. Dev-loop services** (skip with a note if the project has no service/compose config yet)
- Bring up or query the project's declared services (compose, process manager, or equivalent)
- Flag anything not running or unhealthy
- If nothing is running, say how to start it (the project's documented "up" command)

**5. Ports / endpoints** (per the project's quickstart, if one exists)
- Check the ports the quickstart publishes; if a port is in use, identify the holding process

### Output Format

```
Branch:      <branch> (<ahead/behind>)
Changes:     <N modified, N untracked> or "clean"
Last commit: <hash> <message> (<time ago>)

Specs:       001 <status> (N/M tasks) · 002 <status> (N/M tasks)
Harness:     commands <N>, templates <N>, scripts <N>, constitution <present/missing>

Services:    <all healthy / N of M running / down / not scaffolded>
Ports:       <port> <state>, <port> <state>
```

List recommended actions at the end for anything broken (missing governing doc, services down, stale
ports, spec missing its tracker mapping).

---
description: Pre-PR gate verifying lint, typecheck, the full test suite, and no secrets before opening a PR
---

## Pre-flight Check

Run the full quality gate before opening a pull request, so CI does not discover what you could have
caught locally. Mirrors the Definition of Done in `.specify/memory/constitution.md`.

> **Note.** Sections whose target directory does not exist yet report "not yet scaffolded" and are
> excluded from the verdict rather than counted as failures.

### User Input

```text
$ARGUMENTS
```

If the user names a target branch, diff against it. Otherwise default to `main`.

### Checks

Run all of them and collect results before presenting a summary. Do not stop at the first failure.

**1. Working tree**
- `git status`: warn if dirty
- `git diff --stat <target>...HEAD`: what the PR will include
- **Secret scan (blocking).** Look for env files, `*.pem`, `*.key`, and credential files in the diff.
  Per the Constitution's "secrets never in source" constraint, any hit is an immediate fail. Also grep
  the diff for common credential tokens (`API_TOKEN`, `SECRET`, `PASSWORD=`, private-key headers).

**2. Lint and types**
- Run the project's configured linter over changed source (e.g. `ruff`, `eslint`, `golangci-lint`)
- Run the project's type checker if one is configured (e.g. `mypy`, `tsc --noEmit`)

**3. Tests**
- Run the project's test suites — at minimum contract/unit and integration
- **Any suite the constitution marks as blocking (e.g. a dedicated privacy, security, or invariant
  suite) is blocking here too, never advisory.** Run it explicitly and call it out separately.

**4. Data / transform layer** (if the project has one)
- Run whatever validates transforms and their data tests (e.g. `dbt build`, migration checks)

**5. Frontend** (if a frontend exists)
- Lint, typecheck, test, and a production `build` (the build catches missing imports and template
  errors a unit run does not)

**6. Accessibility** (if the change is user-facing and the constitution requires it)
- Run the a11y check; zero critical or serious violations is blocking for user-facing work

**7. Migrations**
- If schema migrations changed, confirm they are reversible. Flag any irreversible or destructive
  migration per the constitution's "no destructive ad-hoc DDL" constraint.

**8. Commit hygiene**
- `git log --oneline <target>...HEAD`
- Flag WIP/fixup/squash commits
- Flag any commit-message convention the project forbids (e.g. `Co-Authored-By` lines or agent
  session URLs, if the project's git conventions exclude them)

### Results Summary

```
Pre-flight Results
==================
[ ] Working tree clean
[ ] No secrets staged
[ ] Lint + typecheck
[ ] Unit/contract tests (N/N)
[ ] Integration tests (N/N)
[ ] Blocking invariant suite (privacy/security/etc.) (N/N)
[ ] Data/transform build + tests
[ ] Frontend lint/typecheck/test/build
[ ] Accessibility: 0 critical/serious
[ ] Migrations reversible
[ ] Commit messages clean
```

`[x]` pass · `[ ]` fail · `[~]` warning · `[-]` not yet scaffolded

### Verdict

- **All pass**: "Ready to push."
- **Any failure**: list exactly what must be fixed. Any suite the constitution marks blocking
  (privacy, security, accessibility, secrets) is never a "warning" — it is a constitutional violation
  and blocks the PR.
- **Warnings only**: "Not blocking. Review before pushing."

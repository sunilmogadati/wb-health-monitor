---
description: Smoke test the full stack from scratch to verify the dev loop works end to end
---

## Smoke Test

Bring the stack up from nothing and verify each layer, following the project's local-dev quickstart.
Use this after a dependency bump, an infra change, or when onboarding a machine.

> **Use the project's documented "up" and "down" commands (make targets, compose invocations, or a
> task runner) rather than bare tool calls.** They supply the config file and env that a bare command
> omits, and they publish the host ports the quickstart documents. A bare invocation often finds no
> config, or falls back to default ports instead of the published ones.

### User Input

```text
$ARGUMENTS
```

`clean` tears down volumes/state first for a true from-scratch run. Default is a non-destructive up.

### Steps

Run in order. Stop at the first failure and report it with the failing command's output.

**1. Prerequisites**
- The language runtimes and tooling the quickstart names, at the versions it names
- Warn if versions differ from quickstart

**2. Bring up infrastructure**
- Run the project's "up" command (build + wait for healthy)
- List services, then verify each answers on its **published** port (data store, object store, cache,
  orchestrator, or whatever this project declares)

**3. Database / persistence**
- Run migrations
- Confirm the expected schemas / namespaces exist
- **Confirm any database-enforced access control the constitution requires is actually enabled.** If
  the constitution makes the database the final arbiter of access, a missing control fails the smoke
  test regardless of anything else.

**4. Data / warehouse layer** (if present)
- Seed, then build transforms
- Report model counts and any failing data test

**5. API** (if present)
- API answers on its published port; the docs/OpenAPI endpoint renders
- An unauthenticated request to a protected route is **denied** (deny-by-default). A 200 there is a
  critical finding.

**6. Frontend** (if present)
- Web answers on its published port
- Run the real-browser check if the project has one. A headless/jsdom unit suite renders a broken page
  happily, so a green unit run is not evidence the page is not blank.
- An unauthenticated deep link redirects to login rather than rendering data

**7. Gateway / edge** (if present)
- The gateway routes to both API and web

**8. Invariant spot-check (blocking, if the constitution defines one)**
- Exercise the single most important constitutional invariant end to end against real running code
  (e.g. small-cell suppression on a published aggregate, tenant isolation, an authorization boundary).
  This must hold in the data/service layer, not merely in the UI.

### Output

```
Smoke Test Results
==================
[ ] Prerequisites
[ ] Services healthy
[ ] Migrations applied
[ ] DB-enforced access control enabled
[ ] Data/transform build + tests
[ ] API up, protected route denies anonymous
[ ] Frontend up, renders in a real browser
[ ] Frontend guards unauthenticated deep links
[ ] Gateway routes
[ ] Core invariant verified end to end
```

End with either "Stack is healthy" or the first failing step, its command, and its output.

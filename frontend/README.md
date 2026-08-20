# Analytics Dashboard (spec 006)

A Next.js (App Router) + Tailwind CSS dashboard for the value-for-money benchmark, indicator
trends, and country comparisons. Reads **only** the spec-005 analytics API — never the database
directly (Principle III).

## Run it

```bash
npm install
npm run dev       # http://localhost:3000
```

By default it points at `http://localhost:8000/api/v1` (the backend's default local port). To
point at a different API base, copy `.env.example` to `.env.local` and set `NEXT_PUBLIC_API_BASE`.

**Spec 005 (the read API) may not be merged yet.** Until it is, the dashboard will show a
"Can't reach the analytics API" banner instead of data — that's the expected, tested
API-unreachable state (see `spec.md` Edge Cases), not a bug.

## Test / lint / build

```bash
npm test     # vitest — component tests against mocked API responses
npm run lint
npm run build
```

## Layout

- `src/lib/api.ts` — the one typed client for all four spec-005 endpoints (FR-007); the endpoint
  contract lives here and nowhere else.
- `src/components/` — `BenchmarkChart`, `TrendChart`, `CompareChart` (Recharts), each pure and
  tested with mocked data.
- `src/app/page.tsx` — fetches from the API client and wires the three components together, with
  loading/error states per section.

# Feature Specification: WDI Ingestion to the Raw Object Store

**Feature Branch**: `001-wdi-ingestion`

**Created**: 2026-08-17

**Status**: Accepted (2026-08-19)

**Clarifications (2026-08-19)**: FR-008 economy scope = **Sub-Saharan Africa (SSF)** for the initial
build (configurable); FR-009 year range = **2015–2022** (configurable); FR-010 cadence = **on-demand**
(`make ingest`), scheduling is a stretch.

**Input**: The first pipeline slice — pull World Bank World Development Indicators (WDI) via `wbgapi`
and land them, unchanged, in the `raw` object-storage zone, with every run recorded. This is the
"bronze" layer that every later stage (staging → warehouse → published → model) reads from.

> **Constitution alignment:** Principle I (public data only, no keys), Principle III (zone
> discipline — data lands in `raw`, nothing user-facing reads it), Principle II (tests before code).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest the core indicators (Priority: P1)

An operator runs a single command to pull the configured WDI indicators for a chosen set of
economies and years. The exact data the World Bank API returns is written, unchanged, into the
`raw` object-storage bucket, and the run is recorded.

**Why this priority**: Nothing downstream can exist without raw data landed reliably. This slice
alone delivers value: a trustworthy, replayable copy of the source data.

**Independent Test**: Run the ingest against the live public WB API (or a recorded fixture) and
confirm one immutable object per indicator appears in `raw` and a `pull_log` row is written.

**Acceptance Scenarios**:

1. **Given** the four core indicators, a set of economies, and a year range, **When** ingest runs,
   **Then** the `raw` bucket contains one immutable NDJSON object per indicator and a `pull_log` row
   records the run (status `succeeded`, counts, object keys, timestamps).
2. **Given** a successful ingest, **When** an operator inspects the object, **Then** its contents are
   the exact API response (no cleaning, no reshaping), one record per line.

### User Story 2 - Safe to re-run (idempotent & immutable) (Priority: P2)

Re-running ingestion never corrupts or overwrites earlier data; a repeat produces a new immutable
pull, never an in-place edit.

**Why this priority**: Operators must be able to re-run without fear (after a failure, or to refresh).
Immutability is what makes the raw zone a trustworthy record.

**Independent Test**: Run ingest twice; verify all prior objects are byte-identical and a second
`pull_log` row exists.

**Acceptance Scenarios**:

1. **Given** a prior successful pull, **When** ingest runs again, **Then** the earlier objects are
   unchanged and a new pull (new timestamped key + new `pull_log` row) is created.
2. **Given** an ingest that fails partway, **When** it is re-run, **Then** no partial or half-written
   object is left usable; the failed run is recorded as `failed`.

### User Story 3 - See what was ingested (lineage) (Priority: P3)

An operator can review every ingest run — what was pulled, when, how much, and whether it succeeded.

**Why this priority**: Trust and debugging. The `pull_log` is the lineage anchor for everything
downstream.

**Acceptance Scenarios**:

1. **Given** several ingest runs, **When** the operator queries `pull_log`, **Then** each run shows
   its indicators, economies, year range, row count, object keys, status, and start/finish times.

### Edge Cases

- An indicator returns **no data** for the requested scope → recorded (not a crash), status reflects it.
- The **WB API is slow or times out** → the run fails cleanly and is logged as `failed`; no partial object is left usable.
- **Object storage is unavailable** → the run fails before writing `pull_log` as `succeeded`.
- An **unknown/invalid indicator code** is configured → the run fails with a clear message; valid indicators in the same run are not silently dropped.
- **Empty scope** (no economies or no years) → rejected with a clear error, no run recorded as succeeded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST fetch the configured WDI indicators for the configured economies and year range from the World Bank data API via `wbgapi`.
- **FR-002**: System MUST write each pull to the `raw` object-storage bucket as an **immutable** newline-delimited JSON object, keyed by pull timestamp and indicator; existing objects MUST NOT be modified or overwritten.
- **FR-003**: System MUST record every ingest run in a `pull_log` table with: indicators, economies, year range, rows fetched, object keys, status, `started_at`, `finished_at`.
- **FR-004**: Ingestion MUST be re-runnable with no partial state: a failed or repeated run never leaves a half-written object usable, and a repeat creates a new immutable pull rather than editing an existing one.
- **FR-005**: System MUST be runnable as a single command (e.g. `make ingest`) and configurable (which indicators, economies, years) **without code changes**.
- **FR-006**: System MUST validate a pull before marking it `succeeded`: the result is non-empty and has the expected shape (economy, indicator, year, value). A failed validation marks the run `failed` and does not mark the data usable.
- **FR-007**: System MUST require **no credentials** for the World Bank source (public data), and MUST write World Bank data to **no store other than** the `raw` bucket and `pull_log` (zone discipline).
- **FR-008**: The default economy scope is **Sub-Saharan Africa (SSF)** for the initial build, configurable to any WB region or all countries. *(Clarified.)*
- **FR-009**: The default year range is **2015–2022**, configurable. *(Clarified.)*
- **FR-010**: Ingest cadence is **on-demand** (`make ingest`); scheduling is a stretch. *(Clarified.)*
- **FR-011**: Ingestion MUST be driven by a **source registry** (`ingestion.data_sources`): each run resolves a **registered, active** source, and every `pull_log` row references it (`source_id`) — so ingestion is config-driven and every run traces to its source (provenance). Adding a public source is a registry row, not a code change (realizes FR-005). The registry holds **no credentials** (FR-007); auth-bearing sources are out of scope (public data only, Principle I).

### Key Entities *(include if feature involves data)*

- **Raw pull object** — an immutable NDJSON file in the `raw` bucket; one per (run, indicator); holds the exact API response. Suggested key: `wdi/<pull-timestamp>/<indicator-code>.ndjson`.
- **pull_log** — one row per ingest run: `pull_id`, `indicators[]`, `economies[]`, `year_from`, `year_to`, `rows_fetched`, `object_keys[]`, `status` (`running`|`succeeded`|`failed`), `started_at`, `finished_at`. The sync-log / lineage anchor for the whole pipeline.
- **Ingest configuration** — the set of indicator codes (the four core), the economy scope, and the year range; supplied as config, not hard-coded.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After an ingest, the `raw` bucket contains exactly one object per configured indicator, and each object's line count equals the number of rows the API returned for that indicator.
- **SC-002**: Every ingest run appears in `pull_log` with an accurate status and counts; no run is silently lost.
- **SC-003**: Running ingest twice yields two `pull_log` rows and leaves all previously written objects byte-identical (immutability verified).
- **SC-004**: A missing/empty indicator result is recorded (status reflects it) rather than crashing the run or affecting the other indicators in the same run.
- **SC-005**: No World Bank data is written anywhere except the `raw` bucket and `pull_log`.

## Assumptions

- The stamped stack is available: object storage (MinIO, S3-compatible) and Postgres. The `raw`
  bucket exists or is created by the ingest on first use.
- `wbgapi` is the WDI client; the source is public (no keys, no scraping).
- Scope is country/WB-region level only (no sub-national data).
- Staging, warehouse, published, and modelling are **out of scope** for this feature — they are
  separate specs that read from what this one lands.

# Tasks: WDI Ingestion (spec 001)

**Status**: Built · **Plan**: `plan.md` · *(All complete — documents the delivered work.)*

## Phase 1 — Lineage substrate
- [x] **T001** Migration `0001`: `ingestion.pull_log` (sync-log / lineage anchor). (FR-003)
- [x] **T002** Migration `0002`: `ingestion.data_sources` registry + seed `world_bank_wdi`; link `pull_log.source_id`. (FR-011)

## Phase 2 — Pull (host)
- [x] **T003** `pull_wdi.py`: `wbgapi` fetches the configured indicators/economies/years → tidy long CSV. (FR-001)

## Phase 3 — Land + load (container)
- [x] **T004** `load_wdi.py`: resolve the registered active source; fail if unregistered. (FR-011)
- [x] **T005** Upload the raw pull to MinIO `raw` (immutable); record the object key in `pull_log`. (FR-002)
- [x] **T006** Load the rows into `staging.wdi_observation`; write the `pull_log` run (status/counts/timestamps). (FR-003/FR-006)

## Phase 4 — DX + gate
- [x] **T007** `make ingest` runs the whole thing (host pull + container load), config-driven. (FR-005)
- [x] **T008** No credentials required; WB data written only to `raw` + `pull_log` (zone discipline). (FR-007)
- [x] **T009** Migration round-trip reversible; a pull is verified before `succeeded`. (SC-002/SC-003)

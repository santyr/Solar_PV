# Energy Data Platform Implementation Plan

**Goal:** Deliver the Stage 2 OpenHAB/PostgreSQL analytics platform as an
additive, test-backed, reversible system, then hand stable contracts to Stages
3–5.

**Architecture:** A Python CLI in `analytics/` reads existing OpenHAB per-Item
tables dynamically, writes only compact products in versioned
`energy_analytics`, and emits reproducible reports/exports. Raw telemetry and
physical-control contracts remain unchanged.

**Stack:** Python 3.12, standard library, psycopg2, PostgreSQL 16, pytest.
Configuration uses JSON so runtime has no new parser dependency.

## Task 1: Freeze the live source and backup inventory

**Files:**

- Create: `docs/audit/stage2-live-data-inventory.md`
- Create: `analytics/config/metric-sources.json`
- Create: `analytics/config/system-epochs.json`

1. Document the database layout, source coverage, protocol provenance,
   stale thresholds, dormant exclusions, missing Philips links, and backup
   gap from live read-only evidence.
2. Seed only verified current sources and explicit epochs.
3. Validate JSON and local Markdown links.
4. Commit the inventory and configuration.

## Task 2: Build pure time-series primitives with TDD

**Files:**

- Create: `analytics/pyproject.toml`
- Create: `analytics/src/earthship_energy/__init__.py`
- Create: `analytics/src/earthship_energy/series.py`
- Create: `analytics/tests/test_series.py`

1. Write failing tests for unit conversion, DST-aware day bounds, bounded-gap
   trapezoidal integration, threshold exposure, and coverage.
2. Run the focused tests and confirm failure.
3. Implement the smallest pure functions that pass.
4. Run focused and full unit tests; commit.

## Task 3: Add source resolution and read-only inventory with TDD

**Files:**

- Create: `analytics/src/earthship_energy/config.py`
- Create: `analytics/src/earthship_energy/db.py`
- Create: `analytics/src/earthship_energy/inventory.py`
- Create: `analytics/src/earthship_energy/cli.py`
- Create: `analytics/tests/test_config.py`
- Create: `analytics/tests/test_inventory.py`

1. Test strict JSON validation, Item-name resolution, zero-padded table
   derivation, ambiguity/missing failures, and secret-safe structured output.
2. Implement `energy-data inventory` and `energy-data validate-sources`.
3. Validate against the live database read-only; commit.

## Task 4: Create versioned schema migrations with TDD

**Files:**

- Create: `analytics/sql/migrations/0001_energy_analytics.sql`
- Create: `analytics/src/earthship_energy/migrations.py`
- Create: `analytics/tests/test_migrations.py`

1. Test ordered discovery, checksums, dry-run, transactional apply, repeat-run
   idempotence, and checksum drift refusal.
2. Implement the isolated schema/tables from the design.
3. Apply only to an isolated test database and exercise rollback; commit.

## Task 5: Implement daily aggregates with TDD

**Files:**

- Create: `analytics/src/earthship_energy/aggregation.py`
- Create: `analytics/tests/test_aggregation.py`

1. Write fixture tests for SOC, sunrise/sunset, DoD, no-full streaks,
   charge/discharge throughput, EFC, PV/load/weather metrics, gaps, and DST.
2. Add the live DC sign-calibration check; fail closed while unknown.
3. Implement idempotent date/range aggregation and structured summaries.
4. Compare a bounded historical day with independent SQL; commit.

## Task 6: Add forecasts, events, and LYNK import with TDD

**Files:**

- Create: `analytics/src/earthship_energy/forecasts.py`
- Create: `analytics/src/earthship_energy/events.py`
- Create: `analytics/src/earthship_energy/imports.py`
- Create: `analytics/tests/test_forecasts.py`
- Create: `analytics/tests/test_events.py`
- Create: `analytics/tests/test_imports.py`

1. Test `issued_at`/`valid_for` semantics and prevention of future leakage.
2. Test snow/inferred-event confidence and operator-confirmation provenance.
3. Test duplicate byte-identical LYNK imports and conflicting batch refusal.
4. Implement and commit.

## Task 7: Add reports, exports, and scenario replay with TDD

**Files:**

- Create: `analytics/src/earthship_energy/reports.py`
- Create: `analytics/src/earthship_energy/export.py`
- Create: `analytics/src/earthship_energy/simulation.py`
- Create: `analytics/tests/test_reports.py`
- Create: `analytics/tests/test_export.py`
- Create: `analytics/tests/test_simulation.py`

1. Test reproducible monthly/winter/lifecycle report bodies.
2. Test 5/15-minute portable feature schema and forecast provenance.
3. Test capacity/PV/load/efficiency scenarios at 100/90/80/70/60% capacity.
4. Implement and commit.

## Task 8: Document and verify production deployment

**Files:**

- Update: `docs/architecture/energy-data-architecture.md`
- Update: `docs/architecture/codex-energy-management.md`
- Update: `docs/operations/energy-analysis-runbook.md`
- Update: `docs/operations/recovery-and-backup.md`
- Create: `docs/audit/stage2-production-validation.md`

1. Locate storage that can safely hold a compressed 15 GB database backup and
   an isolated restore; do not consume the remaining root-disk margin.
2. Create and verify the backup, restore it in isolation, and document hashes,
   sizes, row/schema checks, location, retention, and recovery command without
   secrets.
3. Apply migrations, backfill a bounded range, verify independent queries,
   then backfill the current Discover epoch.
4. Validate stale behavior, source plausibility, OpenHAB health, feeder
   regression, and raw-table immutability.
5. Commit validation evidence.

## Task 9: Hand stable contracts to Stage 3

Do not expose analytics to the UI until Task 8 passes. Stage 3 will create
stable OpenHAB derived Items/API contracts and will also link/persist the
Philips illuminance and occupancy channels for future shade inference. That
work remains observational and requires no shade actuator.

## Verification commands

```bash
cd analytics
python3 -m pytest -q
python3 -m earthship_energy.cli validate-config
python3 -m earthship_energy.cli validate-sources --read-only
python3 -m earthship_energy.cli migrate --dry-run
python3 -m earthship_energy.cli aggregate --date YYYY-MM-DD --dry-run
python3 -m earthship_energy.cli report winter --format json
```

Before every completion claim, also run repository link checks,
`git diff --check`, production readback where applicable, and the Stage 2
acceptance subset from the handoff package.

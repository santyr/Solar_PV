# Energy Data Architecture

```text
Discover BMS / Schneider
          |
          v
       OpenHAB --------> earthship-ui
          |
          v
      PostgreSQL
          |
          v
        Codex ---------> reports / engineering decisions
          |
          v
        Hexmem
```

## Ownership

- Hardware owns electrical limits and protection.
- OpenHAB owns live integration, normalized Items, and bounded automation.
- PostgreSQL owns raw quantitative history and future derived analytics.
- Solar_PV owns definitions, provenance, runbooks, and system epochs.
- Codex reads APIs, database, CLI, source, and Hexmem for analysis.
- Hexmem stores durable conclusions, never raw telemetry or authority.
- earthship-ui consumes stable OpenHAB contracts; it has no database or Hexmem
  credentials.

## Provenance rules

Every derived metric must identify source Item(s), unit, sign convention,
timezone, aggregation window, missing-data policy, and system epoch. Raw
history is retained. Forecast snapshots must preserve issue and valid times to
avoid future-data leakage.

The live OpenHAB database uses UTC while the house operates in
America/Denver. Daily aggregates require explicit local-day and DST tests.

## Current versus planned

OpenHAB JDBC history, the focused `thermal_intel` schema, and version 1 of the
`energy_analytics` schema are deployed. The analytics CLI resolves current Item
tables dynamically, materializes compact daily battery/PV/load/weather rows,
and produces monthly, lifecycle, and winter-scenario JSON or Markdown reports.
The first current-epoch backfill covers 2026-07-19 through 2026-08-19.

Forecast capture and scenario math are deployed. LYNK file ingestion now has
an idempotent dry-run/apply CLI and a provenance-preserving module-health
report; it does not touch the closed-loop battery network. Snow events have an
idempotent operator dry-run/apply CLI, and inferred events have a transactional
observational persistence API. Portable feature exports have a bounded,
read-only CLI and version-2 CSV contract with lagged state, daylight,
instrumented load state, system epochs, and as-of forecast provenance.
Stage 3 owns the stable UI-facing
OpenHAB analytics contract; its Philips observation Items are linked and
persisted. Stage 5 owns scheduling and separately mounted/off-host backups.

Dormant miner data and AGM-derived SOC calculations are excluded from the
active model. Historical rows may be retained with provenance and a historical
system epoch.

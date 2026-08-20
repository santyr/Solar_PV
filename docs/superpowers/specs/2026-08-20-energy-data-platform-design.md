# Energy Data Platform Design

**Status:** Approved by the Earthship Energy AI handoff and the operator's
2026-08-20 instruction to execute the full program. Production deployment is
still gated by backup and live validation.

## Objective

Build a reproducible quantitative layer over the existing OpenHAB PostgreSQL
history without creating another telemetry database, weakening electrical
safety, or changing existing OpenHAB contracts.

The platform must support daily energy accounting, winter sufficiency,
lifecycle analysis, forecast snapshots, portable future-model exports, and
operator reports. It is observational and advisory. Discover, LYNK II,
Schneider equipment, and physical protection remain authoritative.

## Evidence and constraints

Live inspection on 2026-08-20 established:

- OpenHAB persists into PostgreSQL database `openhab` in UTC.
- Raw history lives in `public.itemNNNN` tables resolved through
  `public.items(itemid, itemname)`.
- The database is about 15 GB and contains high-rate tables with millions of
  rows. Raw telemetry must not be copied into another high-resolution table.
- No active PostgreSQL/OpenHAB backup timer was found. Only about 29 GB was
  free on the database filesystem, so a compressed backup plus restore check
  is required before the first production migration.
- Current Discover BMS, Schneider, MPPT, weather, forecast, and selected load
  Items exist. Retired AGM and dormant mining Items also exist and must be
  excluded from current aggregates.
- The Philips `Motion Light Sensor` Zigbee Thing is online and exposes
  illuminance and occupancy, but those channels have no linked or persisted
  Items yet.
- The North Wall WH31E temperature sensor is live near the kiva. Its winter
  response is a candidate input for inferred kiva-use events, not proof of an
  event by itself.

## Chosen architecture

Use the existing `openhab` database with a separate, versioned
`energy_analytics` schema and a small Python command-line package in this
repository.

The alternatives were:

1. Views only over raw Item tables. This minimizes storage but cannot provide
   stable dynamic source resolution, import idempotency, forecast snapshots,
   event annotations, or efficient reproducible reports.
2. A versioned analytics schema with metadata, compact aggregates, events,
   and idempotent materialization. This is selected.
3. A separate service and database. This duplicates operational ownership and
   violates the instruction not to create another telemetry database.

Raw `public` tables remain untouched. Analytics migrations create and alter
only `energy_analytics`. Rollback is a migration or, before first release, a
drop of that isolated schema.

## Repository layout

```text
analytics/
  pyproject.toml
  src/earthship_energy/
    cli.py
    config.py
    db.py
    inventory.py
    aggregation.py
    forecasts.py
    imports.py
    reports.py
    simulation.py
    export.py
    quality.py
  sql/migrations/
  tests/
  config/metric-sources.yaml
  config/system-epochs.yaml
docs/audit/stage2-live-data-inventory.md
docs/architecture/energy-data-architecture.md
docs/architecture/codex-energy-management.md
docs/operations/energy-analysis-runbook.md
```

Credentials are never committed or printed. Runtime connection settings are
read from an explicitly supplied DSN or the protected OpenHAB JDBC service
configuration. Tests use an isolated database/schema or pure fixtures.

## Source contract and provenance

`metric_sources` is the stable registry. Each row records:

- canonical metric name and role;
- OpenHAB Item name;
- source device and protocol;
- canonical unit and raw scaling;
- sign convention;
- expected update interval and stale threshold;
- measured, device-reported, derived, imported, or inferred status;
- confidence and current-system epoch applicability.

Item table names are resolved at runtime from `public.items`; they are never
assumed from a hard-coded numeric ID. Resolution fails closed for a missing,
ambiguous, stale, or type-incompatible source.

Current aggregates use the Discover and current Schneider paths. Historical
AGM Items and all mining Items are denied by explicit source/epoch policy.

## Schema

The first schema version contains:

- `schema_migrations`
- `metric_sources`
- `system_epochs`
- `snow_events`
- `forecast_snapshots`
- `lynk_import_batches`
- `battery_module_samples`
- `daily_battery`
- `daily_pv`
- `daily_load`
- `daily_weather`
- `daily_source_quality`
- `analysis_runs`

Daily tables are compact derived products with a local calendar date and
source coverage metadata. Their natural key includes date and system epoch.
Upserts replace only the requested aggregate day and make reruns idempotent.
Raw history is never updated or deleted.

Forecast snapshots preserve both `issued_at` and `valid_for`. Evaluation must
select the newest forecast issued no later than the evaluation origin; it must
never use realized future weather as a historical input.

Snow and inferred household events keep method, confidence, evidence window,
and optional operator confirmation. Inferences never masquerade as measured
states.

## Time, units, and integration

- Raw timestamps remain UTC.
- Calendar reporting uses `America/Denver` with explicit DST-aware day bounds.
- Canonical power is W, energy is kWh, voltage is V, current is A,
  temperature is degrees C internally, SOC is percent, and irradiance is
  W/m2.
- Integration uses the trapezoidal rule only across intervals within the
  configured gap limit. Missing intervals remain missing and reduce coverage;
  they are not silently interpolated.
- Battery charge and discharge throughput are stored separately as positive
  quantities. The live DC sign convention must pass a correlation-based
  calibration gate before production EFC or energy values are published.
- EFC is `(charge_kWh + discharge_kWh) / (2 * nominal_usable_kWh)`, with raw
  throughput and the capacity assumption retained beside the result.

## Aggregation and quality behavior

The CLI resolves sources, reads only the required time range, normalizes
values, computes coverage, and writes one transaction per date. Every command
supports a dry-run where writes are possible and emits a structured summary
with dates, row counts, missing sources, coverage, and exit status.

Stale or insufficient data produces explicit quality states. It does not
produce a plausible-looking zero. Report publication requires configured
coverage thresholds, known sign convention, and a current system epoch.

The first release computes:

- battery SOC extrema/mean, sunrise/sunset SOC, overnight drop, DoD,
  threshold exposure, charge/discharge throughput, EFC, temperature and BMS
  limit summaries, full-charge milestones, and no-full streaks;
- PV energy/peak/productive window, load energy, PV/load ratio, and balance;
- observed weather and forecast snapshots;
- selected active-load duration/timing only where instrumentation is real;
- winter sufficiency, lifecycle, and monthly reports;
- 5- or 15-minute portable CSV/Parquet features and scenario replay.

Curtailment/lost-harvest estimates remain unavailable until a validated method
distinguishes full-battery curtailment, MPPT limitation, clouds, snow, and
telemetry loss.

## Observational event inference

Two event families are planned as separately validated, confidence-bearing
features:

- **Indoor shades:** after stable Philips Items exist, use illuminance change
  relative to outdoor irradiance, solar geometry, time of day, cloud changes,
  room temperature, and occupancy. Motion may help distinguish human activity
  but cannot alone label shade state.
- **Kiva use:** during winter, evaluate North Wall temperature response against
  outdoor temperature, solar input, adjacent-zone temperatures, and the RC
  thermal residual. A temperature excursion is evidence, not a definitive
  kiva event.

Both begin in shadow evaluation against operator-confirmed events. They expose
state, confidence, method/version, and evidence timestamps. They cannot trigger
physical action or bypass the deterministic thermal model.

## Reports and future-model interface

Named CLI commands generate versioned JSON plus human-readable Markdown. Each
report contains its query window, schema/code version, system epoch, source
coverage, assumptions, and generation time. Re-running against unchanged data
must be content-reproducible apart from explicitly separated run metadata.

Portable features have a documented schema and include current/lagged state,
forecast issue time, daylight, active measured loads, inferred-event confidence,
and system epoch. No production model is trained in this stage.

## Scheduling boundary

Analytics commands contain no embedded scheduler. Stage 5 systemd services and
timers invoke clean, lock-safe CLI entry points. Codex investigates exceptions
and reports; it is not a telemetry polling loop. Routine output goes to
PostgreSQL and journald, not Hexmem.

## Deployment and rollback

Before the first database write:

1. create a compressed PostgreSQL backup on storage with sufficient space;
2. verify the archive manifest and restore it into an isolated test database;
3. capture schema and row-count baselines;
4. apply migrations in one transaction;
5. validate source resolution and a bounded historical date range;
6. compare aggregates with independent raw queries;
7. confirm existing OpenHAB and feeder behavior is unchanged.

Migrations are additive. No raw Item, Thing, rule, endpoint, or persistence
table is renamed or deleted. The analytics DB role receives only the minimum
read on raw history and write on `energy_analytics` when a separate role is
practical.

## Acceptance

Acceptance requires tests for units, sign calibration, trapezoidal integration,
EFC, DST, gaps/staleness, forecast issuance, duplicate imports, epochs,
reproducibility, and scenario math; a verified backup/restore; production
aggregate comparison; documented commands; and regression checks for current
OpenHAB automation and Lightning Goats consumers.

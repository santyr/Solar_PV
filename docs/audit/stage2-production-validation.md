# Stage 2 Production Validation — 2026-08-20

## Outcome

Stage 2 schema deployment and the current Discover-bank backfill passed. The
change is additive and observational: no `public` OpenHAB table, Item, Thing,
rule, feeder contract, or physical setpoint was changed.

## Backup and restore gate

- source database: PostgreSQL 16 `openhab`, approximately 15 GB;
- compressed custom archive: 2.0 GB;
- SHA-256: `3aaa0a7ed6c5a05bfbb1e0f29a56d9772e6a83630f2ff213a016dd939c70183c`;
- complete isolated restore: passed;
- catalog comparison: 418 `public` tables, 3 `thermal_intel` tables, and 416
  `public.items` rows on both source and restore;
- configured history comparison: 15/15 source tables passed 30 bounded
  history checks plus the catalog check;
- temporary restore database: verified absent after cleanup.

The archive is private and same-host. It is adequate for migration rollback,
not host-loss recovery.

## Migration and backfill

- migration `0001_energy_analytics`, checksum
  `b0931c39963b12c6dd4fa5014d58c1abd790794a64c4c150d7d094758d027dd5`;
- post-apply dry run: no pending migrations;
- reference rows: 21 metric sources and 3 system epochs;
- bounded canary: 2026-08-19 matched the independent MPPT daily counter to
  about 0.04 percent (7.388 versus 7.385 kWh);
- current epoch backfill: 32 dates, 2026-07-19 through 2026-08-19;
- aggregate rows: 32 each in daily battery, PV, load, and weather;
- source-quality rows after gap closure: 672 across all 21 sources and all 32
  dates; 416 companion-verified `ok`, 256 optional/uncompanionized
  `freshness_unverified`;
- aggregate quality after rebuild: battery, PV, load, and weather all `ok` on
  all 32 dates;
- PV: 225.911 kWh; load: 180.246 kWh;
- battery throughput: 97.958 kWh charge and 92.852 kWh discharge;
- equivalent full cycles: 4.6585 using 20.48 kWh nominal usable capacity;
- minimum observed daily SOC: 83 percent; all 32 days reached 99 percent.

The battery DC sign calibration used 108 informative hourly comparisons:
positive power aligned with rising SOC 32 times, negative power with falling
SOC 75 times, one comparison disagreed, and the power/SOC-delta correlation was
0.895. The configured sign is therefore `positive_charging`.

## Quality and regression checks

- unit and contract tests after final scenario-workflow closure: 116 passed;
- static Python check: clean;
- OpenHAB service: active throughout migration and backfill;
- REST Item inventory remained readable;
- feeder override remained `OFF` and the most recent manual request/result
  ledger entry remained `complete`;
- public schema table count remained 418; analytics writes are isolated to
  `energy_analytics`;
- retired AGM and dormant mining sources are absent from the active source
  registry.

OpenHAB's `everyChange` persistence deliberately produces long intervals for
unchanged values. Gap closure therefore does not infer health from raw sample
cadence. Each daily run writes all 21 `daily_source_quality` rows with raw
row-count/first/last evidence and coverage authorized by explicit persisted
companions. Required daily domains use BMS communications/device-present,
Schneider update clocks, and `WeatherData_HealthStatus`; their aggregate
quality is downgraded when companion coverage is insufficient. Optional
sources without a validated companion remain `freshness_unverified`.

## Remaining handoffs

Stage 3 may now expose stable read-only analytics contracts. Philips
illuminance, occupancy, and temperature are linked and persisted. Shade and
kiva inference remain confidence-bearing observations requiring
winter/operator validation. Recurring daily materialization, reports, and
backup verification are deployed. A real separately mounted or off-host
backup target still requires operator input.

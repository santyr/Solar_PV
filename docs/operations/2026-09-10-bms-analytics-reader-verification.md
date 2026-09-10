# Atomic BMS analytics reader verification

Status: implementation and read-only comparison complete on
`feat/bms-analytics-reader`; final independent review and production deployment
remain pending. This is not a deployment receipt.

## Implemented contract

The default `battery.soc_pct` source retains the `BMS_SOC` registry identity but
selects `BMS_SOC_Evidence_JSON` with policy `atomic_bms_evidence`. Daily and
feature readers use the JSON record's own SoC; they do not authorize a separate
numeric carry. Missing evidence and ambiguous ordering never fall back to that
numeric history.

Daily extrema, max-minus-min DoD, mean, threshold durations and solar-event
values use individual qualified intervals. Source quality scores the same
intervals and counts evidence-table observations. Empty coverage yields null
SoC statistics, zero observed threshold durations, and insufficient quality.
The 90/50 percent quality thresholds, power and temperature calculations, and
energy-throughput EFC formula remain unchanged.

The daily CLI supplies the selected physical bank epoch in dry-run and apply
modes. Feature export accepts `--epochs` and uses the configured epoch windows.
Its current SoC and one-hour lag are qualified independently at their actual
UTC instants. A lag in a different physical bank is qualified within that bank;
old-bank carry cannot authorize a new-bank point. Undated historical banks
cannot authorize atomic evidence. Observer stream changes never reset a bank
or any counter. Explicit legacy source configurations remain available for
reader rollback/comparison, not as an automatic fallback.

Feature SQL does not read the legacy numeric SoC table in atomic mode. Other
feature fields and CSV schema remain unchanged. Indexed interval lookup retains
half-open boundaries and gaps without rescanning all observations for each row.

## Tests

From the isolated worktree's `analytics` directory:

```sh
PYTHONPATH=/home/sat/earthship-ui/openhab/scripts:src python3 -m pytest -q
```

Result: **381 passed**, 7.48 seconds. Includes parser/interval coverage from
6f97edf, daily integration from1c5d2c9, and hourly/configuration integration.
New tests cover independent current/lag validity, exact expiry, missing and
ambiguous evidence, physical-bank boundaries, both Denver DST transitions,
unchanged unrelated feature values, CLI argument wiring, and default policy.
Three older heartbeat integration tests now supply the required physical bank
epoch; their original timestamp/provenance assertions remain intact.

## Actual PostgreSQL comparison

Both readers ran against one read-only, repeatable-read database transaction,
with five-second connection/statement limits. Source tables were resolved from
the actual inventory, not hard-coded for production reads. No data was written,
no reports were materialized, and no OpenHAB state/control or DM was changed.

For September10's daily window, PV/load/weather/balance outputs and all battery
power/temperature/EFC fields matched the explicit legacy configuration exactly.
Atomic SoC extrema were99 and100. Its source coverage at the comparison snapshot
was0.03349430104166669 and quality `insufficient_data`. This is a partial-day
source snapshot, not an expected final daily value or a whole-day qualification.

The five-minute feature grid started at the previously verified expired instant:

| UTC point | Atomic SoC | One-hour lag |
| --- | --- | --- |
| 2026-09-10T22:00:09.963Z | null | null |
| 2026-09-10T22:05:09.963Z | 100 | null |

All non-SoC feature fields matched the legacy reader exactly. The first point
proves that a still-`valid` JSON status does not bypass `validUntil`; the second
proves that natural recovery qualifies again. Missing pre-stream lag history
remains null.

## Remaining release work and boundaries

Complete independent review, then merge/push and verify deployed imports and
the next normal scheduled run. Do not backfill historical reports to make them
appear qualified. Preserve existing schedules, everyChange persistence, BMS
counters, controls, notification policy, and all stored history. Rollback is
reader/configuration code only. Task82 remains held; Superpowers is disabled.

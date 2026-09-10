# Atomic BMS analytics reader verification

Status: reviewed release b08ae1435bfa456075b4d6eaa1f1b05ad728f1a2 merged,
pushed to origin/main and deployed locally on September10. The next normal
scheduled daily run remains pending verification. The original implementation
and comparison evidence below is followed by the deployment receipt.

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

Verify the next normal scheduled run. Do not backfill historical reports to make them
appear qualified. Preserve existing schedules, everyChange persistence, BMS
counters, controls, notification policy, and all stored history. Rollback is
reader/configuration code only. Task82 remains held; Superpowers is disabled.

## Deployment receipt

The user-designated local Spark agent performed a bounded independent read-only
review of91867f8..b08ae14. Its first checklist covered expiry enforcement,
no numeric fallback, and independent current/lag qualification. The coordinator
required a second pass over aggregation/reader/quality/CLI and the full changed
file list before accepting the accounting/scope check. Both passes reported
PASS with function-level evidence. This was a bounded checklist, not an
independent exhaustive security audit. Hexmem access succeeded; Spark received
no write, control, notification or deployment authority.

Coordinator checks included the accounting diff, all production call sites,
the actual CLI dry run, scheduled delegation with the write-capable CLI mocked
out, and381passing tests on the exact candidate (7.46seconds). The production
checkout was clean at91867f8 before a fast-forward to the reviewed b08ae14.
HEAD and origin/main matched after push. No unit, timer or service was modified
or restarted: existing oneshot jobs import from `/home/sat/Solar_PV/analytics/src`.

Post-deployment imports resolved to that production checkout, the selected
policy was `atomic_bms_evidence`, and a real read-only CLI daily run succeeded
with the partial day's battery quality `insufficient_data`. Before/after
fingerprints of complete historical rows matched exactly:

| Table | Rows | MD5 of ordered row JSON |
| --- | --- | --- |
| daily_battery | 53 | d2abcd0797e8e7971b444cc7a2783de8 |
| daily_pv | 53 | cfa92cc27fcb746599a0c0f35f5f8499 |
| daily_load | 53 | 0856550a50ebcc2d6e0eed45d8881502 |
| daily_weather | 53 | 4e93f13e43feade368e3c66a662a0d93 |

The existing daily timer remained active, next due September11 at00:21:25MDT.
The UI publisher timer also remained active; its16:45:29MDT run exited0.
These checks do not substitute for the next completed daily materialization.
No historical backfill, test DM, source/control write, or accounting reset occurred.

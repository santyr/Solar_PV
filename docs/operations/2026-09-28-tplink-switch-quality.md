# TP-Link supporting load-switch quality: opt-in reader

The Earthship OpenHAB collector began durable source-bound switch receipts at
2026-09-28 16:36:40.989 UTC. `analytics/config/switch-evidence.json` fixes that
cutover, the exact `TPLink_Switch_Evidence_JSON` Item, both canonical fields and
the v1 basis. No earlier local day is eligible. The first *possible* complete
Denver day is September 29, assessable no earlier than September 30 after the
next natural midnight and a strict history check.

The optional `aggregate` arguments are `--switch-evidence-policy` and
`--switch-evidence-db-config`; both are required together. Without them,
Dishwasher and Cistern Pump source quality stays `freshness_unverified`, and
the production daily service remains unchanged. When enabled, one restricted,
read-only repeatable-read transaction resolves exactly the evidence Item and
bounded JDBC table. The shared Earthship reader rejects malformed, duplicated,
missing or out-of-order receipts, sequence gaps, unbarriered restarts,
pre-cutover/incomplete days and unsupported values. It scores each switch
independently, with a 90-second midnight carry-in. `ok` requires continuous
closed-window coverage and no in-day unavailable barrier; partial days do not
show a full-day ON-hour number. The old change-only Switch Item history supplies
only row statistics, never freshness authority.

This is source-only preparation, not permission to release the quality row.
The existing `energy_power_reader` role lacks SELECT on the exact new table
`public.item0656`. A narrow read-only grant is requested separately. After
that grant, run an isolated completed-day read, a dry-run aggregate with the
paired flags and both policy identities, and natural fault/restart and
withdrawal/recovery checks. Only then install a reversible daily-service
drop-in, observe its next natural aggregate, and verify the subsequent UI
publisher. Never backfill September 28 or rewrite earlier aggregates to look
qualified. The collector itself commands neither plug.

Verification at source preparation: 27 Earthship reader tests pass, the strict
parser accepted 21 real partial-day receipts in one contiguous epoch, and the
full Solar_PV analytics suite passed 871 tests before the final partial-ON-hour
withholding refinement; focused integration tests passed afterward. The one
unrelated pre-existing backup-unit test had expected the older restore point;
its assertion was updated to the current installed and documented verified
manifest without changing the backup unit.

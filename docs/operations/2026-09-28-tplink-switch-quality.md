# TP-Link supporting load-switch quality: opt-in reader

The Earthship OpenHAB collector began durable source-bound switch receipts at
2026-09-28 16:36:40.989 UTC. `analytics/config/switch-evidence.json` fixes that
cutover, the exact `TPLink_Switch_Evidence_JSON` Item, both canonical fields and
the v1 basis. No earlier local day is eligible. The originally possible
September 29 complete day is superseded by the versioned collector cutover
below; it must not be used to activate this reader.

The optional `aggregate` arguments are `--switch-evidence-policy` and
`--switch-evidence-db-config`; both are required together. Without them,
Dishwasher and Cistern Pump source quality stays `freshness_unverified`, and
the production daily service remains unchanged. When enabled, one restricted,
read-only repeatable-read transaction resolves exactly the evidence Item and
bounded JDBC table. The shared Earthship reader rejects malformed, duplicated,
missing or out-of-order receipts, sequence gaps, unbarriered restarts,
pre-cutover/incomplete days and unsupported values. It scores each switch
independently, with a version-bounded midnight carry-in (at most 95 seconds).
`ok` requires continuous
closed-window coverage and no in-day unavailable barrier; partial days do not
show a full-day ON-hour number. The old change-only Switch Item history supplies
only row statistics, never freshness authority.

This is source-only preparation, not permission to release the quality row.
The exact `energy_power_reader` SELECT grant on `public.item0656` was later
applied and read back, without write privileges. After a complete v2 day,
run an isolated completed-day read, a dry-run aggregate with the
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

## September 29 versioned source cadence correction

The observational collector's v1 90-second TTL was a few milliseconds shorter
than normal binding-origin report intervals, which reached 90.054 seconds
without an unavailable barrier. Its strict reader correctly found many small
coverage gaps, so September 29 cannot qualify. Earthship UI commit `9965c37`
added v2 receipts with a bounded 95-second TTL and a new unavailable startup
epoch while preserving exact 90-second parsing for historical v1. The
`earthship-ui/docs/operations/2026-09-29-tplink-switch-evidence-v2-cutover.md`
receipt records natural v2 sequences 1–3 after the guarded 04:50 MDT rule
replacement. The restricted reader strictly parsed later v2 JDBC rows in a
read-only transaction. No earlier gaps were backfilled or relabeled.

The first possible complete v2 Denver day is September 30, assessable after
its midnight on October 1. A **staged-only** `zz-qualified-switch.conf`
daily-service drop-in preserves current power and temperature flags while
adding the paired switch policy and restricted reader path. It is not
installed. The drop-in passed systemd's user-unit parser and 30 focused
unit/scheduled tests; the full analytics suite passed 880 tests against the
candidate v2 reader. Install only after strict complete-day, source
fault/restart and withdrawal/recovery checks, then verify the next natural
daily aggregate and UI publisher. Historical days remain unchanged.

## October 2 combined daily-quality candidate

The still-uninstalled `zz-qualified-switch.conf` now also forwards the paired
`--bms-aux-evidence-policy` and `--bms-aux-evidence-db-config` arguments. Both
switch and BMS auxiliary evidence use the existing restricted
`energy-power-reader.jdbc`; aggregate storage keeps the separate
`energy-power-writer.jdbc`. Current power/temperature policies, the original
nonblocking lock, previous-local-day selection and source search path remain
unchanged. No new grant, credential, timer, database write or household control
is introduced by this source candidate.

Candidate SHA-256:
`6a12658f41ba8e6b32e6543681cfd05676f5c4830a6e6f20f62b4f9b40d5a5e5`.
The new regressions failed while the BMS flags were absent, then passed after
the correction. They parse the exact unit command and verify all eight paired
arguments reach the existing scheduled aggregate entrypoint unchanged. The
affected unit/scheduled/CLI/switch/BMS-quality/reader slice passes 84 tests,
with no skips. Two separate actual producer-to-restricted-PostgreSQL and
grant-withdrawal tests also pass (5.56 seconds). Their events and failures are
simulated in disposable data: they are not physical-source/network evidence.

An isolated parser round trip copies the **actual** daily unit and its two
existing power/temperature drop-ins into owned temporary storage. The user
systemd parser accepts the original, combined candidate and restored-original
states. Original bytes and actual production files remain unchanged; the
candidate remains absent from live DropInPaths. This proves syntax and a
temporary file removal, not attended production handoff/rollback or a natural
aggregate. All test storage and owned database containers were removed.

The Earthship completed-day record independently qualifies September 30 and
preserves October 1's partial results. Actual October 2 JVM barrier/native
recovery now passes. Independent physical-source fault qualification and an
exact receipt-backed, reversible user-unit handoff remain before activation;
then require the next natural aggregate and unchanged accounting/UI publication.
This candidate affects daily supporting-quality rows only. It does not enable
the publisher's separate BMS live-health policy, rewrite old snapshots, suppress
partial coverage or change qualified AC/EFC totals.

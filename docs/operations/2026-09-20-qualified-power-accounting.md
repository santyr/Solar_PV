# Qualified power accounting foundation

The isolated `feat/qualified-power-accounting` implementation adds
`analytics/src/earthship_energy/power_intervals.py`. It is not imported by the
daily scheduler and changes no database, existing totals, publisher or control.

`account_power_intervals` consumes already-qualified, ordered, nonoverlapping
half-open held-power segments. It clips them to the requested window, integrates
positive and negative throughput separately, and derives covered/missing time
from exactly the contributing segments. It does not interpolate gaps or infer
health from numeric state. Polarity mapping remains the calibrated caller's
responsibility. Explicit zero-power observation and absent observation have
distinct coverage. Elapsed-time math normalizes to UTC, including Denver DST.

The reproduced 1000W/120-second qualified interval contributes 1/30kWh, not the
24kWh a full-day numeric carry would contribute. Remaining time stays missing.
Tests cover signed energy, clipping, gaps, adjacent segments, invalid/overlapping
evidence, malformed/nonfinite/overflowing values and 23/25-hour days.

## Remaining integration requirements

1. Establish per-field source receipt identity, invalidation and restart/expiry
   contracts. Existing Schneider group timestamps are not automatically atomic
   per-field power evidence.
2. Build qualified segments from persisted evidence without backdating receipt
   visibility or bridging invalid/source-restart boundaries. Preserve original
   timestamps and explicit unknown state.
3. Connect numeric and quality aggregation to the same segments; cover battery,
   PV and household load independently. Do not alter battery sign calibration.
4. Version the materialized accounting contract and record a real cutover;
   retain legacy estimates separately rather than silently relabeling or
   rewriting them. Preserve bank epochs and manufacturer counters.
5. Accumulate observed qualified throughput with explicit missing coverage;
   dropping whole partial days is not a substitute. Propagate the distinction
   through scheduled materialization, reports and the reader-first UI contract.
6. Verify live collection and natural scheduled results before declaring the
   wider power-health/EFC issue resolved.

This foundation deliberately supplies no evidence parser, receipt producer,
schema migration or activation flag. It cannot qualify input on its own and
must not be wired to unqualified numeric carry as a shortcut.

## Historical reader follow-up

`power_evidence.py` now supplies a separate strict parser and per-field interval
builder for the staged OpenHAB power-evidence stream. The original foundation
boundary above describes a8925f9; this follow-up adds parsing, but still no SQL
transport, scheduler integration, migration or live activation.

Closed top-level schema: version1,streamEpoch(UUID),sequence(positive safe integer),
recordedAt(UTC milliseconds),fields(exactly battery.dc_power_w,pv.input_power_w,
pv.output_power_w). Each field contains status,reason,observedAt,validUntil,watts.
Unavailable fields have null measurement members. Valid fields use integral
representable watts and exact120-second expiry after acquisition. Duplicate keys,
unknown members, booleans as numbers, invalid timestamps and future publication
relative to persistence are rejected. Malformed rows remain explicit barriers.

Per-epoch sequences distinguish same-millisecond publications. Conflicting or
regressing order fails closed. Missing sequences stop carry at the previous
known publication; a later complete snapshot cannot revive an old carried field
across that unknown interval. Retired epochs cannot reappear. An unchanged field
does not gain a spurious gap merely because a different field publishes.

Intervals begin no earlier than persistence visibility, end at evidence expiry
or the next relevant publication boundary, preserve invalid/restart gaps and
require post-cutover acquisition. A restored identical record never renews its
coverage. No interpolation or fallback to legacy numeric power is permitted.

Verification:579full analytics tests, including56focused reader/accounting tests;
matching producer1498full UI/OpenHAB tests. An isolated cross-language probe ran
the actual battery JS transform and observer, parsed their two output records
with this reader and integrated the result. With1000W,120-second expiry and1ms
persistence delay, coverage was119.999seconds and energy0.03333305555555555kWh.
This proves code-contract compatibility, not live acquisition or SQL transport.

## Bounded SQL transport follow-up

`power_reader.read_power_history` now opens a dedicated read-only connection with
5-second connect/statement and1-second lock timeouts. A single SELECT snapshot
reads the120-second lookback plus two preceding boundary rows, retaining original
timestamps and duplicates. It builds all three fields from the same rows rather
than issuing separate potentially inconsistent per-field queries.

Requests are capped at25elapsed hours and60000window/lookback rows. An extra row
detects overflow; excessive history raises PowerHistoryLimitError and never
returns a truncated prefix. SQL transfers at most4096bytes per raw record;
oversized values become null invalid barriers rather than truncated JSON.
The two earlier rows expose duplicate latest-carry timestamps; duplicates remain
sequence errors. Windows entirely before cutover do not connect. The requested
table must match the OpenHAB item-number naming convention. Connection closes
on query failure and before parsing.

Verification:16transport tests; full595analytics tests pass. A read-only live
PostgreSQL query of the same boundary/window/size-guard structure against existing
weather history item0646 returned2boundary rows and1window row(max1099bytes).
This proves the query structure on real JDBC storage, not power-data collection.
No power Item table exists by this implementation, and no credentials or table
IDs are hardcoded into the new reader. Filesystem currently has659GiB available;
that is headroom only, not a measured power-record retention budget.

The60000row ceiling accommodates the nominal three5-second fields over25hours,
but publication/storage volume still requires live measurement. This function
is not yet called by the daily scheduler. Read-only credentials, resolved power
table inventory, persistence activation, live provenance checks and explicit
versioned accounting cutover remain required before operational integration.

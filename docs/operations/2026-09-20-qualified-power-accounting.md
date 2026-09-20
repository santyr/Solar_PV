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

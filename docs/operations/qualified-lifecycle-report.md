# Qualified lifecycle throughput

`report lifecycle --power-evidence-policy analytics/config/power-evidence.json`
selects the bounded qualified-snapshot reader, never the legacy daily tables.
Use explicit `--start` and exclusive `--end` dates (1–366 days) and the existing
restricted reader JDBC configuration. Without the flag, legacy reporting is
unchanged and must not be interpreted as receipt-qualified accounting.

The `qualified_lifecycle` v1 result identifies the physical bank, policy, actual
cutover, requested window and revision digests. Charge/discharge kWh and
`period_efc` are observed totals within that window. Missing dates remain listed;
partial coverage is retained per day and never extrapolated. Empty evidence
yields null totals, not zero. Latest revision selection occurs before validation
and never revives an older better-looking revision.

This is not a complete battery-lifetime report. Lifetime/cumulative endpoint EFC
is withheld. High-SoC exposure uses the separately qualified atomic BMS source
record, never power coverage or legacy numeric history. Its own daily coverage,
valid seconds and revision identity accompany observed hours above90/95percent.
Zero valid coverage is unknown; a measured zero duration with valid coverage is
zero. Missing, ambiguous or non-atomic SoC evidence is explicitly unavailable;
inconsistent duration/coverage or duplicate quality records fail closed.
Temperature exposure and independent BMS-cycle comparisons remain explicitly
unavailable, not inferred from power evidence.
Qualified winter energy replay still requires an independently qualified AC-load
source. No consumer schedule, hardware action, historical rewrite or learning
activation is changed by this opt-in command.

Independent module-report safeguard: imported lifetime throughput counters are
only differenced when every supplied sample in that module's requested window
is finite, nonnegative, present and nondecreasing. Any observed reset, invalid
barrier or conflicting same-time counter yields null, not zero or a shortened
window's delta. Equal valid counters still yield measured zero. This does not
qualify sampling gaps, infer reset offsets or complete the qualified lifecycle
BMS comparison; imported provenance and original observations are retained.

September 20 verification: focused lifecycle/power/CLI tests passed. A live call
using `energy-power-reader.jdbc` returned the expected empty/unavailable result
for September 19, with null throughput and no legacy substitution. This does
not establish a nonempty natural daily result; the first qualified daily write
remains scheduled after the current day completes.

September 23 read-only follow-up: the restricted reader returned naturally
written September 20–22 daily snapshots (IDs 1–3), with no missing dates or
legacy substitution. The cutover day has 60.39% battery-power coverage; both
later completed days exceed 99.98%. The observed three-day period EFC is
0.4347889408, and separate atomic-SoC evidence reports 49.5898 hours above
90% and 32.4853 hours above 95%, with at least 99.97% valid SoC coverage on
each day. This closes the first nonempty completed-day readback. The report
correctly remains `partial_observations`: its cutover day is partial, no
missing intervals are extrapolated, and lifetime EFC, temperature exposure
and independent BMS-counter comparison remain unavailable.

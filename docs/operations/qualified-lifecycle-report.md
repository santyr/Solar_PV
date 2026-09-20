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
is withheld. Temperature exposure, high-SoC exposure and independent BMS-cycle
comparisons remain explicitly unavailable, not inferred from power evidence.
Qualified winter energy replay still requires an independently qualified AC-load
source. No consumer schedule, hardware action, historical rewrite or learning
activation is changed by this opt-in command.

September 20 verification: focused lifecycle/power/CLI tests passed. A live call
using `energy-power-reader.jdbc` returned the expected empty/unavailable result
for September 19, with null throughput and no legacy substitution. This does
not establish a nonempty natural daily result; the first qualified daily write
remains scheduled after the current day completes.

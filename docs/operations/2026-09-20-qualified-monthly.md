# Qualified monthly accounting

`scheduled monthly-report --power-evidence-policy PATH` reuses the bounded
qualified snapshot report, never the legacy daily tables. The existing monthly
timer and previous Denver calendar-month window are retained. Other timezones
are refused in qualified mode. No parallel schedule is introduced.

Output is `YYYY-MM/qualified-power-monthly.json` with the unchanged
`qualified_power` report schema, accounting policy/cutover, revision identities,
per-day coverage and explicit missing dates. Totals are observed qualified
throughput within that window, not lifetime EFC. No completed records means null
totals, not zero. Dates before the September 20 cutover stay missing rather than
being filled from legacy data. Unqualified AC load/balance stays unavailable.

The preparation receipt uses `earthship-energy-monthly-preparation/v2` and labels
the accounting basis and legacy exclusion. Original monthly mode and its v1
preparation receipt remain available without the flag. Separate filenames preserve
historical `energy-monthly.json` reports. Failure or mismatched qualified provenance
does not fall back to a legacy report or write an output/review event.

The optional tracked systemd drop-in selects the already-provisioned read-only
power reader. Install only after source deployment, pause the existing monthly
timer during configuration change, verify ExecStart, then restore its original
state. No manual report preparation or operator DM is required for deployment.
Remove only this drop-in to return future preparation to legacy mode; preserve
both historical output series. Natural execution remains a separate evidence gate.

Validation: 706 analytics tests pass, including separate-output preservation,
30 explicit missing September dates for an empty series, reader-error refusal,
legacy-provenance rejection and timezone refusal.

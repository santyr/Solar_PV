# Qualified power feature exports

Use the explicit power policy for new PV feature datasets:

```bash
cd /home/sat/Solar_PV/analytics
PYTHONPATH=src python3 -m earthship_energy.cli export-features \
  --start 2026-09-20T18:00:00Z --end 2026-09-20T19:00:00Z \
  --cadence 5 --output /private/destination/features.csv \
  --power-evidence-policy config/power-evidence.json
```

The destination directory must already exist. Protect exported household data;
do not commit it. No scheduler, training activation or OpenHAB mutation is added.
Without the flag, the existing v2 legacy export contract remains unchanged.

Qualified mode emits CSV v3 with PV basis, actual power cutover, explicitly
unqualified AC-load basis, and an explicit note that other fields retain their
existing source policies. This does not claim every feature is receipt-qualified.
Atomic SoC policy is required. PV current and one-hour lag values use half-open
qualified receipt intervals; zeros are observations, while gaps/expiry/cutover
yield empty cells. AC load and its lag are always empty until an independent
source is qualified. There is no numeric-history fallback on missing/invalid
power evidence or reader failure.

Each request is limited to 24 elapsed hours plus one hour of lag history, within
the existing 25-hour/60,000-row power reader budget. Split longer datasets into
explicit bounded exports. Interval overlap, negative PV, ambiguous evidence,
partial reader configuration and fabricated pre-cutover values fail closed.

Verification September 20: 728 analytics tests passed. A read-only live export
for 18:50–19:05Z produced three v3 rows, with qualified PV/current and lag values
present and all AC-load values absent. Private receipt:
`/tmp/qualified-feature-live-ejemeg12`. No telemetry or training data was inserted.

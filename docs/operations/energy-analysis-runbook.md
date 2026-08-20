# Energy Analysis Runbook

## Evidence order

1. Check timestamp, timezone, freshness, units, and sign conventions.
2. Compare live OpenHAB state with PostgreSQL persistence.
3. Use named, reproducible SQL or report commands.
4. Separate observed facts from forecasts and assumptions.
5. Attach the relevant system epoch.
6. Record a durable conclusion in Hexmem only after verification.

## Commands

Run from `analytics/`:

```bash
pytest -q
PYTHONPATH=src python3 -m earthship_energy.cli validate-sources --read-only
PYTHONPATH=src python3 -m earthship_energy.cli migrate --dry-run
PYTHONPATH=src python3 -m earthship_energy.cli aggregate --date 2026-08-19 --dry-run
PYTHONPATH=src python3 -m earthship_energy.cli report monthly --format json
PYTHONPATH=src python3 -m earthship_energy.cli report lifecycle --format json
PYTHONPATH=src python3 -m earthship_energy.cli report winter --format json
PYTHONPATH=src python3 -m earthship_energy.cli report modules --format json
PYTHONPATH=src python3 -m earthship_energy.cli import-lynk \
  --file /protected/operator-export.csv --dry-run
PYTHONPATH=src python3 -m earthship_energy.cli record-snow \
  --state snow_cleared --occurred-at 2026-12-01T10:30:00-07:00 \
  --method operator --confidence 1.0 --note "array cleared" --dry-run
PYTHONPATH=src python3 -m earthship_energy.cli export-features \
  --start 2026-08-01T00:00:00-06:00 \
  --end 2026-08-02T00:00:00-06:00 \
  --cadence 15 --output /protected/energy-features-2026-08-01.csv
```

Daily writes are idempotent and confined to `energy_analytics`. Migration and
the initial bounded backfill require the verified backup manifest documented in
`recovery-and-backup.md`. Recurring aggregation first verifies that no schema
migration is pending, then updates only compact analytics rows; it does not
rehash the migration backup. Raw `public.itemNNNN` history is read-only.

Daily PV products include input/output energy, MPPT energy ratio, productive
window and hours, and energy on each side of observed solar noon. Solar noon
is the midpoint of the persisted `Sun_Rise_End` and `Sun_Set_Start` events,
not a forecast timestamp. Battery products use those same persisted astro
events for sunrise/sunset SOC and compare the prior sunset with current
sunrise for overnight drop. Weather includes the daily rain counter converted
from inches to millimeters plus the latest snow event known at the day
boundary.

Dishwasher and Shurflo Items are switch states, not watt meters. Their daily
`active_loads` entries therefore say `measurement=state_only`, report
`state_on_hours`, and leave `energy_kwh` null. Do not infer energy use,
reserve impact, or actual motor/appliance activity from those states alone.

The winter report uses November through March rows only. It includes observed
minimum-SOC median and fifth percentile, reserve-threshold day counts,
consecutive no-full days, the worst contiguous PV deficit and time to the next
99% recharge, required 100/90/80/70/60% capacity scenarios, and an explicit
PV-versus-storage matrix. A window with no winter rows returns no simulated
winter evidence.

`import-lynk --dry-run` validates the complete UTF-8 CSV and reports its
SHA-256 without writing. After review, repeat with `--apply`; the command
refuses pending schema migrations and inserts the batch and all module samples
in one transaction. A byte-identical export is a successful write-free
duplicate. `report modules` then reports per-module current-sharing
deviation, cell spread, temperature, throughput deltas, faults, and exact
import-batch provenance.

`record-snow` validates an aware timestamp, closed state vocabulary,
confidence, and optional JSON evidence in dry-run mode. After operator review,
repeat the exact command with `--apply`. The insert is idempotent and confined
to `energy_analytics.snow_events`; it has no OpenHAB or electrical-control
authority. Inferred shade and kiva producers use the corresponding
observational-event persistence API with method version, confidence, bounded
evidence, and optional operator confirmation.

`export-features` reads PostgreSQL without write privileges and writes a
version-2 CSV at an explicit 5- or 15-minute cadence. Each row includes current
and one-hour-lagged SOC/PV/load state, current outdoor temperature and
irradiance, observed daylight, active dishwasher/pump state when available,
the system epoch, as-of hourly weather and daily PV forecasts, and
confidence-bearing shade/kiva observations. Forecast selection requires
`issued_at <= at`; unavailable forecasts remain explicitly unavailable.
Existing output is not replaced unless `--force` is supplied. The command
prints row count, byte count, and SHA-256 for provenance.

## Current limitations

- The available Discover four-module epoch begins 2026-07-19. A winter report
  over the current data explicitly returns `insufficient_winter_observations`;
  summer scenarios must not be presented as winter evidence.
- OpenHAB persists on `everyChange`. Long gaps for unchanged state are expected;
  each daily run now materializes raw row counts, first/last observations,
  explicit companion-authorized coverage, stale intervals, and policy evidence
  in `daily_source_quality`. Required battery, Schneider, and weather products
  are downgraded unless their configured BMS/device/timestamp/health companion
  authorizes the interval. Sources without an explicit companion remain
  `freshness_unverified`; a raw value carried across a day cannot authorize
  publication by itself.
- Curtailment and lost-harvest estimates remain unavailable.
- Philips illuminance, occupancy, and temperature Items are linked, persisted,
  and present in the current 21-source provenance contract; inference remains
  Stage 3 work and must begin observationally.

Never mix retired AGM SOC estimates or dormant miner signals into Discover-bank
analysis.

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
```

Daily writes are idempotent and confined to `energy_analytics`. Migration and
the initial bounded backfill require the verified backup manifest documented in
`recovery-and-backup.md`. Raw `public.itemNNNN` history is read-only.

## Current limitations

- The available Discover four-module epoch begins 2026-07-19. A winter report
  over the current data explicitly returns `insufficient_winter_observations`;
  summer scenarios must not be presented as winter evidence.
- OpenHAB persists on `everyChange`. Long gaps for unchanged state are expected;
  freshness/status companion Items and live health remain part of publication
  review until historical source-quality materialization is complete.
- Curtailment and lost-harvest estimates remain unavailable.
- Philips illuminance/occupancy Items and shade inference remain Stage 3 work.

Never mix retired AGM SOC estimates or dormant miner signals into Discover-bank
analysis.

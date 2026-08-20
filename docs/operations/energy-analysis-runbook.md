# Energy Analysis Runbook

## Evidence order

1. Check timestamp, timezone, freshness, units, and sign conventions.
2. Compare live OpenHAB state with PostgreSQL persistence.
3. Use named, reproducible SQL or report commands.
4. Separate observed facts from forecasts and assumptions.
5. Attach the relevant system epoch.
6. Record a durable conclusion in Hexmem only after verification.

## Current limitations

The general energy analytics schema and named monthly/winter/lifecycle reports
are not deployed yet. Stage 2 owns their implementation. Until then, do not
present ad hoc calculations as canonical metrics.

Never mix retired AGM SOC estimates or dormant miner signals into Discover-bank
analysis.

# Maintenance

## Current recurring checks

- Confirm BMS communications and authoritative SOC.
- Review inverter/MPPT faults and warnings.
- Preserve configuration exports, firmware packages, and vendor manuals.
- Inspect battery connections and environment according to current Discover
  documentation and qualified electrical practice.
- Keep PV access suitable for prompt winter snow clearing.
- Re-verify firmware before firmware-dependent work.
- Revisit the Schneider successor plan on the roadmap cadence.

Do not reuse maintenance values from the retired AGM bank. Electrical settings,
firmware changes, and physical work require separate preparation, backup,
authorization, and post-change verification.

## Winter readiness (prepared 2026-08-22)

The 2026–2027 winter is the first direct validation of the Discover four-module
bank. Instrumentation and workflows are ready before the season starts:

- **Winter sufficiency report** (`report winter`) is deployed and correctly
  returns `insufficient_winter_observations` until November–March rows exist.
  It will populate minimum-SOC median/5th percentile, reserve-threshold day
  counts, consecutive no-full streaks, worst PV deficit, recharge time,
  capacity scenarios, and the PV-versus-storage matrix automatically from the
  daily aggregates.
- **Scenario replay baseline (read-only, observed 2026-07-19 → 2026-08-22):**
  with summer loads (≈198 kWh/35 d) and full PV (≈247 kWh/35 d), the model
  stays above 98% SOC. Holding loads constant, sufficiency holds to roughly a
  0.85 PV multiplier; at ≤0.8 the model enters reserve. Treat these as
  sensitivity context only — real winter has lower loads AND much lower PV,
  so the authoritative answer remains `report winter` on actual November+
  rows, not this extrapolation.
- **Snow events:** operator workflow is
  `record-snow --state snow_covered|snow_cleared --occurred-at <iso> --method operator --confidence 1.0`.
  Dry-run first, then repeat with `--apply`. Snow state feeds daily weather
  products and the winter report.
- **Module health:** `report modules` needs LYNK CSV samples via
  `import-lynk --dry-run` then `--apply`. None have been imported yet; without
  them per-module current sharing and cell-voltage spread (checkpoint item 7)
  cannot be reviewed. Exporting/importing one batch before December closes
  that gap.
- **Review trigger:** run the named winter review after sufficient
  December/January data exists, using the roadmap checkpoint list. Do not
  record a winter conclusion in Hexmem before then.

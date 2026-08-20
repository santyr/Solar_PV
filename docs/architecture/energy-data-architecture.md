# Energy Data Architecture

```text
Discover BMS / Schneider
          |
          v
       OpenHAB --------> earthship-ui
          |
          v
      PostgreSQL
          |
          v
        Codex ---------> reports / engineering decisions
          |
          v
        Hexmem
```

## Ownership

- Hardware owns electrical limits and protection.
- OpenHAB owns live integration, normalized Items, and bounded automation.
- PostgreSQL owns raw quantitative history and future derived analytics.
- Solar_PV owns definitions, provenance, runbooks, and system epochs.
- Codex reads APIs, database, CLI, source, and Hexmem for analysis.
- Hexmem stores durable conclusions, never raw telemetry or authority.
- earthship-ui consumes stable OpenHAB contracts; it has no database or Hexmem
  credentials.

## Provenance rules

Every derived metric must identify source Item(s), unit, sign convention,
timezone, aggregation window, missing-data policy, and system epoch. Raw
history is retained. Forecast snapshots must preserve issue and valid times to
avoid future-data leakage.

The live OpenHAB database uses UTC while the house operates in
America/Denver. Daily aggregates require explicit local-day and DST tests.

## Current versus planned

OpenHAB JDBC history and the focused `thermal_intel` schema exist now. The
general energy analytics schema, portable dataset, scenario simulator, and
scheduled reports are Stage 2 work; this document does not imply they are
deployed.

Dormant miner data and AGM-derived SOC calculations are excluded from the
active model. Historical rows may be retained with provenance and a historical
system epoch.

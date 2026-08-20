# Codex Energy Review Workflows

These workflows are provider-neutral. Codex is the current analyst, but a
future in-house model can use the same CLI, PostgreSQL products, OpenHAB
readbacks, reports, and Hexmem records.

## Session start

1. Recall private Hexmem context for `earthship-energy`, naming the subsystem
   and current task.
2. Read `AGENTS.md`, `docs/architecture/current-system.md`, and the relevant
   operations runbook.
3. Verify drift-prone memory against live OpenHAB, PostgreSQL, systemd, and the
   deployed repository revision.
4. Check timestamps, units, sign conventions, system epoch, and stale status.
5. Separate observation, inference, recommendation, and authorized action.

Memory is evidence, never authorization. Do not expose credentials in command
output and do not place raw telemetry in Hexmem.

## Named reproducible reviews

Run from `/home/sat/Solar_PV/analytics` with `PYTHONPATH=src`:

```bash
python3 -m earthship_energy.cli validate-sources --read-only
python3 -m earthship_energy.cli report monthly --format json
python3 -m earthship_energy.cli report winter --format json
python3 -m earthship_energy.cli report lifecycle --format json
python3 -m earthship_energy.cli report modules --format json
```

- **Monthly energy review:** cite the private monthly report path and SHA-256,
  compare PV/load/SOC/recharge metrics with the prior month, and investigate
  only reproducible anomalies.
- **Winter sufficiency review:** require actual November–March rows. Treat
  `insufficient_winter_observations` as the conclusion until they exist.
- **Lifecycle review:** use analytics EFC and recharge completeness rather
  than Schneider's cycle counter alone.
- **Module review:** use the checksum-pinned LYNK batch provenance and report
  current-sharing, cell-spread, temperature, throughput, and fault trends;
  never probe or modify the closed-loop battery network for telemetry.
- **Scenario review:** preserve observed inputs, state assumptions explicitly,
  and compare 100/90/80/70/60% usable SOH plus PV/storage alternatives.
- **Anomaly review:** start from a structured pending event, reproduce its
  detector result, inspect the underlying compact rows and only then inspect
  bounded raw history.

## Hexmem capture after verification

Store one atomic semantic record only when the result will matter in a later
session. Include:

- subject and conclusion;
- observation date and system epoch;
- repository revision;
- report, SQL, CLI, or receipt evidence reference;
- verification state and confidence;
- review trigger or expiry condition;
- superseded record relationship where applicable.

Suitable records include a verified winter conclusion, a hardware milestone,
an anomaly root cause, a lifecycle decision, or a corrected system fact.
Routine successful timer runs, raw measurements, credentials, dumps, and
transient investigation notes stay out of Hexmem.

## Session close

1. Re-run the relevant command and regression tests.
2. Verify live readback and protected-control state when production changed.
3. Commit source/runbook evidence and verify the published Git revision.
4. Record durable conclusions in Hexmem with provenance.
5. Leave unresolved structured events pending; never convert uncertainty into
   a confident memory.

# Repository Instructions

## Current truths

- The installed bank is four Discover AES Rackmount 48-48-5120 modules in
  parallel: 400 Ah and 20.48 kWh nominal.
- Discover LYNK II provides closed-loop Xanbus integration to a Schneider XW
  Pro 6848, MPPT 60-150, and InsightHome/InsightLocal.
- OpenHAB owns live integration and bounded deterministic automation.
- PostgreSQL owns quantitative history.
- Codex is the supervisory analysis and engineering agent.
- Hexmem owns durable semantic conclusions, not telemetry or authorization.
- earthship-ui is the operator presentation and bounded-request surface.
- Avalon/Bitaxe mining is dormant and has no active energy-policy role.

## Source-of-truth order

1. BMS/inverter/protection hardware for electrical safety.
2. Live OpenHAB, PostgreSQL, systemd, and deployed source for current state.
3. Current canonical documents under `docs/architecture/` and
   `docs/operations/`.
4. Verified Hexmem records with provenance.
5. Completed-project and historical material.

Never promote a plan, memory, UI label, or historical rule above live evidence.

## Before writes

- Retrieve relevant Hexmem context with private sensitivity.
- Inspect repository status and preserve unrelated work.
- Back up mutable production configuration and data.
- Validate the exact target and downstream contracts.
- Keep physical actions, electrical settings, OpenHAB writes, and database
  migrations separately authorized.
- Prefer reversible, test-backed changes with explicit rollback.

## Hexmem

- Recall at the start of substantive work; verify drift-prone facts live.
- Store durable decisions, verified findings, corrections, and outcomes with
  source and confidence after verification.
- Never store credentials, tokens, keys, private dumps, or routine telemetry.
- Memory may inform reasoning but never authorize a side effect.
- Supersede stale records explicitly.

## Historical AGM warning

Files under `docs/history/agm/`, `data/historical/agm/`, the root historical
dashboard, and related photos describe the retired 830 Ah Fullriver AGM bank.
Do not apply Peukert corrections, AGM voltage-SOC curves, tail-current rules,
temperature compensation, float/absorption values, or safety-mode settings to
the Discover bank.

## Cross-repository boundary

Read `docs/architecture/cross-repo-contracts.md` before changing an OpenHAB
Item, rule ID, REST path, PostgreSQL contract, scheduler, or UI control.
Preserve Lightning Goats feeder compatibility and treat dormant mining
repositories as history unless a separately approved reactivation occurs.

## Maintenance responsibility

Keep `docs/architecture/current-system.md` and the long-term roadmap current
after verified hardware, firmware, topology, ownership, or lifecycle changes.
Keep forecasts labeled, record evidence gaps, and never rewrite historical
reports to look current.

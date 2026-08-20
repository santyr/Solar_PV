# Stages 2–5 Completion Audit — 2026-08-20

## Purpose and evidence rule

This is the canonical completion audit for the Stage 2–5 handoff. A passing
test or plausible implementation is not treated as completion unless the
required artifact and, where applicable, production readback exist. Statuses
are `met`, `partial`, `time-gated`, `operator-gated`, or `operator-deferred`.

Evidence was refreshed from:

- `Solar_PV` local `main` and `origin/main`, both at
  `c636d15efebd6c103ed9bd1d9f00a856d1f568a2`;
- `earthship-ui` local `main` and `origin/main`, both at
  `cb9ac07b02c3d5e0ab7415174b61a9e3932df66b`;
- read-only OpenHAB Item inventory through the deployed Vite proxy;
- PostgreSQL `energy_analytics` readback;
- user-level systemd timer/service state and journald;
- private report/event filenames, sizes, modes, and checksums without copying
  telemetry or credentials into this repository;
- the handoff prompts and `docs/acceptance-checklist.md` in the supplied
  handoff package.

Final analytics verification for this audit is `143 passed`, plus clean
`pyflakes`, `compileall`, and diff checks. Final `earthship-ui` verification is
`998 passed`, a successful production build, and `18 passed` Playwright tests
covering both 1340x800 and 1280x720. The read-only scenario canary successfully
replayed all 32 quality-approved current-epoch days with its capacity, reserve,
PV/load multipliers, inverter efficiency, and 100% initial SOC assumption
exposed in the output.

## Stage 2 — PostgreSQL energy data platform

| Requirement group | Status | Evidence | Remaining work |
| --- | --- | --- | --- |
| Critical source inventory and provenance | met | 21/21 current sources resolve to exact OpenHAB JDBC tables; source configuration retains Item, device, protocol, unit, scale, sign, quality policy, role, and confidence | Revalidate before any Item rename or device replacement |
| Raw telemetry retention and write isolation | met | Raw `public.itemNNNN` tables remain read-only; writes are confined to the additive versioned `energy_analytics` schema | None |
| Daily battery, PV, load, weather, recharge, and lifecycle products | met | 32 current-epoch dates materialized; four domain tables remain `quality=ok`; EFC is independently derived from charge/discharge throughput | Accumulate production history normally |
| Source freshness and missing-data evidence | met | 672 `daily_source_quality` rows across 21 sources and 32 dates: 416 companion-verified `ok`, 256 optional `freshness_unverified`; hourly live companion canary is Routine | Add companions for optional sources only when their semantics are validated |
| Forecast provenance and leakage prevention | met | Immutable forecast facts retain issue and valid timestamps; feature selection requires `issued_at <= feature_at`; replay is idempotent | None |
| Snow clearing and observational events | met | Dry-run/apply snow-event path and generic confidence-bearing observational-event persistence are implemented and tested; neither has action authority | Collect real events when they occur |
| System epochs and DST/local-day behavior | met | Three epochs seeded; current Discover epoch begins 2026-07-19; local-day and DST tests pass | Add an epoch only for a real system transition |
| Winter and capacity scenarios | met as capability | Winter-only report implements reserve thresholds, percentiles, no-full streaks, deficit replay, 100/90/80/70/60% capacity, and PV/storage matrix | Current data correctly reports `insufficient_winter_observations` until November–March evidence exists |
| Discover module telemetry | partial | Closed-loop probing was rejected; checksum-pinned, idempotent LYNK CSV import and module-health reports exist | No operator LYNK export has been imported, so current-sharing/cell-spread trends contain no live samples |
| Portable future-model interface | met | Version-2 5/15-minute CSV export includes epoch, current and lagged state, as-of forecasts, states, and confidence-bearing observational features | Parquet is optional, not required for portability |
| Database recovery | met for migration rollback | PostgreSQL archive checksum and complete isolated restore were verified | Off-host disaster recovery is explicitly operator-deferred; keep the limitation visible |

## Stage 3 — `earthship-ui` integration

| Requirement group | Status | Evidence | Remaining work |
| --- | --- | --- | --- |
| Existing console and controls | met | Deployed service is active; local and remote revisions agree; the Energy page uses OpenHAB REST/SSE/history and bounded controls retain their owner contracts; full unit/build/browser regression passed | Preserve owner contracts and re-run regressions after future changes |
| No browser database, Hexmem, SSH, or private credentials | met | Current browser code uses the OpenHAB proxy/API and has no PostgreSQL or Hexmem client | Preserve this boundary |
| Stable long-term analytics contract | met | `earthship-energy-ui/v1` is assembled server-side from bounded PostgreSQL products, published every five minutes to the sole observational `Energy_Analytics_JSON` String Item, and consumed through OpenHAB REST/SSE | Version any incompatible future contract rather than mutating v1 semantics |
| Battery lifecycle and winter visibility | met | The Energy page renders analytics EFC, days since full, no-full streak, winter minimum/median, observation count, forecast status, and explicit unavailable states; vendor cycles remain separately labelled | Winter values correctly remain unavailable until winter observations exist |
| Forecast and analytics freshness UI | met | Payload and UI carry `generatedAt`, `throughDate`, source health, forecast issue/valid timestamps, current/stale/unavailable status, and fail-closed parsing | Preserve the 15-minute stale boundary and future-date refusal |
| Tablet viewport and drill-downs | met | Current analytics layout passed unit tests and Playwright at 1340x800 and 1280x720, including observational detail and missing/stale states | Re-test both viewports after layout changes |
| Mining exclusion | met | No mining cards, controls, or miner-derived analytics are present | Preserve exclusion |

The default architecture remains:

```text
PostgreSQL analytics -> deterministic server-side publisher
                     -> versioned OpenHAB String Item
                     -> earthship-ui REST/SSE consumer
```

One bounded JSON Item is preferred over many independently updated scalar
Items because it gives the browser one version, one generation time, one
through-date, and one internally consistent quality snapshot. Publication must
be observational and fail closed; it cannot add a control path.

## Stage 4 — Codex and Hexmem operations

| Requirement group | Status | Evidence | Remaining work |
| --- | --- | --- | --- |
| Session lifecycle and authority boundary | met | `docs/architecture/codex-energy-management.md`, `AGENTS.md`, and the review runbook require Hexmem context, live verification, explicit authority, rollback, verification, and durable post-work capture | Continue applying the workflow |
| Named reproducible reviews | met | CLI provides monthly, winter, lifecycle, module, read-only scenario, import, event, validation, and feature-export workflows | None |
| Provider-neutral semantic memory | met | Hexmem stores conclusions/decisions with provenance and sensitivity; docs prohibit raw telemetry, secrets, and memory-authorized side effects | Supersede stale records when discovered |
| Future in-house AI portability | met | PostgreSQL schema, source/epoch contracts, report CLI, portable features, versioned OpenHAB payload, and Hexmem workflow are model-independent | Preserve provider-neutral contracts |
| Codex is not a scheduler | met | Deterministic timers invoke Python/SQL only; monthly and actionable artifacts wait for attended reasoning | None |

## Stage 5 — scheduling and review cadence

| Requirement group | Status | Evidence | Remaining work |
| --- | --- | --- | --- |
| Existing scheduler audit and non-duplication | met | Existing OpenHAB/forecast/Hexmem timers were inventoried before deployment; six energy jobs have distinct ownership | Re-audit before adding another timer |
| Required timer/service set | met | All six user timers are enabled/active: hourly quality, two-hour forecast, daily aggregate, weekly backup check, monthly report, and five-minute UI publication | None |
| Idempotence, locking, timeouts, logs, severity | met | Unit tests and manual canaries cover `flock`, bounded runtime, structured journald output, closed severity vocabulary, and idempotent database/report writes | Continue monitoring failures in journald |
| Actionable-event handoff | met | Private deduplicated pending events exist for backup and monthly review; routine healthy output stays in journald/PostgreSQL and never invokes Codex | Investigate attended events rather than adding polling AI |
| Calendar milestones | met | Annual, 2030, 2033, 2034, 2035, and 2038 strategic checkpoints were checked/reconciled; Calendar is not used for machine execution | First-winter conclusions remain data-timed, not invented in advance |
| Backup verification | met for approved local scope / **operator-deferred** off-host | Archive is checksum- and restore-verified; weekly checker correctly reports Actionable because the operator explicitly deferred an off-host/separate-mount backup for now | Keep the limitation visible; select a destination only on new operator direction |
| Elapsed automatic production evidence | **time-gated** | Manual canaries and a 32-day deterministic backfill pass; natural hourly quality, two-hour forecast, and five-minute UI publisher runs have succeeded | Daily, weekly, and monthly timers were installed on 2026-08-20 and have not yet accumulated natural scheduled runs, let alone several days of evidence |

## Compatibility and safety

| Requirement group | Status | Evidence | Remaining work |
| --- | --- | --- | --- |
| External OpenHAB consumers | met for unchanged interfaces | No shared Item/rule/API was renamed or removed; feeder semantics and correlated UI contracts are unchanged | Remote deployment of legacy `middlware` remains unverified; preserve compatibility until separately resolved |
| Dormant mining | met | No miner process, unit, live Item, Thing, or rule was detected; both miner repositories are classified historical/dormant and excluded from active data/UI | Reactivation requires a separate project and epoch |
| AGM retirement | met under operator override | Dashboard moved byte-identically under `docs/history/agm`, GitHub Pages was removed, and the former public page returns 404 | The original “preserve Pages” checklist item was superseded by the operator’s explicit unpublish instruction |
| Electrical safety | met | BMS and Schneider protections remain authoritative; analytics, Codex, Hexmem, UI additions, and energy timers have no protection-setting or actuation authority | Any future physical action requires separate explicit approval |
| OpenHAB deployment tooling drift | partial | Live OpenHAB is 5.2.1 while two older managed configuration tools still pin 5.2.0; newer receipt-bound thermal/photosensor tooling was independently verified | Do not broaden old mutation-tool version acceptance without a separate compatibility review |

## Thermal shadow extension

The thermal shadow is an additional program and does not block completion of
the Stage 2-5 electrical analytics handoff. Philips illuminance, occupancy,
and temperature Items are linked and persisted. Multihorizon schema v3 passed
physics, finite-metric, fold-count, provenance, and objective checks, but its
400-day candidate was refused because 24-hour air MAE was `2.520775 F` versus
`1.675 F` for persistence. No accepted artifact exists. `Thermal_Model_JSON`
and all thermal systemd units remain absent. Any future candidate must pass the
same fail-closed promotion and separately approved Gate B publication gates.

## Exact remaining gates

1. Allow the daily, weekly, and monthly timers to run naturally and accumulate
   several days of production evidence, then run the final validation audit.
2. Provide a LYNK CSV export only if live per-module trend population is
   desired; safe import and reporting capability already exists.
3. Revisit off-host backup only on new operator direction; it is explicitly
   deferred and the current checker must continue reporting the limitation.
4. Treat thermal promotion and Gate B as a separate extension, not as a reason
   to weaken or relabel the completed electrical analytics path.

The Stage 2-5 implementation is deployed and published. Full production
completion remains unproven only because the required elapsed natural
daily/weekly/monthly evidence cannot exist on the installation date.

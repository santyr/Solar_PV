# Stages 2–5 Completion Audit — 2026-08-20

## Purpose and evidence rule

This is the canonical completion audit for the Stage 2–5 handoff. A passing
test or plausible implementation is not treated as completion unless the
required artifact and, where applicable, production readback exist. Statuses
are `met`, `partial`, `time-gated`, or `operator-gated`.

Evidence was refreshed from:

- `Solar_PV` local `main`, tracking `origin/main`, and remote
  `refs/heads/main`, all at `7c08e60cc89080578226f89939f323a727d62dd0`;
- `earthship-ui` local `main` and `origin/main`, both at
  `32c9538f3567bb4ac8376204f6ea3ceef29122fa`;
- read-only OpenHAB Item inventory through the deployed Vite proxy;
- PostgreSQL `energy_analytics` readback;
- user-level systemd timer/service state and journald;
- private report/event filenames, sizes, modes, and checksums without copying
  telemetry or credentials into this repository;
- the handoff prompts and `docs/acceptance-checklist.md` in the supplied
  handoff package.

Final analytics verification for this audit is `116 passed`, plus clean
`pyflakes`, `compileall`, and diff checks. The read-only scenario canary
successfully replayed all 32 quality-approved current-epoch days with its
capacity, reserve, PV/load multipliers, inverter efficiency, and 100% initial
SOC assumption exposed in the output.

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
| Database recovery | met for migration rollback | PostgreSQL archive checksum and complete isolated restore were verified | Off-host disaster recovery remains Stage 5 operator-gated |

## Stage 3 — `earthship-ui` integration

| Requirement group | Status | Evidence | Remaining work |
| --- | --- | --- | --- |
| Existing console and controls | met for current UI | Deployed service is active; local and remote revisions agree; current Energy page uses OpenHAB REST/SSE/history and bounded controls retain their owner contracts | Re-run the full UI/viewport regression after Stage 3 changes |
| No browser database, Hexmem, SSH, or private credentials | met | Current browser code uses the OpenHAB proxy/API and has no PostgreSQL or Hexmem client | Preserve this boundary |
| Stable long-term analytics contract | **operator-gated** | Live Item inventory has no lifecycle/winter/daily analytics Item; repository search finds no consumer of `energy_analytics` products | Approve a versioned server-side PostgreSQL-to-OpenHAB JSON contract before implementation |
| Battery lifecycle and winter visibility | **operator-gated** | Current Energy page shows live SOC, predicted trough, vendor cycle counter, temperature, remaining Ah, and BMS state, but not analytics EFC, days-since-full, winter minima, or no-full streaks | Implement from the approved stable contract; do not relabel vendor cycles as analytics EFC |
| Forecast and analytics freshness UI | partial | Existing forecast/BMS indicators exist; no analytics payload exists whose freshness or quality can be rendered | Add explicit generated-at, through-date, quality, and unavailable states with the contract |
| Tablet viewport and drill-downs | partial | Existing 1340×800 Energy layout and history interactions have tests; the required new lifecycle/winter content has not been designed or tested | Approve compact layout, then test 1340×800, 1280×720, missing data, stale data, and reconnect |
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
| Future in-house AI portability | met | PostgreSQL schema, source/epoch contracts, report CLI, portable features, OpenHAB boundary, and Hexmem workflow are model-independent | Stage 3 payload semantics must also remain provider-neutral |
| Codex is not a scheduler | met | Deterministic timers invoke Python/SQL only; monthly and actionable artifacts wait for attended reasoning | None |

## Stage 5 — scheduling and review cadence

| Requirement group | Status | Evidence | Remaining work |
| --- | --- | --- | --- |
| Existing scheduler audit and non-duplication | met | Existing OpenHAB/forecast/Hexmem timers were inventoried before deployment; five energy jobs have distinct ownership | Re-audit before adding another timer |
| Required timer/service set | met | All five user timers are enabled/active: hourly quality, two-hour forecast, daily aggregate, weekly backup check, monthly report | None |
| Idempotence, locking, timeouts, logs, severity | met | Unit tests and manual canaries cover `flock`, bounded runtime, structured journald output, closed severity vocabulary, and idempotent database/report writes | Continue monitoring failures in journald |
| Actionable-event handoff | met | Private deduplicated pending events exist for backup and monthly review; routine healthy output stays in journald/PostgreSQL and never invokes Codex | Investigate attended events rather than adding polling AI |
| Calendar milestones | met | Annual, 2030, 2033, 2034, 2035, and 2038 strategic checkpoints were checked/reconciled; Calendar is not used for machine execution | First-winter conclusions remain data-timed, not invented in advance |
| Backup verification | partial / **operator-gated** | Archive is readable and restore-verified; weekly checker correctly reports Actionable | Operator must select an encrypted off-host or separately mounted destination, retention, and restore-test cadence |
| Elapsed automatic production evidence | **time-gated** | Manual canaries and a 32-day deterministic backfill pass; hourly quality and two-hour forecast timers have fired | Daily, weekly, and monthly timers were installed on 2026-08-20 and have not yet accumulated several naturally scheduled successful runs |

## Compatibility and safety

| Requirement group | Status | Evidence | Remaining work |
| --- | --- | --- | --- |
| External OpenHAB consumers | met for unchanged interfaces | No shared Item/rule/API was renamed or removed; feeder semantics and correlated UI contracts are unchanged | Remote deployment of legacy `middlware` remains unverified; preserve compatibility until separately resolved |
| Dormant mining | met | No miner process, unit, live Item, Thing, or rule was detected; both miner repositories are classified historical/dormant and excluded from active data/UI | Reactivation requires a separate project and epoch |
| AGM retirement | met under operator override | Dashboard moved byte-identically under `docs/history/agm`, GitHub Pages was removed, and the former public page returns 404 | The original “preserve Pages” checklist item was superseded by the operator’s explicit unpublish instruction |
| Electrical safety | met | BMS and Schneider protections remain authoritative; analytics, Codex, Hexmem, UI additions, and energy timers have no protection-setting or actuation authority | Any future physical action requires separate explicit approval |
| OpenHAB deployment tooling drift | partial | Live OpenHAB is 5.2.1 while two older managed configuration tools still pin 5.2.0; newer receipt-bound thermal/photosensor tooling was independently verified | Do not broaden old mutation-tool version acceptance without a separate compatibility review |

## Thermal shadow extension

The thermal shadow is an additional Stage 3 program, not evidence that the
long-term electrical analytics UI is complete. Philips illuminance, occupancy,
and temperature Items are linked and persisted. The rolling 400-day fit still
has no accepted artifact: the current mass equation can select zero air/mass
coupling, leaving transition spectral radius `1.0`. `Thermal_Model_JSON` and
all thermal systemd units remain absent. The next physics change is
operator-gated and must not weaken stability, backtest, publication, or
no-actuation gates.

## Exact remaining gates

1. Approve the Stage 3 versioned aggregate OpenHAB JSON contract and compact
   Energy-page layout.
2. Approve or reject the thermal mass-to-outdoor exchange redesign. This is a
   separate schema-versioned physics change.
3. Select the off-host/separate-mount backup destination, retention, and
   restore-test cadence.
4. Provide a LYNK CSV export if live per-module trend population is desired.
5. Allow elapsed daily/weekly/monthly schedules to accumulate production
   evidence, then run the final validation audit.

The program is not complete until these gates are resolved and their deployed
outcomes are verified and published.

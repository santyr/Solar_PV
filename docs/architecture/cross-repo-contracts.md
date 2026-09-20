# Cross-Repository Contracts

**Evidence snapshot:** 2026-08-20, America/Denver

The numbered findings below retain that historical snapshot, not current runtime
status. The stable contracts later in this document include subsequent verified
deployments; September 20 accounting supersedes the earlier v2-only boundary.

**Canonical tracker:**
[`docs/audit/cross-repo-dependency-inventory.csv`](../audit/cross-repo-dependency-inventory.csv)

## Findings

### 1. The deployed UI is ahead of GitHub

`earthship-ui.service` is active from `/home/sat/earthship-ui` on port 5190.
That checkout is on `main` and is 34 commits ahead of `origin/main`. The live UI
therefore cannot be reconstructed from the current remote default branch.

No Stage 1 reorganization should describe `origin/main` as the deployed UI
until those commits are intentionally reconciled and published.

### 2. The feeder contract has advanced beyond the older handoff context

The live OpenHAB rule `88bd9ec4de` is an enabled correlated owner triggered by
commands to `GoatFeeder_ManualRequest`. The persisted request ledger and result
Item contain completed UI requests. The live rule-script SHA-256 matches
`openhab/rules/feeder-owner.js` in the deployed checkout:

```text
730053e0f3245cb83461e3fe6e3b05d49c8b508631e8cdb4a889c8be8d915978
```

The same owner preserves triggerless `/runnow` execution for legacy Lightning
Goats callers. That compatibility path does not produce a correlated result for
the caller. It must not be reinterpreted as proof that physical feeding
completed merely because OpenHAB returned HTTP 200.

The exact browser write surface is:

```text
Direct bounded commands
- living_room_1_Switch
- living_room_2_Switch
- LED_living_room_1_Switch
- LivingRoomCircadian_Enable

Correlated owner requests
- NightLoadDevice_Request
- GoatFeeder_ManualRequest
- SouthOutlet_ManualRequest
- NightLoadOverride_Request
```

The browser is explicitly denied direct writes to the feeder, SouthOutlet,
override, dishwasher, Shureflo, and goat-camera actuator Items.

### 3. Three deployed household owner rules match the local source exactly

| Live rule | Purpose | Live status | Matching local SHA-256 |
|---|---|---|---|
| `88bd9ec4de` | Feeder owner | `IDLE` | `730053e0...d915978` |
| `hex_southoutlet_cycle` | SOC-gated SouthOutlet/greywater owner | `IDLE` | `512bba06...04f747d` |
| `hex_night_load_override` | Night-load owner | `IDLE` | `e7aed419...1d793` |

The live SouthOutlet rule is triggered by `DCData_Voltage`, `BMS_SOC`, and
`SouthOutlet_ManualRequest`. The live feeder rule is triggered by
`GoatFeeder_ManualRequest`. The live night-load rule is triggered by its two
request Items, `OverrideSwitch`, and a five-minute reconciliation schedule.

### 4. OpenHAB tooling has a version-guard drift

The authenticated live runtime reports OpenHAB `5.2.1`. The deployed UI's
`scripts/openhab-config.mjs` declares `SUPPORTED_OPENHAB_VERSION = '5.2.0'` and
uses exact equality in feeder snapshot preconditions. Any future managed
deployment must resolve and test this guard before applying changes; bypassing
it is not acceptable.

### 5. Mining is dormant in live state

No Item, Thing, rule, process, container, or systemd unit matching Avalon,
Bitaxe, or miner names was found in the live inventory. Mining repositories
contain real control examples, including `Miner_Power`, but they are not part
of the current operating system.

Do not import their telemetry, controls, lost-harvest analytics, or policy into
the active energy architecture.

### 6. AGM logic is absent from live OpenHAB but retained in PostgreSQL history

No live AGM-derived Items or rules were found. PostgreSQL's historical
`public.items` mapping still contains `BatterySoC_Calculated`,
`BatterySoC_CoulombCounter`, `Battery_Remaining_Ah`, and related AGM-era helper
Items. This is historical evidence, not current battery authority.

The live battery authority path is Discover/Schneider telemetry, including
`BMS_SOC`, `BMS_Comms_Status`, `DCData_Voltage`, and `DCData_Current`.

### 7. PostgreSQL is already the quantitative system of record

The OpenHAB JDBC database is PostgreSQL 16.14. The database timezone is UTC;
the house and OpenHAB runtime use America/Denver. At this snapshot it contains:

```text
public:        418 base tables
thermal_intel:   3 base tables
```

OpenHAB uses `public.items` to map Item names to per-Item history tables. The
timezone split makes local-day and DST tests mandatory before Stage 2 daily
aggregations.

No general energy analytics schema exists yet. `thermal_intel` is a focused
thermal-shadow subsystem and must not be conflated with the planned energy
analytics namespace.

### 8. External feeder consumers remain compatibility requirements

`lightning_goats_V2` and `middlware` both read `FeederOverride` and call:

```text
POST /rest/rules/88bd9ec4de/runnow
```

The local `lightning_goats.service` points at `/home/sat/bin/middleware`, but it
is disabled and inactive; port 8090 is closed. A deployment elsewhere cannot be
excluded from this host, so compatibility must remain until explicitly
resolved.

A newer repository, `lightning-goats/lightning-goats`, is an important
additional consumer omitted from the original repository map. Its standalone
Rust backend has implemented a serialized feeder ledger and ambiguous-outcome
handling, but its own status document says the existing LNbits production stack
remains authoritative and real canary/cutover work is still pending. It reads
`FeederOverride`, optionally reads a temperature Item, and calls a configured
OpenHAB rule's `/runnow` endpoint.

### 9. Existing scheduling must be extended, not duplicated

The user scheduler already runs:

- `openhab-sanity.timer` every ten minutes;
- `forecast-json.timer` every two hours;
- `forecast-intel.timer` daily;
- Hexmem ingest, snapshot, and outcome timers.

Stage 5 must audit and reuse these jobs before adding the proposed energy timer
set. The current system timer inventory contains no `energy-*` timers.

## Ownership and safety rules

1. BMS, inverter, charger, and protection hardware remain electrical safety
   authority.
2. OpenHAB owns live household integration and bounded deterministic actions.
3. PostgreSQL owns quantitative history.
4. `Solar_PV` owns canonical engineering meaning and cross-repository contracts.
5. Hexmem owns durable semantic conclusions, never telemetry or authorization.
6. `earthship-ui` presents state and sends only bounded/direct or correlated
   owner requests.
7. External feeder systems may use the preserved OpenHAB rule contract, but
   energy optimization may not alter feeding semantics.

## Stage 1 entry conditions

Stage 1 may reorganize `Solar_PV` documentation without changing live
interfaces. Before any later shared-interface change:

- reconcile or explicitly preserve the 34 deployed UI commits not on
  `origin/main`;
- fix and verify the OpenHAB 5.2.1 version guard in a separately approved UI
  change;
- preserve rule `88bd9ec4de`, `FeederOverride`, and the correlated feeder owner;
- resolve whether any external `lightning_goats_V2` or `middlware` deployment
  remains active;
- treat the standalone Rust Lightning Goats cutover as a separate program;
- preserve AGM PostgreSQL history while preventing AGM logic from appearing
  current;
- avoid duplicate scheduler ownership.

## Reproduction notes

The inventory used account-wide GitHub repository and code searches, shallow
temporary checkouts for evidence-bearing repositories, the deployed
`/home/sat/earthship-ui` checkout, authenticated read-only OpenHAB REST calls,
sanitized UI proxy reads, read-only PostgreSQL transactions, and read-only
systemd/process/container inspection.

No OpenHAB write endpoint, rule `/runnow` endpoint, database mutation, service
state change, or physical action was used.


## Stable energy analytics UI boundary

`Solar_PV` owns PostgreSQL analytics and publishes the closed
`earthship-energy-ui/v3` payload every five minutes with explicit qualified
power accounting. The v1/v2/v3 reader was deployed before the v3 publisher's
September 20 activation. OpenHAB hosts one observational String
Item, `Energy_Analytics_JSON`. `earthship-ui` consumes that Item through its
existing REST/SSE store, rejects payloads at or above 16 KiB and evidence older
than 15 minutes, and exposes no control from the analytics surface. Unknown
data remains explicit rather than becoming zero.

Historical version 2 preserves every version 1 field and meaning, and adds two nullable
battery fields sourced from the latest persisted `daily_battery` row:
`latestDepthOfDischargePct` is the 0--100 daily SoC range, and `latestEfc` is
the nonnegative daily energy-throughput EFC. Both are populated only when that
battery row has `quality=ok`; otherwise they are null and battery status is
degraded (or unavailable when there is no daily row). This remains
observational evidence, not a health measurement or an action authority.

Version 3 selects bounded latest revisions from `daily_power_snapshots`, never
falling back to legacy daily power totals. Its accounting object carries policy
`qualified_power_evidence_v1`, actual collection cutover, requested date window,
present/missing day counts, coverage and latest revision identity. EFC describes
observed qualified throughput in that window, not complete lifetime use. Legacy
cumulative EFC, unqualified AC-load balance and unsupported winter estimates are
withheld. A valid empty series exposes WAITING / No daily data with null totals.
The first natural completed-day write is due September 21; deployment does not
prove full-day coverage or improved accuracy. Exact UI contract and activation
receipts are in earthship-ui `docs/operations/2026-09-20-qualified-energy-ui-contract.md`
and `2026-09-20-power-production-activation.md`.

For contract rollback, restore the publisher first and verify its payload before
removing corresponding reader support. Preserve persisted revisions and history;
never silently label legacy totals as qualified accounting.

The publisher is the only state writer and may call only
`PUT /rest/items/Energy_Analytics_JSON/state`. The Item definition is now file-owned
from earthship-ui `openhab/file-config/items/energy-analytics.items`, installed at
`/etc/openhab/items/energy-analytics.items`. The old receipt-bound managed tool
refuses this noneditable resource; it cannot take ownership back through REST.
File-to-managed-to-file rollback was rehearsed for this Item with exact state
restore, unchanged JDBC mapping/history and no control changes. All other provider
transfers require their own inventory and verification; this does not qualify a
full restart or protected-control recovery.
This contract does not rename or reinterpret any feeder, greywater, night-load,
forecast, thermal, AGM-history, BMS, inverter, or charge-controller interface.


## Forecast detail input boundary

`Solar_PV` forecast snapshot capture supports exactly integer versions 1 and 2
of the OpenHAB forecast-detail payload. Version 1 snapshots retain
`forecast_version: 1` provenance. Version 2 snapshots retain
`forecast_version: 2` plus a validated, independent copy of
`temperatureAdjustment`; their metric values are the published corrected
forecast and must not be treated as raw Open-Meteo values or corrected again.

Both versions preserve `generatedAt` as the forecast issue time, the published
target timestamp as its validity time, and the existing snapshot persistence
key `(source, issued_at, valid_for, metric)`. Capture rejects malformed versions,
metadata, timestamps, and non-finite or nonnumeric recognized metric values
before persistence. The evidence inventory above remains the historical
2026-08-20 snapshot; this supported-input statement makes no deployment or
fresh-history claim.

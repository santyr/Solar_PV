# Stage 2 Live Energy Data Inventory

**Snapshot:** 2026-08-20
**Method:** authenticated/read-only OpenHAB REST, local JSONDB, protected JDBC
configuration parsed without printing secrets, read-only PostgreSQL queries,
systemd inventory, deployed source, and repository history.

## Storage and persistence

- PostgreSQL 16.14 database `openhab`; database timezone `Etc/UTC`.
- OpenHAB JDBC persistence is the only persistence service and uses
  `* : everyChange, restoreOnStartup` through UI-managed configuration.
- `public.items(itemid, itemname)` maps names to zero-padded raw tables such as
  Item 550 -> `public.item0550`.
- There are 418 public base tables plus three existing `thermal_intel` tables.
- Database size was about 15 GB. Largest high-rate tables were about 0.4–1.2
  GB each.
- Root storage had about 29 GB free (99% used). No active PostgreSQL/OpenHAB
  backup timer was found; the packaged `pg_basebackup@.timer` was disabled.

Because persistence is `everyChange`, the newest raw row is not itself a safe
freshness test when a sensor value remains constant. Analytics must use the
explicit BMS/Schneider freshness Items or documented source-health rules and
must carry the prior step value into a bounded window where appropriate.

No production schema migration is allowed until a compressed backup is stored
off the constrained root filesystem and an isolated restore is verified.

## Current authoritative sources

The machine-readable contract is
[`analytics/config/metric-sources.json`](../../analytics/config/metric-sources.json).
Key sources are:

| Metric | OpenHAB Item | Origin | Raw persistence observed | Status |
|---|---|---|---|---|
| Battery SOC | `BMS_SOC` | Discover via LYNK II, Schneider SunSpec 802, managed scaler | 15,826 rows, 2026-07-14 through snapshot | Current authority |
| Remaining capacity | `BMS_Capacity_Remaining_Ah` | Discover Battery Monitor map, Modbus unit 190 | 4,130 rows, 2026-07-14 through snapshot | Current |
| Battery temperature | `BMS_Temperature` | Discover Battery Monitor map, Modbus unit 190 | 572 changes, 2026-07-14 through snapshot | Current; Fahrenheit raw |
| DC voltage/current/power | `DCData_Native_*` | Schneider SunSpec 802 native scaler path | High-rate history from 2025-09-29 | Current; sign calibration required |
| PV input power | `MPPT60_PV_Power` | Schneider MPPT native Modbus, unit 30 | Item/table present | Current |
| PV output power | `MPPT60_DC_OutputPower` | Schneider MPPT native Modbus, unit 30 | Item/table present | Current |
| PV daily energy | `MPPT60_EnergyFromPV_Today` | Schneider MPPT native Modbus, unit 30 | Item/table present | Cross-check, not sole integration source |
| House AC power | `ConextGateway_ACPowerValue` | XW Pro through Conext Modbus | 18,874,413 rows from 2025-05-19 | Current |
| Irradiance | `AmbientWeatherWS2902A_SolarRadiation` | WS-2902A through local HTTP feed | Item/table present | Current |
| Outdoor temperature | `AmbientWeatherWS2902A_WeatherDataWs2902a_Temperature` | WS-2902A through local HTTP feed | Item/table present | Current; Fahrenheit raw |
| North Wall temperature | `AmbientWeatherWS2902A_WH31E_193_Temperature` | WH31E through weather station/local feed | Item/table present | Current; kiva-adjacent observational input |
| Dishwasher state | `Dish_Washer_Power` | TP-Link HS103 | 978 changes from 2025-05-19 | Active state only, no measured watts |
| Shurflo pump state | `ShurefloPump_Power` | TP-Link HS103 | 1,965 changes from 2025-05-19 | Active state only, no measured watts |

The live `BMS_Comms_Status` was `OK`, `BMS_DevicePresent` was `1`, and
Schneider freshness timestamps were current during the snapshot. These are
point-in-time checks, not guarantees.

## Known data gaps

- No live OpenHAB Items were found for BMS charge/discharge current limits,
  SOH, module cell spread, or BMS alarms/warnings.
- LYNK ACCESS remains USB/operator tooling; no safe automated per-module
  interface was established. Stage 2 therefore provides idempotent CSV import
  rather than touching the closed-loop network.
- The Philips Zigbee Thing `Motion Light Sensor` was ONLINE and exposes
  illuminance, occupancy, temperature, and battery channels, but had zero
  Item-channel links. It has no PostgreSQL history yet. Stage 3 must create
  stable managed Items, links, and persistence before shade inference work.
- Forecast Items expose current/latest forecasts. A Stage 2 snapshot job must
  preserve `issued_at` and `valid_for` before retrospective evaluation.
- Curtailment cannot yet be distinguished reliably from clouds, snow, MPPT
  limits, a full battery, or missing data.
- The exact Qcells model and PV string topology remain unverified, although
  the original quote identifies 12 × 350 W Qcells panels (4.2 kW) installed
  with the inverter and charge controller on 2021-08-06.

## Explicit exclusions

- `BatterySoC_Calculated`, `CoulombCounter`, and other AGM-derived Items are
  historical evidence only.
- Avalon, Bitaxe, and other mining artifacts are dormant and are not current
  loads, policy, telemetry, or scenario inputs.
- Schneider's legacy cycle counter is not accepted as lifecycle EFC.
- Inferred shade or kiva events are confidence-bearing observations only and
  cannot authorize control.

## Production gates

1. Off-root compressed backup plus verified isolated restore.
2. Current source resolution and type check.
3. DC current/power sign calibration against SOC direction and PV/load balance.
4. Independent aggregate comparison over bounded dates including a DST day.
5. Existing OpenHAB safety/freshness rules and feeder contracts unchanged.

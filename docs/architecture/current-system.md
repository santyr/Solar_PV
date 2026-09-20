# Current Earthship Electrical System

**Evidence baseline:** 2026-08-20 Stage 0 audit, supplemented by the
2026-08-19 operator handoff where explicitly labeled.

## Electrical topology

```text
PV array -> Schneider MPPT 60-150 -> 51.2 V DC bus
                                         |
4 x Discover AES 48-48-5120 -> Lynx Power In -> XW Pro 6848 -> 120/240 V loads
          |
          +-- AEbus -- LYNK II -- Xanbus -- XW Pro / MPPT / InsightHome
```

The four Discover modules operate in parallel. Each is 100 Ah / 5.12 kWh; the
bank is 400 Ah / 20.48 kWh nominal. Discover BMS limits and protection are
authoritative. Schneider devices provide inversion, charging, supervisory
protection, and local telemetry.

## Verified component inventory

| Component | Current state | Evidence status |
|---|---|---|
| Battery | 4 × Discover AES Rackmount 48-48-5120, LiFePO4 | Current handoff plus live BMS telemetry |
| Bank | 400 Ah / 20.48 kWh nominal | Model/count and live Schneider bank capacity |
| BMS gateway | LYNK II, AEbus battery side, Xanbus Schneider side | Commissioning record and live telemetry |
| Inverter | Schneider XW Pro 6848 NA, split phase | Live Thing/telemetry and repository record |
| Charge controller | Schneider MPPT 60-150 | Live Thing/telemetry and repository record |
| PV array | 12 × Qcells 350 W modules, 4.2 kW DC | Operator transcription from original quote, 2026-08-20 |
| Gateway | InsightHome / InsightLocal | Live Schneider integration |
| Automation | OpenHAB 5.2.1 | Authenticated live REST, 2026-08-20 |
| Persistence | PostgreSQL 16.14, database timezone UTC | Read-only live query, 2026-08-20 |
| House timezone | America/Denver | Live runtime |

Recently observed firmware from the 2026-08-19 operator handoff—not re-read
from device management during Stage 0—is battery `4.11.1.0`, LYNK II
`2.7.0.0`, LYNK ACCESS `2.7.0.0`, and XW Pro `2.04.00bn29`. Re-verify
these values before firmware-dependent work.

## PV array

- Twelve Qcells 350 W modules: **4.2 kW DC**.
- The array, XW Pro inverter, and MPPT charge controller were installed on
  **2021-08-06**.
- Tilt is intentionally optimized for winter solar gain.
- Snow is manually cleared promptly.

The repository used 4.2 kW consistently from its first README through early
2026. Commit `18f6f03` changed it to 4.8 kW as part of a broad prose rewrite,
without supporting evidence. The operator subsequently checked the original
quote and transcribed 12 Qcells modules at 350 W each, independently resolving
the total to 4.2 kW. Accordingly, 4.8 kW is rejected as unsupported.

The exact Qcells module model, series/parallel string configuration, conductor
details, and cold-voltage calculation remain **unverified evidence gaps**. The
count, per-module quote rating, total rating, and installation date are
operator-sourced original-quote facts; they have not been checked against a
quote image or field nameplate in this repository.

## Telemetry and automation

OpenHAB consumes Discover/Schneider data through local interfaces including
Modbus TCP. Current battery authority includes `BMS_SOC`,
`BMS_Comms_Status`, `DCData_Voltage`, and `DCData_Current`. PostgreSQL
stores quantitative OpenHAB history using `public.items` and per-Item tables.

OpenHAB may observe, alert, and execute bounded deterministic owner rules. It
does not replace BMS/inverter protection. The current browser sends only its
documented direct light/circadian commands and correlated owner requests; see
[cross-repository contracts](cross-repo-contracts.md).

## Software ownership

| Owner | Responsibility |
|---|---|
| Solar_PV | Engineering meaning, current architecture, history, roadmap |
| OpenHAB | Live integration, Items, Things, bounded automation |
| PostgreSQL | Quantitative telemetry and analytics |
| Codex | Evidence-backed analysis, implementation, reporting |
| Hexmem | Durable semantic conclusions with provenance |
| earthship-ui | Tablet-first presentation and bounded requests |

Mining is not active. AGM logic is historical. Neither belongs in current
telemetry, controls, policy, or UI.

## Observational learning lifecycle — September 19, 2026

The energy_analytics migration ledger is now1–4. Existing06:40 forecast
intelligence captures immutable advisory decisions/publication results through
a dedicated insert-only role, and assesses only fully completed20:00–11:00
trough windows using atomic BMS receipt history. Assessment cutover is
2026-09-20T00:48:40Z. A separate restricted assessor may append outcome/selection
records but cannot write raw telemetry. Original daily/forecast data fingerprints
and learned model state were unchanged at release. The old prematurely scored
trough-error display was retired to UNDEF pending qualified samples.

Temperature receipt collection and qualified hourly temperature learning were
also activated, using model/ID-bound observations and original receipt expiry.
Neither release changes BMS/Schneider safety authority, household controls,
advisory thresholds, notification policy, or everyChange persistence. First
natural captured origins/completed outcomes and qualified hourly updates still
require observation; installation is not a claim of learned improvement or
causal reward. See earthship-ui's September19 activation receipts.

## Known current gaps

- Capture the original PV quote or field nameplates; verify the exact Qcells
  model and string configuration.
- Re-verify firmware before firmware-sensitive maintenance.
- As of 2026-09-05, the general `energy_analytics` schema and reproducible daily
  products are established. Read-only production verification found 48
  `daily_battery` rows from 2026-07-19 through 2026-09-04 with minimum/maximum
  SoC, daily SoC range, daily EFC, and cumulative EFC. Publication of the two
  additional daily-use fields in the v2 UI payload was verified after
  reader-first deployment on 2026-09-05; values match the persisted day/epoch.
- Keep deployed earthship-ui commits reconciled with its remote before shared
  contract work; both repositories were merged and pushed for the September 5 release.
- Verify whether any external legacy Lightning Goats deployment remains.

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
| Gateway | InsightHome / InsightLocal | Live Schneider integration |
| Automation | OpenHAB 5.2.1 | Authenticated live REST, 2026-08-20 |
| Persistence | PostgreSQL 16.14, database timezone UTC | Read-only live query, 2026-08-20 |
| House timezone | America/Denver | Live runtime |

Recently observed firmware from the 2026-08-19 operator handoff—not re-read
from device management during Stage 0—is battery `4.11.1.0`, LYNK II
`2.7.0.0`, LYNK ACCESS `2.7.0.0`, and XW Pro `2.04.00bn29`. Re-verify
these values before firmware-dependent work.

## PV array

- Installed approximately 2021.
- Tilt is intentionally optimized for winter solar gain.
- Snow is manually cleared promptly.
- **Documented working rating: 4.2 kW DC.**

The repository used 4.2 kW consistently from its first README through early
2026. Commit `18f6f03` changed it to 4.8 kW as part of a broad prose rewrite,
without a module schedule, nameplate photo, invoice, or string diagram.
Accordingly, 4.8 kW is rejected as unsupported.

The exact module model/count, module-level nameplate sum, series/parallel string
configuration, conductor details, and cold-voltage calculation remain
**unverified evidence gaps**. Until an installation record or field survey is
captured, use 4.2 kW only as the documented planning rating—not as a verified
nameplate value.

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

## Known current gaps

- Field-verify PV modules, nameplate total, and string configuration.
- Re-verify firmware before firmware-sensitive maintenance.
- Build the general energy analytics schema and reproducible reports in Stage 2.
- Reconcile the deployed earthship-ui commits with its remote before shared
  contract work.
- Verify whether any external legacy Lightning Goats deployment remains.

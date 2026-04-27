# Solar Power System

This repository serves as the central knowledge base for the Schneider Electric solar energy system powering the residence.

## 📂 Documentation Index

### 1. Health & Maintenance (Current AGM Bank)

* **📄 [System Usage & Defect Analysis](System_Defect_Analysis.md)**
  + *Content:* **Engineering Report.** Telemetry data and photographic evidence linking installation defects (splices/resistance) to battery capacity loss. Includes Exhibits A-D.
* **📊 [Battery Health Dashboard](https://santyr.github.io/Solar_PV/battery_dashboard.html)**
  + *Content:* **Interactive live chart.** Per-battery voltage trends, spread tracking, and prognosis. Updated monthly with new readings.

### 2. Upgrade Strategy

* **🔋 [Battery Upgrade Plan](battery-upgrade-plan-rev2.md)** — **CURRENT**
  + *Content:* Active project plan for the **4-Unit Discover AES Rackmount** upgrade. Covers BOM, physical layout, Lynx Power In connection plan, installation timeline, autonomy analysis, and warranty terms. Reflects current supply chain conditions (April 2026) and CMS cost-share framework.
* **⚙️ [LYNK II Deployment Guide](lynk2-deployment-guide.md)** — **CURRENT**
  + *Content:* Step-by-step software configuration for LYNK II, XW Pro 6848, and MPPT 60-150. Includes jumper configuration for Schneider Xanbus, LYNK Network topology, LYNK ACCESS protocol selection, and complete InsightLocal settings (Battery Settings, BMS Comms-Loss Fallback, Charger Settings) for both inverter and charge controller.
* **📦 [Discover Lithium Upgrade](Discover-Lithium-Upgrade.md)** — *DEPRECATED*
  + *Content:* Earlier design using the Discover 950-0049 Battery Module Combiner. Superseded by the upgrade plan above. Retained for git history.

---

## ⚡ System Hardware Profile

* **Inverter:** Schneider Electric XW Pro 6848 NA 120/240 (Schneider P/N 865-8348-21)
* **Charge Controller:** Schneider MPPT 60-150
* **Gateway:** Schneider InsightHome (Xanbus network)
* **Solar Array:** 4.8 kW PV
* **Backup Power:** Winco PSS8 8 kW propane generator
* **Current Storage:** 48V Fullriver DC400-6 AGM (16× batteries, 8S2P, 830 Ah / ~40 kWh nominal) — failing
* **Planned Storage:** 4× Discover AES Rackmount 48-48-5120 (4P, 400 Ah / 20.48 kWh usable, closed-loop via LYNK II)
* **Load Profile:** ~4.9 kWh/day winter (worst case)
* **Monitoring:** InsightLocal + OpenHAB integration via Modbus TCP

---

## ⚙️ Critical Configuration Settings (SAFETY MODE)

*Status: Active as of Dec 25, 2025. Designed to protect imbalanced AGM batteries while awaiting replacement.*

| Parameter | Value | Reason |
| --- | --- | --- |
| **Battery Type** | **AGM** | |
| **Bulk / Absorption** | **57.6 V** | Reduced from original 58.8V to limit stress on weak cells |
| **Absorb Time** | **60 min** | Reduced to limit stress |
| **Float Voltage** | **54.6 V** | Standard maintenance |
| **High Battery Cut Out** | **64.0 V** | **Critical:** Prevents inverter tripping in cold temps |
| **Temp Compensation** | **Warm** | |

> **Note:** These settings will be replaced entirely once the Discover AES bank is commissioned. Closed-loop BMS will manage charge voltage, absorption time, and temperature compensation automatically. See the [LYNK II Deployment Guide](lynk2-deployment-guide.md) for the complete post-upgrade configuration.

---

## 📅 Action Plan Timeline

* **2026 Q1:** ✅ System defect analysis completed; warranty dispute opened with Colorado Mountain Solar (CMS)
* **2026 Q2 (in progress):** Coordinate Discover AES replacement with CMS
  + Cost-share framework: 86% CMS / 14% Shane (based on measured 88/625 EFC Fullriver utilization)
  + Hardware sourcing: Jonsson Tech ($1,350/module) — primary supplier given supply chain constraints
  + Installation: pending CMS scheduling
* **2026 Q2–Q3:** Execute lithium replacement and commissioning
  + Configure closed-loop BMS via LYNK II → Xanbus
  + Register warranty within 30 days of installation (10-year coverage)
  + Integrate BMS data into OpenHAB

# Solar Power System

This repository serves as the central knowledge base for the Schneider Electric solar energy system powering the residence.

## 📂 Documentation Index

### 1. Health & Maintenance (Current AGM Bank)
*   **📄 [System Usage & Defect Analysis](System_Defect_Analysis.md)**
    *   *Content:* **Engineering Report.** Telemetry data and photographic evidence linking installation defects (splices/resistance) to battery capacity loss. Includes Exhibits A-D.
*   **📄 [Fullriver Battery Lifecycle Analysis](Fullriver_Battery_Lifecycle_Analysis.md)**
    *   *Content:* Analysis of the current imbalance and the "Triage" plan to extend life to 2027.


### 2. Upgrade Strategy & Financials
*   **🔋 [Lightning Goats Lithium Upgrade](Lightning-Goats-Lithium-Upgrade.md)**
    *   *Content:* Technical specifications for the **5-Unit Discover AES Rackmount** upgrade, split-stack configuration, and installation logistics.

---

## ⚡ System Hardware Profile

*   **Inverter:** Schneider Electric XW6848+
*   **Charge Controller:** Schneider MPPT 60 150
*   **Solar Array:** 4.2 kW
*   **Current Storage:** 48V Fullriver DC400-6 AGM (830Ah)
*   **Load Profile:** ~5.3 kWh/day (House + Goats + Laptop + Fridge)

---

## ⚙️ Critical Configuration Settings (SAFETY MODE)

*Status: Active as of Dec 25, 2025. Designed to protect imbalanced batteries.*

| Parameter | Value | Reason |
| :--- | :--- | :--- |
| **Battery Type** | **AGM** | |
| **Bulk / Absorption** | **57.6 V** | Lowered from 58.8V to stop "High" batteries from venting. |
| **Absorb Time** | **60 min** | Reduced to limit stress. |
| **Float Voltage** | **54.6 V** | Standard maintenance. |
| **High Battery Cut Out** | **64.0 V** | **Critical:** Prevents inverter tripping in cold temps. |
| **Temp Compensation** | **Cold** | Adjusted for cellar temps (60°F - 70°F). |

---

## 📅 Action Plan Timeline

*   **Jan 2026:** Perform Manual Balancing on low batteries (#10, #4, #16, #5)?
*   **Quarterly:** Check voltage spread.
*   **2026-2027:** Possible Early End-of-Life / Lithium Upgrade?

# Lightning Goats Solar Power System

This repository serves as the central knowledge base for the Schneider Electric solar energy system powering the residence and the **Lightning Goats** infrastructure.

## 📂 Documentation Index

### 1. Health & Maintenance (Current AGM Bank)
*   **📄 [Fullriver Battery Lifecycle Analysis](Fullriver_Battery_Lifecycle_Analysis.md)**
    *   *Content:* Analysis of the current imbalance and the "Triage" plan to extend life to 2027.
*   **🔧 [Battery Balance & Triage Procedure](Battery_Balance_Check.md)**
    *   *Content:* Safety instructions for Quarterly checks and **Manual Balancing** using the NOCO charger.

### 2. Upgrade Strategy & Financials
*   **🔋 [Battery Replacement Strategy](Battery_Replacement_Strategy.md)**
    *   *Content:* Technical specs for the **5-Unit Discover AES Rackmount** upgrade (Split-Stack configuration).
*   **💰 [Economic ROI Analysis](Lightning_Goats_Battery_ROI.md)**
    *   *Content:* Financial breakdown of the upgrade, showing a 13.5-year payback via Goat Revenue.

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

*   **Jan 2026:** Perform Manual Balancing on low batteries (#10, #4, #16, #5).
*   **Quarterly:** Check voltage spread.
*   **Aug 2027:** Scheduled End-of-Life / Lithium Upgrade.

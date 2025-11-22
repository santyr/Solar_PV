# Lightning Goats Solar Power System

This repository serves as the central knowledge base for the Schneider Electric solar energy system powering the residence and the **Lightning Goats** infrastructure. It contains configuration history, health analysis, and strategic planning documents.

## 📂 Documentation Index

### 1. Health & Maintenance (Current AGM Bank)
*   **📄 [Fullriver Battery Lifecycle Analysis](Fullriver_Battery_Lifecycle_Analysis.md)**
    *   *Content:* Detailed assessment of the current DC400-6 AGM bank (installed Aug 2022). Includes the "Square Wave" health indicators and expected voltage behaviors for 2025–2029.
*   **🔧 [Quarterly Battery Balance Procedure](Battery_Balance_Check.md)**
    *   *Content:* Safety instructions and log sheet for checking individual 6V battery balance. **Critical maintenance** to prevent sudden bank failure.

### 2. Upgrade Strategy & Financials
*   **💰 [Economic ROI Analysis](Lightning_Goats_Battery_ROI.md)**
    *   *Content:* Breakdown of how the $1,000/year revenue from the Lightning Goats Feeder offsets the cost of a Lithium upgrade, turning the battery bank into a profit-generating asset.
*   **🔋 [2025+ Battery Replacement Strategy](Battery_Replacement_Strategy_2025.md)**
    *   *Content:* Technical specifications for the recommended **Discover AES (LiFePO4)** upgrade, including integration notes for the Schneider XW inverter and closed-loop communication.

---

## ⚡ System Hardware Profile

*   **Inverter:** Schneider Electric XW6848+
*   **Charge Controller:** Schneider MPPT 60 150
*   **Solar Array:** 4.2 kW
*   **Current Storage:** 48V Fullriver DC400-6 AGM (830Ah)
*   **Load Profile:** ~4.4 kWh/day (House + Goat Feeder)

---

## ⚙️ Critical Configuration Settings (Active)

*Updated Nov 21, 2025. Do not revert these without reviewing the Lifecycle Analysis.*

| Parameter | Setting | Reason |
| :--- | :--- | :--- |
| **Battery Type** | **AGM** | |
| **Bulk / Absorption** | **58.8 V** | Increased from 57.6V to remove sulfation. |
| **Float Voltage** | **54.6 V** | Manufacturer spec for Fullriver. |
| **High Battery Cut Out** | **64.0 V** | **Critical:** Prevents inverter tripping in cold temps. |
| **Temp Compensation** | **Cold** | Adjusted for cellar temps (64°F - 70°F). |
| **Max Charge Rate** | **15%** | ~60A-80A (Current limit of MPPT). |

---

## 📅 Recurring Tasks

*   **Daily:** Verify morning absorption reaches ~60V (due to temp comp).
*   **Quarterly:** Perform [Balance Check](Battery_Balance_Check.md).
*   **Annually:** Review "Lightning Goats" revenue vs. Battery ROI.

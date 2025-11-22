# Lightning Goats Solar Power System

This repository contains configuration documentation, health analysis, and upgrade strategies for the Schneider Electric solar energy system powering the residence and the "Lightning Goats" infrastructure.

## 📂 Document Index

### 1. Current System Health
*   **File:** `Fullriver_Battery_Lifecycle_Analysis.md`
*   **Description:** A detailed assessment of the existing Fullriver DC400-6 AGM battery bank (installed Aug 2022). Includes specific charging parameters to extend life through 2029 and a quarterly maintenance schedule.

### 2. Economic Analysis
*   **File:** `Lightning_Goats_Battery_ROI.md`
*   **Description:** Financial breakdown of the proposed Lithium upgrade. Analyzes how the $1,000/year revenue from the Goat Feeder offsets the hardware cost, resulting in a net-positive asset rather than a backup expense.

### 3. Upgrade Strategy
*   **File:** `Battery_Replacement_Strategy_2025.md`
*   **Description:** Technical recommendations for replacing the AGM bank with Schneider-integrated Lithium Iron Phosphate (LiFePO4) batteries. Focuses on the **Discover AES** system with Closed-Loop communication.

---

## ⚡ System Hardware Profile

*   **Inverter:** Schneider Electric XW6848+
*   **Charge Controller:** Schneider MPPT 60 150
*   **Solar Array:** 4.2 kW
*   **Current Storage:** 48V Fullriver DC400-6 AGM (830Ah)
*   **Load Profile:** ~4.4 kWh/day (House + Lightning Goats Feeder)

---

## ⚙️ Critical Configuration (Current AGM Bank)

*Settings updated Nov 21, 2025, to correct chronic undercharging.*

| Parameter | Value | Notes |
| :--- | :--- | :--- |
| **Battery Type** | AGM | Fullriver DC400-6 |
| **Bulk / Boost** | **58.8 V** | Increased from 57.6V to remove sulfation. |
| **Absorption** | **58.8 V** | |
| **Float** | **54.6 V** | |
| **High Battery Cut Out** | **64.0 V** | Set on Inverter to prevent cold-weather tripping. |
| **Temp Setting** | **Cold** | Matches cellar temp (64°F - 70°F). |

---

## 📅 Maintenance Schedule

*   **Daily:** Monitor for "Square Wave" absorption voltage (~60V) on sunny mornings.
*   **Quarterly (Jan/Apr/Jul/Oct):** Check individual 6V battery balance with multimeter while in Float.
*   **Target Upgrade Date:** 2028-2030 (Or sooner if revenue allows).

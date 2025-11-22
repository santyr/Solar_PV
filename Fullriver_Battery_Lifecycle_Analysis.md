# Fullriver DC400-6 Battery Analysis & Lifecycle Schedule
**Date:** November 22, 2025
**Status:** Active / Maintenance Phase

## 1. Asset Overview

*   **Battery Model:** Fullriver DC400-6 (AGM Deep Cycle)
*   **Bank Configuration:** 48V / 830Ah (Nominal)
*   **Installation Date:** August 2022
*   **Current Age:** 3 Years, 3 Months
*   **Daily Usage:** ~4.4 kWh (~11% of capacity)
*   **Discharge Floor:** ~49.0V (Never deep cycled)

---

## 2. Health Assessment (Current State)

**Verdict: Chemically Aged, Mechanically Pristine.**

Your batteries exist in a unique paradox due to the specific history of usage versus charging settings:

1.  **The "Chemical" Damage (Sulfation):**
    For the first 3 years (Aug 2022 – Nov 2025), the system was charged at **57.6V** instead of the required **58.8V**. This chronically undercharged the bank, likely causing hard sulfation crystals to form.
    *   *Estimated Capacity Loss:* 20% - 30%.
    *   *Effective Capacity:* Likely operating as a ~600Ah bank rather than 830Ah.

2.  **The "Mechanical" Preservation:**
    Despite the charging issue, the batteries were never discharged below roughly **93% State of Charge (SoC)**.
    *   *Physical Impact:* The lead plates have experienced almost zero expansion/contraction stress. There is likely no grid corrosion or active material shedding.

**Conclusion:** You have a "smaller tank" than you bought (due to sulfation), but the tank walls are solid. Because your daily energy needs are so low, this capacity loss has no functional impact on your operations.

---

## 3. Projected Lifecycle Schedule

Based on the correction of settings to **58.8V** on Nov 21, 2025, here is the expected timeline for the remainder of the battery life.

### Phase 1: The "Undercharge" Era (Aug 2022 – Nov 2025)
*   **Status:** Completed.
*   **Wear Level:** Moderate chemical degradation.
*   **Symptoms:** False "Float" status at 10:00 AM; voltage spikes on sunny mornings.

### Phase 2: The "Maintenance & Stability" Era (Nov 2025 – 2028)
*   **Status:** Current Phase.
*   **Expectation:** With the new 58.8V absorption setting, the "soft" sulfation will slowly break down. The battery performance will stabilize.
*   **Performance:** You will see voltage holding ~60V on cold mornings. The batteries will easily cover the 4.4 kWh nightly load without voltage sag.
*   **Risk Factor:** Low.

### Phase 3: The "Voltage Depression" Era (2029 – 2030)
*   **Status:** Future Decline.
*   **Expectation:** Internal resistance will naturally rise due to age.
*   **Symptoms:** The batteries will still hold energy, but the voltage will sag lower when heavy loads turn on (e.g., well pump + microwave).
*   **Action:** You may need to lower your "Low Battery Cut Out" settings slightly to prevent nuisance tripping during surges.

### Phase 4: End of Life (2030+)
*   **Status:** Retirement.
*   **Trigger:** A single battery cell will likely short or fail, causing the voltage of the whole bank to become erratic.
*   **Total Lifespan:** **7 to 9 Years.**

---

## 4. Critical Maintenance Settings (Do Not Change)

To ensure the schedule above holds true, these settings must remain locked in your Schneider Equipment:

| Setting | Value | Reason |
| :--- | :--- | :--- |
| **Bulk/Absorption Voltage** | **58.8 V** | Required to push past resistance/sulfation. |
| **Float Voltage** | **54.6 V** | Maintenance voltage for Fullriver AGM. |
| **High Batt Cut Out (Inverter)**| **64.0 V** | Prevents false alarms in cold weather. |
| **Charge Controller Temp** | **Cold** | Ensures higher voltage in your 64°F-70°F cellar. |

---

## 5. Quarterly "Health Check" Procedure

Since the bank is aging, you must watch for **Cell Imbalance**. This is the #1 killer of series-connected AGM banks.

**Every 3 Months (Jan / Apr / Jul / Oct):**
1.  Wait for the system to reach **Float** (mid-day).
2.  Use a multimeter to measure the voltage of each individual 6V battery.
3.  **Healthy:** All batteries are within **0.1V - 0.2V** of each other.
4.  **Warning Sign:** One battery is >0.5V lower or higher than the others.
    *   *If this happens, the end of life has arrived early.*

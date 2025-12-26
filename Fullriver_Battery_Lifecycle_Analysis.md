# Fullriver DC400-6 Battery Analysis & Lifecycle Schedule
**Date:** December 26, 2025
**Status:** **CRITICAL WATCH / TRIAGE MODE**

## 1. Asset Overview

*   **Battery Model:** Fullriver DC400-6 (AGM Deep Cycle)
*   **Bank Configuration:** 48V / 830Ah (Nominal) - 2 Parallel Strings
*   **Installation Date:** August 2022
*   **Current Age:** 3 Years, 4 Months
*   **Daily Usage:** ~5.3 kWh (~13% of capacity with Laptop/Fridge added)
*   **Discharge Floor:** ~50.2V (Extremely Shallow)

---

## 2. Health Assessment (Updated Dec 2025)

**Verdict: Severe Voltage Imbalance / Structural Degradation.**

While the daily performance appears stable due to light load, the individual battery voltages reveal a critical failure mode:

1.  **The "Loose Bolt" Discovery:**
    Loose connections found in Dec 2025 caused high resistance. This prevented specific batteries from charging for years, creating a "Drift" that the solar charger could not see or fix.
    
2.  **The Imbalance (0.94V Spread):**
    *   **"High" Batteries (>7.40V):** Have been chronically overcharged/boiled. Risk of venting/drying out is high.
    *   **"Low" Batteries (<6.50V):** Have been chronically undercharged. Severe hard sulfation is likely present.
    *   *Note:* A healthy spread is <0.20V. A spread of 0.94V indicates the bank is chemically fractured.

**Conclusion:** The bank is currently functioning only because the "Good" batteries (~7.0V) are carrying the load. The "Low" batteries are dead weight, and the "High" batteries are fragile.

---

## 3. Projected Lifecycle Schedule (Downgraded)

Based on the imbalance discovery, the previous estimate of 2030 has been revised.

### Phase 1: The "Silent Damage" Era (Aug 2022 – Dec 2025)
*   **Status:** Completed.
*   **Cause:** Incorrect settings (57.6V) + Loose Connections.
*   **Result:** Bank drifted apart. Sulfation hardened on low cells; Electrolyte loss occurred in high cells.

### Phase 2: The "Triage & Repair" Era (Jan 2026)
*   **Status:** **Upcoming Critical Phase.**
*   **Action:** Manual balancing required using NOCO Genius 5 charger on specific low batteries (#10, #4, #16).
*   **Goal:** Reduce spread to <0.30V.
*   **Success Scenario:** If balancing works, we return to Phase 3.
*   **Failure Scenario:** If balancing fails, we accelerate to Phase 4 immediately.

### Phase 3: The "Zombie" Era (2026 – Mid 2027)
*   **Status:** Likely Future.
*   **Expectation:** The bank will hold charge for your light loads, but capacity is permanently reduced (likely ~50% of nameplate).
*   **Risk:** One "High" battery may eventually dry out and fail open, or a "Low" battery may short.
*   **Lifespan:** The "Light Usage" (13% DoD) is the only thing keeping these alive.

### Phase 4: End of Life (August 2027)
*   **Status:** Planned Replacement.
*   **Trigger:** Voltage sag under load becomes noticeable, or a single cell short causes a voltage drop to <46V overnight.
*   **Total Lifespan:** **~5 Years.**

---

## 4. Critical Configuration Settings

**⚠️ CURRENT STATE: "SAFETY / TRIAGE" MODE**
*Use these settings NOW to prevent the 7.4V batteries from venting until manual balancing is complete.*

| Setting | Value | Reason |
| :--- | :--- | :--- |
| **Bulk/Absorption Voltage** | **57.6 V** | Lowered to stop "High" batteries from boiling. |
| **Absorb Time** | **60 min** | Reduced to limit stress duration. |
| **Float Voltage** | **54.6 V** | Standard maintenance. |
| **Temp Setting** | **Cold** | Correct for cellar. |

**✅ FUTURE STATE: "PERFORMANCE" MODE**
*Only revert to these settings IF the manual balancing succeeds and the spread is <0.20V.*

| Setting | Value | Reason |
| :--- | :--- | :--- |
| **Bulk/Absorption Voltage** | **58.8 V** | Required to desulfate Fullriver AGM. |
| **Absorb Time** | **150 min** | Standard saturation time. |

---

## 5. Manual Balancing Log (Triage Plan)

**Equipment:** NOCO Genius 5 (6V AGM Mode).
**Procedure:** Charge individual batteries while system is in Float.

**Priority Targets (The "Lows"):**
1.  **Battery #10:** (Last measured 6.47V) - **CRITICAL**
2.  **Battery #4:**  (Last measured 6.50V) - **CRITICAL**
3.  **Battery #16:** (Last measured 6.52V) - **CRITICAL**
4.  **Battery #5:**  (Last measured 6.60V) - *Secondary Target*

*After charging these, wait 24 hours and re-measure the whole bank. If Highs drop to <7.1V, the system is stabilized.*

# System Usage & Battery Health Analysis
**Site:** 283 High Peaks Ranch Road
**Date:** January 3, 2026
**System Age:** 4 Years, 4 Months (Installed Aug 2021)

## Executive Summary
This engineering report documents the premature failure of the Fullriver DC400-6 battery bank. The data conclusively proves that the failure is not due to normal wear and tear, as the system has utilized less than **7%** of its rated cycle life.

The root cause is identified as **Installation & Commissioning Negligence**. Multiple NEC Code Violations (Exhibits A & B) introduced high resistance into the charging circuit, while failure to program the inverter settings (Exhibit C) caused chronic undercharging. This combination resulted in severe **Voltage Imbalance** (Exhibit D) and physical damage to the battery bank (Exhibit E).

---

## SECTION 1: INSTALLATION DEFECTS & CODE VIOLATIONS

### Exhibit A: Main Conductor Splices
**Source Files:**
*   [PXL_20220809_132948559.jpg](photos/PXL_20220809_132948559.jpg) (Exposed Splice - Reported 2022)
*   [PXL_20251227_151536430.jpg](photos/PXL_20251227_151536430.jpg) (Junction Box Splice)

**Defect:** Multiple mechanical splices on main 4/0 AWG battery cables.
**Analysis:**
1.  **Exposed Splice:** A single conductor splice located outside of a junction box.
    *   **Violation:** **NEC 300.15** requires a box or conduit body at each conductor splice point.
2.  **Impact:** Mechanical splices on high-amperage charging circuits introduce electrical resistance. This causes a voltage drop, creating a "blind spot" where the Inverter reads "Full" (e.g., 58.8V) while the batteries physically receive a lower voltage, leading to chronic undercharging.

### Exhibit B: Safety & Workmanship Violations
**Source File:** [Terminal_Detail_Defects.jpg](photos/Terminal_Detail_Defects.jpg)

**Defect:** Systematic omission of safety guarding and corrosion protection.
**Analysis:**
1.  **Unguarded Live Parts:** Every battery terminal is fully exposed. The manufacturer-supplied safety caps were omitted, and no industry-standard rubber boots were provided for the 4/0 lugs.
    *   **Violation:** **NEC 110.27(A)** requires guarding of live parts >50V. **NEC 110.3(B)** requires installation per manufacturer instructions.
2.  **Lack of Corrosion Protection:** No anti-oxidant grease is visible.
    *   **Violation:** **NEC 110.12** (Workmanship). Failure to inhibit corrosion accelerates resistance buildup, exacerbating the voltage drop issues cited in Exhibit A.

### Exhibit C: Improper Commissioning (Configuration)
**Source Files:**
1. [Commissioning_Day_Zero.png](photos/Commissioning_Day_Zero.png) (Aug 22, 2021 - **Installation Day**)
2. [Configuration_Audit_Nov2025.png](photos/Configuration_Audit_Nov2025.png) (Nov 2025 - Discovery)

**Defect:** Failure to program Inverter/Charger with manufacturer-required parameters. This incorrect configuration persisted from the very first hour of operation (Day 1) through Year 4.

**Analysis:**
The telemetry reveals that the system was commissioned using "Factory Default" settings rather than the specific charge profile required by the battery warranty.
*   **Day 1 Failure (Aug 22, 2021):** The charge cycle peaked at **~57.6V** (Generic AGM Default) instead of the required **58.8V**.
*   **Missing Temp Compensation:** The temperature setting was left on **"Warm"** despite the unheated battery box location, preventing the necessary voltage boost during winter charging.

---

## SECTION 2: PHYSICAL DAMAGE & SYMPTOMS

### Exhibit D: Critical Voltage Imbalance
**Source:** Manual Multimeter Readings (Dec 2025)
**Defect:** Severe divergence in individual battery voltages during Charge cycle.

**Analysis:**
Direct measurement of the 16 individual battery units revealed a catastrophic voltage spread:
*   **Highest Battery:** **7.42 V** (Over-Voltage)
*   **Lowest Battery:** **6.48 V** (Under-Voltage)
*   **Total Spread:** **0.94 Volts**

**Conclusion:**
A healthy series bank should have a spread of **<0.20V**.
The resistance from the wiring defects (Exhibit A) prevented the charger from equalizing the bank. The charger pushed current to satisfy the "Low" batteries, forcing the "High" batteries dangerously past their 7.35V maximum limit, directly causing the venting documented in Exhibit E.

### Exhibit E: Evidence of Venting
**Source File:** [Battery_Venting_Evidence.jpg](photos/Battery_Venting_Evidence.jpg)

**Defect:** Acid residue and discoloration on battery casings.
**Analysis:**
Visual inspection reveals dark residue accumulating on battery tops. This is consistent with **Electrolyte Venting**.
*   **Correlation:** This physical evidence aligns perfectly with the voltage data in Exhibit D. The batteries reading **7.42V** were forced to vent sulfuric acid mist due to the charger over-driving them against the resistance of the circuit.

---

## SECTION 3: USAGE TELEMETRY (DEFENSE)

### Exhibit F: Lifetime Battery Discharge
**Source File:** [Lifetime_Energy_Use.png](photos/Lifetime_Energy_Use.png)
**Data Point:** **3.2 MWh (3,200 kWh)** Lifetime Discharge

**Analysis:**
*   **Rated Cycle Life (Fullriver Spec):** ~1,250 Cycles @ 50% Depth of Discharge.
*   **Usage Math:** $3,200 \text{ kWh} \div 40 \text{ kWh (Capacity)} = \mathbf{80 \text{ Equivalent Full Cycles}}$.
*   **Verdict:** The system has utilized only **6.4%** of its rated mechanical life. The batteries are not "worn out."

### Exhibit G: Solar Production & Pass-Through
**Source Files:** [Inverter_Performance_History.png](photos/Inverter_Performance_History.png), [Solar_Production_History.png](photos/Solar_Production_History.png)

**Analysis:**
*   **Total Solar Harvest:** ~8.8 MWh.
*   **Net Surplus:** **+1.6 MWh** (Production > Consumption).
*   **Verdict:** The system is Energy Positive. The failure was not caused by lack of solar supply or heavy usage.

### Exhibit H: Diagnostic Intervention (Safety Mode)
**Source File:** [Safety_Mode_Response.png](photos/Safety_Mode_Response.png)
**Data Point:** Dec 28, 2025 (Safety Mode)

**Analysis:**
Upon discovery of the imbalance (Exhibit D), the Owner attempted to apply the correct 58.8V Fullriver profile. This immediately triggered "High Voltage" alarms because the imbalance is now structurally severe.
*   **Mitigation:** The system was reverted to a "Safety Mode" (57.6V) to stop the venting.
*   **Current State:** The attached chart shows the batteries accepting charge with a smooth current taper. This proves the **chemistry is still active** and not "dead" from old age or overuse. However, the bank is **structurally failed** because it cannot be safely charged to full voltage without venting the high cells.

---

## Final Determination

### Root Cause Attribution
The failure is definitively attributed to **Installation & Commissioning Defects**.
1.  **Exhibit A (Wiring):** Illegal splices introduced resistance.
2.  **Exhibit B (Workmanship):** Lack of corrosion protection/guarding.
3.  **Exhibit C (Configuration):** Factory default settings chemically starved the batteries.

These factors combined to create the **Critical Voltage Imbalance (Exhibit D)**, which caused specific batteries to vent (Exhibit E) while others sulfated, resulting in the premature failure of a system that is mechanically young (Exhibit F).

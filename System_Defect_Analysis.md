# System Usage & Battery Health Analysis
**Date:** December 31, 2025
**System Age:** 4 Years, 4 Months (Installed Aug 2021)

## Executive Summary
This engineering report documents the premature failure of the Fullriver DC400-6 battery bank. The data conclusively proves that the failure is not due to normal wear and tear, as the system has utilized less than **7%** of its rated cycle life.

The root cause is identified as **Installation Negligence**. Multiple NEC Code Violations (Exhibits A & B) introduced high resistance into the charging circuit. This resistance prevented proper voltage regulation, resulting in severe imbalance and physical damage to the battery bank (Exhibit C).

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

---

## SECTION 2: PHYSICAL DAMAGE

### Exhibit C: Evidence of Venting
**Source File:** [Battery_Venting_Evidence.jpg](photos/Battery_Venting_Evidence.jpg)

**Defect:** Acid residue and discoloration on battery casings.
**Analysis:**
Visual inspection reveals dark residue accumulating on battery tops. This is consistent with **Electrolyte Venting**.
*   **Mechanism:** The resistance from Exhibit A caused the charger to misread the bank voltage. While trying to overcome this resistance, the charger over-drove specific "High" batteries past their gassing threshold (7.35V), causing them to vent sulfuric acid mist.
*   **Conclusion:** The installation defects directly caused physical loss of electrolyte, permanently damaging the battery chemistry.

---

## SECTION 3: USAGE TELEMETRY (DEFENSE)

### Exhibit D: Lifetime Battery Discharge
**Source File:** [Lifetime_Energy_Use.png](photos/Lifetime_Energy_Use.png)
**Data Point:** **3.2 MWh (3,200 kWh)** Lifetime Discharge

**Analysis:**
*   **Rated Cycle Life (Fullriver Spec):** ~1,250 Cycles @ 50% Depth of Discharge.
*   **Usage Math:** $3,200 \text{ kWh} \div 40 \text{ kWh (Capacity)} = \mathbf{80 \text{ Equivalent Full Cycles}}$.
*   **Verdict:** The system has utilized only **6.4%** of its rated mechanical life. The batteries are not "worn out."

### Exhibit E: Solar Production & Pass-Through
**Source Files:** [Inverter_Performance_History.png](photos/Inverter_Performance_History.png), [Solar_Production_History.png](photos/Solar_Production_History.png)

**Analysis:**
*   **Total Solar Harvest:** ~8.8 MWh.
*   **Total Home Consumption:** ~7.2 MWh.
*   **Net Surplus:** **+1.6 MWh**.
*   **Pass-Through:** Over 55% of home loads were powered directly by solar, bypassing the batteries entirely.
*   **Verdict:** The system is Energy Positive. The batteries were not undercharged due to lack of sun or heavy usage; they were undercharged because the wiring defects (Exhibit A) restricted the flow of this abundant energy.

### Exhibit F: Current Chemical Response
**Source File:** [Safety_Mode_Response.png](photos/Safety_Mode_Response.png)
**Data Point:** Dec 28, 2025 (Safety Mode)

**Analysis:**
Following the discovery of the defects, charging voltage was lowered to 57.6V to stop the venting seen in Exhibit C. The resulting charge curve shows a smooth current taper.
*   **Verdict:** The battery chemistry is active and responsive. The batteries are not "dead" from old age; they are simply imbalanced and damaged by the resistance in the circuit.

---

## Final Determination
The data is conclusive:
1.  **Usage:** Negligible (80 Cycles).
2.  **Supply:** Abundant (+1.6 MWh Surplus).
3.  **Root Cause:** **Installation Defects.** The combination of illegal splices (Exhibit A) and poor workmanship (Exhibit B) created high resistance. This resistance unbalanced the bank, causing some batteries to sulfate and others to vent (Exhibit C), resulting in premature failure of a barely-used system.

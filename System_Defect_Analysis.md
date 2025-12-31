# System Usage & Battery Health Analysis
**Date:** December 31, 2025
**System Age:** 4 Years, 4 Months (Installed Aug 2021)

## Executive Summary
Telemetry data exported from the Schneider InsightLocal gateway confirms that the Fullriver DC400-6 battery bank has experienced negligible wear and tear over its service life (<7% cycle usage). The current battery failure is not due to consumption.

The failure is directly attributable to **Installation Defects** and **Code Violations** (Exhibits A & G) which introduced high resistance into the charging circuit. This resistance confused the charging logic, causing severe voltage imbalances that physically damaged the battery bank via chronic undercharging of some units and acute overcharging/venting of others (Exhibit F).

---

## Exhibit A: Main Conductor Defects
**Source Files:**
*   [PXL_20220809_132948559.jpg](photos/PXL_20220809_132948559.jpg) (Exposed Splice - Reported 2022)
*   [PXL_20251227_151536430.jpg](photos/PXL_20251227_151536430.jpg) (Junction Box Splice - Found 2025)

**Defect Identified:** Multiple mechanical splices on main 4/0 AWG battery cables.

### Analysis
The main DC path between the battery bank and the inverter contains unauthorized mechanical splices:
1.  **Exposed Splice:** A single conductor splice located outside of a junction box/enclosure.
    *   **Code Violation:** **NEC 300.15** requires a box or conduit body at each conductor splice point. Exposed single conductors are subject to physical damage and environmental stress.
2.  **Junction Box Splice:** A secondary mechanical connection inside the pull box.

**Failure Mechanism (Voltage Drop):**
Standard electrical theory dictates that mechanical splices on high-amperage circuits introduce electrical resistance. This resistance causes a voltage drop, creating a discrepancy between the voltage measured by the Inverter and the actual voltage at the battery terminals. This "Blind Spot" prevents the system from properly saturating the battery bank.

---

## Exhibit B: Lifetime Battery Discharge
**Source File:** [Lifetime_Energy_Use.png](photos/Lifetime_Energy_Use.png)
**Data Point:** **3.2 MWh (3,200 kWh)** Lifetime Discharge

### Analysis
*   **Rated Cycle Life (Fullriver Spec):** ~1,250 Cycles @ 50% Depth of Discharge.
*   **Usage Math:** $3,200 \text{ kWh} \div 40 \text{ kWh (Capacity)} = \mathbf{80 \text{ Equivalent Full Cycles}}$.

**Conclusion:**
Over 4.5 years, the system has cycled the equivalent of only **80 times** (6.4% of rated life). The failure is not caused by cycle wear.

---

## Exhibit C: Inverter Performance & Pass-Through
**Source File:** [Inverter_Performance_History.png](photos/Inverter_Performance_History.png)
**Data Point:** **~7.2 MWh** Lifetime DC Energy Out

### Analysis
*   **Total Energy Delivered to Home:** ~7.2 MWh
*   **Difference (Solar Pass-Through):** **4.0 MWh** (55% of total).

**Conclusion:**
For the majority of the system's life, the batteries have been sitting in "Float" (Idle) mode. They are not being stressed by heavy daily loads.

---

## Exhibit D: Solar Production History
**Source File:** [Solar_Production_History.png](photos/Solar_Production_History.png)
**Data Point:** **~8.8 MWh** Lifetime DC Energy Produced

### Analysis
*   **Net Surplus:** **+1.6 MWh** (Production > Consumption).

**Conclusion:**
The system is "Energy Positive." The batteries were not undercharged due to lack of sunlight; energy supply was abundant.

---

## Exhibit E: Current Battery Response (Safety Mode)
**Source File:** [Safety_Mode_Response.png](photos/Safety_Mode_Response.png)
**Data Point:** Daily Charge Cycle (Dec 28, 2025)

### Analysis
Following the discovery of the spliced cables, the system charging parameters were temporarily lowered to a "Safety Mode" (57.6V Limit). The charge curve shows a smooth current taper, indicating that the battery chemistry remains active and responsive. The batteries are not chemically "dead" from old age; they are simply unable to remain balanced due to the resistance from the wiring defects.

---

## Exhibit F: Physical Evidence of Venting
**Source File:** [Battery_Venting_Evidence.jpg](photos/Battery_Venting_Evidence.jpg)
**Defect Identified:** Acid residue and discoloration on battery casings.

### Analysis
Visual inspection reveals dark brown/black residue accumulating on the battery tops and between the casings.
*   **Mechanism:** This residue is consistent with **Electrolyte Venting** (Acid Mist). When a VRLA (Sealed) battery is forced to an over-voltage state, the internal pressure valves release gas containing sulfuric acid.
*   **Correlation:** This aligns with voltage measurements where specific "High" batteries reached **7.42V** (exceeding the 7.35V max spec) due to the resistance-induced imbalance.

---

## Exhibit G: Safety & Workmanship Violations
**Source File:** [Terminal_Detail_Defects.jpg](photos/Terminal_Detail_Defects.jpg)
**Defect Identified:** Missing terminal guards and lack of corrosion protection.

### Analysis
1.  **Missing Terminal Covers:** The red/black safety caps provided by the manufacturer were not installed on the battery terminals.
    *   **Code Violation:** **NEC 110.27(A)** requires that live parts operating at 50 volts or more be guarded against accidental contact. (System charging voltage is ~59V).
2.  **Lack of Corrosion Protection:** No anti-oxidant grease or spray is visible on the lead terminals.
    *   **Workmanship Issue:** **NEC 110.12** requires electrical equipment to be installed in a neat and workmanlike manner. Failure to apply corrosion inhibitors to lead-acid terminals accelerates resistance buildup, contributing to the voltage drop issues cited in Exhibit A.

## Final Determination
The telemetry data refutes any claim that the battery bank has been "worn out." Usage is negligible (<6% DoD daily).

**Root Cause Attribution:**
The failure is attributed to **Installation Defects**.
1.  **High-Resistance Splices (NEC 300.15 Violation):** Prevented accurate voltage sensing and proper charging.
2.  **Lack of Guarding/Protection (NEC 110.27 Violation):** Exacerbated terminal corrosion and safety risks.
3.  **Resulting Imbalance:** Caused the system to chronically undercharge some units (sulfation) while simultaneously overcharging others (venting/drying out), destroying the bank despite light usage.

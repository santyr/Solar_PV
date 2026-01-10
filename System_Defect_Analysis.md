# System Defect & Battery Bank Health Analysis
**Date:** January 3, 2026  
**System Age:** 4 Years, 4 Months (Installed Aug 2021)  
**Status:** **CRITICAL WATCH / TRIAGE MODE**

---

## Executive Summary

This report documents abnormal degradation and unsafe operating behavior in a **Fullriver DC400-6 AGM battery bank**. The evidence supports four key findings:

1. **Severe unit-to-unit imbalance exists** across the individual 6V batteries (measured spread **0.94 V**), consistent with a bank that cannot be safely charged as a single system without **overcharging some units** while **undercharging others**.
2. The system recorded a **DC Over Voltage (Event 49)** alarm on **Nov 21, 2025**, consistent with the inverter/charger approaching its **High Battery Cut Out** threshold during charging.
3. The installation exhibits **workmanship and safety defects** (splices/junction practices in high-current conductors, unguarded >50 V terminals, incomplete termination protection) that plausibly increase resistance and hazard.
4. Commissioning/configuration appears **inconsistent with the manufacturer’s recommended charge profile**, which can drive chronic partial state-of-charge and sulfation over time.

### Primary Determination (supported)
The battery bank is in a **critical, structurally imbalanced state** and should be treated as **triage mode** until either:
- (a) imbalance is reduced and charge behavior is validated under measurement, or
- (b) the bank is replaced.

### Root Cause Attribution (supported, with one required verification test)
The most likely contributors are:
- **Incorrect commissioning/configuration** relative to the manufacturer’s charge profile and temperature compensation, and
- **connection/termination defects** (including splices and/or loose/high-resistance joints).

A definitive assignment of causality to *connection resistance vs battery deterioration* requires one missing measurement: **voltage-drop testing under charge current** (see Section 8).

---

## 1) Asset Overview

- **Battery Model:** Fullriver DC400-6 (AGM Deep Cycle)
- **Bank Configuration (reported):** 48V / ~830Ah nominal, **2 parallel strings**
- **Battery Installation Date:** Aug 2021
- **Daily Usage (reported):** ~5.3 kWh
- **Discharge Floor (reported):** ~50.2V (shallow)

> Note: Energy/cycle calculations in this report assume ~40 kWh nominal bank energy (48V × 830Ah ≈ 39.8 kWh). If nameplate differs, recalc method is provided in Section 6.

---

## 2) Manufacturer Requirements (Fullriver DC400-6)

Fullriver’s DC400-6 datasheet specifies (at 25 °C / 77 °F):

- **48V Bulk/Absorption:** **58.8 V**  
- **48V Float:** **54.6 V**  
- **Temperature effects:** The recommended charge voltage varies with battery temperature (see datasheet).  

**Important system note:** This site’s Schneider configuration uses a **fixed “Warm/Cold” mode** (not true per-degree temperature compensation). Therefore, the chosen mode must be matched to the **measured battery-box temperature range**.

**Battery-box temperature (measured, 2-week sample):** approximately **60–78°F**, with most operation around **~63–75°F**.

**Implication:** Selecting an overly “Warm” assumption when the box is typically cooler can contribute to undercharge; selecting an overly “Cold” assumption can raise charge voltage and may increase overvoltage/venting risk in an already-imbalanced bank.

**Datasheet reference:**  
- Local copy in this repo: **[Fullriver DC400-6 Datasheet (PDF)](DC400-6.pdf)**

---

## 3) Installation Defects & Safety Issues (Field Evidence)

### Exhibit A: Main Conductor Splices / Junction Practices

**Source files:**
- [PXL_20220809_132948559.jpg](photos/PXL_20220809_132948559.jpg) (Exposed splice – reported 2022)
- [PXL_20251227_151536430.jpg](photos/PXL_20251227_151536430.jpg) (Junction box splices – Dec 2025)

**Finding:** Multiple mechanical splices exist on high-current battery conductors.

**Engineering impact:**  
Mechanical splices and non-ideal junction practices can increase resistance and create localized heating/voltage drop. If the inverter/charger regulates to its own DC terminal voltage (rather than true battery-post voltage), extra resistance between charger and battery posts can reduce the effective charging voltage delivered to the bank during high current—contributing to chronic undercharge and string divergence.

**Code note (jurisdiction dependent):** Splices outside approved enclosures may violate NEC requirements for splices in boxes (often cited under NEC 300.15, context dependent).

---

### Exhibit B: Safety & Workmanship Violations

**Source file:** [Terminal_Detail_Defects.jpg](photos/Terminal_Detail_Defects.jpg)

**Findings:**
- **Unguarded live parts:** exposed terminals/lugs in a >50 V system.
- **Termination protection/corrosion control:** not evident in the photo set (boots/caps, protective coverings, corrosion inhibitor).

**Engineering impact:**  
- Increases shock/arc risk.
- Increases likelihood of resistance growth over time, worsening charge accuracy and imbalance.

**Code note (jurisdiction dependent):** Commonly implicated: NEC 110.27(A) (guarding) and NEC 110.12 / 110.3(B) (workmanship / install per listing & instructions).

---

## 4) Commissioning & Configuration (Telemetry Evidence)

### Exhibit C: Improper Commissioning (Charge Profile / Temperature Profile)

**Source files:**
1. [Commissioning_Day_Zero.png](photos/Commissioning_Day_Zero.png) (Aug 22, 2021 – Day 1)
2. [Configuration_Audit_Nov2025.png](photos/Configuration_Audit_Nov2025.png) (Nov 2025 – discovery)

**Finding:** Telemetry indicates the system charging peaks at **~57.6 V** rather than the datasheet’s **58.8 V** (at 25°C). Additionally, the system uses a fixed **“Warm/Cold”** temperature assumption; prior configuration indicates it was left on **“Warm.”** Measured battery-box temperatures (~60–78°F over a 2-week sample) suggest the appropriate selection should be confirmed based on the actual environment.

**Engineering impact:**  
Long-term operation below recommended absorb voltage/time and with an incorrect **Warm/Cold temperature assumption** can cause:
- chronic partial state-of-charge,
- sulfation,
- capacity loss,
- increased unit-to-unit divergence.

> Note: Charge voltage alone is not the whole story—absorb **time at voltage**, actual **battery temperature**, and **where voltage is sensed** are also critical.

---

## 5) Observed Symptoms & Damage

### Exhibit D: System Alarms (Trigger Event)

**Source file:** (InsightLocal Events screenshot; Nov 21, 2025)  
**Finding:** **DC Over Voltage (Event 49)** recorded on **Nov 21, 2025**.

**Interpretation:**  
This alarm indicates battery voltage approached a cut-out threshold during charging. This is consistent with charging into an imbalanced bank, incorrect cut-out thresholds, temperature/profile mismatch, and/or sensing artifacts under current.

---

### Exhibit E: Critical Voltage Imbalance (Direct Measurement)

**Source:** manual multimeter readings (Dec 2025)

**Finding:** Divergence across 6V units:
- **Highest:** **7.42 V**
- **Lowest:** **6.48 V**
- **Spread:** **0.94 V**

**Interpretation:**  
A spread of this magnitude indicates the bank is **chemically and electrically divergent**. In this condition:
- raising system charge voltage risks **overcharging high units** (venting/dry-out),
- while low units remain **undercharged** (hard sulfation/capacity loss).

---

### Exhibit F: Evidence Consistent with Venting

**Source file:** [Battery_Venting_Evidence.jpg](photos/Battery_Venting_Evidence.jpg)

**Finding:** discoloration/residue consistent with electrolyte mist venting.

**Interpretation:**  
Visual evidence alone is not proof, but paired with the measured high unit voltages and overvoltage events, venting is a credible explanation.

---

## 6) Usage Telemetry & Cycle-Life Position (Corrected)

### Exhibit G: Lifetime Battery Discharge

**Source file:** [Lifetime_Energy_Use.png](photos/Lifetime_Energy_Use.png)

**Reported value:** **3.2 MWh (3,200 kWh)** lifetime discharge.

**Equivalent Full Cycles (EFC):**  
Assuming ~40 kWh nominal bank energy:

- **EFC ≈ 3,200 kWh ÷ 39.8 kWh ≈ 80 EFC**

**Comparison to “1,250 cycles @ 50% DoD”:**  
A rating of ~1,250 cycles at 50% DoD corresponds to ~**625 EFC** of energy throughput (because each 50% cycle delivers ~0.5 EFC). Therefore:

- **80 / 625 ≈ 12.8%** of rated energy-throughput life (order-of-magnitude: **~10–15%**, depending on true capacity and counter validity).

**Conclusion (supported, now accurate):**  
If the lifetime counter is correct and the capacity assumption is correct, the bank appears to have used only a modest fraction of rated throughput life. This supports the hypothesis that the observed failure mode is not primarily “normal wear,” but rather driven by configuration and/or connection/installation defects.

> Verification note: Some dashboards reset counters or mix time windows; confirm via CSV export and/or inverter history.

---

### Exhibit H: Solar Production & Pass-Through

**Source files:**
- [Inverter_Performance_History.png](photos/Inverter_Performance_History.png)
- [Solar_Production_History.png](photos/Solar_Production_History.png)

**Finding (reported):** total solar harvested ~8.8 MWh; apparent net surplus.

**Conclusion:**  
The system does not appear supply-starved. The failure mode is more consistent with **charge-control/connection/temperature** issues than with heavy cycling.

---

### Exhibit I: Diagnostic Intervention (Safety Mode)

**Source file:** [Safety_Mode_Response.png](photos/Safety_Mode_Response.png)

---

### Exhibit J: Battery-Box Temperature (Operational Context)

**Source:** Owner temperature logging (2-week sample)

**Finding:** Battery-box air temperature ranged approximately **60–78°F**, typically **~63–75°F**.

**Interpretation:** The battery environment is generally near room temperature, so temperature-driven voltage corrections are modest most days. However, because the Schneider configuration uses a **fixed “Warm/Cold”** assumption rather than per-degree compensation, confirming the correct mode remains important—especially when attempting to apply a higher absorb target in an already imbalanced bank.


**Finding:** Applying a higher absorb target (e.g., 58.8 V) immediately aggravates overvoltage behavior; lowering the cap (~57.6 V) yields smoother taper.

**Interpretation (defensible form):**  
This behavior is **consistent with** charging into an imbalanced bank and/or voltage sensing/drop effects under current. It strongly indicates the bank cannot be safely driven to the datasheet absorb target **without first addressing imbalance and validating sensing/termination under measurement**. It does not, by itself, prove that wiring resistance is the sole cause.

---

## 7) Final Determination

### Determination
The battery bank is **critically imbalanced** and operating in a condition where:
- some units are at risk of **overcharge/venting**, and
- other units are likely **chronically undercharged** and sulfated.

### Most likely contributors (ranked)
1. **Incorrect charge profile / temperature configuration** relative to the Fullriver datasheet.
2. **High-resistance connections and junction practices**, including splices and/or loose/poorly protected terminations.
3. Secondary contributors may include unit variation, early battery defect(s), and thermal/environmental stresses.

---

## 8) Required Verification Tests (to make causality “proven”)

To convert “consistent with/likely” into “proven,” perform:

1) **Voltage-drop test under charge current**
   - During absorb at meaningful current, measure:
     - **V_inv:** inverter DC input terminals
     - **V_bank:** battery bank posts
   - Record charge current **I**.
   - Compute ΔV = V_inv − V_bank. A significant ΔV under current indicates resistance/sensing issues.

2) **Millivolt drop per joint/splice**
   - Under the same current, measure mV drop across each splice/lug to locate hotspots.

3) **Per-battery conductance/IR + controlled discharge**
   - Distinguishes “undercharged but recoverable” from “sulfated/failing.”

---

## 9) Immediate Mitigation (Triage)

Until imbalance is reduced and charging is validated:

- Keep conservative charge settings to avoid overdriving “high” units.
- Reduce charge current where possible.
- Correct safety hazards (terminal guards/boots, enclosures, torque verification, cleaning/retorque, corrosion inhibition where appropriate).

> **Safety note:** Any per-battery “manual balancing” should be done only with the target 6V battery electrically isolated from the bank (to avoid unintended current paths and charging errors).

---

## References

- **Fullriver DC400-6 Datasheet (PDF):** [DC400-6.pdf](DC400-6.pdf)

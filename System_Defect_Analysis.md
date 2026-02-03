# System Defect & Battery Bank Health Analysis
**Date:** January 3, 2026 (updated February 3, 2026)  
**System Age:** 4 Years, 6 Months (Installed Aug 2021)  
**Status:** **END-OF-LIFE / REPLACEMENT REQUIRED**

**Canonical repo version:** https://github.com/santyr/Solar_PV/blob/main/System_Defect_Analysis.md  
**Interactive dashboard:** https://santyr.github.io/Solar_PV/battery_dashboard.html

---

## Executive Summary

This report documents abnormal degradation and unsafe operating behavior in a **Fullriver DC400-6 AGM battery bank**. The evidence supports four key findings:

1. **Unit-to-unit imbalance exists** across the individual 6V batteries (measured spread **0.94 V** in Dec 2024, now **0.44 V** in Feb 2026), consistent with a bank that cannot be safely charged as a single system without **overcharging some units** while **undercharging others**.
2. The system recorded a **DC Over Voltage (Event 49)** alarm on **Nov 21, 2025**, consistent with the inverter/charger approaching its **High Battery Cut Out** threshold during charging.
3. The installation exhibits **workmanship and safety defects** (splices/junction practices in high-current conductors, unguarded >50 V terminals, incomplete termination protection) that plausibly increase resistance and hazard.
4. Commissioning/configuration appears **inconsistent with the manufacturer's recommended charge profile**, which can drive chronic partial state-of-charge and sulfation over time.
5. **As of February 2026, 4 of 16 batteries (25%) are effectively dead** (stuck at ≤6.49 V at float), up from 3 in December 2025. The degradation front is widening and the bank is not recoverable.

### Primary Determination (supported)
The battery bank has reached **end-of-life** due to irreversible sulfation and chemical divergence. Replacement should be executed within **2–4 months** (by Q2 2026) before overnight capacity becomes unreliable or a sudden string failure causes an unplanned outage.

### Root Cause Attribution (supported, with one required verification test)
The most likely contributors are:
- **Incorrect commissioning/configuration** relative to the manufacturer's charge profile and temperature compensation, and
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

Fullriver's DC400-6 datasheet specifies (at 25 °C / 77 °F):

- **48V Bulk/Absorption:** **58.8 V**  
- **48V Float:** **54.6 V**  
- **Temperature compensation:** charge voltage should be adjusted with temperature (see datasheet for factor and basis).

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
Mechanical splices and non-ideal junction practices may increase resistance and create localized heating/voltage drop. If the inverter/charger regulates to its own DC terminal voltage (rather than true battery-post voltage), extra resistance between charger and battery posts can reduce the effective charging voltage delivered to the bank during high current—contributing to chronic undercharge and string divergence.

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

**Finding:** Telemetry indicates the system charging peaks at **~57.6 V** rather than the datasheet's **58.8 V** (at 25°C). Additionally, audit evidence suggests the system temperature profile was left on a "Warm" mode despite a cooler battery environment (reported).

**Engineering impact:**  
Long-term operation below recommended absorb voltage/time and with incorrect temperature compensation can cause:
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

**Additional Finding:** The historical log also shows three more DC Over Voltage (Event 49) alarms in December 2025:

- 2025-12-02 12:25:46 -0700
- 2025-12-06 14:42:52 -0700
- 2025-12-06 15:23:35 -0700



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

**Comparison to "1,250 cycles @ 50% DoD":**  
A rating of ~1,250 cycles at 50% DoD corresponds to ~**625 EFC** of energy throughput (because each 50% cycle delivers ~0.5 EFC). Therefore:

- **80 / 625 ≈ 12.8%** of rated energy-throughput life (order-of-magnitude: **~10–15%**, depending on true capacity and counter validity).

**Conclusion (supported, now accurate):**  
If the lifetime counter is correct and the capacity assumption is correct, the bank appears to have used only a modest fraction of rated throughput life. This supports the hypothesis that the observed failure mode is not primarily "normal wear," but rather driven by configuration and/or connection/installation defects.

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

**Finding:** Applying a higher absorb target (e.g., 58.8 V) immediately aggravates overvoltage behavior; lowering the cap (~57.6 V) yields smoother taper.

**Interpretation (defensible form):**  
This behavior is **consistent with** charging into an imbalanced bank and/or voltage sensing/drop effects under current. It strongly indicates the bank cannot be safely driven to the datasheet absorb target **without first addressing imbalance and validating sensing/termination under measurement**. It does not, by itself, prove that wiring resistance is the sole cause.

---

### Exhibit K: Torque Correction — Measured Improvement in Voltage Spread

**Source:** Owner manual multimeter readings (handwritten log; transcribed)

**Files:**
- Transcription (CSV): [handwritten_voltage_readings_transcribed.csv](handwritten_voltage_readings_transcribed.csv)
- Summary stats (CSV): [handwritten_voltage_readings_stats.csv](handwritten_voltage_readings_stats.csv)

**Context:** In Dec 2025 the owner found multiple battery lugs noticeably loose and re-torqued the battery connections. The final column in the log reflects readings **after torquing**.

**Summary (16 batteries):**

| Measurement set | Min (V) | Max (V) | Spread (V) |
|---|---:|---:|---:|
| 2025-12-24 (set A) | 6.48 | 7.42 | 0.94 |
| 2025-12-24 (set B) | 6.47 | 7.33 | 0.86 |
| 2025-12-26 (after torque) | 6.47 | 7.22 | 0.75 |

**Interpretation:** After torque correction, the bank's measured voltage spread tightened by approximately **0.19 V** (0.94 → 0.75, ~20% reduction) and the highest observed unit voltage decreased (7.42 → 7.22). This is consistent with connection integrity (loose/high-resistance joints) materially affecting observed charging/imbalance behavior. It does not by itself prove the spliced run is the sole root cause, but it strongly supports performing and documenting a full termination audit and voltage-drop testing under charge current.

---

### Exhibit L: February 2026 Follow-Up — Accelerating Degradation

**Source:** Owner manual multimeter readings (Feb 3, 2026)  
**Conditions:** Float (~54.6 V bank) after ≥2 hours idle. Same method as Dec 2025 readings.

**Interactive dashboard:** [Battery Health Dashboard](https://santyr.github.io/Solar_PV/battery_dashboard.html)

**Per-battery readings (all at float):**

| Battery | Dec 24 A | Dec 26 (torqued) | Feb 3, 2026 | Change (Dec 26 → Feb 3) | Status |
|---:|---:|---:|---:|---:|:---|
| 1 | 6.89 | 6.66 | 6.57 | −0.09 | WEAK |
| 2 | 7.22 | 6.87 | 6.73 | −0.14 | OK |
| 3 | 6.91 | 6.81 | 6.70 | −0.11 | OK |
| 4 | 6.53 | 6.50 | 6.47 | −0.03 | ⛔ FAILED |
| 5 | 7.09 | 6.60 | 6.47 | −0.13 | ⛔ FAILED |
| 6 | 7.42 | 7.12 | 6.89 | −0.23 | OK |
| 7 | 7.31 | 7.16 | 6.86 | −0.30 | OK |
| 8 | 7.25 | 7.06 | 6.85 | −0.21 | OK |
| 9 | 7.12 | 6.95 | 6.85 | −0.10 | OK |
| 10 | 6.48 | 6.47 | 6.49 | +0.02 | ⛔ FAILED |
| 11 | 7.26 | 7.02 | 6.86 | −0.16 | OK |
| 12 | 7.40 | 7.22 | 6.91 | −0.31 | OK |
| 13 | 7.21 | 6.95 | 6.84 | −0.11 | OK |
| 14 | 7.29 | 7.00 | 6.87 | −0.13 | OK |
| 15 | 6.80 | 6.77 | 6.65 | −0.12 | WEAK |
| 16 | 6.49 | 6.52 | 6.49 | −0.03 | ⛔ FAILED |

**Summary statistics:**

| Measurement set | Min (V) | Max (V) | Spread (V) | Mean (V) | Failed (≤6.49 V) |
|---|---:|---:|---:|---:|---:|
| 2025-12-24 (set A) | 6.48 | 7.42 | 0.94 | 7.04 | 2 |
| 2025-12-26 (after torque) | 6.47 | 7.22 | 0.75 | 6.86 | 3 |
| **2026-02-03** | **6.47** | **6.91** | **0.44** | **6.75** | **4** |

**Key findings:**

1. **Spread reduction is misleading.** The drop from 0.94 V to 0.44 V is not recovery — it reflects the formerly high-resistance batteries (e.g., #6: 7.42 → 6.89, #12: 7.40 → 6.91) settling back toward normal after torque correction. The *minimum* voltage has not moved (6.47–6.49 V across all measurement sets).

2. **A fourth battery has failed.** Battery #5 dropped from 6.60 V (Dec 26) to 6.47 V (Feb 3), crossing from "weak" into the same voltage floor as batteries #4, #10, and #16. The degradation front is widening.

3. **The weak batteries are not recoverable.** Their voltage floor has been stuck at 6.47–6.49 V for over 6 weeks across all measurement sets. This indicates hard sulfation — the plates cannot accept charge.

4. **Mean voltage is declining.** 7.04 → 6.86 → 6.75 V across the three measurement periods, indicating the bank is losing capacity overall, not just at the extremes.

5. **Estimated remaining usable capacity:** ~50–60% of original (20–24 kWh). At 5.3 kWh/day this still covers overnight loads in good weather, but the margin is thin and shrinking.

**Prognosis:**
- **Gradual path:** Bank becomes functionally inadequate (cannot reliably cover overnight) within **2–4 months**. Essentially useless within 9–12 months.
- **Sudden path (higher risk):** Any of the four failed batteries develops an internal short, dropping its series string and forcing the remaining parallel string to carry full load at twice the discharge current. This can cascade to total bank failure with no warning.
- **Recommendation:** Execute lithium replacement (Discover AES 48-48-5120) by **Q2 2026**. See [Lithium Upgrade Plan](Discover-Lithium-Upgrade.md).

---

## 7) Final Determination

### Determination
The battery bank is **imbalanced** and operating in a condition where:
- some units are at risk of **overcharge/venting**, and
- other units are likely **chronically undercharged** and sulfated.

As of February 2026, **4 of 16 batteries (25%) have reached irreversible failure**, and the degradation front is actively widening. The bank has reached end-of-life at only **~13% of rated cycle throughput**.

### Most likely contributors (ranked)
1. **Incorrect charge profile / temperature configuration** relative to the Fullriver datasheet.
2. **High-resistance connections and junction practices**, including splices and/or loose/poorly protected terminations.
3. Secondary contributors may include unit variation, early battery defect(s), and thermal/environmental stresses.

---

## 8) Required Verification Tests (to make causality "proven")

To convert "consistent with/likely" into "proven," perform:

1) **Voltage-drop test under charge current**
   - During absorb at meaningful current, measure:
     - **V_inv:** inverter DC input terminals
     - **V_bank:** battery bank posts
   - Record charge current **I**.
   - Compute ΔV = V_inv − V_bank. A significant ΔV under current indicates resistance/sensing issues.

2) **Millivolt drop per joint/splice**
   - Under the same current, measure mV drop across each splice/lug to locate hotspots.

3) **Per-battery conductance/IR + controlled discharge**
   - Distinguishes "undercharged but recoverable" from "sulfated/failing."

---

## 9) Immediate Mitigation (Triage)

Until imbalance is reduced and charging is validated:

- Keep conservative charge settings to avoid overdriving "high" units.
- Reduce charge current where possible.
- Correct safety hazards (terminal guards/boots, enclosures, torque verification, cleaning/retorque, corrosion inhibition where appropriate).
- **Monitor monthly.** Take per-battery float readings under consistent conditions (≥2 hr float, no loads). Watch for any battery dropping below **6.3 V** at float — this indicates a likely internal short and should be treated as urgent.

> **Safety note:** Any per-battery "manual balancing" should be done only with the target 6V battery electrically isolated from the bank (to avoid unintended current paths and charging errors).

---

## References

- **Fullriver DC400-6 Datasheet (PDF):** [DC400-6.pdf](DC400-6.pdf)
- **Battery Health Dashboard:** [battery_dashboard.html](https://santyr.github.io/Solar_PV/battery_dashboard.html)
- **Lithium Upgrade Plan:** [Discover-Lithium-Upgrade.md](Discover-Lithium-Upgrade.md)

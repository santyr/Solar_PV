# System Defect & Battery Bank Health Analysis
**Date:** January 3, 2026 (updated February 9, 2026)  
**System Age:** 4 Years, 6 Months (Installed Aug 2021)  
**Status:** **END-OF-LIFE / REPLACEMENT REQUIRED**

**Canonical repo version:** https://github.com/santyr/Solar_PV/blob/main/System_Defect_Analysis.md  
**Interactive dashboard:** https://santyr.github.io/Solar_PV/battery_dashboard.html

---

## Executive Summary

This report documents abnormal degradation and unsafe operating behavior in a **Fullriver DC400-6 AGM battery bank**. The evidence supports five key findings:

1. **Unit-to-unit imbalance exists** across the individual 6V batteries (measured spread **0.94 V** in Dec 2025, now **0.44 V** in Feb 2026), consistent with a bank that cannot be safely charged as a single system without **overcharging some units** while **undercharging others**.
2. The XW inverter event log recorded **three DC Over Voltage (Event 49) alarms** in December 2025 — on Dec 2 and twice on Dec 6 — after the owner raised the absorb voltage to the manufacturer-specified 58.8V. MPPT charger telemetry confirms sustained overvoltage events (60.2V on Nov 22, 60.6V on Dec 24) consistent with the inverter approaching its **High Battery Cut Out** threshold during charging.
3. The installation exhibits **workmanship and safety defects** (splices/junction practices in high-current conductors, unguarded >50 V terminals, incomplete termination protection) that plausibly increase resistance and hazard.
4. Commissioning/configuration was **inconsistent with the manufacturer's recommended charge profile** from installation through April 2025 — a period of 3 years and 8 months. Telemetry from **nine sample dates** confirms the system ran on Schneider factory-default settings (57.6V absorb vs. the required 58.8V) throughout this period, driving chronic partial state-of-charge and sulfation.
5. **As of February 2026, 4 of 16 batteries (25%) are effectively dead** (stuck at ≤6.49 V at float), up from 3 in December 2025. The degradation front is widening and the bank is not recoverable.

### Primary Determination (supported)
The battery bank has reached **end-of-life** due to irreversible sulfation and chemical divergence. Replacement should be executed within **2–4 months** (by Q2 2026) before overnight capacity becomes unreliable or a sudden string failure causes an unplanned outage.

### Root Cause Attribution (supported, with one required verification test)
The most likely contributors are:
- **Incorrect commissioning/configuration** relative to the manufacturer's charge profile and temperature compensation, maintained at factory defaults for 3 years 8 months, and
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
1. [Commissioning_Day_One.png](photos/Commissioning_Day_One.png) (Aug 7, 2021 – first full day of operation)
2. [Configuration_Audit_Nov2025.png](photos/Configuration_Audit_Nov2025.png) (Nov 2025 – discovery)
3. MPPT charger telemetry CSV exports from nine dates: Aug 7/9/10 2021, Feb 1 2022, Feb 1 2023, Feb 1 2024, Feb 1 2025, Apr 11 2025, Apr 12 2025

**Finding:** The system was left on Schneider XW+ factory-default charge settings at installation. Telemetry from **nine sample dates spanning 3 years and 8 months** (Aug 7, 2021 through Apr 11, 2025) confirms the absorb voltage **never once reached even the 57.6V factory-default setpoint** — let alone the Fullriver-specified 58.8V:

| Date | Float (V) | Absorb Peak (V) | Minutes ≥ 57.6V |
|------|-----------|-----------------|-----------------|
| Aug 7, 2021 | 53.3 | 57.25 | **0** |
| Aug 9, 2021 | 53.4 | 57.01 | **0** |
| Aug 10, 2021 | 53.4 | 57.17 | **0** |
| Feb 1, 2022 | 53.5 | 57.22 | **0** |
| Feb 1, 2023 | 53.5 | 57.16 | **0** |
| Feb 1, 2024 | 53.5 | 57.16 | **0** |
| Feb 1, 2025 | 53.8 | 57.50 | **0** |
| **Apr 11, 2025** | **53.8** | **57.48** | **0** |
| **Apr 12, 2025** | **54.8** | **59.19** | **18** |

On April 12, 2025 — 3 years and 8 months after installation — the owner first adjusted charge settings while building OpenHAB monitoring software and reading the Fullriver spec sheet. The float was raised from ~53.8V to ~54.8V (closer to the Fullriver-specified 54.6V), and a brief absorb test reached 59.19V. The fact that the bank overshot to 59.19V when ~58.8V was targeted indicates battery imbalance was **already present** at this point — the same pattern that would later manifest more severely as 60.2V (Nov 22) and 60.6V (Dec 24).

The float voltage was also below the Fullriver specification for the entire factory-default period: ~53.3–53.8V measured vs. the specified 54.6V. Additionally, audit evidence suggests the system temperature profile was left on a "Warm" mode despite a cooler battery environment (reported site elevation ~7,000 ft), meaning the batteries needed *even more* voltage than 58.8V.

**Engineering impact:**  
Long-term operation below recommended absorb voltage/time and with incorrect temperature compensation can cause:
- chronic partial state-of-charge,
- sulfation,
- capacity loss,
- increased unit-to-unit divergence.

> Note: Charge voltage alone is not the whole story—absorb **time at voltage**, actual **battery temperature**, and **where voltage is sensed** are also critical. However, the telemetry shows the system never reached even the *setpoint* voltage on any factory-default sample date, indicating the absorb phase was being terminated prematurely — likely due to low current triggers or timer limits combined with the sub-spec voltage target.

---

## 5) Observed Symptoms & Damage

### Exhibit D: System Alarms (Trigger Event)

**Source file:** InsightLocal Events > Historical (screenshot, Dec 27, 2025)

**Finding:** The XW inverter event log shows exactly **three DC Over Voltage (Event 49) alarms**, all occurring after the owner raised the absorb voltage to the Fullriver-specified 58.8V in late November 2025:

| Date/Time | Event | ID |
|-----------|-------|----|
| 2025-12-02 12:25:46 -0700 | DC Over Voltage | 49 |
| 2025-12-06 14:42:52 -0700 | DC Over Voltage | 49 |
| 2025-12-06 15:23:35 -0700 | DC Over Voltage | 49 |

**MPPT charger telemetry context:** The charger-side telemetry provides additional detail on the overvoltage behavior:

| Date | Absorb Setting | Peak Voltage | Minutes ≥ 60V | Context |
|------|---------------|-------------|---------------|---------|
| Nov 21, 2025 | 57.6V (original) | 57.56V | 0 | Last day at factory-default absorb — normal operation |
| Nov 22, 2025 | 58.8V (corrected) | **60.20V** | **50** | First day at corrected absorb — immediate overvoltage |
| Dec 24, 2025 | 58.8V (corrected) | **60.59V** | **51** | Worsening — higher peak, longer duration |
| Dec 25, 2025 | ~57.4V (lowered) | 57.45V | 0 | Owner lowered absorb as safety measure |

**Interpretation:**  
The alarms and overvoltage events only occurred after the absorb voltage was raised to the manufacturer-specified value. This does **not** indicate the owner caused the damage — it indicates the bank was **already too damaged** to accept the correct charge voltage. The damaged (sulfated) batteries cannot absorb their share of the charge current, forcing voltage onto the healthier batteries in the same series string. The worsening trajectory (59.19V in Apr → 60.20V in Nov → 60.59V in Dec) confirms the imbalance is accelerating.

The owner was forced to lower the absorb voltage back to ~57.4V to keep the system running safely — not because 57.6V is the correct setting, but because the bank is too far gone for the correct settings to work.

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

**Finding:** Applying the manufacturer-specified absorb target (58.8V) causes the bank to spike to 60V+ within minutes; lowering the absorb to ~57.4V yields smoother operation but perpetuates the chronic undercharge that caused the damage.

**Interpretation (defensible form):**  
This behavior is **consistent with** charging into an imbalanced bank where sulfated batteries cannot accept charge current. The bank cannot be safely driven to the datasheet absorb target without overcharging the healthy batteries. This is characteristic of **irreversible sulfation damage** — the bank is trapped between two harmful states:
- Correct voltage → overvoltage/venting on healthy units
- Reduced voltage → continued undercharge/sulfation on all units

The overvoltage trajectory is worsening over time: 59.19V (Apr 2025) → 60.20V (Nov 2025) → 60.59V (Dec 2025), indicating accelerating divergence between healthy and damaged batteries.

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
1. **Incorrect charge profile / temperature configuration** relative to the Fullriver datasheet — maintained at Schneider factory defaults for 3 years and 8 months (Aug 2021 through Apr 2025), confirmed by telemetry from nine sample dates showing the absorb voltage never reached even the 57.6V setpoint.
2. **High-resistance connections and junction practices**, including splices and/or loose/poorly protected terminations.
3. Secondary contributors may include unit variation, early battery defect(s), and thermal/environmental stresses.

### Owner configuration changes (transparency note)
The owner first adjusted charge settings on **April 12, 2025** — 3 years and 8 months after installation — while building OpenHAB monitoring software and reviewing the Fullriver specification sheet. The float voltage was raised from ~53.8V to ~54.8V (closer to the Fullriver-specified 54.6V), and a brief absorb test was conducted. In late November 2025, the owner raised the absorb voltage to the Fullriver-specified 58.8V, which triggered the overvoltage events documented in Exhibit D. These changes did not cause the battery damage — the damage was caused by 3+ years of chronic undercharging at factory-default settings. The owner's attempts to correct the voltage to the manufacturer's specification **revealed** the existing damage; they did not create it.

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

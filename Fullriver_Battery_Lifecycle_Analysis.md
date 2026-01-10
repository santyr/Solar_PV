# Fullriver DC400-6 Battery Bank — Condition Summary & Lifecycle Outlook
**Date:** December 26, 2025  
**Status:** **CRITICAL WATCH / TRIAGE MODE**  
**Related system report (canonical):** https://github.com/santyr/Solar_PV/blob/main/System_Defect_Analysis.md

---

## 1. Asset Overview

- **Battery Model:** Fullriver DC400-6 (AGM Deep Cycle)  
- **Bank Configuration:** 48V / ~830Ah (Nominal) — **2 parallel strings** (16× 6V units)  
- **Installation Date:** **August 2021** (same as system install)  
- **Current Age (as of Dec 26, 2025):** ~4 years, 4 months  
- **Typical Daily Usage:** ~5.3 kWh (≈13% of ~40 kWh nominal)  
- **Typical Discharge Floor:** ~50.2V (shallow cycling)

---

## 2. Health Assessment (Updated Dec 2025)

**Assessment: Significant voltage imbalance requiring triage.**

Daily performance can appear stable under light loads, but individual 6V measurements show a large spread that increases the risk of **overcharging some units** while **undercharging others**.

### A) Connection integrity findings (Dec 2025)
In Dec 2025, multiple battery connections were found noticeably loose and were re-torqued. After torquing, measured voltage spread improved:

- **12/24/25:** max **7.42V**, min **6.48V**, spread **0.94V**  
- **12/26/25 (after torquing):** max **7.22V**, min **6.47V**, spread **0.75V**

**Interpretation:** The improvement after torquing suggests connection integrity (and therefore resistance at joints/terminations) materially affects observed imbalance. This does not, by itself, prove the root cause, but it supports a full termination audit and voltage-drop testing under charge current.

### B) Current imbalance level
Even with improvement, a spread of **0.75V** across 6V units is still substantial. In this condition:

- **Higher-voltage units** may approach overcharge/venting risk sooner during absorb.  
- **Lower-voltage units** may remain chronically undercharged, increasing the likelihood of sulfation and capacity loss.

**Working conclusion:** The bank is operating in a state where “whole-bank” charging is difficult to optimize safely until imbalance is reduced and wiring/termination losses are verified.

---

## 3. Operational Indicators (Overvoltage Events)

Historical logging shows multiple **DC Over Voltage (Event 49)** alarms, including a trigger event in Nov 2025 and additional events in Dec 2025 (three events visible in the December log).

**Interpretation:** Repeated overvoltage events are consistent with an imbalanced bank and/or voltage sensing/drop artifacts under current. This supports prioritizing:
- **V_inv vs V_bank voltage-drop testing** under charge current, and  
- **millivolt-drop testing** across splices/lugs to identify hotspots.

---

## 4. Projected Lifecycle Outlook (Revised, with uncertainty)

Because imbalance and possible overcharge/undercharge conditions were observed, long-horizon life estimates should be treated as uncertain until the system is stabilized and tested.

### Phase 1: Normal operation with emerging imbalance (Aug 2021 – 2024/2025)
- **Status:** Historical period.  
- **Notes:** Light cycling likely reduced wear, but long-term imbalance can still develop due to configuration, temperature assumption, and/or connection quality.

### Phase 2: Triage & Stabilization (late 2025 – early 2026)
- **Status:** Current.  
- **Goals:**  
  - confirm/repair wiring and terminations,  
  - document voltage-drop under charge current,  
  - verify configuration against manufacturer requirements, and  
  - return to stable charge behavior without recurring alarms.

### Phase 3: Degraded-but-serviceable period (2026 – TBD)
- **Status:** Possible.  
- **Expectation:** If imbalance is reduced and charging is stable, the bank may continue to support light loads, though some permanent capacity loss is possible.

### Phase 4: Replacement planning (date TBD)
Replacement timing should be based on measured performance rather than an assumed date. Typical triggers:
- noticeably increased voltage sag under normal loads,  
- inability to reach/hold appropriate absorb behavior without alarms,  
- recurring large spread that does not improve after corrective work, or  
- a failed unit (short/open) impacting string voltage.

---

## 5. Charging / Configuration Notes

### Key manufacturer reference (Fullriver DC400-6)
At 25°C / 77°F, Fullriver guidance is typically:
- **48V Absorb/Bulk:** **58.8V**  
- **48V Float:** **54.6V**

### Important site-specific note: temperature mode is a fixed assumption
This Schneider setup uses **fixed “Warm/Cold”** mode (not true per-degree temperature compensation). Battery-box temperature measurements over a 2-week sample show approximately **60–78°F** (often ~63–75°F).

**Implication:** The Warm/Cold selection should be aligned to actual conditions. Choosing an overly “Warm” assumption can contribute to undercharge; choosing an overly “Cold” assumption can raise charge voltage and may increase overvoltage/venting risk in an already imbalanced bank.

---

## 6. Current Conservative Settings (Triage Mode)

**Goal:** Minimize further stress while the system is being evaluated and stabilized.

| Setting | Value | Purpose |
| :--- | :--- | :--- |
| **Bulk/Absorption Voltage** | **57.6 V** | Conservative cap while imbalance is present (reduces risk of pushing high units too hard). |
| **Absorb Time** | **60 min** | Limits time at elevated voltage during triage. |
| **Float Voltage** | **54.6 V** | Standard maintenance float reference. |
| **Temp Setting** | **Warm/Cold (fixed)** | Verify selection against measured battery-box temps (~60–78°F sample). |

### Returning toward higher absorb voltage
Only consider moving toward the manufacturer absorb target (e.g., **58.8V**) after:
- termination and cable issues are corrected/verified,  
- voltage-drop measurements are documented, and  
- unit-to-unit spread is reduced to a safer range.

---

## 7. Installer Evaluation Items (requested)

Because corrective work involves high-energy DC circuits, the following items are recommended for installer execution and documentation:

- **Replace or remediate high-resistance points** (splices, lugs, terminations) as indicated by inspection and measurement.
- **Torque verification** on battery and inverter DC terminations (documented).
- **Voltage-drop testing under charge current:** measure inverter DC terminal voltage vs battery-post voltage and record charge current.
- **Millivolt drop per joint/splice:** identify and correct hotspots.
- **Confirm final configuration:** absorb/float targets and Warm/Cold selection documented with rationale.

---

## 8. What “improvement” looks like (practical targets)

- sustained reduction in spread (trend line improving after mechanical fixes)  
- no recurring DC Over Voltage events during normal charging  
- stable absorb behavior without repeated protective trips  
- documented low voltage drop between inverter terminals and battery posts under charge current

# Project: Lithium Upgrade

**Document Date:** January 21, 2026  
**Site:** Off-Grid Earthship / NO GENERATOR

---

## Why Discover AES Lithium?

The Discover AES Rackmount system offers significant advantages over lead-acid AGM for off-grid energy storage:

### Automatic Charge Management (Closed-Loop BMS)
Unlike AGM batteries that require manual configuration of charge voltages, absorption times, and temperature compensation, the Discover AES system's BMS **automatically communicates optimal charge parameters** to the Schneider XW+ via Xanbus/LYNK II. This eliminates configuration complexity and ensures the batteries always receive correct charging.

### Key Advantages Over AGM

| Feature | Fullriver AGM | Discover AES Lithium |
|---------|---------------|---------------------|
| Charge Configuration | Manual (voltage, time, temp comp) | **Automatic via BMS** |
| Usable Capacity | 50% DoD recommended | **100% DoD** |
| Cycle Life | 1,250 @ 50% DoD | **4,000+ @ 100% DoD** |
| State of Charge | Voltage-based estimation | **True SOC from BMS** |
| Weight (equivalent capacity) | ~2,000 lbs | **~485 lbs** |
| Maintenance | Periodic torque checks, terminal cleaning | Virtually none |
| Expected Lifespan | 5-7 years | **15-20 years** |

---

## 1. Physical Constraints & Dimensional Analysis

### Battery Box Specifications
| Dimension | Measurement | Notes |
|-----------|-------------|-------|
| **Width** | 48 inches | Allows two side-by-side stacks |
| **Depth** | 36 inches | Single row of 19" rackmount units |
| **Height** | **24 inches** | **CRITICAL LIMIT** - max 4 units stacked |

### Thermal Environment (Verified via 6-Month Telemetry)
| Season | Temperature Range | LiFePO4 Compatibility |
|--------|-------------------|----------------------|
| Summer (Aug-Sep) | 75-82°F | ✅ Optimal |
| Fall (Oct-Nov) | 70-80°F | ✅ Optimal |
| Winter (Dec-Jan) | 60-70°F | ✅ Well above 32°F charge threshold |

**Conclusion:** Passive thermal mass maintains enclosure above lithium charging minimum (32°F) year-round. The standard 48-48-5120 module is appropriate; no heating option required.

### Equipment to Remove
| Item | Quantity | Unit Weight | Total Weight |
|------|----------|-------------|--------------|
| Fullriver DC400-6 | 16 | 127 lbs | **2,032 lbs** |

---

## 2. Capacity Analysis: Matching/Exceeding Current System

### Current System (AGM Bank)
| Specification | Value |
|---------------|-------|
| Configuration | 8S2P (8 series × 2 parallel strings) |
| Nominal Voltage | 48V |
| Nominal Capacity | 830 Ah |
| Usable @ 50% DoD | **415 Ah / ~20 kWh** |

### Proposed System (Discover AES Rackmount)
| Specification | Value |
|---------------|-------|
| Configuration | 5 modules in parallel |
| Nominal Voltage | 51.2V |
| Nominal Capacity | 500 Ah |
| Usable @ 100% DoD | **500 Ah / 25.6 kWh** |
| Effective Upgrade | **+20% Ah capacity, +28% usable energy** |

**Capacity Verification:** 500 Ah lithium (100% DoD) exceeds 415 Ah usable from AGM (50% DoD) by **20%**, meeting the requirement to "slightly exceed current amp hours."

---

## 3. Hardware Bill of Materials

### Core Components
| Item | Part Number | Qty | Unit Price* | Extended | Link |
|------|-------------|-----|-------------|----------|------|
| AES Rackmount Battery Module | 48-48-5120 | 5 | $1,773 | $8,865 | [Spec Sheet](https://www.solarelectricsupply.com/media/sparsh/product_attachment/48-48-5120-specifications.pdf) |
| Battery Module Combiner | 950-0049 | 1 | $1,194 | $1,194 | [Data Sheet](https://discoverenergysys.com/s4x_files/resources/808-0043-aes-rackmount-battery-module-combiner-data-sheet.pdf) |
| LYNK II Communication Gateway | 950-0025 | 1 | $550 | $550 | [User Manual (XW+)](https://discoverbattery.com/s4x_files/resources/des-lynk-2-schneider-xw-insighthome-xanbus-manual.pdf) |
| Quick Stack Rack Bracket Set | 950-0050 | 6 | $74 | $444 | [Manual](https://www.solar-electric.com/lib/wind-sun/discover-aes-rackmount-quick-stack-rack-manual-950-0050.pdf) |

**Hardware Subtotal:** ~$11,053

*\*Prices from Inverter Supply, NAZ Solar Electric, Solar Electric Supply (Jan 2025). Call for current quotes.*

**Note:** The standard 48-48-5120 is appropriate for this installation—battery box telemetry confirms temperatures never drop below 60°F, well above the 32°F charging threshold. The heated variant (48-48-5120-H) is unnecessary.

---

## 4. Installation Layout: The "Split Stack"

To fit within the **24-inch height limit**, the system must be installed as two side-by-side stacks on Quick Stack Racks.

```
┌─────────────────────────────────────────────────────────┐
│                    BATTERY BOX (48" × 36" × 24")        │
│                                                         │
│   ┌─────────────────┐         ┌─────────────────┐       │
│   │   Battery #3    │         │    Combiner     │       │  
│   │   (5.12 kWh)    │         │    (950-0049)   │       │  ~21.15"
│   ├─────────────────┤         ├─────────────────┤       │  (incl.
│   │   Battery #2    │         │   Battery #5    │       │   rack
│   │   (5.12 kWh)    │         │   (5.12 kWh)    │       │   brackets)
│   ├─────────────────┤         ├─────────────────┤       │
│   │   Battery #1    │         │   Battery #4    │       │
│   │   (5.12 kWh)    │         │   (5.12 kWh)    │       │
│   └─────────────────┘         └─────────────────┘       │
│        LEFT STACK                 RIGHT STACK           │
│        (3 units)              (2 units + combiner)      │
│                                                         │
│   ←────── 17.3" ──────→       ←────── 17.3" ──────→     │
│   ←──────────────── 34.6" total ─────────────────→      │
└─────────────────────────────────────────────────────────┘
```

### Dimensional Verification
| Measurement | Required | Actual | Status |
|-------------|----------|--------|--------|
| Stack Height (3 units + racks) | ≤24" | **21.15"** (3 × 7.05") | ✅ 2.85" clearance |
| Stack Height (2 units + combiner + racks) | ≤24" | **21.15"** (3 × 7.05") | ✅ 2.85" clearance |
| Total Width (2 stacks) | ≤48" | 34.6" (2 × 17.3") | ✅ |
| Depth (single row) | ≤36" | 19.6" | ✅ |

**Note:** Each Quick Stack Rack bracket set adds 1.75" to the 5.3" battery height, resulting in 7.05" per mounted unit. The combiner box has the same 3U form factor as the batteries.

### Interconnect Requirements
| Connection | Cable Type | Length | Notes |
|------------|-----------|--------|-------|
| Left Stack → Combiner | 4 AWG DC (×3 pairs) | ~4-5 ft | Custom length with SurLok Plus |
| Right Stack → Combiner | Included with combiner | Standard | Pre-made cables included |
| Combiner → Inverter | **Existing 4/0 AWG** | ~6 ft | Reuse if continuous; replace if spliced |
| LYNK II → Xanbus | CAT5e | ~10 ft | To InsightHome/SCP |
| Inter-stack Data | CAT5e | ~3 ft | LYNK Port daisy chain |

---

## 5. System Integration: XW+ Closed-Loop Communication

### Compatibility Confirmation
| Component | Compatibility | Notes |
|-----------|--------------|-------|
| Schneider XW+ 6848 | ✅ Supported | Via LYNK II + InsightHome |
| Schneider MPPT 60-150 | ✅ Supported | Xanbus network member |
| InsightHome Gateway | ✅ Already installed | Existing Xanbus infrastructure |
| Discover AES Rackmount | ✅ Supported | Via LYNK II Gateway |

**Reference Documentation:**
- Discover User Manual: *"LYNK II User Manual for Schneider XW+ with InsightHome"* (805-0052)
- Confirms closed-loop communication is supported for XW+ (not just XW Pro)

### Required Configuration Pathway
```
[AES Rackmount Batteries] 
        │ (LYNK Port / AEbus)
        ▼
   [LYNK II Gateway]
        │ (CAN → Xanbus via RJ45)
        ▼
   [InsightHome/Facility]
        │ (Xanbus network)
        ▼
[XW+ 6848] ←→ [MPPT 60-150]
```

### What Closed-Loop Provides
| Function | Manual Config (Current) | Closed-Loop (Proposed) |
|----------|------------------------|------------------------|
| Charge Voltage | Manually set | **BMS-controlled** |
| Absorption Time | Manually set | **BMS-controlled** |
| Temperature Comp | Manually set | **Internal to BMS** |
| SOC Reporting | Voltage-based estimate | **Actual SOC from BMS** |
| Low Voltage Cutoff | Voltage trigger | **SOC trigger (more accurate)** |

---

## 6. Cable Replacement Requirement

**CRITICAL:** The existing 4/0 AWG cables between the battery box and inverter contain **multiple splices** that must be eliminated as part of this project.

| Current Condition | Required Resolution |
|-------------------|---------------------|
| Split-bolt splice in free air (code violation) | Remove |
| Mechanical splice in junction box | Remove |
| High-resistance connections documented | Eliminate |

**Recommendation:** Replace with continuous, unspliced 4/0 AWG runs from the new Combiner Box to the inverter. This ensures the new lithium system operates within specification with minimal voltage drop.

---

## 7. Budget Summary

### Hardware
| Category | Cost |
|----------|------|
| 5× AES Rackmount 48-48-5120 | $8,865 |
| 1× Battery Module Combiner | $1,194 |
| 1× LYNK II Gateway | $550 |
| 6× Quick Stack Rack Brackets | $444 |
| **Hardware Subtotal** | **~$11,053** |

### Labor (Contractor)
| Task | Estimated Cost |
|------|----------------|
| Removal of 2,000 lbs AGM batteries | $500 - $800 |
| Installation of rack system & batteries | $800 - $1,200 |
| DC wiring (custom interconnects + main run) | $600 - $1,000 |
| Commissioning & testing | $300 - $500 |
| **Labor Subtotal** | **$2,200 - $3,500** |

### Project Total
| Scenario | Total Cost |
|----------|------------|
| Low Estimate | $13,250 |
| High Estimate | $14,550 |
| **Target Budget** | **~$13,500 - $14,000** |

### Cost Comparison vs. AGM Replacement
| Solution | Hardware Cost |
|----------|---------------|
| 16× Fullriver DC400-6 AGM | ~$11,200 - $12,800 |
| 5× Discover AES Rackmount | **~$11,053** |
| **Difference** | **Lithium is $150 - $1,750 LESS** |

**The Discover lithium solution costs the same or less than AGM replacement** while providing superior capacity, longevity, and automatic charge management.
---

## 8. Comparison: AGM Replacement vs. Lithium Upgrade

| Factor | AGM (16× Fullriver DC400-6) | Lithium (5× Discover AES Rackmount) |
|--------|------------------------------|-----------------------------------|
| Hardware Cost | ~$11,200 - $12,800 | **~$11,053** |
| Usable Capacity | 415 Ah (20 kWh @ 50% DoD) | 500 Ah (25.6 kWh @ 100% DoD) |
| Charge Management | Manual configuration required | **Automatic via closed-loop BMS** |
| SOC Monitoring | Voltage-based estimate | **True SOC from BMS** |
| Cycle Life | 1,250 @ 50% DoD | 4,000+ @ 100% DoD |
| Weight | 2,032 lbs | ~485 lbs |
| Warranty | 3-5 years typical | **10 years / 38 MWh throughput** |
| Expected Lifespan | 5-7 years | **15-20 years** |

**Bottom Line:** The Discover AES system costs **less** than AGM replacement while providing:
- 20% more usable amp-hours
- 28% more usable energy (kWh)
- 3-4× longer cycle life
- Automatic charge management via closed-loop communication
- 76% weight reduction
- Longer warranty with throughput guarantee
- True state-of-charge monitoring

---

## 9. Next Steps

1. **Obtain formal quote** from Discover battery distributor (Solar Electric Supply, NAZ Solar, Inverters R Us)
2. **Coordinate installation** with qualified installer
3. **Dispose of AGM batteries** via recycler (Interstate Batteries, local scrap yard)

---

## Appendix: Component Specifications

### Discover AES Rackmount 48-48-5120
| Specification | Value |
|---------------|-------|
| Nominal Voltage | 51.2V |
| Capacity | 100 Ah / 5.12 kWh |
| Chemistry | LiFePO4 |
| Dimensions (L×W×H) | 19.6" × 17.3" × 5.3" (3U) |
| Weight | 97 lbs (44 kg) |
| Max Continuous Current | 100A charge / 100A discharge |
| Peak Current (3 sec) | 218A |
| Operating Temp (Discharge) | -4°F to 131°F |
| Operating Temp (Charge) | 32°F to 113°F |
| Cycle Life | 4,000+ @ 100% DoD |
| Warranty | 10 years / 38 MWh throughput |
| Certifications | UL1973, UL9540-BESS |

**Documentation:**
- [AES Rackmount User Manual](https://discoverbattery.com/s4x_files/resources/des-aes-rackmount-user-manual.pdf)
- [LYNK II Manual for Schneider XW+](https://discoverbattery.com/s4x_files/resources/des-lynk-2-schneider-xw-insighthome-xanbus-manual.pdf)
- [Quick Stack Rack Manual](https://www.solar-electric.com/lib/wind-sun/discover-aes-rackmount-quick-stack-rack-manual-950-0050.pdf)

### Fullriver DC400-6 (Current System - For Reference)
| Specification | Value |
|---------------|-------|
| Nominal Voltage | 6V |
| Capacity | 415 Ah |
| Chemistry | AGM Lead-Acid |
| Dimensions (L×W×H) | 11.6" × 7.1" × 16.8" |
| Weight | 127 lbs |
| Cycle Life | 1,250 @ 50% DoD |
| Warranty | 7 years (per original installation contract) |

---

*Document prepared: January 21, 2026*  
*GitHub Repository: https://github.com/santyr/Solar_PV*

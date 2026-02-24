# Project: Lithium Upgrade

**Document Date:** February 24, 2026  
**Site:** Off-Grid Earthship / NO GENERATOR  
**Revision:** Updated with Inverter Supply pricing

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
| **Height** | **24 inches** | **CRITICAL LIMIT** - max 3 units per stack |

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

### Core Components (Inverter Supply Pricing - February 2026)
| Item | Part Number | Qty | Unit Price | Extended |
|------|-------------|-----|------------|----------|
| AES Rackmount Battery Module | 48-48-5120 | 5 | $1,363.50 | **$6,817.50** |
| Battery Module Combiner | 950-0049 | 1 | $1,147.50 | **$1,147.50** |
| LYNK II Communication Gateway | 950-0025 | 1 | $432.30 | **$432.30** |
| Quick Stack Rack Bracket Set | 950-0050 | 6 | $74.00 | **$444.00** |

| | | | **Hardware Total:** | **$8,841.30** |

*Source: InverterSupply.com shopping cart, February 2026*

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
│   ←──────────────────── 34.6" total ────────────────→   │
└─────────────────────────────────────────────────────────┘
```

### Dimensional Verification (per Quick Stack Rack Manual 805-0056)
| Measurement | Required | Actual | Status |
|-------------|----------|--------|--------|
| Stack Height (3 units + racks) | ≤24" | **21.15"** (3 × 7.05") | ✅ 2.85" clearance |
| Stack Height (2 units + combiner + racks) | ≤24" | **21.15"** (3 × 7.05") | ✅ 2.85" clearance |
| Total Width (2 stacks) | ≤48" | 34.6" (2 × 17.3") | ✅ |
| Depth (single row) | ≤36" | 19.6" | ✅ |
| Required clearance above | 1.75" (1U) | 2.85" available | ✅ |

**Note:** Each Quick Stack Rack bracket set adds 1.75" to the 5.3" battery height, resulting in **7.05" per mounted unit** (179mm per manual spec). The combiner box has the same 3U form factor as the batteries.

### Interconnect Requirements
| Connection | Cable Type | Length | Notes |
|------------|-----------|--------|-------|
| Batteries → Combiner | 3 AWG DC w/ SurLok Plus | 1.5m (5 ft) | **Included with combiner** |
| Combiner → Inverter | **Existing 4/0 AWG** | ~6 ft | Reuse existing cables |
| LYNK II → Xanbus | CAT5e | ~10 ft | To InsightHome |
| Battery-to-Battery Data | CAT5e | As needed | LYNK network daisy chain |

---

## 5. Existing Cable Assessment

### Current Condition
The existing 4/0 AWG cables between the battery box and inverter contain splices:
- Split-bolt splice in free air (code violation)
- Mechanical splice in junction box

### Evaluation
| Factor | Assessment |
|--------|------------|
| Electrical capacity | 4/0 AWG rated 230A; system max ~142A discharge | ✅ Adequate |
| Heat under load | None observed during monitoring | ✅ Functional |
| Cable length | ~6 ft run | ✅ Acceptable |
| BMS communication | Separate data path via LYNK II | ✅ Not affected by DC cable splices |

**Decision:** Reuse existing 4/0 AWG cables. While splices are not code-compliant, they are electrically functional and do not affect BMS communication. Future replacement can be considered if issues arise.

---

## 6. System Integration: XW+ Closed-Loop Communication

### Compatibility Confirmation
| Component | Compatibility | Notes |
|-----------|--------------|-------|
| Schneider XW+ 6848 | ✅ Supported | Via LYNK II + InsightHome |
| Schneider MPPT 60-150 | ✅ Supported | Xanbus network member |
| InsightHome Gateway | ✅ Already installed | Existing Xanbus infrastructure |
| Discover AES Rackmount | ✅ Supported | Via LYNK II Gateway |

### Required Configuration Pathway
```
[AES Rackmount Batteries] 
        │ (LYNK Port / AEbus - CAT5e daisy chain)
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
| Function | Manual Config (Current AGM) | Closed-Loop (Proposed Lithium) |
|----------|----------------------------|-------------------------------|
| Charge Voltage | Manually set | **BMS-controlled** |
| Absorption Time | Manually set | **BMS-controlled** |
| Temperature Comp | Manually set | **Internal to BMS** |
| SOC Reporting | Voltage-based estimate | **Actual SOC from BMS** |
| Low Voltage Cutoff | Voltage trigger | **SOC trigger (more accurate)** |

### OpenHAB Integration
Battery data flows through InsightHome and is accessible via **Modbus TCP**:
- Enable Modbus TCP: Setup → Network → Modbus TCP settings
- Port 502 for BMS data (SOC, voltage, current, temperature)
- Port 503 for device data (XW+, MPPT)
- Schneider Modbus maps available for register addresses

---

## 7. Budget Summary

### Hardware (Inverter Supply - February 2026)
| Item | Cost |
|------|------|
| 5× AES Rackmount 48-48-5120 | $6,817.50 |
| 1× Battery Module Combiner | $1,147.50 |
| 1× LYNK II Gateway | $432.30 |
| 6× Quick Stack Rack Brackets | $444.00 |
| **Hardware Subtotal** | **$8,841.30** |

### Installation Labor Estimates
| Scenario | Labor Cost | Notes |
|----------|------------|-------|
| DIY | $0 | Owner performs all work |
| Installer (owner supplies hardware) | $1,500 - $2,500 | 2-person crew, 6-9 hours |
| Installer supplies everything | $2,500 - $4,000 | Includes equipment markup |

### AGM Battery Recycling Credit
| Item | Value |
|------|-------|
| 16× Fullriver DC400-6 (2,032 lbs) | **$300 - $500 credit** |
| Lead-acid scrap rate | $0.15 - $0.25/lb |

### Project Total Scenarios
| Scenario | Hardware | Labor | AGM Credit | **Net Total** |
|----------|----------|-------|------------|---------------|
| **DIY Install** | $8,841 | $0 | -$400 | **~$8,440** |
| **Installer (owner buys hardware)** | $8,841 | $2,000 | -$400 | **~$10,440** |
| **Installer supplies all** | ~$10,500 | included | -$400 | **~$11,500 - $13,000** |

---

## 8. Comparison: AGM Replacement vs. Lithium Upgrade

| Factor | AGM (16× Fullriver DC400-6) | Lithium (5× Discover AES) |
|--------|------------------------------|---------------------------|
| **Hardware Cost** | ~$11,200 - $12,800 | **$8,841** |
| Usable Capacity | 415 Ah (20 kWh @ 50% DoD) | **500 Ah (25.6 kWh @ 100% DoD)** |
| Charge Management | Manual configuration required | **Automatic via closed-loop BMS** |
| SOC Monitoring | Voltage-based estimate | **True SOC from BMS** |
| Cycle Life | 1,250 @ 50% DoD | **4,000+ @ 100% DoD** |
| Weight | 2,032 lbs | **~485 lbs** |
| Warranty | 3-5 years typical | **10 years / 38 MWh throughput** |
| Expected Lifespan | 5-7 years | **15-20 years** |

### Cost Advantage Summary
| Metric | Value |
|--------|-------|
| Lithium hardware cost | $8,841 |
| AGM replacement cost | $11,200 - $12,800 |
| **Lithium saves** | **$2,359 - $3,959** |

**Bottom Line:** The Discover AES system costs **significantly less** than AGM replacement while providing:
- 20% more usable amp-hours
- 28% more usable energy (kWh)
- 3-4× longer cycle life
- Automatic charge management via closed-loop communication
- 76% weight reduction
- Longer warranty with throughput guarantee
- True state-of-charge monitoring

---

## 9. Installation Timeline (Summer Solstice Target)

### Pre-Install (Days -3 to -1)
- [ ] All hardware received and inspected
- [ ] Optional: Bench charge 2-3 modules using existing system
- [ ] Verify cable reach, test-fit rack brackets
- [ ] Confirm LYNK ACCESS software installed on laptop

### Install Day
| Time | Task |
|------|------|
| 6:30 AM | Open battery disconnect, isolate system |
| 7:00-9:00 AM | Remove 16× AGM batteries (2,032 lbs) - two-person lift |
| 9:00-10:30 AM | Assemble rack brackets, place 5 Discover modules |
| 10:30-11:00 AM | Mount combiner, connect SurLok cables |
| 11:00-11:30 AM | Connect existing 4/0 cables to combiner, close disconnect |
| 11:30 AM-12:00 PM | Verify operation, begin solar charging |
| 1:00-2:30 PM | Install LYNK II, connect to InsightHome, configure closed-loop |
| 2:30-5:00 PM | Verify BMS communication, test OpenHAB/Modbus integration |
| 8:30 PM | Sunset - system charged and operational |

---

## 10. Next Steps

- [x] Obtain formal quote from distributor - **Complete (Inverter Supply $8,841.30)**
- [ ] Place order with Inverter Supply
- [ ] Coordinate installation date (target: summer solstice for maximum solar)
- [ ] Arrange AGM battery recycling (Interstate Batteries, local scrap yard)
- [ ] Download LYNK ACCESS software
- [ ] Review LYNK II Schneider integration manual

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

### 5-Battery System Totals (per Quick Stack Rack Manual Table 4-1)
| Specification | Value |
|---------------|-------|
| Total Capacity | 25 kWh usable |
| Peak Current (3 sec) | 1,090A |
| Max Continuous Discharge (1 hr) | 475A |
| Max Continuous Charge (1 hr) | 475A |

### Documentation Links
- [AES Rackmount User Manual](https://discoverbattery.com/s4x_files/resources/des-aes-rackmount-user-manual.pdf)
- [LYNK II Manual for Schneider XW+](https://discoverbattery.com/s4x_files/resources/des-lynk-2-schneider-xw-insighthome-xanbus-manual.pdf)
- [Quick Stack Rack Manual (805-0056)](https://discoverenergysys.com/s4x_files/resources/805-0056-aes-rackmount-quick-stack-rack-manual.pdf)
- [Battery Module Combiner Data Sheet](https://discoverenergysys.com/s4x_files/resources/808-0043-aes-rackmount-battery-module-combiner-data-sheet.pdf)
- [Schneider Modbus Maps](https://solar.se.com/us/wp-content/uploads/sites/7/2022/02/Conext-Gateway-InsightHome-InsightFacility-Modbus-Maps.zip)

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

*Document prepared: February 24, 2026*  
*Previous revision: January 21, 2026*  
*GitHub Repository: https://github.com/santyr/Solar_PV*

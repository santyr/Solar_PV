# ⚠️ DEPRECATED — See [battery-upgrade-plan-rev2.md](battery-upgrade-plan-rev2.md)

> **This document is superseded.** The BOM, layout, and costs below reflect an earlier design using the Discover 950-0049 Battery Module Combiner ($1,147.50). The current plan uses a Victron Lynx Power In M8 ($150) instead, saving ~$1,000. All current planning information is in [battery-upgrade-plan-rev2.md](battery-upgrade-plan-rev2.md). Software configuration is in [lynk2-deployment-guide.md](lynk2-deployment-guide.md). This file is retained for git history only.

---

# Project: Lithium Upgrade (ARCHIVED)

**Document Date:** February 24, 2026  
**Site:** Off-Grid Earthship / NO GENERATOR  
**Revision:** Updated for 4-module configuration with Inverter Supply pricing

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
| Weight (equivalent capacity) | ~2,000 lbs | **~388 lbs** |
| Maintenance | Periodic torque checks, terminal cleaning | Virtually none |
| Expected Lifespan | 5-7 years | **15-20 years** |

---

## 1. Physical Constraints & Dimensional Analysis

### Battery Box Specifications
| Dimension | Measurement | Notes |
|-----------|-------------|-------|
| **Width** | 48 inches | Allows two side-by-side stacks |
| **Depth** | 36 inches | Single row of 19" rackmount units |
| **Height** | **24 inches** | **CRITICAL LIMIT** |

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

## 2. Capacity Analysis

### Current System (AGM Bank)
| Specification | Value |
|---------------|-------|
| Configuration | 8S2P (8 series × 2 parallel strings) |
| Nominal Voltage | 48V |
| Nominal Capacity | 830 Ah |
| Usable @ 50% DoD | **415 Ah / ~20 kWh** |

### Proposed System (4× Discover AES Rackmount)
| Specification | Value |
|---------------|-------|
| Configuration | 4 modules in parallel |
| Nominal Voltage | 51.2V |
| Nominal Capacity | 400 Ah |
| Usable @ 100% DoD | **400 Ah / 20.48 kWh** |

**Capacity Match:** 400 Ah lithium (100% DoD) is functionally equivalent to 415 Ah usable from AGM (50% DoD), matching the original system design capacity within 4%.

### Autonomy Analysis (No Generator)

Based on actual InsightLocal consumption data (February 2026) and Coaldale, CO (81222) climate:

| Metric | Value |
|--------|-------|
| Winter daily load (worst case) | ~4.9 kWh/day |
| Days of autonomy (full capacity) | **4.2 days** |
| Days of autonomy (20% reserve) | **3.4 days** |
| Average daily DoD | **~10%** |

**Climate context:**
- 260 sunny days per year (US average: 205)
- 6.4 peak sun hours/day (fixed tilt)
- ~105 overcast days/year
- Typical winter storm duration: 2–3 days, rare events 4–5 days
- Even heavy overcast yields 10–25% of rated solar output

**Conclusion:** 4 modules provide 3.4 days of true autonomy with safety reserve, comfortably covering typical 3-day winter storms and surviving rare 4–5 day events when factoring in partial solar production during overcast conditions.

---

## 3. Hardware Bill of Materials

### Core Components (Inverter Supply Pricing — February 2026)
| Item | Part Number | Qty | Unit Price | Extended |
|------|-------------|-----|------------|----------|
| AES Rackmount Battery Module | 48-48-5120 | 4 | $1,363.50 | **$5,454.00** |
| Battery Module Combiner | 950-0049 | 1 | $1,147.50 | **$1,147.50** |
| LYNK II Communication Gateway | 950-0025 | 1 | $432.30 | **$432.30** |
| Quick Stack Rack Bracket Set | 950-0050 | 5 | $74.00 | **$370.00** |

| | | | **Hardware Total:** | **$7,403.80** |

*Source: InverterSupply.com shopping cart, February 2026*

**Note:** The standard 48-48-5120 is appropriate for this installation—battery box telemetry confirms temperatures never drop below 60°F, well above the 32°F charging threshold. The heated variant (48-48-5120-H) is unnecessary.

---

## 4. Installation Layout: The "Split Stack"

To fit within the **24-inch height limit**, the system is installed as two side-by-side stacks on Quick Stack Racks.

```
┌─────────────────────────────────────────────────────────┐
│                    BATTERY BOX (48" × 36" × 24")        │
│                                                         │
│                                                         │
│                                    ┌─────────────────┐  │
│                                    │    Combiner     │  │
│   ┌─────────────────┐              │    (950-0049)   │  │
│   │   Battery #2    │              ├─────────────────┤  │
│   │   (5.12 kWh)    │              │   Battery #4    │  │
│   ├─────────────────┤              │   (5.12 kWh)    │  │
│   │   Battery #1    │              ├─────────────────┤  │
│   │   (5.12 kWh)    │              │   Battery #3    │  │
│   └─────────────────┘              └─────────────────┘  │
│        LEFT STACK                      RIGHT STACK      │
│     (2 units, 14.1")            (2 units + combiner,    │
│                                       21.15")           │
│                                                         │
│   ←────── 17.3" ──────→        ←────── 17.3" ──────→   │
│   ←──────────────────── 34.6" total ────────────────→   │
└─────────────────────────────────────────────────────────┘
```

### Dimensional Verification (per Quick Stack Rack Manual 805-0056)
| Measurement | Required | Actual | Status |
|-------------|----------|--------|--------|
| Stack Height, Left (2 units + racks) | ≤24" | **14.1"** (2 × 7.05") | ✅ 9.9" clearance |
| Stack Height, Right (2 units + combiner + racks) | ≤24" | **21.15"** (3 × 7.05") | ✅ 2.85" clearance |
| Total Width (2 stacks) | ≤48" | 34.6" (2 × 17.3") | ✅ |
| Depth (single row) | ≤36" | 19.6" | ✅ |

**Note:** Each Quick Stack Rack bracket set adds 1.75" to the 5.3" battery height, resulting in **7.05" per mounted unit** (179mm per manual spec). The combiner box has the same 3U form factor as the batteries. The left stack has nearly 10" of clearance for wiring and airflow.

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

## 7. Warranty & Longevity Analysis

### Discover AES Warranty Terms (per module)
| Parameter | Limit |
|-----------|-------|
| Base Workmanship Warranty | 5 years |
| Extended Warranty (with registration) | **10 years** |
| Annual Energy Throughput Limit | 3,000 kWh/module |
| Total Energy Throughput Limit | **30 MWh/module** |
| End-of-Warranty Capacity | ≥60% of rated Wh |

### Projected Usage Against Warranty Limits (4 Modules)

Based on 4.55 years of actual InsightLocal data (commissioned 8/6/2021):

| Metric | Value |
|--------|-------|
| Lifetime battery discharge | 3.4 MWh |
| Lifetime battery charge | 4.6 MWh |
| Average annual throughput | ~1.76 MWh/year |
| Projected per-module annual throughput | ~380 kWh |
| Per-module annual limit | 3,000 kWh |
| **Utilization of annual limit** | **~13%** |
| Years to reach 30 MWh per-module limit | ~79 years |
| Equivalent full cycles per year | ~37 EFC |
| Years to reach 4,000 cycle rating | ~108 years |

### Life Expectancy

Cycle life and throughput will not be the limiting factor at this usage level. The limiting factor will be **calendar aging of LiFePO4 cells**, typically 15–20 years. Battery box temperatures of 60–82°F are near-ideal for longevity.

**Expected service life: 15–20 years**, limited by calendar aging rather than cycling.

---

## 8. Budget Summary

### Hardware (Inverter Supply — February 2026)
| Item | Cost |
|------|------|
| 4× AES Rackmount 48-48-5120 | $5,454.00 |
| 1× Battery Module Combiner | $1,147.50 |
| 1× LYNK II Gateway | $432.30 |
| 5× Quick Stack Rack Brackets | $370.00 |
| **Hardware Subtotal** | **$7,403.80** |

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
| **DIY Install** | $7,404 | $0 | -$400 | **~$7,004** |
| **Installer (owner buys hardware)** | $7,404 | $2,000 | -$400 | **~$9,004** |
| **Installer supplies all** | ~$9,000 | included | -$400 | **~$9,500 - $11,000** |

---

## 9. Comparison: AGM Replacement vs. Lithium Upgrade

| Factor | AGM (16× Fullriver DC400-6) | Lithium (4× Discover AES) |
|--------|------------------------------|---------------------------|
| **Hardware Cost** | ~$11,200 - $12,800 | **$7,404** |
| Usable Capacity | 415 Ah (20 kWh @ 50% DoD) | **400 Ah (20.48 kWh @ 100% DoD)** |
| Charge Management | Manual configuration required | **Automatic via closed-loop BMS** |
| SOC Monitoring | Voltage-based estimate | **True SOC from BMS** |
| Cycle Life | 1,250 @ 50% DoD | **4,000+ @ 100% DoD** |
| Weight | 2,032 lbs | **~388 lbs** |
| Warranty | 3-5 years typical | **10 years / 30 MWh per module** |
| Expected Lifespan | 5-7 years | **15-20 years** |

### Cost Advantage Summary
| Metric | Value |
|--------|-------|
| Lithium hardware cost | $7,404 |
| AGM replacement cost | $11,200 - $12,800 |
| **Lithium saves** | **$3,796 - $5,396** |

**Bottom Line:** The 4-module Discover AES system costs **roughly half** the price of AGM replacement while providing:
- Equivalent usable capacity (~20 kWh)
- 3.4 days of autonomy (covers typical winter storms without generator)
- 3-4× longer cycle life
- Automatic charge management via closed-loop communication
- 81% weight reduction
- Longer warranty with throughput guarantee
- True state-of-charge monitoring

---

## 10. Installation Timeline (Summer Solstice Target)

### Pre-Install (Days -3 to -1)
- [ ] All hardware received and inspected
- [ ] Optional: Bench charge 1-2 modules using existing system
- [ ] Verify cable reach, test-fit rack brackets
- [ ] Confirm LYNK ACCESS software installed on laptop

### Install Day
| Time | Task |
|------|------|
| 6:30 AM | Open battery disconnect, isolate system |
| 7:00-9:00 AM | Remove 16× AGM batteries (2,032 lbs) — two-person lift |
| 9:00-10:00 AM | Assemble rack brackets, place 4 Discover modules (2+2 stacks) |
| 10:00-10:30 AM | Mount combiner on right stack, connect SurLok cables |
| 10:30-11:00 AM | Connect existing 4/0 cables to combiner, close disconnect |
| 11:00-11:30 AM | Verify operation, begin solar charging |
| 11:30 AM-1:00 PM | Install LYNK II, connect to InsightHome, configure closed-loop |
| 1:00-3:00 PM | Verify BMS communication, test OpenHAB/Modbus integration |
| 8:30 PM | Sunset — system charged and operational |

---

## 11. Next Steps

- [x] Obtain formal quote from distributor — **Complete (Inverter Supply $7,403.80)**
- [ ] Place order with Inverter Supply
- [ ] Register warranty within 30 days of installation for 10-year extended coverage
- [ ] Coordinate installation date (target: summer solstice for maximum solar)
- [ ] Arrange AGM battery recycling (Interstate Batteries, local scrap yard)
- [ ] Download LYNK ACCESS software
- [ ] Review LYNK II Schneider integration manual (805-0052)

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
| Warranty | 10 years / 30 MWh throughput (per module, with registration) |
| Certifications | UL1973, UL9540-BESS |

### 4-Battery System Totals
| Specification | Value |
|---------------|-------|
| Total Capacity | 20.48 kWh usable |
| Total Amp-Hours | 400 Ah |
| Peak Current (3 sec) | 872A |
| Max Continuous Discharge (1 hr) | 380A |
| Max Continuous Charge (1 hr) | 380A |

### Documentation Links
- [AES Rackmount User Manual](https://discoverbattery.com/s4x_files/resources/des-aes-rackmount-user-manual.pdf)
- [LYNK II Manual for Schneider XW+](https://discoverbattery.com/s4x_files/resources/des-lynk-2-schneider-xw-insighthome-xanbus-manual.pdf)
- [Quick Stack Rack Manual (805-0056)](https://discoverenergysys.com/s4x_files/resources/805-0056-aes-rackmount-quick-stack-rack-manual.pdf)
- [Battery Module Combiner Data Sheet](https://discoverenergysys.com/s4x_files/resources/808-0043-aes-rackmount-battery-module-combiner-data-sheet.pdf)
- [Schneider Modbus Maps](https://solar.se.com/us/wp-content/uploads/sites/7/2022/02/Conext-Gateway-InsightHome-InsightFacility-Modbus-Maps.zip)

### Fullriver DC400-6 (Current System — For Reference)
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

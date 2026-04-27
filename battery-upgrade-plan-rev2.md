# Earthship Battery Upgrade — Project Plan (Rev 3)

## Discover AES Rackmount + Closed-Loop via LYNK II

**Companion document:** [LYNK II Deployment Guide](lynk2-deployment-guide.md) — step-by-step software configuration for LYNK II, XW Pro 6848, and MPPT 60-150 (including all InsightLocal settings, current-vs-target values, and comms-loss fallback configuration).

---

## System Summary

| Parameter | Current (AGM) | Upgrade (LiFePO4) |
|-----------|---------------|-------------------|
| Batteries | 16× Fullriver DC400-6 (6V) | 4× Discover AES 48-48-5120 |
| Configuration | 8S2P | 4P (each module is 51.2V) |
| Nominal Voltage | 48V | 51.2V |
| Total Capacity | 830 Ah / 39.8 kWh | 400 Ah / 20.48 kWh |
| Usable Capacity | ~415 Ah / ~20 kWh (50% DoD) | ~20.48 kWh (100% DoD) |
| Weight | 2,032 lbs | 388 lbs |
| Days of Autonomy | ~2 days | 3.4 days (20% reserve) |
| Communication | None (open-loop) | Closed-loop via LYNK II → Xanbus |

**Inverter:** Schneider XW Pro 6848 NA 120/240 + MPPT 60-150 + InsightHome (Xanbus network)
**Location:** Earthship, Coaldale, CO 81222 (off-grid, no generator)
**Battery Box:** 48"W × 36"D × 24"H
**Temperature Range:** 60–82°F year-round (non-heated batteries appropriate)

---

## Physical Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                BATTERY BOX (48"W × 36"D × 24"H)                  │
│                                                                  │
│                                                    RIGHT WALL    │
│                                                   ┌──────────┐   │
│   ┌─────────────────┐    ┌─────────────────┐      │  LYNX    │   │
│   │   Battery #2    │    │   Battery #4    │      │  POWER   │   │
│   │   (5.12 kWh)    │    │   (5.12 kWh)    │      │   IN     │   │
│   ├─────────────────┤    ├─────────────────┤      │  M8      │   │
│   │   Battery #1    │    │   Battery #3    │      │          │   │
│   │   (5.12 kWh)    │    │   (5.12 kWh)    │      │[+]  [-]  │   │
│   └─────────────────┘    └─────────────────┘      │ s1   s1  │   │
│     LEFT STACK             RIGHT STACK            │ s2   s2  │   │
│     14.1" tall             14.1" tall             │ s3   s3  │   │
│     9.9" clearance         9.9" clearance         │ s4   s4  │   │
│                                                   └────┬─────┘   │
│   ←── 17.3" ──→          ←── 17.3" ──→                 │         │
│                                                        │         │
│                     Inverter 4/0 cables enter ─────────┘         │
│                     from right wall (existing, in wall/ceiling)  │
└──────────────────────────────────────────────────────────────────┘
```

**Stack dimensions (each, per AES Rackmount manual 805-0043 REVD):**
- Battery: 19.6"L × 17.3"W × 5.3"H (3U)
- Quick Stack Rack adds: 1.75" height (1U recommended spacing per manual)
- Per unit mounted: 7.05"
- Stack of 2: 14.1" (leaves 9.9" clearance to 24" box lid)

**Total footprint:** 34.6"W (13.4" clearance in 48" box)

---

## Lynx Power In M8 — Connection Plan (5 Connections Per Pole)

The Lynx Power In has **4 front M8 studs** plus **1 side M8 busbar tab** per pole = 5 total connection points. This matches our requirement exactly: 4 batteries + 1 inverter.

```
    SIDE TAB            FRONT STUDS (4× M8)              SIDE TAB
   (left side)                                          (right side)
  ┌──────────┐    ┌──────────────────────────────┐    ┌──────────┐
  │          │    │                              │    │          │
  │  [+]INV ─┼────┤  s1[B1]  s2[B2]  s3[B3]  s4[B4] │    │  [cap]   │
  │  4/0 AWG │    │     POSITIVE BUSBAR          │    │          │
  │          │    │                              │    │          │
  ├──────────┤    ├──────────────────────────────┤    ├──────────┤
  │          │    │                              │    │          │
  │  [-]INV ─┼────┤  s1[B1]  s2[B2]  s3[B3]  s4[B4] │    │  [cap]   │
  │  4/0 AWG │    │     NEGATIVE BUSBAR          │    │          │
  │          │    │                              │    │          │
  └──────────┘    └──────────────────────────────┘    └──────────┘
```

**Front studs 1–4:** Discover 950-0055 cable kits (M8 ring terminals) — one per battery
**Left side tabs:** Existing 4/0 inverter cables (M8 lugs) — bolted through with M8 hardware
**Right side tabs:** Capped (unused) — available for future expansion

**Side tab connection method:**
- Remove rubber cap from left side busbar tab
- Insert M8 stainless bolt through busbar hole
- Place existing inverter cable M8 lug on bolt
- Flat washer → lock washer → M8 nut → torque to 14 Nm

---

## Communication Network — Closed-Loop

```
                              LYNK Network (RJ45 / CAT5e or higher)
[LYNK II]──LYNK──[Batt 4]──LYNK──[Batt 3]──LYNK──[Batt 2]──LYNK──[Batt 1]   (no terminator)
    │
    │ CAN Out (RJ45)
    │
    ├─────────────────────── Xanbus Network ───────────────────────┐
    │                           │                                  │
[InsightHome]              [XW Pro 6848]                    [MPPT 60-150]
```

**LYNK Network cables needed:** 4 (LYNK II↔B4, B4↔B3, B3↔B2, B2↔B1) — each AES Rackmount has 2 LYNK ports for daisy chaining
**Xanbus cable needed:** 1 (LYNK II CAN Out → existing Xanbus network)
**External terminator:** NONE — both LYNK II and AES Rackmount batteries are internally terminated per manual 805-0033

**What closed-loop provides:**
- BMS automatically controls charge voltage, absorption time, temp compensation
- True SOC reporting (replaces voltage-based estimation)
- Dynamic charge optimization (~25% faster recharge vs. open-loop)
- XW Pro "Fixed" and "Dynamic" settings overwritten by BMS automatically
- User retains control of "Adjustable" settings (Grid Support, gen triggers) via InsightLocal
- SOC-based triggers recommended over voltage-based

**Communication failure behavior (important for no-generator setup):**
- XW Pro applies configured Comms Loss action after 7-10s timeout (Warning, with graceful-degradation current limits per Deployment Guide)
- Over time, stale parameters could push batteries to over-charge or over-discharge
- BMS self-protects and disconnects when limits reached
- Manual intervention required to restart
- Mitigation: wired CAN bus — failures are rare

**Critical:** Conext Battery Monitor is INCOMPATIBLE with LYNK II — must be removed from Xanbus if present.

---

## Complete Bill of Materials

### Already Purchased (Sourced During Negotiation Period)

| # | Item | Part Number | Qty | Status |
|---|------|-------------|-----|--------|
| A1 | Discover Battery Cable Set (3 AWG, 2-Pos/Neg) | 950-0055 | 2 sets | ✅ On hand |
| A2 | Victron Lynx Power In M8 | LYN020102000 | 1 | ✅ On hand |
| A3 | LYNK Network / Xanbus CAT5e patch cables | 1–2 ft | 5+ | ✅ On hand |

### Remaining Components — To Be Sourced

| # | Item | Part Number | Qty | Unit Price | Extended | Source |
|---|------|-------------|-----|-----------|----------|--------|
| 1 | AES Rackmount Battery | 48-48-5120 | 4 | $1,350.00 | $5,400.00 | Jonsson Tech |
| 2 | Cable Kit (SurLok→M8, 2m) | 950-0055 | 2 | ~$129.05 | ~$258.10 | TBD |
| 3 | LYNK II Comm Gateway | 950-0025 | 1 | ~$432.30 | ~$432.30 | TBD |
| 4 | Quick Stack Rack | 950-0050 | 4 | ~$74.00 | ~$296.00 | TBD |

> **Note on cable kits (item 2):** Each Discover 950-0055 cable set provides 2 positive + 2 negative cables (one set serves 2 batteries). With 2 sets already on hand and 4 batteries total, we need 2 additional sets — but verify cable set contents at order time. If a single set already covers all 4 batteries' needs, this item may not be needed.

### Configuration

| # | Item | Spec | Qty | Unit Price | Extended | Source |
|---|------|------|-----|-----------|----------|--------|
| 5 | USB cable for LYNK II | Type-B mini | 1 | ~$8.00 | ~$8.00 | Amazon |

### Hardware — Lynx Side Tab Connections (Inverter Cables)

| # | Item | Spec | Qty | Unit Price | Extended | Source |
|---|------|------|-----|-----------|----------|--------|
| 6 | M8 stainless steel bolts | M8-1.25 × 25mm (or 1") | 2 | — | — | Hardware store |
| 7 | M8 stainless steel nuts | M8-1.25 | 2 | — | — | Hardware store |
| 8 | M8 flat washers | Stainless | 4 | — | — | Hardware store |
| 9 | M8 lock washers | Stainless (split or Nordlock) | 2 | — | — | Hardware store |
| | | | | **Hardware subtotal:** | ~$10.00 | |

### Mounting

| # | Item | Spec | Qty | Unit Price | Extended | Source |
|---|------|------|-----|-----------|----------|--------|
| 10 | Lynx Power In mounting screws | Per Lynx manual (may be included) | — | — | ~$5.00 | Hardware store |
| 11 | Wall anchors / wood screws | For right wall mounting | — | — | ~$5.00 | Hardware store |

### Optional but Recommended

| # | Item | Spec | Qty | Unit Price | Extended | Source |
|---|------|------|-----|-----------|----------|--------|
| 12 | Anti-oxidant compound | No-Ox-Id or Ox-Guard | 1 | ~$10.00 | ~$10.00 | Amazon / hardware store |
| 13 | Cable ties / velcro straps | For cable management | 1 pkg | ~$8.00 | ~$8.00 | Amazon |

---

### Cost Summary

| Category | Cost |
|----------|------|
| Already on hand (items A1–A3) | $0 (sunk) |
| Discover AES batteries (item 1) | $5,400.00 |
| Cable kits (item 2) | ~$258.10 |
| LYNK II Gateway (item 3) | ~$432.30 |
| Quick Stack Racks (item 4) | ~$296.00 |
| Configuration cable (item 5) | ~$8.00 |
| Side tab hardware (items 6–9) | ~$10.00 |
| Mounting hardware (items 10–11) | ~$10.00 |
| Optional items (items 12–13) | ~$18.00 |
| **Subtotal hardware (remaining)** | **~$6,432** |
| AGM recycling credit (2,032 lbs) | −$300 to −$500 |
| **Estimated net cost (remaining)** | **~$5,930 to $6,130** |

> **Cost-share note:** Per the warranty dispute resolution framework with Colorado Mountain Solar (CMS), CMS reimburses 86% of fair-market hardware cost, with Sat covering ~14% (reflecting actual measured Fullriver bank usage of 88/625 EFC). At ~$6,432 remaining hardware total: CMS share ~$5,531, Sat share ~$893, plus CMS providing labor.

---

### Tools Required (on hand or borrow)

- Wrenches: 13mm (for M8 nuts/bolts)
- Torque wrench capable of 14 Nm / ~10 ft-lbs (for M8 connections)
- Multimeter (voltage verification)
- Phillips screwdriver (rack assembly, Lynx mounting)
- Windows 10/11 64-bit laptop or VM (LYNK ACCESS 2.5 or later software)

### No Special Tools Needed

- No hydraulic crimper — all cables come pre-terminated
- No drilling — all holes pre-made
- No soldering
- Assembly is entirely bolt-on connections with standard wrenches

---

## Installation Timeline — Coordinated with CMS Labor

> **Status:** Replacement scheduling in progress with Colorado Mountain Solar. Exact install date pending CMS confirmation.

### Pre-Install (Days −3 to −1)

- [ ] All hardware received and inspected
- [ ] Verify 950-0055 cable reach: 2m (6.5 ft) from each battery to right-wall Lynx
- [ ] Test-fit one Quick Stack Rack bracket on one battery
- [ ] Verify M8 bolt fits through Lynx Power In side busbar tab
- [ ] Verify M8 bolt + inverter lug + washers + nut fits side tab properly
- [ ] Install LYNK ACCESS software on Windows laptop/VM
- [ ] Download Discover manuals 805-0033 (LYNK II) and 805-0043 REVD (AES Rackmount)
- [ ] Confirm Conext Battery Monitor NOT present on Xanbus (remove if found)
- [ ] Coordinate AGM recycling pickup
- [ ] Measure Xanbus cable run: LYNK II location → nearest Xanbus jack

### Install Day

| Time | Task | Duration |
|------|------|----------|
| 6:30 AM | Open battery disconnect, isolate system from inverter | 10 min |
| 6:40–9:00 AM | Remove 16× AGM batteries (127 lbs each, two-person lift) | 2.5 hrs |
| 9:00–9:30 AM | Clean battery box, inspect for corrosion | 30 min |
| 9:30–10:00 AM | Assemble 4× Quick Stack Racks, mount batteries in 2+2 stacks | 30 min |
| 10:00–10:30 AM | Mount Lynx Power In on right wall near cable entry point | 30 min |
| 10:30–11:00 AM | Connect 4× 950-0055 cables: SurLok to batteries, M8 to Lynx front studs | 30 min |
| 11:00–11:15 AM | Bolt existing 4/0 inverter cables to Lynx side tabs (M8 hardware) | 15 min |
| 11:15–11:30 AM | Torque all connections to 14 Nm. Close battery disconnect. | 15 min |
| 11:30 AM | **System live — solar charging begins** | — |
| 11:30 AM–12:00 PM | Verify voltage on InsightLocal, confirm charging current | 30 min |
| 12:00–12:30 PM | Lunch break (system charges unattended) | 30 min |
| 12:30–1:00 PM | Install LYNK II: connect LYNK Network daisy chain between all 4 batteries | 30 min |
| 1:00–1:15 PM | Connect LYNK Network from Battery #4 to LYNK II | 15 min |
| 1:15–1:30 PM | (Skip — no terminator needed; both ends internally terminated) | — |
| 1:30–2:00 PM | Connect LYNK II CAN Out to Xanbus network (RJ45 patch cable) | 30 min |
| 2:00–3:00 PM | Configure LYNK II via USB + LYNK ACCESS: select Schneider Electric - Xanbus protocol, save (see [Deployment Guide](lynk2-deployment-guide.md)) | 1 hr |
| 3:00–3:30 PM | Verify on InsightLocal: Battery Bank = 400 Ah, SOC reporting active. Configure XW Pro and MPPT settings per [Deployment Guide](lynk2-deployment-guide.md) | 30 min |
| 3:30–4:00 PM | Apply anti-oxidant to all connections, tidy cable management | 30 min |
| 8:30 PM | Sunset — system fully charged and operational | — |

---

## Post-Installation

### Within 24 Hours

- [ ] Monitor first full charge/discharge cycle
- [ ] Verify SOC accuracy: LYNK II vs. InsightLocal
- [ ] Check all connection temperatures under load (hand-feel for warmth at Lynx studs and side tabs)

### Within 30 Days

- [ ] **Register warranty online for 10-year coverage** (critical deadline — do not miss)
- [ ] Configure SOC-based triggers on XW Pro via InsightLocal (replace voltage-based)
- [ ] Set "Adjustable" parameters: Grid Support thresholds, low-SOC generator triggers

### Ongoing

- [ ] Integrate monitoring into OpenHAB via Modbus TCP (ports 502/503)
- [ ] Document final XW Pro configuration settings
- [ ] Periodic visual inspection of connections (quarterly)
- [ ] Annual torque check on all Lynx connections

---

## Warranty & Longevity

| Parameter | Value |
|-----------|-------|
| Base warranty | 5 years |
| Extended (with registration within 30 days) | 10 years |
| Annual throughput limit | 3,000 kWh/module |
| Total throughput limit | 30 MWh/module |
| End-of-warranty capacity | ≥60% rated Wh |
| Your projected annual throughput | ~380 kWh/module (13% of limit) |
| Years to throughput limit | ~79 years |
| Equivalent full cycles/year | ~37 EFC |
| Expected service life | 15–20 years (limited by calendar aging, not cycling) |

---

## Autonomy Analysis

| Parameter | Value |
|-----------|-------|
| Total capacity | 20.48 kWh |
| Winter daily load (worst case) | ~4.9 kWh/day |
| Days of autonomy (full capacity) | 4.2 days |
| Days of autonomy (20% reserve) | 3.4 days |
| Average daily DoD | ~10% |
| Typical winter storm duration | 2–3 days |
| Rare extended storm | 4–5 days |
| Overcast solar yield | 10–25% of rated |

Coaldale, CO receives 260 sunny days/year and 6.4 peak sun hours/day. The 3.4-day autonomy covers typical storms comfortably and survives rare 4–5 day events with partial solar production.

---

## Open Items — Verify Before Ordering

1. **✅ RESOLVED: Inverter cable lug hole = M8 (5/16")**
   Fullriver DC400-6 datasheet confirms M8 terminal studs. Existing lugs are M8.

2. **✅ RESOLVED: No Conext Battery Monitor on Xanbus network**
   Confirmed via InsightHome device list — not present.

3. **✅ RESOLVED: No external LYNK Network terminator needed**
   Per Discover 805-0033, both LYNK II and AES Rackmount batteries are internally terminated. Removed from BOM.

4. **☐ VERIFY: Jonsson Tech availability and price hold**
   Contact pending. Confirm 4 modules in stock at $1,350 each plus shipping.

5. **☐ VERIFY: 950-0055 cable kit contents**
   Each kit contains 2 positive + 2 negative cables (covers 2 batteries). Confirm at order time whether 2 sets already on hand cover all 4 batteries, or whether additional sets needed.

6. **☐ VERIFY: Lynx Power In M8 side tab bolt clearance**
   Confirm on receipt that M8 bolt passes through side busbar hole cleanly and lug + washers + nut fit without interference from housing.

7. **☐ MEASURE: Xanbus cable length**
   Distance from planned LYNK II location to nearest Xanbus RJ45 jack, to order correct length CAT5e patch cable.

---

## Reference Documents

| Document | Location / Link |
|----------|----------------|
| LYNK II Deployment Guide | [lynk2-deployment-guide.md](lynk2-deployment-guide.md) |
| LYNK II Installation and Operation Manual | Discover 805-0033 |
| AES Rackmount Installation and Operation Manual | Discover 805-0043 REVD |
| Fullriver DC400-6 Datasheet | [DC400-6.pdf](DC400-6.pdf) |
| Quick Stack Rack Manual | Discover 805-0056 |
| Schneider Modbus Maps | [solar.se.com](https://solar.se.com/us/wp-content/uploads/sites/7/2022/02/Conext-Gateway-InsightHome-InsightFacility-Modbus-Maps.zip) |
| System Defect Analysis | [System_Defect_Analysis.md](System_Defect_Analysis.md) |

### Supplier Links

| Item | URL |
|------|-----|
| AES Rackmount Battery (primary source) | [Jonsson Tech](https://www.jonssontech.net/products/aes-rackmount-battery-48-48-5120?variant=46323021250779) |
| Lynx Power In M8 (alt) | [Current Connected](https://www.currentconnected.com/product/victron-lynx-power-in-distribution-system/) |

> **Supply note (April 2026):** The Discover AES Rackmount battery supply situation has materially deteriorated. Inverter Supply has dropped the SKU. Most major distributors (Inverters R Us, NAZ Solar, Off Grid Source) show backorder status with no firm ship dates. Discover's own site no longer publishes pricing. Jonsson Tech at $1,350/module is at or below the current market floor — pricing and availability may not hold long.

---

*Document Rev 3 — April 27, 2026. Updates from Rev 2.1: corrected Schneider inverter model (XW Pro 6848 NA, not XW+); removed external LYNK terminator (internally terminated per 805-0033); updated manual references (805-0033 for LYNK II, 805-0043 REVD for AES Rackmount); split BOM into items already purchased vs. remaining; updated supplier from Inverter Supply (no longer carries SKU) to Jonsson Tech; added cost-share framework with CMS; added supply chain notes. Prices subject to change. Verify all pricing at time of order.*

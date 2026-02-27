# Earthship Battery Upgrade — Project Plan (Rev 2)
## Discover AES Rackmount + Closed-Loop via LYNK II
### M8 (5/16") Confirmed — Fullriver DC400-6 terminals are M8 per datasheet

---

## System Summary

| Parameter | Current (AGM) | Upgrade (LiFePO4) |
|-----------|---------------|-------------------|
| Batteries | 16× Fullriver DC400-6 (6V) | 4× Discover AES 48-48-5120 |
| Configuration | 8S2P | 4P (each module is 48V) |
| Nominal Voltage | 48V | 51.2V |
| Total Capacity | 400 Ah / 19.2 kWh | 400 Ah / 20.48 kWh |
| Usable Capacity | ~9.6 kWh (50% DoD) | ~20.48 kWh (100% DoD) |
| Weight | 2,032 lbs | 388 lbs |
| Days of Autonomy | ~2 days | 3.4 days (20% reserve) |
| Communication | None (open-loop) | Closed-loop via LYNK II → Xanbus |

**Inverter:** Schneider XW6848 + MPPT 60-150 + InsightHome (Xanbus network)
**Location:** Earthship, Coaldale, CO 81222 (off-grid, no generator)
**Battery Box:** 48"W × 36"D × 24"H
**Temperature Range:** 60–82°F year-round (non-heated batteries appropriate)

---

## Physical Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                BATTERY BOX (48"W × 36"D × 24"H)                 │
│                                                                  │
│                                                    RIGHT WALL    │
│                                                   ┌──────────┐  │
│   ┌─────────────────┐    ┌─────────────────┐      │  LYNX    │  │
│   │   Battery #2    │    │   Battery #4    │      │  POWER   │  │
│   │   (5.12 kWh)    │    │   (5.12 kWh)    │      │   IN     │  │
│   ├─────────────────┤    ├─────────────────┤      │  M8      │  │
│   │   Battery #1    │    │   Battery #3    │      │          │  │
│   │   (5.12 kWh)    │    │   (5.12 kWh)    │      │[+]  [-]  │  │
│   └─────────────────┘    └─────────────────┘      │ s1   s1  │  │
│     LEFT STACK             RIGHT STACK            │ s2   s2  │  │
│     14.1" tall             14.1" tall             │ s3   s3  │  │
│     9.9" clearance         9.9" clearance         │ s4   s4  │  │
│                                                   └────┬─────┘  │
│   ←── 17.3" ──→          ←── 17.3" ──→                │        │
│                                                        │        │
│                     Inverter 4/0 cables enter ─────────┘        │
│                     from right wall (existing, in wall/ceiling)  │
└──────────────────────────────────────────────────────────────────┘
```

**Stack dimensions (each):**
- Battery: 17.3"W × 19.1"D × 5.3"H
- Quick Stack Rack adds: 1.75" height
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
                              AEbus Daisy Chain (RJ45 / CAT5e)
[LYNK II]──AEbus──[Batt 4]──AEbus──[Batt 3]──AEbus──[Batt 2]──AEbus──[Batt 1]──[Terminator]
    │
    │ CAN Out (RJ45)
    │
    ├─────────────────────── Xanbus Network ───────────────────────┐
    │                           │                                  │
[InsightHome]              [XW+ 6848]                       [MPPT 60-150]
```

**AEbus cables needed:** 4 (LYNK II↔B4, B4↔B3, B3↔B2, B2↔B1)
**Xanbus cable needed:** 1 (LYNK II CAN Out → existing Xanbus network)
**Terminator needed:** 1 (at Battery #1, end opposite LYNK II)

**What closed-loop provides:**
- BMS automatically controls charge voltage, absorption time, temp compensation
- True SOC reporting (replaces voltage-based estimation)
- Dynamic charge optimization (~25% faster recharge vs. open-loop)
- XW+ "Fixed" and "Dynamic" settings overwritten by BMS automatically
- User retains control of "Adjustable" settings (Grid Support, gen triggers) via InsightLocal
- SOC-based triggers recommended over voltage-based

**Communication failure behavior (important for no-generator setup):**
- XW+ continues with last received settings (no error displayed)
- Over time, could overcharge/over-discharge batteries
- BMS self-protects and disconnects when limits reached
- Manual intervention required to restart
- Mitigation: wired CAN bus — failures are rare

**Critical:** Conext Battery Monitor is INCOMPATIBLE with LYNK II — must be removed from Xanbus if present.

---

## Complete Bill of Materials

### Main Components

| # | Item | Part Number | Qty | Unit Price | Extended | Source |
|---|------|-------------|-----|-----------|----------|--------|
| 1 | AES Rackmount Battery | 48-48-5120 | 4 | $1,363.50 | $5,454.00 | Inverter Supply |
| 2 | Cable Kit (SurLok→M8, 2m) | 950-0055 | 4 | $129.05 | $516.20 | Inverter Supply |
| 3 | LYNK II Comm Gateway | 950-0025 | 1 | ~$400.00 | ~$400.00 | Inverter Supply |
| 4 | Quick Stack Rack | 950-0050 | 4 | $74.00 | $296.00 | Inverter Supply |
| 5 | Victron Lynx Power In M8 | LYN020102000 | 1 | ~$150.00 | ~$150.00 | Inverter Supply / Current Connected |

### Communication Cables

| # | Item | Spec | Qty | Unit Price | Extended | Source |
|---|------|------|-----|-----------|----------|--------|
| 6 | AEbus patch cables | CAT5e RJ45, 1–2 ft | 4 | ~$5.00 | ~$20.00 | Amazon |
| 7 | Xanbus patch cable | CAT5e RJ45, length TBD | 1 | ~$5.00 | ~$5.00 | Amazon |
| 8 | AEbus Terminator | RJ45 terminator plug | 1 | ~$10.00 | ~$10.00 | Discover / Amazon |

### Configuration

| # | Item | Spec | Qty | Unit Price | Extended | Source |
|---|------|------|-----|-----------|----------|--------|
| 9 | USB cable for LYNK II | Type-B mini | 1 | ~$8.00 | ~$8.00 | Amazon |

### Hardware — Lynx Side Tab Connections (Inverter Cables)

| # | Item | Spec | Qty | Unit Price | Extended | Source |
|---|------|------|-----|-----------|----------|--------|
| 10 | M8 stainless steel bolts | M8-1.25 × 25mm (or 1") | 2 | — | — | Hardware store |
| 11 | M8 stainless steel nuts | M8-1.25 | 2 | — | — | Hardware store |
| 12 | M8 flat washers | Stainless | 4 | — | — | Hardware store |
| 13 | M8 lock washers | Stainless (split or Nordlock) | 2 | — | — | Hardware store |
| | | | | **Hardware subtotal:** | ~$10.00 | |

### Mounting

| # | Item | Spec | Qty | Unit Price | Extended | Source |
|---|------|------|-----|-----------|----------|--------|
| 14 | Lynx Power In mounting screws | Per Lynx manual (may be included) | — | — | ~$5.00 | Hardware store |
| 15 | Wall anchors / wood screws | For right wall mounting | — | — | ~$5.00 | Hardware store |

### Optional but Recommended

| # | Item | Spec | Qty | Unit Price | Extended | Source |
|---|------|------|-----|-----------|----------|--------|
| 16 | Anti-oxidant compound | No-Ox-Id or Ox-Guard | 1 | ~$10.00 | ~$10.00 | Amazon / hardware store |
| 17 | Cable ties / velcro straps | For cable management | 1 pkg | ~$8.00 | ~$8.00 | Amazon |

---

### Cost Summary

| Category | Cost |
|----------|------|
| Main components (items 1–5) | $6,816.20 |
| Communication cables (items 6–8) | ~$35.00 |
| Configuration cable (item 9) | ~$8.00 |
| Side tab hardware (items 10–13) | ~$10.00 |
| Mounting hardware (items 14–15) | ~$10.00 |
| Optional items (items 16–17) | ~$18.00 |
| **Total hardware** | **~$6,897** |
| AGM recycling credit (2,032 lbs) | −$300 to −$500 |
| **Estimated net cost** | **~$6,400 to $6,600** |

---

### Tools Required (on hand or borrow)

- Wrenches: 13mm (for M8 nuts/bolts)
- Torque wrench capable of 14 Nm / ~10 ft-lbs (for M8 connections)
- Multimeter (voltage verification)
- Phillips screwdriver (rack assembly, Lynx mounting)
- Windows 10/11 64-bit laptop (LYNK ACCESS software)

### No Special Tools Needed

- No hydraulic crimper — all cables come pre-terminated
- No drilling — all holes pre-made
- No soldering
- Assembly is entirely bolt-on connections with standard wrenches

---

## Installation Timeline — Summer Solstice Target

### Pre-Install (Days −3 to −1)

- [ ] All hardware received and inspected
- [ ] Verify 950-0055 cable reach: 2m (6.5 ft) from each battery to right-wall Lynx
- [ ] Test-fit one Quick Stack Rack bracket on one battery
- [ ] Verify M8 bolt fits through Lynx Power In side busbar tab
- [ ] Verify M8 bolt + inverter lug + washers + nut fits side tab properly
- [ ] Install LYNK ACCESS software on Windows laptop
- [ ] Download Discover manual 805-0052 REV B
- [ ] Confirm Conext Battery Monitor NOT present on Xanbus (remove if found)
- [ ] Arrange helper for AGM removal (2,032 lbs — two-person minimum)
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
| 12:30–1:00 PM | Install LYNK II: connect AEbus daisy chain between all 4 batteries | 30 min |
| 1:00–1:15 PM | Connect AEbus from Battery #4 to LYNK II | 15 min |
| 1:15–1:30 PM | Install AEbus terminator on Battery #1 | 15 min |
| 1:30–2:00 PM | Connect LYNK II CAN Out to Xanbus network (RJ45 patch cable) | 30 min |
| 2:00–3:00 PM | Configure LYNK II via USB + LYNK ACCESS: select Xanbus protocol, save | 1 hr |
| 3:00–3:30 PM | Verify on InsightLocal: Battery Bank = 400 Ah, SOC reporting active | 30 min |
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
- [ ] Configure SOC-based triggers on XW+ via InsightLocal (replace voltage-based)
- [ ] Set "Adjustable" parameters: Grid Support thresholds, low-SOC generator triggers

### Ongoing
- [ ] Integrate monitoring into OpenHAB via Modbus TCP (ports 502/503)
- [ ] Document final XW+ configuration settings
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

1. **☐ VERIFY: Inverter cable lug hole = M8 (5/16")**
   Status: Fullriver DC400-6 datasheet confirms M8 terminal studs. Lugs currently on those studs are almost certainly M8. Physical verification recommended tomorrow with breaker off.

2. **☐ VERIFY: No Conext Battery Monitor on Xanbus network**
   Check InsightHome device list. Must be removed before LYNK II installation.

3. **☐ VERIFY: LYNK II current pricing at Inverter Supply**
   Range seen: $328–$432. Budget at ~$400.

4. **☐ VERIFY: Lynx Power In M8 side tab bolt clearance**
   Confirm on receipt that M8 bolt passes through side busbar hole cleanly and lug + washers + nut fit without interference from housing.

5. **☐ MEASURE: Xanbus cable length**
   Distance from planned LYNK II location to nearest Xanbus RJ45 jack, to order correct length CAT5e patch cable.

---

## Reference Documents

| Document | Location / Link |
|----------|----------------|
| Original BOM | /mnt/user-data/uploads/docs/battery-bom-feb-2026.md |
| Battery box photo | /mnt/user-data/uploads/images/fullriver-battery-box.jpg |
| Lynx Distributor Manual | /mnt/user-data/uploads/docs/lynx-distributor-manual.pdf |
| LYNK II + XW+ Manual | [805-0052 REV B](https://discoverbattery.com/s4x_files/resources/des-lynk-2-schneider-xw-insighthome-xanbus-manual.pdf) |
| Fullriver DC400-6 Datasheet | [fullriver.com](http://www.fullriver.com/upload/article/20220723/62db951348bfe.pdf) |
| Quick Stack Rack Manual | 805-0056 |
| Schneider Modbus Maps | [solar.se.com](https://solar.se.com/us/wp-content/uploads/sites/7/2022/02/Conext-Gateway-InsightHome-InsightFacility-Modbus-Maps.zip) |

### Supplier Links

| Item | URL |
|------|-----|
| AES Rackmount Battery | [Inverter Supply](https://www.invertersupply.com/index.php?main_page=product_info&products_id=204421) |
| Cable Kit 950-0055 | [Inverter Supply](https://www.invertersupply.com/index.php?main_page=product_info&products_id=204427) |
| LYNK II Gateway | [Inverter Supply](https://www.invertersupply.com/index.php?main_page=product_info&products_id=204420) |
| Quick Stack Rack | [Inverter Supply](https://www.invertersupply.com/index.php?main_page=product_info&products_id=204430) |
| Lynx Power In M8 | [Inverter Supply](https://www.invertersupply.com/index.php?main_page=product_info&products_id=1221) |
| Lynx Power In M8 (alt) | [Current Connected](https://www.currentconnected.com/product/victron-lynx-power-in-distribution-system/) |

---

*Document generated February 27, 2026. Prices subject to change. Verify all pricing at time of order.*

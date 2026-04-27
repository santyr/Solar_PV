# LYNK II Deployment Guide

## Discover AES Rackmount → Schneider XW Pro 6848 + MPPT 60-150 (Xanbus)

**References:**
- Discover **805-0033** — LYNK II Installation and Operation Manual
- Discover **805-0043 REVD** — AES Rackmount Installation and Operation Manual

**System:** 4× AES Rackmount 48-48-5120 → LYNK II → XW Pro 6848 NA 120/240 + MPPT 60-150 via Xanbus
**Expected Battery Bank Capacity after configuration:** 400 Ah (4 × 100 Ah, 20.48 kWh usable)

---

## Prerequisites

* All 4 batteries physically installed, powered ON, and cabled to Lynx Power In M8
* System live and charging (DC voltage confirmed ~53V on InsightLocal)
* Windows VM running (Win 11 Eval) with USB passthrough enabled
* LYNK ACCESS software (2.5 or later) downloaded from discoverlithium.com and installed on Windows VM
* USB Type-B mini cable on hand
* 5× CAT5e or higher patch cables (1–2 ft): 4 for LYNK Network daisy chain (LYNK II → 4 batteries), 1 for Xanbus connection from LYNK II CAN Out
* Confirm NO Conext Battery Monitor on the Xanbus network (incompatible with LYNK II)

> **Note on cabling:** The LYNK II manual specifies "CAT5e or higher" for the LYNK Network. The AES Rackmount ships with one CAT6 patch cable in the box per battery, which can be used as part of the daisy chain. Standard straight-through Ethernet patch cables only — never crossover cables.

> **Termination note:** Both the LYNK II Communication Gateway and the AES Rackmount battery modules are **internally terminated** by default. **No external terminator is required** anywhere on the LYNK Network. Per the LYNK II manual: *"No extra termination is required as the LYNK II Communication Gateway and AES RACKMOUNT batteries are terminated internally."*

---

## Phase 1: Verify LYNK II Jumper Configuration (Xanbus Pinout)

**Do this with LYNK II powered off and disconnected from everything.**

The LYNK II ships with internal jumpers that map CAN H, CAN L, and CAN GND signals to the RJ45 CAN Out port. For Xanbus, the pin assignments must be:

| Signal | Header Jumper | RJ45 Pin |
| --- | --- | --- |
| CAN L | H3 - 6-8 | Pin 4 |
| CAN H | H2 - 7-9 | Pin 5 |
| CAN GND | H2 - 2-4 | Pin 6 |

### Steps:

1. Open the LYNK II enclosure per manual 805-0033 to access the header board.
2. Locate headers H2 and H3 (refer to the Schneider Electric Xanbus pin assignments figure on page LV-BMS 42 of 805-0033).
3. Verify jumper on **H3** bridges pins **6–8** (CAN L → RJ45 pin 4).
4. Verify jumper on **H2** bridges pins **7–9** (CAN H → RJ45 pin 5).
5. Verify jumper on **H2** bridges pins **2–4** (CAN GND → RJ45 pin 6).
6. **Do not remove the LYNK Termination jumper** — leave it in place (LYNK II is internally terminated by default).
7. Close the enclosure.

> **Note:** These are the Xanbus-specific positions. If the jumpers are already set this way (common for units sold for Schneider integration), no changes are needed. Just verify.

---

## Phase 2: LYNK Network — Battery Daisy Chain

**Connect the batteries to the LYNK II via the LYNK Network (also called AEbus in the LYNK II manual).**

### Topology:

```
[LYNK II LYNK Port]──CAT5e──[B4 LYNK]──CAT5e──[B4 LYNK]──CAT5e──[B3 LYNK]──CAT5e──[B3 LYNK]──CAT5e──[B2 LYNK]──...──[B1 LYNK]
```

Each AES Rackmount battery has **two LYNK Ports** to support daisy-chain wiring (in/out).

### Steps:

1. Power OFF all batteries (press and hold the ON/OFF key on each).
2. Connect a CAT5e (or higher) patch cable from the **LYNK Port on the LYNK II** to one of the LYNK ports on Battery #4.
3. From the second LYNK port on Battery #4, run another CAT5e cable to a LYNK port on Battery #3.
4. Continue the daisy chain: B3 → B2 → B1, one cable between each adjacent pair.
5. Leave the unused LYNK port on Battery #1 (the far end of the chain) **open** — no terminator needed.
6. Power ON all 4 batteries (briefly press the ON/OFF key on each).

> **Important:**
> - Both LYNK II and the AES Rackmount modules are internally terminated. **Do NOT install an external terminator.**
> - Use straight-through CAT5e or higher cables. Never use crossover cables.
> - Keep LYNK Network cables physically separated from DC power cables to avoid interference.
> - Do NOT mix the LYNK Network with other CAN networks (Xanbus is connected separately at the LYNK II CAN Out side).

---

## Phase 3: USB Configuration via LYNK ACCESS

**Set the LYNK II communication protocol to "Schneider Electric - Xanbus".**

### Steps:

1. Connect the USB Type-B mini cable from the **LYNK II USB Mini Port** to your Windows VM.
2. Ensure USB device is passed through to the VM (VirtualBox: Devices → USB → select LYNK II device).
3. Confirm LYNK II has power (LED activity) — it draws power from the LYNK Network through the connected batteries. (A powered USB hub may be required if LYNK II is not yet on the battery network.)
4. Open **LYNK ACCESS** software.
5. Verify only one LYNK device is connected to the computer.
6. Select the **LYNK tab**.
7. Click the **blue gear icon** in the upper right of the CAN Settings tile.
8. From the pre-configured Closed-Loop Protocols dropdown, select **"Schneider Electric - Xanbus"**.
9. Click **SAVE**.
10. LYNK II will automatically restart after saving, briefly interrupting communications with other devices.
11. Wait for LYNK II to fully reboot (LED stabilizes).
12. Disconnect USB cable.

---

## Phase 4: Connect LYNK II to Xanbus Network

**Bridge the battery BMS data to the inverter/charger network.**

### Steps:

1. Connect a CAT5e (or higher) patch cable from the **LYNK II CAN Out port** to any available **Xanbus port** on the existing Xanbus chain (e.g., an open port on the XW Pro, MPPT 60-150, or InsightHome).
2. LYNK II CAN Out is **internally terminated** — no additional Xanbus termination is required at the LYNK II end.

> **Reminder:**
> - Only ONE LYNK device can be connected to the Xanbus network at a time.
> - Pins 1, 2, and 7 on the Xanbus connector carry power for Xanbus-enabled devices. Connect Xanbus cables only to other Xanbus ports — do NOT connect Xanbus to a LAN, CAN, or any other type of port.

### Final Network Topology:

```
[LYNK II]──LYNK──[B4]──LYNK──[B3]──LYNK──[B2]──LYNK──[B1]   (no terminator)
    │
    │ CAN Out (RJ45, Xanbus protocol)
    │
    ├─────────── Xanbus Network ──────────────┐
    │                │                        │
[InsightHome]   [XW Pro 6848]         [MPPT 60-150]
```

---

## Phase 5: Verification

### 5a. Verify Xanbus Connection

On InsightLocal, navigate to:

**Dashboard → Devices → Device Overview**

All 4 batteries should appear as a **single battery device** (represented by a Conext Battery Monitor icon, even though no physical monitor exists).

### 5b. Verify Battery Bank Capacity

Navigate to:

**Devices → Inverter/Charger → Configuration (Advanced) → Battery Settings**

Confirm **Battery Bank Capacity** reads **400 Ah** (4 batteries × 100 Ah each).

If it does not show 400 Ah:

* Check LYNK Network cable connections and confirm batteries are powered ON
* Confirm all batteries have the same firmware revision (use LYNK ACCESS to verify)
* Power-cycle batteries and LYNK II, then check again
* Verify the Schneider Electric - Xanbus protocol is selected in LYNK ACCESS

### 5c. Verify MPPT Battery Bank Capacity

Navigate to:

**Devices → MPPT Charge Controller → Configuration (Advanced) → Battery Settings**

Manually set **Battery Bank Capacity** to **400 Ah** (this is an Adjustable setting on the MPPT — it is not auto-populated like the XW Pro).

---

## Phase 6: XW Pro Configuration (InsightLocal)

There are **three** settings pages on the XW Pro that are relevant. Most Battery Settings are **Fixed** or **Dynamic** (auto-managed by the BMS over Xanbus). Only **Adjustable** settings need attention.

### 6a. Battery Settings

**Devices → Inverter/Charger → Configuration (Advanced) → Battery Settings**

Current AGM values (830 Ah, AGM, 3 Stage, SOC Disabled) will be overwritten by the BMS.

| Setting | Type | Action |
| --- | --- | --- |
| Battery Type | Fixed | BMS sets to **Custom** (currently AGM — will change automatically) |
| Charge Cycle | Adjustable | BMS sets to **2 Stage** (currently 3 Stage — will change) |
| SOC Control Enable | Adjustable | BMS sets to **Enable** (currently Disabled — will change) |
| Battery Bank Capacity | Fixed | BMS auto-sets to **400 Ah** (currently 830 Ah) |
| Maximum Charge Rate | Adjustable | Change to **100%** (currently 60% — was likely de-rated for AGM health) |
| Default Battery Temperature | Adjustable | Leave at **Warm** (BMS sends actual temp in closed loop) |
| Battery Temperature Coefficient | Adjustable | Set to **0 mV/°C** (currently 108 — not needed with BMS temp data) |
| Low Battery Cut Out Delay | Adjustable | Already set to **10 s** ✅ |
| Bulk Termination Time | Adjustable | Already set to **1 s** ✅ |
| Charge Cycle Timeout | Adjustable | Already set to **480 min** ✅ |
| High SOC Cut Out | Adjustable | Currently 99% — review after commissioning |
| Low SOC Cut Out | Adjustable | Currently 25% — review after commissioning (consider 10-20% for lithium) |

All voltage-based settings (Low/High Battery Cut Out, Bulk Termination Voltage, Absorption/Boost voltages) are **Fixed** or **Dynamic** — the BMS overrides them automatically. Ignore displayed values.

> **Reference:** AES Rackmount nominal charge profile per 805-0043 REVD Table 3-1 — Bulk/Absorption 55.2 V, Float 53.6 V, Low Voltage Disconnect (recommended) 48.0 V, hard LVD 40.0 V. The BMS communicates these dynamically; no manual entry is required.

### 6b. Battery Management System Settings (Comms-Loss Fallback)

**Devices → Inverter/Charger → Configuration (Advanced) → Battery Management System Settings**

These define what the XW Pro does if LYNK II communication is lost. **Critical for off-grid operation.**

| Setting | Current Value | Recommendation | Notes |
| --- | --- | --- | --- |
| BMS Communication Loss Triggers | **Fault** | **Warning** | See "graceful degradation" notes below |
| BMS Communication Loss Trip Time | **7 s** | **7–10 s** ✅ | How long comms must be lost before the trigger fires |
| SOC Communication Loss Triggers | **Warning** | **Warning** ✅ | Less severe — just alerts, doesn't trip |
| SOC Communication Loss Trip Time | **7 s** | **7 s** ✅ |  |
| Comms Lost Charge Voltage Limit | **55 V** | **55 V** ✅ | Below the AES Rackmount 55.2 V max — safe ceiling for LFP |
| Comms Lost Discharge Voltage Limit | **45 V** | **45 V** ✅ | Above the BMS hard cutoff (40 V) and below recommended LVD (48 V) |
| Comms Lost Charge Current Limit | **0 A** | **50 A** | See note below — graceful degradation |
| Comms Lost Discharge Current Limit | **0 A** | **50 A** | See note below — graceful degradation |
| Charge Overcurrent Offset | **5 A** | **5 A** ✅ |  |
| Discharge Overcurrent Offset | **5 A** | **5 A** ✅ |  |
| Overvoltage Offset | **1 V** | **1 V** ✅ |  |
| Undervoltage Offset | **3 V** | **3 V** ✅ |  |

**Comms-Loss Current Limits — Off-Grid Configuration (Graceful Degradation):**

The default 0A/0A current limits would cause an instant blackout on comms loss. For a no-generator earthship, graceful degradation is the better approach — the system continues at reduced power with conservative voltage limits while the BMS remains the ultimate safety net.

| Setting | Current Value | Change To |
| --- | --- | --- |
| BMS Communication Loss Triggers | Fault | **Warning** |
| Comms Lost Charge Current Limit | 0 A | **50 A** |
| Comms Lost Discharge Current Limit | 0 A | **50 A** |

All other BMS Settings values are fine as-is. The 55V charge ceiling and 45V discharge floor are conservative and safe for LFP chemistry. If comms drop, the system runs at reduced capacity within safe voltage limits, giving you time to notice and fix the issue without losing the house. The battery BMS still self-protects if anything goes out of range.

### 6c. Charger Settings

**Devices → Inverter/Charger → Configuration (Advanced) → Charger Settings**

| Setting | Type | Action |
| --- | --- | --- |
| ReCharge Voltage | Adjustable | Disabled when SOC Control is enabled — ignore |
| Charge Block Start/Stop | Adjustable | N/A — off-grid, no AC charging source |

---

## Phase 7: MPPT 60-150 Configuration (InsightLocal)

### Charger Settings

**Devices → MPPT Charge Controller → Configuration (Advanced) → Charger Settings**

| Setting | Type | Current Value | Change To |
| --- | --- | --- | --- |
| Charge Cycle | Adjustable | 3 Stage | **3 Stage** ✅ no change |
| Charge Mode | Adjustable | Primary | **Primary** ✅ no change |
| Default Battery Temperature | Adjustable | Warm | **Warm** ✅ no change |
| Equalize Now | Fixed | Disabled | BMS disables — no change |
| Maximum Charge Rate | Adjustable | 80% | **100%** (de-rating not needed for lithium) |
| Absorption Time | Adjustable | 60 min | **180 min** (per Discover recommendation) |

All voltage set points (Bulk/Boost, Float, Absorption, Equalize, Recharge) are **Fixed** or **Dynamic** — BMS manages them. Ignore displayed values.

### Battery Settings

**Devices → MPPT Charge Controller → Configuration (Advanced) → Battery Settings**

| Setting | Type | Current Value | Change To |
| --- | --- | --- | --- |
| Nominal Battery Voltage | Adjustable | 48 V | **48 V** ✅ no change |
| Battery Type | Adjustable | AGM | **Custom** |
| Battery Bank Capacity | Adjustable | 830 Ah | **400 Ah** (4 × 100 Ah) |
| Battery Temperature Coefficient | Adjustable | -84 mV/°C | **0 mV/°C** (BMS sends actual temp) |

---

## Communication Failure Behavior

**Critical for off-grid / no-generator operation:**

* If LYNK II loses communication with Xanbus for >7-10 seconds, the XW Pro and MPPT will trigger the configured Comms Loss action (Warning, with graceful-degradation current limits per Section 6b).
* Over time, stale parameters can push the battery to over-charge or over-discharge, at which point the **BMS self-protects** and disconnects the battery.
* **Manual intervention required** to restart: reconnect LYNK Network → LYNK II → Xanbus. If unsuccessful, restart batteries and XW Pro, and convert to open-loop before resuming.
* Wired CAN bus failures are rare but worth monitoring, especially in a no-generator setup where an unexpected battery disconnect means losing the house.

---

## Post-Deployment Checklist

* Battery Bank Capacity shows 400 Ah on XW Pro Battery Settings
* Battery Type changed from AGM to Custom (auto by BMS)
* SOC Control shows Enabled (auto by BMS)
* Charge Cycle changed to 2 Stage (auto by BMS)
* Maximum Charge Rate changed to 100% (from 60%)
* Battery Temperature Coefficient set to 0 mV/°C on XW Pro
* Low Battery Cut Out Delay confirmed at 10 seconds
* Bulk Termination Time confirmed at 1 second
* BMS Setup page left at "None" (does not apply to XW Pro with LYNK II)
* Comms-loss fallback set to graceful degradation: Warning trigger, 50A charge/discharge limits
* Battery Bank Capacity manually set to 400 Ah on MPPT Battery Settings
* Battery Temperature Coefficient set to 0 mV/°C on MPPT
* MPPT Charge Cycle set to 3 Stage
* MPPT Battery Type set to Custom, 48V, 400 Ah
* MPPT Charge Mode set to Primary
* First full charge/discharge cycle monitored
* SOC accuracy cross-checked (LYNK II vs InsightLocal)
* Connection temperatures checked under load (all bus bar connections)
* **Warranty registered within 30 days of installation**

# LYNK II Deployment Guide
## Discover AES Rackmount → Schneider XW6848 + MPPT 60-150 (Xanbus)

**Reference:** Discover 805-0052 REV B  
**System:** 4× AES Rackmount 48-48-5120 → LYNK II → XW6848-21 + MPPT 60-150 via Xanbus  
**Expected Battery Bank Capacity after configuration:** 400 Ah (4 × 100 Ah)

---

## Prerequisites

- [ ] All 4 batteries physically installed, powered ON, and cabled to Lynx Power In M8
- [ ] System live and charging (DC voltage confirmed ~53V on InsightLocal)
- [ ] Windows VM running (Win 11 Eval) with USB passthrough enabled
- [ ] LYNK ACCESS software downloaded from discoverlithium.com and installed on Windows VM
- [ ] USB Type-B mini cable on hand
- [ ] 5× CAT5e patch cables (1–2 ft): 4 for AEbus daisy chain, 1 for Xanbus connection
- [ ] 1× AEbus RJ45 terminator
- [ ] Confirm NO Conext Battery Monitor on the Xanbus network (incompatible with LYNK II)

---

## Phase 1: Verify LYNK II Jumper Configuration (Xanbus Pinout)

**Do this with LYNK II powered off and disconnected from everything.**

The LYNK II ships with internal jumpers that map CAN H / CAN L signals to the RJ45 CAN Out port. For Xanbus, the pin assignments must be:

| Signal | Header | Jumper Position | RJ45 Pin |
|--------|--------|-----------------|----------|
| CAN H  | H2     | 7–9             | Pin 5    |
| CAN L  | H3     | 6–8             | Pin 4    |

### Steps:
1. Open the LYNK II enclosure per manual 805-0033 to access the header board.
2. Locate headers H2 and H3 (see Figure 2, page 10 of 805-0052).
3. Verify jumper on **H2** bridges pins **7–9** (CAN H → RJ45 pin 5).
4. Verify jumper on **H3** bridges pins **6–8** (CAN L → RJ45 pin 4).
5. **Do not remove the AEbus/LYNK termination jumper** — leave it in place (LYNK II is internally terminated by default).
6. Close the enclosure.

> **Note:** These are the Xanbus-specific positions. If the jumpers are already set this way (common for units sold for Schneider integration), no changes are needed. Just verify.

---

## Phase 2: AEbus Battery Network

**Connect the batteries to the LYNK II via AEbus daisy chain.**

### Topology:
```
[LYNK II AEbus Port]──CAT5──[B4]──CAT5──[B3]──CAT5──[B2]──CAT5──[B1]──[Terminator]
```

### Steps:
1. Power OFF all batteries (press and hold power buttons).
2. Connect a CAT5e patch cable from the **LYNK II AEbus port** to Battery #4's AEbus port.
3. Daisy chain: B4 → B3 → B2 → B1, one CAT5e cable between each.
4. Insert the **RJ45 terminator** into Battery #1's open AEbus port (the far end of the chain).
5. Power ON all 4 batteries.

> **Important:** Both LYNK II and the AES Rackmount modules are internally terminated. The terminator goes on the opposite end from LYNK II (Battery #1). Do NOT plug AEbus cables into the LYNK II Ethernet port — only the AEbus port.

---

## Phase 3: USB Configuration via LYNK ACCESS

**Set the LYNK II communication protocol to Xanbus.**

### Steps:
1. Connect the USB Type-B mini cable from the **LYNK II USB port** to your Windows VM.
2. Ensure USB device is passed through to the VM (VirtualBox: Devices → USB → select LYNK II device).
3. Confirm LYNK II has power (LED activity) — it draws power from the AEbus-connected batteries.
4. Open **LYNK ACCESS** software.
5. Verify only one LYNK device is connected to the computer.
6. Select the **LYNK tab**.
7. Click the **blue gear icon** (upper right of the CAN Settings tile).
8. Select the **pre-configured Xanbus protocol** from the dropdown.
9. Click **SAVE**.
10. LYNK II will automatically shut down and restart after saving.
11. Wait for LYNK II to fully reboot (LED stabilizes).
12. Disconnect USB cable.

---

## Phase 4: Connect LYNK II to Xanbus Network

**Bridge the battery BMS data to the inverter/charger network.**

### Steps:
1. Connect a CAT5e patch cable from the **LYNK II CAN Out port** to any available **Xanbus port** on the Xanbus network (e.g., an open port on the XW+ or InsightHome daisy chain).
2. LYNK II CAN Out is **internally terminated** — no additional Xanbus termination is required for the LYNK II end.

> **Reminder:** Only ONE LYNK device can be connected to the Xanbus network at a time.

### Final Network Topology:
```
[LYNK II]──AEbus──[B4]──AEbus──[B3]──AEbus──[B2]──AEbus──[B1]──[Terminator]
    │
    │ CAN Out (RJ45, Xanbus protocol)
    │
    ├─────────── Xanbus Network ──────────────┐
    │                │                        │
[InsightHome]   [XW+ 6848]            [MPPT 60-150]
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
- Check AEbus cable connections and terminator
- Confirm all batteries have the same firmware revision
- Verify all batteries are powered ON
- Restart batteries and LYNK II, then check again

### 5c. Verify MPPT Battery Bank Capacity
Navigate to:

**Devices → MPPT Charge Controller → Configuration (Advanced) → Battery Settings**

Manually set **Battery Bank Capacity** to **400 Ah** (this is an Adjustable setting on the MPPT — it is not auto-populated like the XW+).

---

## Phase 6: XW+ Configuration (InsightLocal)

There are **three** settings pages on the XW+ that are relevant. Most Battery Settings are **Fixed** or **Dynamic** (auto-managed by the BMS). Only **Adjustable** settings need attention.

### 6a. Battery Settings
**Devices → Inverter/Charger → Configuration (Advanced) → Battery Settings**

Current AGM values (830 Ah, AGM, 3 Stage, SOC Disabled) will be overwritten by the BMS.

| Setting | Type | Action |
|---------|------|--------|
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

### 6b. Battery Management System Settings (Comms-Loss Fallback)
**Devices → Inverter/Charger → Configuration (Advanced) → Battery Management System Settings**

These define what the XW+ does if LYNK II communication is lost. **Critical for off-grid operation.**

| Setting | Current Value | Recommendation | Notes |
|---------|--------------|----------------|-------|
| BMS Communication Loss Triggers | **Fault** | **Fault** ✅ | Keeps the current "Fault" setting — the inverter will trip on comms loss |
| BMS Communication Loss Trip Time | **7 s** | **7–10 s** ✅ | How long comms must be lost before the fault triggers |
| SOC Communication Loss Triggers | **Warning** | **Warning** ✅ | Less severe — just alerts, doesn't trip |
| SOC Communication Loss Trip Time | **7 s** | **7 s** ✅ | |
| Comms Lost Charge Voltage Limit | **55 V** | **55 V** ✅ | Safe ceiling for LFP (max cell voltage ~3.65V × 16 = 58.4V) |
| Comms Lost Discharge Voltage Limit | **45 V** | **45 V** ✅ | Conservative floor (BMS would disconnect at ~42V anyway) |
| Comms Lost Charge Current Limit | **0 A** | **See note below** | |
| Comms Lost Discharge Current Limit | **0 A** | **See note below** | |
| Charge Overcurrent Offset | **5 A** | **5 A** ✅ | |
| Discharge Overcurrent Offset | **5 A** | **5 A** ✅ | |
| Overvoltage Offset | **1 V** | **1 V** ✅ | |
| Undervoltage Offset | **3 V** | **3 V** ✅ | |

**Comms-Loss Current Limits — Off-Grid Configuration (Graceful Degradation):**

Your current 0A/0A settings would cause an instant blackout on comms loss. For a no-generator earthship, graceful degradation is the better approach — the system continues at reduced power with conservative voltage limits while the BMS remains the ultimate safety net.

| Setting | Current Value | Change To |
|---------|--------------|-----------|
| BMS Communication Loss Triggers | Fault | **Warning** |
| Comms Lost Charge Current Limit | 0 A | **50 A** |
| Comms Lost Discharge Current Limit | 0 A | **50 A** |

All other BMS Settings values are fine as-is. The 55V charge ceiling and 45V discharge floor are conservative and safe for LFP chemistry. If comms drop, the system runs at reduced capacity within safe voltage limits, giving you time to notice and fix the issue without losing the house. The battery BMS still self-protects if anything goes out of range.

### 6c. Charger Settings
**Devices → Inverter/Charger → Configuration (Advanced) → Charger Settings**

| Setting | Type | Action |
|---------|------|--------|
| ReCharge Voltage | Adjustable | Disabled when SOC Control is enabled — ignore |
| Charge Block Start/Stop | Adjustable | N/A — off-grid, no AC charging source |

---

## Phase 7: MPPT 60-150 Configuration (InsightLocal)

### Charger Settings
**Devices → MPPT Charge Controller → Configuration (Advanced) → Charger Settings**

| Setting | Type | Current Value | Change To |
|---------|------|---------------|-----------|
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
|---------|------|---------------|-----------|
| Nominal Battery Voltage | Adjustable | 48 V | **48 V** ✅ no change |
| Battery Type | Adjustable | AGM | **Custom** |
| Battery Bank Capacity | Adjustable | 830 Ah | **400 Ah** (4 × 100 Ah) |
| Battery Temperature Coefficient | Adjustable | -84 mV/°C | **0 mV/°C** (BMS sends actual temp) |

---

## Communication Failure Behavior

**Critical for off-grid / no-generator operation:**

- If LYNK II loses communication with Xanbus for >10 seconds, the XW+ and MPPT **continue operating** with the last received charge parameters.
- **No error or fault is displayed** on any Xanbus device — the failure is silent.
- Over time, stale parameters can push the battery to over-charge or over-discharge, at which point the **BMS self-protects** and disconnects the battery.
- **Manual intervention required** to restart: reconnect battery network → LYNK II → Xanbus. If unsuccessful, restart batteries and XW+, and convert to open-loop before resuming.
- Wired CAN bus failures are rare but worth monitoring, especially in a no-generator setup where an unexpected battery disconnect means losing the house.

---

## Post-Deployment Checklist

- [ ] Battery Bank Capacity shows 400 Ah on XW+ Battery Settings
- [ ] Battery Type changed from AGM to Custom (auto by BMS)
- [ ] SOC Control shows Enabled (auto by BMS)
- [ ] Charge Cycle changed to 2 Stage (auto by BMS)
- [ ] Maximum Charge Rate changed to 100% (from 60%)
- [ ] Battery Temperature Coefficient set to 0 mV/°C on XW+
- [ ] Low Battery Cut Out Delay confirmed at 10 seconds
- [ ] Bulk Termination Time confirmed at 1 second
- [ ] BMS Setup page left at "None" (does not apply to XW+ with LYNK II)
- [ ] Comms-loss fallback set to graceful degradation: Warning trigger, 50A charge/discharge limits
- [ ] Battery Bank Capacity manually set to 400 Ah on MPPT Battery Settings
- [ ] Battery Temperature Coefficient set to 0 mV/°C on MPPT
- [ ] MPPT Charge Cycle set to 3 Stage
- [ ] MPPT Battery Type set to Custom, 48V, 400 Ah
- [ ] MPPT Charge Mode set to Primary
- [ ] First full charge/discharge cycle monitored
- [ ] SOC accuracy cross-checked (LYNK II vs InsightLocal)
- [ ] Connection temperatures checked under load (all bus bar connections)
- [ ] **Warranty registered within 30 days of installation**

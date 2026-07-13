# openHAB Cutover Plan — Fullriver AGM → Discover AES Rackmount (Closed-Loop)

**Companion documents:**
[Battery Upgrade Plan](battery-upgrade-plan-rev2.md) (hardware/BOM/layout) and
[LYNK II Deployment Guide](lynk2-deployment-guide.md) (InsightLocal/BMS configuration).
This document covers only the **openHAB monitoring and automation layer** at
`192.168.1.161` — what changes, when, and how to verify it.

**Scope principle:** openHAB *observes and alerts*; it does not participate in
charge control. The LYNK II BMS owns charging. openHAB's jobs after cutover:
accurate SOC/telemetry, load automation gating, and **comms-loss alerting**
(the no-generator failure mode).

---

## Status as of 2026-07-13 (eve of hardware day)

Execution detail lives in the on-host runbook
(`~/openhab/docs/plans/2026-07-14-discover-aes-cutover-runbook.md`, v2).
Summary of what changed since this plan was written:

1. **Hardware day is a FULL site power-down** — the openHAB host itself goes
   dark and the site is offline (no internet). Phase 1 below is superseded by
   the runbook's pre-shutdown checklist (snapshot, disable
   `hex_southoutlet_cycle`, graceful `systemctl poweroff` before the battery
   disconnect) and post-boot recovery checklist (services → things → telemetry
   → rules, plus a known-bogus SoC window until Phase 3).
2. **LYNK II stays OFF the LAN** until later analysis (operator decision):
   closed-loop via Xanbus proceeds; LYNK ACCESS is USB-only. No openHAB step
   needs IP access to the LYNK II.
3. **Comms-loss alerting: IMPLEMENTED and tested** (decision revised later
   the same day): Nostr NIP-04 DM from the hexdaemon identity to the
   operator-monitored account, sent by staged rule `hex_bms_comms_watchdog`
   via a whitelisted exec script. End-to-end tested through the openhab
   service user; enable in Phase 2. Caveat: it cannot page during a
   whole-site outage (no internet) — accepted.
4. **`SouthOutlet_LowSocCutoff` = 45** post-cutover (operator decision).
5. **Phase 0 is complete** (re-verified 2026-07-13): registers identified
   (XW Pro = gateway unit 10; storage model 40216–40231), poller + items
   staged disabled (items tagged `cutover-staged` after a dead-item sweep
   deleted three of them), AGM history pg_dump taken without sudo via the
   persistence DB credentials, snapshots moved out of `/tmp` to
   `~/openhab/backups/cutover-20260714/` with an offsite copy on lnnode.
6. **Phases 2/3 are pre-staged**: rules `hex_bms_soc_scale` (raw→BMS_SOC
   scaling + freshness) and `hex_bms_soc_passthrough` (SOC authority swap,
   400 Ah / 20 % floor derivations) exist DISABLED; the SouthOutlet re-gate
   and all dashboard edits are ready-to-apply BEFORE/AFTER JSON artifacts in
   the backups dir. Hardware day is enable-and-verify.
7. **Display cards added to scope** — see the expanded dashboard step in
   Phase 3: Overview battery card (AGM Float-implies-full logic), Solar page
   Battery block (SoC/voltage color bands, EMA footer, runtime floor label,
   new BMS SOC + BMS Comms cards), `battery-metrics-vertical` widget
   (runtime floor label). Chart pages and `UpdateBatteryIcon` need no edits.

---

## What the battery change breaks in openHAB

| Component | Today (AGM, open-loop) | Problem after cutover |
|---|---|---|
| `Battery Soc` rule (coulomb counter) | Integrates `DCData_Current` against `TOTAL_CAPACITY_AH = 830`, tail-current full detection (`16.6 A`), temp factor, 40% SoC floor (`RUNTIME_DOD_LIMIT_PCT = 60`) | Every constant is wrong: capacity becomes 400 Ah, tail/temp/full logic is BMS-owned, floor moves to ~20% reserve. Whole estimation approach is obsolete — BMS reports true SOC |
| `voltage_to_soc.py` + `exec:command:battery_soc` thing | AGM voltage→SoC interpolation (50.0 V→80% … 52.0 V→100%) | Already orphaned (0 links, 0 rule refs). Meaningless on LiFePO4's flat curve at 51.2 V nominal. Delete |
| `hex_southoutlet_cycle` | Gates on `DCData_Voltage > 51.0` + SoC | 51.0 V is *below resting voltage* for the new bank — gate becomes always-true. Voltage gating is generally useless on LFP; must move to SOC gating |
| SunSpec battery telemetry (`modbus:tcp:schneiderBatterySunSpec`, 192.168.1.145:502, unit 1, model 802) | V/A/W raw registers scaled by `hex_dcdata_native_scale_side_by_side` | Source device chain changes (BMS → Xanbus → Insight). Registers/scale factors must be re-validated; model 802 SOC/SOH points may now populate from the BMS |
| `ChargerStatus` semantics (`mppt60_native_status_mapper`) | Bulk/Absorption/Float drive full-detection and charge-state classification | Stages become BMS-driven (XW auto-switches to 2-stage); Float no longer implies "approaching full". Mapper keeps working but downstream *interpretation* changes |
| Dashboards/widgets | Runtime row assumes 40% floor; Ah figures assume 830 Ah; voltage chart ranges sized for 48–58.8 V AGM swing | Labels and ranges wrong; `Battery_Remaining_Ah` derived from wrong capacity |
| `AGENTS.md` system map | Documents 16× DC400-6, tail-charge convention, "never pin 100% without tail confirmation" | Must be rewritten at cutover so future agents don't "fix" lithium behavior back to AGM assumptions |

What does **not** change: MPPT60 PV telemetry (503/unit 30), Conext gateway AC
telemetry, weather, the Schneider safety publisher mechanism (it gains a new
input), persistence policy (new items persist automatically under `*`).

---

## Phase 0 — Pre-cutover prep (do now, before hardware day)

1. **Preserve AGM telemetry history.** Do NOT drop `DCData_*`, `BatterySoC_*`,
   `Battery_*` Postgres tables — they are evidence in the CMS warranty dispute
   (88/625 EFC analysis). Take a dated dump:
   `sudo -u postgres pg_dump -d openhab -t 'item*' -t items > /backup/openhab-agm-history-<date>.sql`
2. **Delete the orphaned voltage-SoC path** (verified unused):
   thing `exec:command:battery_soc` and `/etc/openhab/scripts/voltage_to_soc.py`.
3. **Identify the XW Pro SOC register.** From the Schneider Conext/Insight
   Modbus map (linked in the upgrade plan), find the XW Pro device unit ID on
   the gateway and its "Battery State of Charge" register. Do this from the
   map + InsightLocal device list — do not guess addresses. The XW's
   SOC is BMS-fed once closed-loop is active, making it openHAB's
   authoritative SOC source.
4. **Stage (disabled) the new Modbus poller** for the XW SOC register under
   the existing 503 bridge, plus items `BMS_SOC`, `BMS_Comms_Status` (UI-managed,
   per house policy: REST, no files).
5. **Confirm alerting path.** The comms-loss watchdog (Phase 2) needs a way to
   reach a human. Verify what notification channel openHAB should use and test
   it end-to-end before hardware day.

## Phase 1 — Hardware day (openHAB in observation mode)

1. Before power-down: disable `hex_southoutlet_cycle` via REST
   (`POST /rest/rules/hex_southoutlet_cycle/enable`, body `false`). Its
   fail-closed design would handle the chaos anyway, but a deliberate disable
   is cleaner than relying on it.
2. Leave all telemetry rules running — they fail safe on NULL/stale and the
   transition data is useful.
3. Expect during the swap: `SchneiderTelemetry_Status` goes `STALE:dc|...`,
   `DCData_Voltage` UNDEF/garbage, `ChargerStatus` transitions. This is normal;
   no action.
4. After LYNK II commissioning (per deployment guide Phases 1–7), confirm from
   openHAB host: `DCData_Voltage` reads ~51–54 V, `SchneiderTelemetry_Status`
   returns to `OK`.

## Phase 2 — Re-baseline telemetry (first 48 h)

1. **Re-validate SunSpec model 802** at 502/unit 1: voltage, current, power
   raw registers and scale factors under lithium voltage range. Check whether
   SOC/SOH points now populate (BMS-fed). Compare against InsightLocal and
   LYNK ACCESS readings.
2. **Enable the XW SOC poller** staged in Phase 0. Run `BMS_SOC` side-by-side
   against the legacy coulomb counter — do not relink anything yet
   (same side-by-side discipline as the dc_data.py migration).
3. **Stand up the comms-loss watchdog** (highest-value new automation):
   - Extend `hex_schneider_safety` with a `BMS_SOC` freshness source
     (LastUpdate stamp + stale threshold, same pattern as existing sources).
   - Alert on: `BMS_SOC` stale > 120 s, SOC frozen while current is flowing,
     or charger status inconsistent with BMS state.
   - Rationale (deployment guide "Communication Failure Behavior"): LYNK
     comms loss > ~10 s triggers fallback current limits; prolonged loss ends
     in BMS self-protect disconnect = **dark house, no generator**. openHAB is
     the only component positioned to page a human before that point.
4. Verify persistence is capturing the new items (`/rest/persistence/items/BMS_SOC?serviceId=jdbc`).

## Phase 3 — Logic cutover (after BMS_SOC validates)

1. **Replace the `Battery Soc` rule** (uid `8af1f76a8b`): retire coulomb
   integration, tail-current detection, temp factor, and the 100%-pin guard.
   New rule derives from `BMS_SOC`:
   - `BatterySoC_Calculated` = BMS_SOC passthrough (keeps every downstream
     consumer working unmodified),
   - `Battery_Remaining_Ah` = 400 × SOC/100,
   - `Battery_Runtime_Hours` = time to **20% reserve floor** (was 40%) from
     current draw,
   - `Battery_TimeToFull_Hours` from charge current.
   Keep the old rule disabled (not deleted) for one week as rollback.
2. **Re-gate `hex_southoutlet_cycle`:** drop the 51.0 V voltage threshold
   (meaningless on LFP), gate on SOC only. Revisit `SouthOutlet_LowSocCutoff`
   (80.2 was sized for AGM cycle-life protection at 50% DoD; with 100% DoD
   lithium and 20% reserve the operator may want a different number —
   **operator decision, ask before changing**).
3. **Dashboards / display cards** (ready-to-apply artifacts prepared
   2026-07-13, see runbook 3.3):
   - Solar page Battery block: SoC color bands 80/50 → 50/30; voltage bands
     48.5/50/57.8 → 47/49.5/57.6; `Battery_Voltage_EMA` footer → live power;
     "Runtime to 40%" → "Runtime to 20%"; new BMS SOC + BMS Comms cards.
   - Overview battery card: drop the AGM `Float && SoC≥99` full-detection
     clause (Float no longer implies full under BMS control); keep the
     `BatteryChargingStatus` animation (item stays — maintained by
     `UpdateBatteryIcon`).
   - `widget:battery-metrics-vertical`: floor label 40%→20%; Ah values
     self-correct via the passthrough rule (400 Ah basis).
   - No edits needed: `BatteryVoltage`/`BatteryCurrent` chart pages
     (auto-scale) and `UpdateBatteryIcon` (SoC-percent based).
4. **Update `AGENTS.md`:** system map (4× AES 48-48-5120, 4P, closed-loop
   LYNK II), remove tail-charge/AGM conventions, add comms-loss watchdog as
   protected safety chain, note BMS owns charge control.

## Phase 4 — Validation and cleanup (first full week)

1. Monitor one full charge/discharge cycle; cross-check `BMS_SOC` vs LYNK
   ACCESS vs InsightLocal (matches the upgrade plan's post-deployment
   checklist item).
2. Confirm `SchneiderTelemetry_Status` stays `OK` and the watchdog has not
   false-alarmed; tune staleness thresholds if needed.
3. Retire AGM-specific items once nothing references them:
   `Battery_Voltage_EMA`, `Battery_Voltage_EMA_Ts`, `Battery_TailOk_Since`,
   `Battery_Rest_Since`, `BatteryChargingStatus` (verify each via
   `/rest/links` and rule grep first). Keep their history per Phase 0.
4. Delete the disabled legacy `Battery Soc` rule after the rollback window.
5. Re-run the standard verification checklist (AGENTS.md): all rules IDLE,
   no unexpected OFFLINE things, log clean, no stale diagnostics.

---

## Rollback

Hardware rollback is out of scope (see upgrade plan). openHAB rollback at any
phase = re-enable the disabled legacy `Battery Soc` rule, re-enable
`hex_southoutlet_cycle` with its previous config, disable the BMS_SOC
passthrough. All replaced configs are managed objects — snapshot
`/var/lib/openhab/jsondb/automation_rules.json` and the items JSONDB before
Phase 3, per standing backup policy (`/tmp`, dated).

## Open questions for the operator

1. ~~Notification channel for the comms-loss watchdog~~ — RESOLVED
   2026-07-13: **Nostr DM (hexdaemon → operator)**, implemented and
   end-to-end tested; staged rule enables in Phase 2.
2. ~~Post-cutover `SouthOutlet_LowSocCutoff` value~~ — RESOLVED 2026-07-13:
   **45**.
3. Whether AGM history should be archived out of the live `openhab` DB
   (13 GB today) once the warranty dispute settles, or kept in place.
4. When (and whether) to put the LYNK II on the LAN — deferred pending
   later analysis; everything works without it.

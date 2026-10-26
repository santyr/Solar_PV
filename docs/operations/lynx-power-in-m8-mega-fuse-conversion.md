# Lynx Power In M8 — four-branch MEGA fuse conversion

**Recorded:** 2026-10-26  
**Status:** Operator-reported modification **in progress**; no as-built photo, electrical verification, or commissioning receipt yet.  
**Classification:** Modification of existing DC distribution hardware, **not** a Lynx Distributor purchase or an inverter-system migration.

## Intent and existing topology

The installed battery bank consists of four parallel Discover AES Rackmount
48-48-5120 LiFePO4 modules, 51.2 V / 100 Ah / 5.12 kWh each (20.48 kWh nominal
total). The current DC distribution part is the **Victron Lynx Power In M8**,
part LYN020102000, with four front battery cable pairs and a side connection for
the existing 4/0 inverter cables, as documented in the completed battery project.
The installed inverter remains **Schneider XW Pro 6848**; battery control remains
**Discover LYNK II to Schneider Xanbus**.

On 2026-10-26 the operator reported **modifying the existing Lynx Power In M8**
to accept **Victron Energy Blue Power MEGA-fuse 125 A / 80 V,
CIP138125020** in the individual positive battery branches, using published
community conversion examples rather than buying a new Lynx Distributor.
The operator's reported incremental **nuts, bolts, and washers cost is under
US$8**. This is the reported fastener/hardware cost, **not a verified installed
total**: fuse purchase cost, labor, inspection, and any additional protection
or rework are not established. Do not import distributor replacement costs as
the working plan.

**Do not mark these fuses installed, commissioned or adequate until the gates
below are satisfied.** The archived community examples are useful mechanical
precedent, not a certified manufacturer engineering instruction or evidence of
retained product listing/warranty.

## Proposed parts and evidence

| Item | Quantity / details | Evidence status |
| --- | --- | --- |
| Existing distribution enclosure | One Lynx Power In M8, LYN020102000 | Installed, recorded in completed upgrade project |
| New per-module fuse | Four Victron 125 A / 80 V MEGA fuses, **CIP138125020** | Operator-selected; physical installation unverified |
| Fasteners | Nuts, bolts and washers for conversion | Operator-reported budget **under $8**; exact grade and dimensions not recorded |
| Existing positive/negative battery cables | Four separate Discover module cable pairs | Record in completed battery project; field reconfirmation required |
| Existing main battery/inverter protection | Schneider path and existing device(s) | **Not verified** for fuse interrupt rating or coordination; do not assume absent or adequate |

Victron's price lists identify **CIP138125020** as a **MEGA-fuse 125A/80V**.
Victron community posts describe fitting MEGA fuses to a Lynx Power In; a
Victron Energy employee reported doing this using stainless fasteners.
Separate owners describe two-stage fastener torquing and contact flatness.
**None of these posts substitutes for a signed-off electrical design,
installation manual for this exact modification, or an approval of the
125A protection choice.**

### Required electrical and mechanical checks before commissioning

1. **Interrupt/breaking capacity: OPEN / SAFETY CRITICAL.** Verify the
   *exact fuse manufacturer's* published interrupt rating **at the DC voltage
   and installation conditions**, not just 125 A continuous / 80 V maximum
   working voltage. Verify the maximum **available prospective fault current
   at every proposed fuse and at the main DC protective device**, including
   backfeed from three other parallel modules through a faulted branch.
   The Discover 48-48-5120 installation manual lists **3.8 kA (100 ms)**
   maximum short-circuit fault current for a module and an integrated
   two-pole 100 A breaker; this is **not automatically the complete-bank
   fault-current calculation**. Confirm whether the selected MEGA fuse's
   breaking capacity is sufficient; if not, use appropriate adequately rated
   branch/main protection instead of treating the conversion as complete.
   Victron's *Wiring Unlimited* requires at least one adequately interrupt-
   rated battery DC fuse and stresses that fuse ampere rating alone is
   insufficient for lithium batteries.
2. **Protection coordination: OPEN.** Validate the 125 A MEGA fuse time-
   current behavior against each AES module's continuous 70 A, one-hour
   95 A, 3-second peak 218 A, integral 100 A breaker, selected cable ampacity,
   system surge conditions, and *both* directions of possible fault current.
   A 125 A fuse does not guarantee it opens before the battery breaker.
   Verify any separate inverter/main DC fuse and battery disconnect provisions.
3. **Mechanical/thermal: OPEN.** With appropriate qualified electrical
   isolation and installer review, verify the actual M8 interface, washer
   arrangement, stud engagement, fuse contact area/flatness, retaining
   clearance, busbar integrity, physical protection against accidental
   shorts, enclosure closure and cable strain. Use applicable **M8**
   manufacturer-approved connection torques; do not silently transfer M10
   specifications from newer Lynx manuals. Record both contact and
   post-commission thermal inspection results.
4. **Status/records: OPEN.** Photograph each branch and the complete bus,
   record fuse markings/lot, cable cross-sections and lengths, exact
   fasteners, torque/inspection results, observed protection path, the
   final DC one-line and a documented rollback to the previous topology.
   Confirm with insurer/AHJ/vendor whether modified equipment affects
   listing or warranty.
5. **Expansion: OPEN.** Four front positions are currently occupied by four
   batteries, while the 4/0 inverter cables use a side connection. A
   prospective fifth/sixth module would require a separately engineered
   protected distribution expansion; it is not enabled simply by adding
   the branch fuses. Size any expansion against measured winter deficits and
   the house's **10% SoC operational loss-of-load threshold**, considering
   load curtailment first.

**Scope boundary:** This document records operator intent and design
verification gates. It does **not** authorize rewiring, energizing, protection
setpoint changes or an assumption that modifications have passed inspection.
Discover BMS and the current Schneider protections remain the safety authority.

## Sources

- [2020 Victron Community: Power In fuse conversion, Victron employee comment](https://communityarchive.victronenergy.com/questions/55125/converting-a-lynx-power-in-hold-mega-fuses-lynx-di.html).
- [2023 Victron Community: Power In versus Distributor and owner conversion notes](https://communityarchive.victronenergy.com/questions/226845/lynx-power-in-or-distribution.html).
- [Victron fuse catalog and datasheets](https://www.victronenergy.com/dc-distribution-systems/fuses-and-fuse-holders).
- [Victron Wiring Unlimited — DC protection and lithium interrupt ratings](https://www.victronenergy.com/media/pg/The_Wiring_Unlimited_book/en/dc-wiring.html).
- [Discover AES Rackmount manual (48-48-5120)](https://discoverbattery.com/s4x_files/resources/des-aes-rackmount-user-manual.pdf).
- [Victron Lynx Power In manual; M8 discontinued and archived](https://www.victronenergy.com/media/pg/Lynx_Power_In/en/introduction.html).
- [Completed Discover AES bank installation project](../projects/completed/discover-battery-upgrade.md).

## Closure criteria

Update the [current-system record](../architecture/current-system.md) only
after operator/installer provides evidence that the conversion is complete,
correctly protected and commissioned. Preserve this design and verification
history rather than rewriting it as though protection had always existed.

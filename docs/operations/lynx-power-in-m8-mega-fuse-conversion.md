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

## Engineering review — 2026-10-26 (manufacturer-source cross-check)

**Finding: do not yet commission the CIP138125020 MEGA fuses as verified
battery-branch short-circuit protection.** The 125 A **normal-current**
selection and 80 V voltage rating are compatible with anticipated operating
currents and system voltage; this is **not** the same as a validated
high-current interruption design. No primary Victron datasheet located in
this review specifies the actual DC interrupt/breaking rating of this **exact
CIP138125020**. The Victron 80 V MEGA table publishes only approximate voltage
drop and cold resistance (**110 mV; 0.653 mΩ at the table's conditions**).
Published 1–2.5 kA breaking ratings for *other* MEGA series cannot be
transferred as certification, but justify concern.

### Different currents, different questions

| Situation | Relevant manufacturer figure | Interpretation |
| --- | --- | --- |
| Normal installed PV charging | Schneider MPPT 60-150: **60 A maximum total** | About **15 A/module** if four modules share equally; a 125 A branch fuse should not open in routine solar charging |
| XW Pro optional AC charging | **140 A DC maximum** in charger mode | **Not a current source in the documented no-AC-charging topology**; four-way balanced 35 A/module if added |
| XW Pro normal inverter output | **180 A DC** at rated continuous power | Four-way balanced **45 A/module** |
| XW Pro transient | Discover LYNK II example estimates **276 A** surge for 60s, which is not an independent sustained DC-current rating | Balanced **69 A/module**, assuming healthy equal branches |
| AES module protections | **70 A continuous, 95 A for one hour, 218 A/3 seconds, internal 100 A 2-pole breaker** | Not a limit on all prospective instantaneous fault contributions |
| AES published short-circuit contribution | **3.8 kA over 100 ms** for a *single module* | Evaluating fuse interrupt capacity requires **fault analysis**, not the XW Pro's normal rating |
| Four parallel AES modules | Screening arithmetic **up to ~15.2 kA** on a common-bus fault if four 3.8 kA figures coincided; **up to ~11.4 kA** from three peers into a faulted branch | These numbers are **illustrative, not certified prospective fault-current or fuse duty**; real values depend on voltage, impedance, fault location and BMS/breaker behavior |

The Discover internal 100 A breaker and BMS may open in some faults. But a
100 A **nominal breaker rating is not an interrupt-capacity rating** and
does not prove a downstream MEGA fuse will never encounter a much larger
prospective DC fault. A bus-end fuse also does not alone protect the entire
battery-to-bus cable against current sourced from the battery end.

### Schneider's additional inverter protection requirement

Schneider XW Pro NA installation guide **990-91228E-01**, pages **43–44**,
states: if installed with a **Power Distribution Panel (PDP)**, its integrated
DC breaker is rated **10 kA DC**, and where connected batteries/chargers have
**aggregate available short-circuit capability greater than 10 kA**, XW Pro
inverters and breakers **must be protected by current-limiting fuses**.
Examples listed by Schneider include **L17T400 (400 A, 100 kA)** and
**L50QS400 (400 A, 50 kA)**, distinct from the conventional
**250 A maximum** listed for 4/0 inverter cables in conduit. Schneider
specifically distinguishes equipment current-limiting protection from ordinary
wiring overcurrent protection; *do not* substitute a single 400 A fuse
for a 250 A wire-protection device just because both appear in this guide.

**As-built status unknown:** repository does not verify if this Earthship has
the Schneider PDP, the DC main breaker model and its DC interrupt rating,
or any high-interrupting current-limiting main fuse. The **10 kA** PDP rating
must not be assumed for an unidentified main breaker. A separate high-AIC
main device also **does not by itself establish selectivity or adequate
breaking capacity of individual downstream battery-branch MEGA fuses**.

### Cable ampacity is a second acceptance gate

The completed Discover installation plan describes **3 AWG copper** per-module
cables (950-0055). As a preliminary conventional NEC Table 310.16 reference,
3 AWG copper has **100 A at 75°C** and **115 A at 90°C** for the standard
three-or-fewer-conductors / 30°C ambient conditions; actual cable listing,
insulation, routing, ambient, terminal temperature and applicable rules must
be used. A **125 A fuse is not automatically permissible to protect that
cable**, even if normal current is far lower or the Discover battery contains
a 100 A breaker. A qualified designer should document the applicable
conductor ampacity and overcurrent exception/coordination, if any.
Do not infer that the 100 A breaker by itself prevents *backfeed* from other
modules through the bus into a faulted branch conductor.

### Better-documented alternative protection path

For comparison only, the **Eaton Bussmann JJN-125 Class T** product's own
datasheet explicitly rates it **125 A, 160 V DC, 20 kA DC interrupting**.
This is an example of the **kind of manufacturer-documented interrupt
rating** to seek. It does **not** fit the MEGA bolt footprint, is **not**
approved as a drop-in conversion in this Lynx Power In, and is **not**
selected for the installed 3 AWG cable without conductor and coordination
review. Suitable 100 A or alternative current-rated high-AIC
fuse/holder arrangements should be compared before committing to a BOM.

**Is adding fuses safer?** Properly designed **individual high-AIC branch
protection is preferable to leaving parallel battery branches without
independently coordinated fault isolation**, especially for faults fed by
other modules. **The exact low-cost 125 A MEGA retrofit cannot presently
be declared categorically safer than the existing installation** because a
fuse interrupting above its rating, poor modified contact, or incorrect
cable overcurrent coordination can itself cause fire or arc damage.
Do not energize the modified assembly relying on these fuses to clear
worst-case battery short-circuits without verified written ratings,
protection topology and installer approval. The fastener budget is
separate from the safety design.

### Close-out information to obtain

- Photo/model, placement and DC interrupt rating of the **existing main
  battery/inverter breaker/fuse/disconnect**, including whether a Schneider
  PDP is installed and any high-AIC current-limiting fuse.
- An **exact primary manufacturer DC interrupt-rating sheet**
  explicitly applicable to **CIP138125020** at the system's maximum DC
  voltage, including any required upstream protection/series rating.
- Discover identification / interrupt curve of the **actual 100 A internal
  breaker** and verified contribution/clearing calculations for each
  credible cable, busbar, and internal-battery fault.
- Cable assembly's actual **conductor size, insulation, listing, routing,
  temperature-rated terminations, permitted ampacity**, and an appropriate
  branch protection device's time-current curve.
- Modified Lynx fuse seat geometry/spacing, mechanical load, contact
  resistance/torque, enclosure and listing implications, plus qualified
  installer commissioning record.

### Primary sources for this review

- [Discover AES Rackmount 805-0043 Rev D, pp. 7 and 22](https://discoverbattery.com/s4x_files/resources/des-aes-rackmount-user-manual.pdf).
- [Schneider XW Pro installation guide 990-91228E-01, pp. 43–44](https://solar.se.com/us/wp-content/uploads/sites/7/2021/10/XW-Pro-NA-Installation-Guide_990-91228.pdf).
- [Victron MEGA fuse datasheet, 125 A / 80 V electrical values](https://www.a2t.ro/source/Fisa_tehnica_MEGA_fuse_125A80V.pdf).
- [Victron Wiring Unlimited §4.6.1 — lithium fault-current / interrupt-rating selection](https://www.victronenergy.com/media/pg/The_Wiring_Unlimited_book/en/dc-wiring.html).
- [Eaton Bussmann JJN-125 manufacturer specifications — 20 kA DC at 160 V](https://www.eaton.com/us/en-us/skuPage.JJN-125.html).
- [Victron community discussion: 80 V ceramic MEGA fuse data and questions](https://community.victronenergy.com/t/ceramic-mega-fuse-80v-125a-time-current-characteristic/19790).

## Updated field evidence — Schneider panel photographs and identified MEGA OEM (2026-10-26)

**New photo-backed observations supplied by the operator in the 2026-10-26
conversation; images have not been copied into this repository:**

- The upper/right-hand breaker is labeled **`INV 1 DISCONNECT`** and its
  operator-facing label reads **`ALM 250`**. The handle, markings and
  chassis visually match Schneider's **865DCBRK250**, listed by Schneider as
  a **250 A, 160 VDC** panel-mount inverter/battery breaker. Identification
  confidence is **high**, but the hidden actual part-number label remains
  unphotographed. Schneider also identifies a comparable former part number
  865-1065 for this function. **Nominal rating 250 A is not its DC
  interrupting/breaking rating.**
- The two other upper-panel breakers are labeled **`PV1 DISCONNECT` 60**
  and **`CHARGE CONTROLLER 1` 80**. Their layout is consistent with
  Schneider's XW PDP; exact PDP enclosure SKU and per-breaker DC voltage
  and interrupt ratings remain unverified from the frontal photo.
- The lower panel has **`INV1 IN (GRID)`**, **`GRID BYPASS`** and
  **`INV1 OUT (AC LOADS)`**, with Square D 60 A breakers marked
  **`10 kA 120/240V~`** and an output/bypass mechanical interlock.
  These labels refer to the **AC breakers**: their printed 10 kA AIC
  **must not** be treated as the DC main-breaker interrupt rating.
- The pictures strongly support the **Schneider XW Power Distribution
  Panel family** but do not confirm **865-1015-01 versus a similarly
  equipped Mini PDP or exact factory configuration**. A panel interior
  nameplate or invoice would resolve that.
- The photograph includes `TRIPPED` printed beside the DC breaker
  mechanism; its actual energized/trip state **cannot be established
  reliably from the photograph**, so do not assert an active DC fault.
- No separate high-interrupting **current-limiting main fuse is
  established by these photos**. It may be elsewhere in the circuit.
  Identifying one requires a physical as-built tracing or documentation,
  not an assumption that it is absent.

**Original primary-product cross-check:** Schneider's
[865DCBRK250 page](https://www.se.com/us/en/product/865DCBRK250/250a-160vdc-panel-mount-dc-breaker/)
links to an OEM front-view photograph matching the `ALM 250` sticker.
Schneider's [XW PDP 865-1015-01 page](https://www.se.com/us/en/product/865-1015-01/xw-power-distribution-panel/)
also explicitly lists a 250 A battery/inverter DC breaker and three AC breakers.

### Fuse OEM identification materially narrows, but does not close, the interrupt question

The operator clarified the exact proposed Victron fuse SKU as
**`CIP138125020`**. Victron's price list confirms **125 A / 80 V
ceramic MEGA fuse (five-pack)**. In [a January 2025 Victron Community
discussion](https://community.victronenergy.com/t/ceramic-mega-fuse-80v-125a-time-current-characteristic/19790),
a participant identifies **Zeeman** as the OEM for Victron's 80 V
ceramic MEGA range and provides the OEM **ANMH** product sheet. In
[a March 2025 discussion explicitly about the 125 A / 80 V Victron
fuse](https://community.victronenergy.com/t/victron-mega-fuse-fake/23732/6),
another comment repeats this Zeeman OEM identification.
Zeeman's **[ANMH primary manufacturer specifications](https://www.zeeman.cn/en/cproduct/Bolt-onFuses/2021-06-18/641.html)**
list **2,000 A at 80 VDC interrupting rating** for the ANMH series,
including a 125 A entry. Zeeman also publishes a slow-blow time-current
range, not instantaneous opening as soon as 125 A is exceeded.

**Important evidence tier:** OEM attribution comes from community
participants and a visually/physically matching product series, **not
an explicit Victron-issued cross-reference from CIP138125020 to Zeeman
ANMH 125**. Thus **2 kA is a strong provisional working figure, not a
certified interrupt rating for this exact Victron SKU**. Ask Victron or
its OEM for a written part-specific data sheet and any applicable
series-protection requirements.

**Safety consequence:** Discover specifies **3.8 kA (100 ms) for each
48-48-5120**. A common-bus fault can receive current from an individual
module through its individual branch fuse; a faulted battery branch
may receive current from **three healthy peer batteries**.
The possible fault currents can exceed **2 kA**. The aggregate
four-module source capability is arithmetically **4 × 3.8 kA = 15.2
kA** before site-specific impedance and dynamics; this is a
**screening ceiling, not a measured or validated prospective fault
current at the panel**. Even **one** module's 3.8 kA specified
contribution is larger than the likely 2 kA fuse-series AIC. Do
**not** qualify this modified Power In as independently high-AIC
branch protection without coordination design backed by component
manufacturer evidence.

Schneider's 990-91228E-01 guide says that its XW **PDP DC breaker
has 10 kA DC interruption**, unlike the lower AC devices' markings.
If aggregate available fault current exceeds 10 kA, Schneider
requires an independent current-limiting fuse protection arrangement
for the inverter and DC breaker. The newly photographed 250 A
breaker does **not** itself prove compliance with this requirement,
nor does it protect **all cross-feed faults between battery branches**.

**Updated engineering status:**
- **CONFIRMED:** a Schneider-pattern **250 A, 160 VDC** inverter
  breaker is present; 60 A PV-input and 80 A charge-controller
  breakers are present; Square D 60 A 120/240VAC breakers are present.
- **STRONGLY SUPPORTED, NOT PROVEN:** installed main breaker is
  Schneider **865DCBRK250** in an XW-series PDP.
- **SUPPORTED, NOT PROVEN FOR VIC­TRON SKU:** the 80 V 125 A ceramic
  MEGA family resembles Zeeman **ANMH**, **2 kA AIC**.
- **STILL OPEN:** actual short-circuit duty at fuse positions and
  main disconnect; exact main-fuse existence and location;
  exact CIP138125020 certified AIC; 3 AWG ampacity/terminal
  coordination; installation/contact approvals.
- **RECOMMENDATION:** retain the aim of individual battery fault
  isolation, but **defer energizing the unqualified MEGA modification
  as safety protection**. Compare appropriately DC-rated,
  high-interrupting branch protection with compatible cables,
  enclosures and placement after reviewing the actual DC single-line.
  The inexpensive fastener modification is not a substitute for
  rated protection.

## Closure criteria

Update the [current-system record](../architecture/current-system.md) only
after operator/installer provides evidence that the conversion is complete,
correctly protected and commissioned. Preserve this design and verification
history rather than rewriting it as though protection had always existed.

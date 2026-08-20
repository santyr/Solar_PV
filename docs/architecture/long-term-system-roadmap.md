# Long-Term Solar, Storage, and Energy-Control Roadmap

**Status:** Living planning document  
**Planning horizon:** 2026–2040+  
**Last updated:** 2026-08-19  
**Revision note:** Added Schneider product lifecycle / 2035 end-of-standard-service planning constraint.

**Companion documents:**
- [Current system](current-system.md) — verified installed-system baseline
- [Battery Upgrade Record](../projects/completed/discover-battery-upgrade.md) — Discover AES hardware design and installation record
- [LYNK II Deployment Record](../projects/completed/lynk2-deployment.md) — Schneider/Discover closed-loop commissioning
- [openHAB Cutover Record](../projects/completed/openhab-lithium-cutover.md) — monitoring and automation migration

---

## 1. Purpose

This document defines the long-term direction for the Earthship's off-grid power system. It is intentionally **not** a commitment to any specific future inverter, battery chemistry, solar module, or communications protocol.

The goal is to preserve flexibility while operating the current system for as long as it remains reliable and economically sensible. Future replacements should be selected using actual site data, the technology available at the time, and a strong preference for **local control, open interfaces, data ownership, repairability, and graceful component-by-component migration**.

The working assumption is that the present Discover battery bank and Schneider power electronics are a bridge into a substantially more capable generation of residential energy systems rather than hardware that must be kept indefinitely.

---

## 2. Current System Baseline — 2026

### Storage

- **4 × Discover AES Rackmount 48-48-5120** LiFePO4 modules
- **400 Ah / 20.48 kWh nominal bank capacity**
- Closed-loop battery control through **LYNK II → Xanbus → Schneider**
- Individual battery telemetry available through LYNK ACCESS
- Bank commissioned in 2026
- Battery #4 accumulated modest additional throughput because it operated alone for approximately two weeks while the remaining battery cables were pending

### Power electronics

- **Schneider XW Pro 6848** 120/240 V split-phase inverter/charger
- **Schneider MPPT 60-150** charge controller
- **InsightHome / InsightLocal** monitoring and configuration
- Discover BMS remains authoritative for battery charge/discharge limits and battery protection

### Schneider product support lifecycle — hard planning constraint

The current Schneider platform is already in its post-commercialization lifecycle in the United States:

| Component | U.S. status | End of standard service |
|---|---|---|
| **XW Pro 6848 (865-6848-21)** | Discontinued July 27, 2025 | **April 4, 2035** |
| **Conext MPPT 60-150 (865-1030-1)** | Discontinued July 19, 2025 | **April 4, 2035** |
| **InsightHome (865-0330)** | Discontinued July 17, 2025 | **April 4, 2035** |

Schneider defines *end of standard service* as the last date it expects to provide maintenance services such as repair and spare parts. As of August 2026, Schneider's U.S. product pages do not list direct replacements for these references.

This creates an important asymmetry in the long-term plan:

- the **Discover battery bank may still be healthy and useful well beyond 2035**;
- the Schneider inverter/MPPT/gateway ecosystem reaches its official service horizon first;
- therefore the next major migration is more likely to be **power electronics first, batteries later**.

**Planning rule:** treat **April 4, 2035** as the latest date by which a tested migration path away from dependence on Schneider factory service should exist.

This does **not** mean the Schneider equipment must be removed in 2035. If it remains reliable, it can continue operating as legacy equipment. However, continued operation after that date should assume reduced vendor repair/spares availability and should only occur with a replacement design, budget, configuration plan, and installation path already prepared.

**Recommended readiness targets:**

- **2026–2030:** preserve configuration backups, firmware, manuals, logs, and system documentation; monitor the replacement market.
- **2030–2032:** begin a serious architecture comparison, with Victron and other local-first platforms evaluated against actual site data.
- **By 2033:** select a preferred replacement architecture and validate compatibility with the then-current Discover bank if reuse is desirable.
- **2033–2034:** establish budget, BOM, installer/DIY plan, wiring changes, migration runbook, and fallback strategy.
- **Before April 2035:** be capable of replacing the XW Pro/MPPT/Insight stack without an emergency redesign.

### Solar array

- **12 × Qcells 350 W modules, 4.2 kW DC**, from the original quote as
  transcribed by the operator
- PV array, XW Pro, and MPPT installed **2021-08-06**
- Array tilt is intentionally optimized for **winter solar gain**
- Snow is manually cleared promptly to preserve winter production
- The array continues to produce useful energy under cloudy conditions, although at reduced power
- The exact Qcells model and string configuration remain a field-verification item before any future array redesign

### Monitoring and automation

- **openHAB** is the house automation and supervisory monitoring platform
- Long-term telemetry is persisted in **PostgreSQL**
- Schneider telemetry is currently consumed through local interfaces such as Modbus TCP
- The automation layer should observe, forecast, alert, and optimize, but **must not replace BMS/inverter hardware safety controls**

---

## 3. What the First Month of Discover Data Tells Us

The initial operating profile indicates that the current four-module battery bank is generously sized for normal daily use.

Observed summer behavior is approximately:

- Daily recharge to roughly **99–100% SOC**
- Typical overnight minimum around **85% SOC**
- Typical daily depth of discharge roughly **12–15%**
- Individual module current sharing and cell-voltage balance have been very close
- Batteries 1–3 accumulated only about **~6 equivalent full cycles** during the first month; Battery 4 is only modestly ahead because of its temporary solo operation

A first-order winter estimate, based on longer nights and the site's winter-optimized array, is:

- **Typical clear midwinter morning low:** approximately **78–83% SOC**
- Reaching **99–100% again on most winter days** is expected if historical site behavior continues
- The most important stress case is not the winter solstice itself, but an uncommon sequence of **multiple low-solar days without full recovery**

Historically, the site has had relatively few events requiring two or more days to return the battery bank to full. The 2026–2027 winter will provide the first direct validation with the Discover bank.

### Winter validation checkpoint

After sufficient December/January data exists, review:

1. Daily minimum SOC
2. Daily maximum SOC
3. Percentage of days reaching ≥99% SOC
4. Longest consecutive period without reaching full
5. Lowest SOC during a multi-day storm event
6. Daily PV production versus household load
7. Per-module current sharing and cell-voltage spread

**Current planning assumption:** a fifth battery is **not required** unless real winter data demonstrates repeated or operationally inconvenient multi-day deficits.

---

## 4. Battery Bank Life Planning

The current bank is expected to be **calendar-aging limited rather than cycle-life limited**.

Because normal cycling is shallow, a reasonable planning model is:

- **Primary planning horizon:** approximately **12–18 years** of useful service
- **Central planning assumption:** begin serious replacement evaluation around **year 12 (~2038)**
- The bank may remain useful well beyond that point if reduced capacity still comfortably meets overnight and storm-autonomy requirements
- Replacement should be based on **usable system capability**, not merely a nominal state-of-health threshold

For example, even a substantially aged bank with only ~70% of original capacity would still retain approximately **14.3 kWh**, which may remain comfortably above ordinary overnight requirements.

### Do not optimize away useful reserve

The system should not intentionally sacrifice off-grid resilience merely to minimize calendar aging. A high average SOC is less ideal electrochemically than mid-SOC storage, but the purpose of the bank is to provide reliable autonomy through uncertain weather.

The preferred strategy is therefore:

- shallow normal cycling
- moderate battery temperature
- closed-loop BMS control
- conservative low-SOC reserve
- full use of available capacity when weather requires it

### Future expansion rule

If an additional 48-48-5120 module is considered while the current bank is still young, the age mismatch should remain small because the existing batteries are accumulating very little cycle wear. Expansion should still follow Discover's then-current requirements for model compatibility, firmware, SOC/voltage matching, cabling, and commissioning.

Once the bank is materially older, expansion with a new module should be reconsidered against complete bank replacement with the best current technology.

---

## 5. Technology Assumption: 2038 Will Not Look Like 2026

The replacement system should not be designed today around the assumption that the best future choice will simply be another 48 V LFP rack battery.

By the late 2030s, plausible options may include:

- significantly improved LFP variants
- sodium-ion stationary storage
- manganese-enhanced lithium chemistries
- solid-state lithium where economics justify it
- zinc-, iron-, or flow-based storage
- technologies not yet commercially important in 2026

Sodium-ion is already becoming commercially relevant for stationary storage. Its lower dependence on lithium and potentially attractive safety, cost, and cold-weather characteristics make it particularly interesting for stationary applications where mass and volume are less important than in vehicles.

AI-assisted materials discovery, cell design, degradation modeling, manufacturing optimization, and BMS control are also likely to accelerate battery development. However, physical validation, manufacturing scale, field reliability, and safety certification will remain important constraints.

**Planning principle:** do not predict the winning chemistry. Preserve the ability to adopt it.

---

## 6. Future Inverter and Charge-Controller Direction

### Current leading architectural preference: Victron ecosystem

If replacement were being planned with today's technology, **Victron** would be a leading candidate because of its local integration model rather than because any particular 2026 inverter model is expected to be the right purchase in 2038.

Attributes worth preserving in a future platform include:

- true 120/240 V split-phase support suitable for the existing house
- local control without mandatory cloud dependence
- documented **Modbus TCP** and/or **MQTT** interfaces
- local event and telemetry access
- compatibility with third-party BMS systems
- programmable supervisory layer
- strong support for component-level service and replacement
- multi-inverter operation where appropriate
- native integration with house automation systems

Victron's current **Venus OS / GX** architecture is attractive because it can expose inverter, MPPT, and battery information locally and can coexist with Node-RED, MQTT, Modbus TCP, and other automation tools.

### Do not preselect a future model

Today's MultiPlus-II, Quattro, SmartSolar, Cerbo GX, and related products should be treated as **architecture examples**, not predetermined future purchases.

At replacement time, compare the then-current products from Victron and competitors against the requirements in this document.

### Split-phase requirement

The residence requires true **120/240 V split-phase** service. Any future inverter architecture must be evaluated specifically for battery-mode split-phase behavior rather than relying on product names that may imply 120/240 V pass-through without producing true split phase while islanded.

---

## 7. Solar Array Replacement Strategy

Solar modules should be treated differently from batteries and power electronics.

The existing array was installed around 2021 and may still have substantial productive life when the batteries or inverter electronics eventually require replacement.

### Default strategy

**Keep the existing modules as long as they remain productive and reliable.**

Do not replace panels merely because newer modules have higher efficiency.

A future array replacement becomes attractive when one or more of the following is true:

- meaningful module degradation
- physical damage or insulation faults
- failure of enough modules to make matching replacements impractical
- a future inverter/MPPT architecture strongly favors a different string voltage
- substantially more winter power can be obtained from the same available array area
- panel cost falls enough that replacement has a compelling autonomy or lifecycle benefit

### Winter performance remains the priority

Any future array design should retain the site's deliberate bias toward **winter production**, because winter is the limiting solar season for an off-grid system.

Snow-shedding behavior, manual access for clearing, low-sun-angle performance, and cold-weather string voltage must all remain explicit design considerations.

---

## 8. Desired Future Energy Architecture

The long-term target is a layered architecture in which each subsystem has a clear responsibility.

```text
                    ┌──────────────────────────────┐
                    │        PV ARRAY(S)           │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │  MPPT / POWER ELECTRONICS   │
                    │ deterministic local control │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
┌───────────────────────┐   ┌──────────────────────────────┐
│ BATTERY + HARDWARE BMS│◄─►│ INVERTER / AC POWER SYSTEM  │
│ safety authority      │   │ safety + real-time control  │
└───────────┬───────────┘   └──────────────┬───────────────┘
            │                               │
            └──────────────┬────────────────┘
                           ▼
               ┌────────────────────────┐
               │ LOCAL ENERGY GATEWAY   │
               │ MQTT / Modbus / API    │
               └────────────┬───────────┘
                            ▼
               ┌────────────────────────┐
               │ openHAB + PostgreSQL   │
               │ automation + history   │
               └────────────┬───────────┘
                            ▼
               ┌────────────────────────┐
               │ LOCAL AI ENERGY MODEL  │
               │ forecast / optimize /  │
               │ diagnose / recommend   │
               └────────────────────────┘
```

### Control hierarchy

1. **BMS and inverter hardware** own instantaneous electrical safety.
2. **Energy gateway** provides deterministic protocol translation and local control interfaces.
3. **openHAB** provides house-level state, automation, telemetry, and bounded control actions.
4. **Local AI** provides prediction, optimization, anomaly detection, and decision support.

The AI layer must never be the only mechanism preventing overcharge, over-discharge, over-current, unsafe temperature, or electrical faults.

---

## 9. Future Local AI Energy Manager

A future in-house AI model should be able to reason over the entire property rather than treating the battery as an isolated appliance.

Potential inputs include:

- battery SOC, SOH, voltage, current, temperature, and cell spread
- per-module battery telemetry
- PV generation and MPPT operating state
- inverter AC load and power quality
- historical household load patterns
- weather forecast and cloud cover
- modeled next-day PV yield
- sunrise/sunset and seasonal day length
- cistern levels and water-system status
- planned well pumping
- discretionary appliance loads
- equipment maintenance history
- historical fault/event logs

Potential bounded actions include:

- recommending or adjusting operating reserve targets
- deferring discretionary loads before a multi-day storm
- scheduling flexible loads when excess PV is expected
- identifying abnormal battery current sharing
- detecting gradual PV underperformance
- detecting inverter/MPPT efficiency changes
- predicting whether full recharge is likely before sunset
- warning when several days of energy deficit are developing
- recommending maintenance before a hard failure occurs

### Example future decision

```text
SOC:                  64%
Next 48 h forecast:   heavy cloud / snow
Expected PV yield:    below normal household load
Battery health:       normal
Cistern level:        adequate
Laundry:              optional
Well pumping:         non-urgent

AI recommendation:
- preserve battery reserve
- defer discretionary laundry
- defer non-essential well pumping
- alert operator if modeled minimum SOC approaches reserve threshold
```

The same model should recognize that an SOC of 64% before several clear winter days is not an emergency and avoid unnecessary intervention.

---

## 10. Data Strategy — Preserve the Training History Now

The usefulness of a future local AI model will depend heavily on the quality of historical data collected before it exists.

### Preserve long-term time series for

- battery SOC
- battery voltage/current/power
- individual battery/module values when available
- PV power and daily energy production
- inverter AC load and daily energy consumption
- MPPT state and limits
- charge/discharge limits supplied by the BMS
- minimum/maximum battery temperature
- cell-voltage spread
- fault and warning events
- weather data
- sunrise/sunset/day length
- major load state where available

### Derived metrics worth storing

- daily minimum SOC
- daily maximum SOC
- daily depth of discharge
- days reaching ≥99% SOC
- consecutive days without full recharge
- estimated equivalent full cycles
- daily PV yield
- daily consumption
- PV surplus/deficit
- overnight consumption
- seasonal load averages
- estimated battery efficiency
- per-module current-sharing deviation

### Data ownership principle

Whenever possible, operational history should remain locally accessible in standard formats such as PostgreSQL, CSV, MQTT, or documented APIs. Cloud dashboards may be useful but should not be the sole repository for critical long-term history.

---

## 11. Migration Philosophy: Replace Layers Independently

Avoid an unnecessary all-at-once replacement whenever interfaces allow components to be migrated safely in stages.

### Scenario A — Schneider electronics are replaced first

This is now the **default long-term scenario**, not merely a failure contingency, because Schneider standard service for the XW Pro, MPPT 60-150, and InsightHome is scheduled to end in 2035.

If the Discover batteries remain healthy:

1. Replace the inverter/charge-controller/gateway platform before or around the Schneider support horizon.
2. Reuse the Discover bank if it remains healthy and is safely supported by the new system.
3. Use LYNK II, native battery CAN, or whatever supported BMS interface exists at that time.
4. Preserve openHAB/PostgreSQL history and local automation interfaces.
5. Replace the batteries later when economics, health, or technology justify it.

A failure before 2035 may accelerate this schedule. Continued reliable operation after 2035 may delay physical replacement, but should not delay **migration readiness**.

### Scenario B — Battery bank ages first

If Schneider remains reliable:

1. Evaluate batteries compatible with the existing inverter architecture
2. Compare that against the cost/benefit of moving to a new complete power-electronics platform
3. Avoid buying a battery whose communications lock the property into an undesirable future ecosystem

### Scenario C — Major technology transition is economically compelling

If a future system offers a large improvement in cost, safety, autonomy, integration, or serviceability, replacing multiple layers together may be justified even before outright failure.

---

## 12. Replacement Triggers

### Battery replacement evaluation

Begin serious evaluation when one or more of the following occurs:

- useful capacity no longer meets normal winter-night requirements with adequate reserve
- multi-day weather events routinely approach the configured reserve
- SOH degradation accelerates materially
- module current sharing or cell balance degrades persistently
- BMS/electronics reliability becomes problematic
- replacement technology offers a compelling lifecycle advantage

**Calendar checkpoint:** begin formal market review around **2037–2038**, even if the bank remains healthy.

### Inverter / charge-controller replacement evaluation

Unlike the battery bank, the Schneider power electronics have a known external lifecycle deadline: **standard service ends April 4, 2035** for the current U.S. XW Pro 6848, MPPT 60-150, and InsightHome product references.

Therefore:

- architecture review should begin well before failure;
- a preferred replacement platform should be identified by approximately **2032–2033**;
- the site should be migration-ready by **2034**;
- operation beyond April 2035 is acceptable only as a deliberate legacy-hardware choice, not because no replacement plan exists.

Additional triggers for earlier replacement include:

- repeated hardware faults
- inability to obtain repair parts
- declining availability of spares
- loss of useful firmware or protocol support
- communications limitations that materially restrict automation
- poor efficiency compared with current systems
- need for substantially more PV or AC capacity
- opportunity to simplify the architecture while retaining local control

### PV replacement evaluation

Trigger review for:

- measurable degradation that affects winter autonomy
- repeated module failures
- inability to source electrically compatible replacement modules
- economically compelling increase in watts per available array area
- future MPPT/string-voltage redesign that makes panel replacement advantageous

---

## 13. Planning Timeline

### 2026–2027 — Establish the lithium baseline

- Operate the four-module Discover bank through a complete winter
- Validate predicted winter SOC lows
- Quantify multi-day deficit frequency
- Preserve per-module LYNK data where practical
- Continue refining openHAB battery telemetry
- Establish daily EFC and recharge-completeness metrics

### 2027–2030 — Observe, preserve, and avoid unnecessary upgrades

- Annual battery health review
- Track capacity and throughput trends
- Track PV seasonal production and degradation
- Preserve local copies of Schneider firmware, configuration exports, manuals, and commissioning records
- Improve local data collection where useful
- Follow development of Victron and competing locally controlled ecosystems
- Follow sodium-ion and other stationary-storage technologies without committing prematurely
- Watch availability and pricing of Schneider spare equipment as the discontinued product family ages

### 2030–2032 — Early power-electronics architecture review

- Treat the known **2035 Schneider end-of-standard-service date** as the primary planning clock
- Assess Discover bank measured SOH and likely remaining service life
- Compare current inverter efficiency/integration against the market
- Verify whether the existing PV array remains adequate for winter recovery
- Define hard requirements for the next inverter/MPPT/gateway platform
- Evaluate whether the Discover bank can and should be retained through the electronics migration
- Compare Victron against the best then-current local-first alternatives

### 2032–2033 — Select preferred migration architecture

- Select a preferred replacement ecosystem
- Confirm true 120/240 V split-phase behavior
- Confirm battery/BMS compatibility
- Confirm local MQTT/Modbus/API integration
- Define wiring, protection, communications, and panel changes
- Determine whether existing PV modules/stringing can be retained
- Develop a preliminary BOM and budget

### 2033–2034 — Become migration-ready

- Finalize implementation design
- Maintain an executable cutover and rollback runbook
- Identify installers or validate DIY scope as appropriate
- Budget or reserve funds for the migration
- Verify lead times and availability
- Preserve a path to reuse the Discover batteries if their health remains good

### Before April 4, 2035 — Schneider support-horizon checkpoint

By this point the site should be capable of replacing the Schneider inverter, charge controller, and gateway without an emergency engineering exercise.

If the Schneider equipment remains healthy, continued use after end of standard service is reasonable, but the system should be treated as **supported-by-owner legacy infrastructure** with a ready replacement path.

### 2037–2039 — Battery-technology and whole-system review

Independently of whether the Schneider electronics have already been replaced, evaluate the battery market and broader system architecture using the accumulated site history.

Questions to answer:

- What storage chemistry now gives the best $/usable-kWh over expected life?
- What battery capacity is justified by the worst observed multi-day weather sequences?
- Is 48 V still the preferred battery architecture?
- Does the current array remain worth keeping?
- Can significantly more winter production fit in the same array footprint?
- Which inverter ecosystem provides the best local interfaces and long-term serviceability?
- Can the new platform integrate cleanly with openHAB and the local AI system?
- Is cloud access optional rather than mandatory?
- Can the BMS and inverter continue operating safely if the home-automation/AI layer is offline?

### 2040+ — Replace based on condition and value, not age alone

If the current hardware remains capable and reliable, continue using it. If the market offers a compelling improvement, migrate deliberately using the layered strategy above.

---

## 14. Procurement Principles for the Next Generation

Future hardware should score well on the following criteria, in approximately this order:

1. **Safety and electrical suitability**
2. **Reliability and serviceability**
3. **Local operation without mandatory cloud dependency**
4. **Documented local telemetry/control interfaces**
5. **Interoperability with third-party batteries and automation**
6. **Availability of replacement components**
7. **Winter efficiency and cold-weather performance**
8. **Lifecycle cost rather than initial purchase price alone**
9. **Ability to preserve/export historical data**
10. **Suitability for AI-assisted supervisory control without making AI safety-critical**

Vendor ecosystem should remain a consideration, but **architecture should outrank brand loyalty**.

---

## 15. Current Working Conclusions

As of August 2026:

- **Four Discover modules appear sufficient.** There is no present operational case for adding a fifth module.
- The bank is cycling so lightly that **calendar life should dominate cycle wear**.
- A **~12–18 year useful-life planning range** remains reasonable for the Discover bank, but **the Schneider electronics have an earlier external deadline: end of standard service in April 2035**.
- The most likely migration order is therefore **inverter/MPPT/gateway first, battery bank later**.
- The current PV array should likely be retained until performance, economics, or architecture creates a specific reason to replace it.
- **Victron is the current leading future architecture to watch** because of its local-control and automation-friendly ecosystem, not because today's specific hardware should be purchased years in advance.
- A preferred successor architecture should be identified by roughly **2032–2033**, with the property migration-ready by **2034**, even if the Schneider equipment ultimately continues operating beyond 2035.
- The future system should be **local-first, modular, interoperable, and AI-ready**.
- openHAB/PostgreSQL history being accumulated now may become one of the most valuable inputs to a future locally hosted energy-management model.
- Battery chemistry should remain an open decision until replacement is actually needed; sodium-ion and other emerging stationary-storage technologies should be monitored.

---

## 16. Document Maintenance

Revisit this roadmap at least annually and after any major hardware change.

Update it when:

- the first full winter of Discover-bank data is available
- measured battery SOH/capacity changes materially
- the array is modified or expanded
- Schneider hardware is replaced
- a fifth battery is seriously considered
- a future inverter ecosystem is selected
- local AI energy-management work begins
- a new battery chemistry reaches compelling residential/off-grid maturity

The objective is not to preserve today's predictions. The objective is to preserve **good decision criteria** as the technology changes.

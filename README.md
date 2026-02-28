# Solar Power System

Central knowledge base for the Schneider Electric off-grid solar energy system.

## System Hardware

| Component | Model |
|-----------|-------|
| Inverter | Schneider XW6848-21 |
| Charge Controller | Schneider MPPT 60-150 |
| Gateway | InsightHome (Xanbus) |
| Solar Array | 4.2 kW |
| Current Storage | 48V Fullriver DC400-6 AGM (830 Ah) — **end-of-life, replacement in progress** |
| Planned Storage | 4× Discover AES Rackmount 48-48-5120 (400 Ah / 20.48 kWh LiFePO4) |
| Load Profile | ~5.3 kWh/day |

---

## Documentation

### Lithium Upgrade (Active — Q2 2026)

| Document | Description |
|----------|-------------|
| **[Battery Upgrade Plan (Rev 2)](battery-upgrade-plan-rev2.md)** | Master project plan: BOM, layout, Lynx Power In M8 bus bar, installation timeline, wiring diagrams. **Start here.** |
| **[LYNK II Deployment Guide](lynk2-deployment-guide.md)** | Step-by-step software configuration: jumper verification, AEbus network, LYNK ACCESS setup, XW+ and MPPT settings with current→target values, comms-loss fallback config. |

### AGM Battery Forensics (Historical)

| Document | Description |
|----------|-------------|
| [System Defect Analysis](System_Defect_Analysis.md) | Engineering report documenting AGM failure: installation defects, incorrect commissioning, voltage data, photographic evidence. Supports warranty/CMS claim. |
| [Battery Health Dashboard](https://santyr.github.io/Solar_PV/battery_dashboard.html) | Interactive per-battery voltage trends and spread tracking. |

### Archived

| Document | Description |
|----------|-------------|
| ~~[Discover-Lithium-Upgrade.md](Discover-Lithium-Upgrade.md)~~ | **Deprecated.** Earlier design using 950-0049 combiner. Superseded by Rev 2 plan. |

---

## Quick Reference — Upgrade Summary

| Parameter | Current (AGM) | Upgrade (LiFePO4) |
|-----------|---------------|-------------------|
| Batteries | 16× Fullriver DC400-6 | 4× Discover AES 48-48-5120 |
| Usable Capacity | ~20 kWh (50% DoD) | 20.48 kWh (100% DoD) |
| Weight | 2,032 lbs | 388 lbs |
| Communication | Open-loop (manual config) | Closed-loop via LYNK II → Xanbus |
| Bus Bar | N/A | Victron Lynx Power In M8 |
| Hardware Cost | ~$7,404 (combiner design) | **~$6,897 (Lynx Power In design)** |
| Target Install | Summer Solstice 2026 | |

---

*Repository: https://github.com/santyr/Solar_PV*

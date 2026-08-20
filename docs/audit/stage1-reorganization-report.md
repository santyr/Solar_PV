# Stage 1 Solar_PV Reorganization Report

**Date:** 2026-08-20

**Scope:** Repository documentation and file organization only

**Production mutations:** None

## Outcome

`Solar_PV` now has an explicit current-authority layer, operational runbooks,
completed-project records, isolated AGM history, organized vendor references,
and the Stage 0 cross-repository contract baseline.

## Before and after

Before, current plans, retired AGM procedures, CSV evidence, vendor manuals,
and the public dashboard shared a flat repository root. The README still
described a failing AGM bank and an active upgrade.

After:

```text
Solar_PV/
├── README.md
├── AGENTS.md
├── battery_dashboard.html
├── data/historical/agm/
├── docs/
│   ├── README.md
│   ├── architecture/
│   ├── audit/
│   ├── history/agm/
│   ├── operations/
│   ├── projects/completed/
│   ├── reference/{discover,schneider,victron}/
│   └── superpowers/{plans,specs}/
└── photos/
```

No original tracked artifact was deleted. Git history remains the authority for
older deleted designs that were already absent from `HEAD`.

## Path moves

| Old path | New path | Classification |
|---|---|---|
| `System_Defect_Analysis.md` | `docs/history/agm/system-defect-analysis.md` | Retired AGM evidence |
| `handwritten_voltage_readings_*.csv` | `data/historical/agm/handwritten-voltage-readings-*.csv` | Raw AGM evidence |
| `DC400-6.pdf` | `docs/history/agm/reference/fullriver-dc400-6.pdf` | Retired battery reference |
| `battery-upgrade-plan-rev2.md` | `docs/projects/completed/discover-battery-upgrade.md` | Completed project |
| `lynk2-deployment-guide.md` | `docs/projects/completed/lynk2-deployment.md` | Completed commissioning |
| `openhab-cutover-plan.md` | `docs/projects/completed/openhab-lithium-cutover.md` | Completed cutover |
| `long-term-system-roadmap.md` | `docs/architecture/long-term-system-roadmap.md` | Current architecture |
| Discover manuals | `docs/reference/discover/` | Vendor reference |
| Schneider integration manual | `docs/reference/schneider/` | Vendor reference |
| Victron Lynx manual | `docs/reference/victron/` | Vendor reference |

## Canonical current documents

- `docs/architecture/current-system.md`
- `docs/architecture/energy-data-architecture.md`
- `docs/architecture/codex-energy-management.md`
- `docs/architecture/cross-repo-contracts.md`
- `docs/architecture/long-term-system-roadmap.md`
- `docs/operations/`

## Factual conflicts resolved

- **Battery:** retired 830 Ah Fullriver prose was removed from the current
  layer; four Discover modules, 400 Ah / 20.48 kWh, are canonical.
- **Upgrade status:** battery, LYNK II, and OpenHAB cutover documents are
  completed records, not active plans.
- **PV rating:** 4.2 kW is retained as the documented working rating. The 4.8
  kW value first appeared without supporting evidence in commit `18f6f03`
  and is rejected. Module nameplates and string configuration remain a named
  field-verification gap.
- **Mining:** Avalon/Bitaxe work is dormant and excluded from current policy.
- **AGM persistence:** historical PostgreSQL mappings are evidence, not current
  battery authority.

## Broken or stale material found

- The former root README described the retired AGM bank as current.
- It called completed upgrade/cutover work active.
- It linked an already deleted `Discover-Lithium-Upgrade.md`.
- The AGM report referenced a nonexistent
  `Commissioning_Day_One.png`; the retained file is
  `Commissioning_Day_Zero.png`.
- Moved documents contained root-relative links that required repair.
- Current UI deployment tooling supports exact OpenHAB 5.2.0 while live
  OpenHAB is 5.2.1; this remains a cross-repository blocker, not a Stage 1
  documentation change.

## Compatibility

- `battery_dashboard.html` remains at the root, preserving
  `https://santyr.github.io/Solar_PV/battery_dashboard.html`.
- `photos/` paths remain stable.
- OpenHAB Items, rule IDs, REST paths, persistence, and services were not
  changed.
- Lightning Goats rule `88bd9ec4de` and `FeederOverride` contracts were not
  changed.

## Ownership and verification

Solar_PV owns engineering meaning; live hardware/OpenHAB/PostgreSQL remain
runtime authority. Codex performed the reorganization on an isolated branch
and verified it against the live Stage 0 evidence. No separate independent-agent
verification occurred. The operator subsequently authorized commit, local
`main` merge, and publication to `origin/main` on 2026-08-20; the initial
reorganization commit is `fb95ecc`.

Evidence includes repository history, account-wide dependency searches,
authenticated read-only OpenHAB inspection, read-only PostgreSQL inspection,
systemd/process inventory, deployed-source hashes, and link/hash/tree checks.

## Remaining active work and handoffs

1. Field-capture PV module nameplates and string topology.
2. Re-verify firmware through current device interfaces when firmware matters.
3. Implement the reversible PostgreSQL analytics platform in Stage 2.
4. Resolve the earthship-ui OpenHAB version guard before managed deployments.
5. Reconcile the deployed UI's unpublished commits before shared-contract work.
6. Resolve external legacy Lightning Goats deployment status before removing
   compatibility.

Stage 0 durable outcomes were stored in Hexmem facts `1781`–`1784`.
Stage 1's PV-rating and documentation-architecture decisions were stored after
verification in Hexmem facts `1785` and `1786`.

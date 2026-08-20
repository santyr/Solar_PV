# Earthship Off-Grid Energy System

Canonical engineering knowledge base for the installed electrical system,
its telemetry, operating boundaries, completed projects, and long-term plan.

Start with [the current-system document](docs/architecture/current-system.md).
Historical AGM material is deliberately separated from current lithium
operations.

| Layer | Current implementation |
|---|---|
| Battery | 4 × Discover AES Rackmount 48-48-5120 |
| BMS gateway | Discover LYNK II |
| Inverter | Schneider XW Pro 6848 |
| MPPT | Schneider MPPT 60-150 |
| Automation | OpenHAB |
| Data | PostgreSQL |
| AI manager | Codex |
| Durable memory | Hexmem |
| Operator UI | earthship-ui |
| Mining / discretionary-load policy | None active |

## Canonical documents

- [Current system](docs/architecture/current-system.md)
- [Energy data architecture](docs/architecture/energy-data-architecture.md)
- [Codex energy management](docs/architecture/codex-energy-management.md)
- [Cross-repository contracts](docs/architecture/cross-repo-contracts.md)
- [Long-term roadmap](docs/architecture/long-term-system-roadmap.md)
- [Operations index](docs/operations/README.md)
- [Completed projects](docs/projects/completed/README.md)
- [AGM history](docs/history/agm/README.md)
- [Stage 1 reorganization report](docs/audit/stage1-reorganization-report.md)

## Compatibility

The historical
[battery dashboard](https://santyr.github.io/Solar_PV/battery_dashboard.html)
remains at the repository root for GitHub Pages compatibility. It describes the
retired AGM bank and is not a current battery dashboard.

## Safety

The Discover BMS and Schneider protection functions are the electrical safety
authority. OpenHAB provides bounded deterministic automation. Codex, Hexmem,
PostgreSQL, and the UI must never become the sole safety layer or authorize
unreviewed physical actions.

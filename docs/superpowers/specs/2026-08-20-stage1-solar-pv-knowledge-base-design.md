# Stage 1 Solar_PV Knowledge-Base Design

**Status:** Approved by the Earthship Energy AI handoff and the operator's
2026-08-20 instruction to proceed.

## Objective

Turn `Solar_PV` from an upgrade-era working folder into the canonical
engineering knowledge base for the installed off-grid electrical system,
without erasing AGM evidence or breaking the published battery dashboard.

## Approaches considered

1. **Minimal index refresh.** Rewrite only the root README and leave the flat
   tree intact. This preserves URLs but does not prevent stale AGM procedures
   from being mistaken for current operations.
2. **Clean-slate rewrite.** Replace old documents with new canonical prose.
   This creates a tidy tree but destroys evidentiary context and weakens the
   warranty/commissioning record.
3. **Canonical layer plus explicit history.** Add a small current-system layer,
   move completed projects and AGM evidence into labeled archives, organize
   manuals by vendor, and preserve compatibility files at their published
   paths.

The third approach is selected. It makes current authority obvious while
keeping history auditable.

## Information architecture

- `README.md` is the concise entry point and current layer table.
- `AGENTS.md` is the operating contract for future agents.
- `docs/architecture/` owns current topology, data/AI ownership, cross-repo
  contracts, and the long-term roadmap.
- `docs/operations/` owns current monitoring, maintenance, analysis, and
  recovery procedures.
- `docs/projects/completed/` owns the Discover upgrade, LYNK II deployment,
  and OpenHAB lithium cutover records. Each record points back to current
  canonical docs.
- `docs/history/agm/` and `data/historical/agm/` quarantine AGM assumptions
  and evidence.
- `docs/reference/<vendor>/` owns manuals.
- `battery_dashboard.html` remains at the repository root so the established
  GitHub Pages URL does not change.
- `photos/` remains stable because historical reports link to those paths.

## Current-fact policy

Live OpenHAB, PostgreSQL, deployed source, and current equipment evidence
outrank repository prose. Facts that cannot be verified are labeled as such.

The PV discrepancy is resolved as follows:

- 4.2 kW is the earliest and repeatedly documented array rating.
- 4.8 kW first appeared in commit `18f6f03` during a broad README rewrite.
- No module schedule, nameplate photograph, invoice, or string diagram in this
  repository supports 4.8 kW.
- Therefore 4.8 kW is rejected as unsupported. The canonical document uses
  **4.2 kW documented rating**, while explicitly marking module count,
  module-level nameplate, and string configuration as unverified pending a
  field record.

This resolves which value may be used operationally without manufacturing
precision that the evidence does not contain.

## Safety and compatibility

- Discover BMS and Schneider protection remain electrical safety authority.
- OpenHAB remains the bounded automation/integration owner.
- Documentation work does not change live Items, rules, services, database
  rows, firmware, or configuration.
- AGM values such as 830 Ah, Peukert corrections, voltage-SOC curves, and
  tail-current rules are historical only.
- Dormant mining code remains outside the current system.
- External feeder contracts identified in Stage 0 remain unchanged.
- Root dashboard and photo paths remain compatible.

## Verification

Stage 1 is accepted only after:

- every Markdown link resolves locally or is an intentional external URL;
- the dashboard remains byte-identical at `battery_dashboard.html`;
- all original tracked files are present at a canonical or historical path;
- current documents contain no active AGM or mining policy;
- the required ownership/safety/source-of-truth rules are present;
- the before/after migration map and unresolved evidence gaps are documented.

# Stage 1 Solar_PV Knowledge-Base Implementation Plan

> **Required execution skill:** `superpowers:executing-plans`.

**Goal:** Normalize `Solar_PV` into the canonical current-system knowledge
base while preserving historical evidence and public compatibility.

**Constraints:** Documentation-only; no production writes; no interface,
service, database, firmware, or hardware changes; no commit or push without
explicit authorization.

### Task 1: Preserve and classify

- [x] Record the before tree and file migration map.
- [x] Preserve the dashboard bytes and keep `photos/` paths stable. The
  operator later superseded the root-path requirement: the dashboard is
  archived under `docs/history/agm/` and Pages is disabled.
- [x] Move AGM reports/data/manuals into explicit historical locations.
- [x] Move completed upgrade/cutover documents into
  `docs/projects/completed/`.
- [x] Move vendor manuals under `docs/reference/<vendor>/`.

### Task 2: Establish the canonical current layer

- [x] Rewrite the root `README.md` as the concise system entry point.
- [x] Add `AGENTS.md` with safety, source-of-truth, Hexmem, and cross-repo
  rules.
- [x] Add `docs/README.md`.
- [x] Add `docs/architecture/current-system.md` with evidence labels and the
  resolved PV discrepancy.
- [x] Add current data/AI architecture and Codex operating documents.
- [x] Install the roadmap at
  `docs/architecture/long-term-system-roadmap.md` and repair its links.
- [x] Add current operations indexes/runbooks without duplicating live config.

### Task 3: Label history and completed work

- [x] Add status headers and canonical-current links to completed project
  records.
- [x] Add an AGM history warning/index that forbids reuse of AGM parameters.
- [x] Keep raw historical CSV values unchanged.

### Task 4: Verify

- [x] Verify all local Markdown links.
- [x] Verify the root dashboard hash matches `HEAD`.
- [x] Verify every original tracked file remains represented.
- [x] Scan current docs for stale AGM/mining language and unsupported 4.8 kW.
- [x] Validate required current-system, ownership, safety, and roadmap facts.
- [x] Record the after tree, factual conflicts, compatibility decisions,
  remaining active work, evidence, and handoffs in a Stage 1 report.

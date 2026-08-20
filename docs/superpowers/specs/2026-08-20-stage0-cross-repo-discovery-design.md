# Stage 0 Cross-Repository Discovery Design

**Status:** Approved by the 2026-08-19 Earthship Energy AI handoff and the
operator's 2026-08-20 instruction to proceed.

## Purpose

Establish the current repository, runtime, OpenHAB, PostgreSQL, and scheduler
contracts before any shared Item, rule, endpoint, schema, or service changes.
The output is an evidence-backed dependency inventory owned by `Solar_PV`.

## Approaches considered

1. **Repository-only audit.** Fast and reproducible, but cannot establish what
   is deployed or distinguish historical code from live authority.
2. **Live-host-only audit.** Authoritative for current execution, but misses
   dormant repositories and external consumers that can still be broken by a
   future interface change.
3. **Hybrid static and live audit.** Search every accessible `santyr/*` and
   `lightning-goats/*` repository, then verify relevant findings against live
   OpenHAB, PostgreSQL, systemd, processes, and the deployed UI checkout.

The hybrid approach is selected because it follows the handoff's
source-of-truth order and is the only approach that covers both compatibility
and deployment state.

## Boundaries

- Discovery is read-only except for audit documentation on an isolated branch.
- No OpenHAB Item, rule, metadata, persistence, or UI contract changes.
- No database writes.
- No service starts, stops, enables, disables, or restarts.
- No feeder, outlet, miner, inverter, charger, or battery action calls.
- Hexmem is context, never authorization.
- Secrets are read only by existing protected clients and are never printed or
  copied into documentation.

## Evidence model

Each inventory row records repository/service identity, deployment state,
OpenHAB reads and writes, database dependency, Hexmem relationship, physical
side effects, currentness, classification, action, and reproducible evidence.

Drift-prone facts require live evidence. Repository searches establish possible
contracts; live OpenHAB and system/process state establish current authority.
Unknown remote deployments remain explicitly unknown rather than inferred.

## Deliverables

- `docs/audit/cross-repo-dependency-inventory.csv` is the canonical tracker.
- `docs/architecture/cross-repo-contracts.md` explains the verified contracts,
  conflicts, safety boundaries, and next-stage blockers.

## Acceptance

- All accessible repositories are covered by account-wide searches.
- Every identified OpenHAB consumer has a deployment/currentness classification.
- Exact UI write allowlists and external feeder calls are documented.
- Live mining and AGM status are verified.
- Existing scheduler overlap is recorded for Stage 5.
- No production state changes occur.

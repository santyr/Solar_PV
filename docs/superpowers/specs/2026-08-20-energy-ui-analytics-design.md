# Energy UI Analytics Contract Design

**Status:** Approved by the operator on 2026-08-20.

## Purpose

Publish a compact, deterministic, observational summary of PostgreSQL energy
analytics to `earthship-ui` without giving the browser database access or any
new control authority.

## Boundary

- PostgreSQL remains the quantitative source of truth.
- `Solar_PV/analytics` builds and validates the payload server-side.
- OpenHAB exposes exactly one stable String Item: `Energy_Analytics_JSON`.
- `earthship-ui` consumes the Item through its existing REST snapshot and SSE
  paths. It performs no direct SQL and cannot write the Item.
- The publisher may update only `/rest/items/Energy_Analytics_JSON/state`.
- The payload is observational and cannot authorize an electrical or household
  action.

## Payload contract

The state is canonical UTF-8 JSON below 16 KiB with schema
`earthship-energy-ui/v1`. It contains exact top-level keys:

```text
schema, generatedAt, timezone, epochId, throughDate, status,
battery, energy, winter, lifecycle, forecast, health
```

All timestamps are timezone-aware ISO-8601 strings. Missing evidence is encoded
as `null` plus an explicit status or reason; zero is never substituted for
unknown data. Daily-history values include only quality-approved compact rows
from the active system epoch. Current raw values already shown by the UI remain
on their authoritative OpenHAB Items and are not relabeled as analytics.

The sections expose these bounded summaries:

- `battery`: latest quality-approved minimum SoC, reach-99 status, cumulative
  EFC, and no-full streak evidence.
- `energy`: latest quality-approved PV/load/charge/discharge totals. Switch-only
  household loads remain explicitly state-only and never become inferred watts.
- `winter`: winter observation count, lowest SoC, longest no-full sequence, and
  worst deficit period when evidence exists.
- `lifecycle`: quality-approved EFC and throughput totals, high-SoC exposure,
  and module health only when an imported LYNK batch supports it.
- `forecast`: persisted forecast freshness and supported forecast values;
  unsupported next-morning/full-probability fields remain unavailable.
- `health`: publisher, analytics, forecast, BMS, Schneider, weather, and
  collector status with explicit freshness reasons.

## Publication and failure behavior

The builder is deterministic for explicit input rows and generation time. A
publisher validates the exact schema and byte bound before issuing one
`text/plain` state update. It refuses redirects, non-loopback default targets,
unknown paths, malformed payloads, and non-2xx responses. Failed builds or
writes leave the prior Item state intact and exit nonzero.

A user-level systemd oneshot runs every five minutes with a lock, private umask,
read-only home/system protection, and the existing OpenHAB environment file.
It invokes no Codex process, no rule, no actuator, and no OpenHAB restart.

## UI behavior

The Energy page parses the closed contract and shows a compact analytics summary
plus an operator-opened detail surface. Invalid, stale, oversized, future-dated,
or unsupported payloads fail closed to an unavailable/degraded state. Existing
numeric OpenHAB charts remain the time-series surfaces; JSON-derived summaries
are not misrepresented as native persisted numeric Items.

The 1340x800 tablet and 1280x720 laptop viewports must retain readable SoC/PV
plots, no page scroll, no overflowing grid cells, and keyboard-accessible detail
controls.

## Deployment

Provision the one Item through a checksum-bound snapshot, rehearsal, exact
apply/readback, close, and rollback-capable receipt. Back up mutable OpenHAB
configuration before the first write. Deploy the publisher only after the Item
is verified, then verify exact readback through OpenHAB and the UI proxy. The
off-host backup remains intentionally deferred; the existing same-host verified
restore point stays recorded and the backup check remains `Actionable`.

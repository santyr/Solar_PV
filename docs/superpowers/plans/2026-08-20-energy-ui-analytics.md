# Energy UI Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish one validated PostgreSQL analytics summary through OpenHAB and render it safely in earthship-ui.

**Architecture:** `Solar_PV` owns a pure payload builder, bounded database reader, exact publisher, and five-minute user service. `earthship-ui` owns the exact JSON parser, compact/detail presentation, and receipt-bound provisioning of the observational String Item. The browser retains read-only REST/SSE access and no database or action authority.

**Tech Stack:** Python 3.12, psycopg2, pytest, Node.js ESM, Svelte 5, Vitest/jsdom, Playwright, OpenHAB 5.2 REST, PostgreSQL 16, user-level systemd.

## Global Constraints

- Approved design: `docs/superpowers/specs/2026-08-20-energy-ui-analytics-design.md`.
- The only new OpenHAB resource is String Item `Energy_Analytics_JSON`.
- The only publisher write is `PUT /rest/items/Energy_Analytics_JSON/state` with canonical `text/plain` JSON below 16 KiB.
- PostgreSQL remains the quantitative source of truth; the browser never connects to it.
- Unknown evidence is `null` with explicit status or reason; it is never fabricated as zero.
- State-only loads remain state-only and do not acquire watt or kWh labels.
- The payload and UI are observational and cannot authorize actions.
- Existing feeder, greywater, night-load, forecast, thermal, and browser proxy contracts remain unchanged.
- Off-host backup is deferred; same-host restore evidence remains intact and backup health remains `Actionable`.

---

### Task 1: Pure versioned analytics payload

**Files:**
- Create: `analytics/src/earthship_energy/ui_payload.py`
- Create: `analytics/tests/test_ui_payload.py`

**Interfaces:**
- Consumes: quality-approved daily rows, winter/lifecycle/module reports, forecast-health evidence, explicit `generated_at`, timezone, and epoch ID.
- Produces: `build_energy_ui_payload(...) -> dict[str, object]`, `validate_energy_ui_payload(payload, *, now=None) -> dict[str, object]`, and `encode_energy_ui_payload(payload) -> bytes`.

- [ ] **Step 1: Write failing exact-contract tests**

Create tests that build two payloads from identical inputs and assert equality,
the exact schema/top-level keys, timezone-aware chronology, explicit unavailable
fields, rejection of booleans as numbers, unknown keys, future generation times,
non-finite values, and encoded size at or above 16,384 bytes.

```python
assert first == second
assert first["schema"] == "earthship-energy-ui/v1"
assert set(first) == {
    "schema", "generatedAt", "timezone", "epochId", "throughDate", "status",
    "battery", "energy", "winter", "lifecycle", "forecast", "health",
}
with pytest.raises(ValueError, match="below 16 KiB"):
    encode_energy_ui_payload(oversized)
```

- [ ] **Step 2: Run RED**

Run `pytest -q analytics/tests/test_ui_payload.py` from the repository root.
Expected: collection fails because `earthship_energy.ui_payload` does not exist.

- [ ] **Step 3: Implement the minimal pure builder and validator**

Use closed field sets, aware timestamp parsing, finite-number checks that reject
`bool`, ordered local dates, exact enum vocabularies, and canonical compact JSON
with `sort_keys=True`, `separators=(",", ":")`, and UTF-8 byte counting.

- [ ] **Step 4: Run GREEN and commit**

Run `pytest -q analytics/tests/test_ui_payload.py analytics/tests/test_reports.py`.
Expected: all selected tests pass.

```bash
git add analytics/src/earthship_energy/ui_payload.py analytics/tests/test_ui_payload.py
git commit -m "feat: define stable energy UI analytics payload"
```

### Task 2: Bounded PostgreSQL reader and snapshot assembly

**Files:**
- Create: `analytics/src/earthship_energy/ui_reader.py`
- Create: `analytics/tests/test_ui_reader.py`
- Modify: `analytics/src/earthship_energy/ui_payload.py`
- Modify: `analytics/tests/test_ui_payload.py`

**Interfaces:**
- Consumes: a read-only psycopg2 connection, active epoch, `as_of` instant, and existing compact analytics tables.
- Produces: `fetch_energy_ui_inputs(connection, epoch_id, start, end, as_of) -> dict[str, object]` and `build_energy_ui_snapshot(connection, epochs, generated_at) -> dict[str, object]`.

- [ ] **Step 1: Write failing query-boundary tests**

Use a recording cursor and assert every query names `energy_analytics` tables,
has explicit epoch/time parameters, includes quality filters where applicable,
uses bounded `LIMIT` clauses for latest rows, and never selects raw per-Item
tables or secret configuration.

- [ ] **Step 2: Run RED**

Run `pytest -q analytics/tests/test_ui_reader.py`.
Expected: module-not-found failure.

- [ ] **Step 3: Implement read-only assembly**

Reuse `fetch_daily_report_rows`, `winter_report`, `lifecycle_report`, and
`module_health_report`. Select the active epoch from `system-epochs.json` and
bound history from epoch start through the last completed local day. Fetch only
the latest persisted forecast issue/valid evidence required by the contract.
Return explicit unavailable statuses when there are no quality-approved rows.

- [ ] **Step 4: Run GREEN and commit**

Run `pytest -q analytics/tests/test_ui_reader.py analytics/tests/test_ui_payload.py analytics/tests/test_report_reader.py analytics/tests/test_reports.py`.
Expected: all selected tests pass.

```bash
git add analytics/src/earthship_energy/ui_reader.py analytics/src/earthship_energy/ui_payload.py analytics/tests/test_ui_reader.py analytics/tests/test_ui_payload.py
git commit -m "feat: assemble UI analytics from bounded PostgreSQL evidence"
```

### Task 3: Exact OpenHAB publisher and scheduler

**Files:**
- Create: `analytics/src/earthship_energy/ui_publish.py`
- Create: `analytics/tests/test_ui_publish.py`
- Modify: `analytics/src/earthship_energy/scheduled.py`
- Modify: `analytics/tests/test_scheduled.py`
- Create: `deploy/systemd/user/energy-ui-publish.service`
- Create: `deploy/systemd/user/energy-ui-publish.timer`
- Modify: `analytics/tests/test_systemd_units.py`

**Interfaces:**
- Consumes: validated canonical payload bytes, exact loopback/default OpenHAB base URL, optional API token, and JDBC configuration.
- Produces: `publish_energy_ui_state(payload, *, base_url, token, opener=urlopen) -> dict[str, object]` and scheduler command `energy-ui-publish`.

- [ ] **Step 1: Write publisher RED tests**

Assert exactly one `PUT` to `/rest/items/Energy_Analytics_JSON/state`,
`Content-Type: text/plain; charset=utf-8`, Bearer token authentication when a
token is supplied, redirect refusal, a 16 KiB preflight, sanitized failures,
and no request when payload construction fails.

- [ ] **Step 2: Run RED**

Run `pytest -q analytics/tests/test_ui_publish.py analytics/tests/test_scheduled.py -k energy_ui`.
Expected: missing publisher/command failures.

- [ ] **Step 3: Implement publisher and command**

Build with a read-only DB connection, close it before the network write, validate
and encode once, publish once, and print a receipt containing only schema,
generated timestamp, byte count, SHA-256, Item name, and status. Never log the
token, raw JDBC settings, or full payload.

- [ ] **Step 4: Add hardened five-minute units**

The timer uses `OnCalendar=*-*-* *:0/5:00`, `Persistent=true`, and a bounded
random delay. The oneshot uses the existing working directory/PYTHONPATH,
environment file, flock, `UMask=0077`, `NoNewPrivileges=true`, strict system
protection, read-only home, and no writable directory requirement.

- [ ] **Step 5: Run GREEN and commit**

Run `pytest -q analytics/tests/test_ui_publish.py analytics/tests/test_scheduled.py analytics/tests/test_systemd_units.py`.
Expected: all selected tests pass.

```bash
git add analytics/src/earthship_energy/ui_publish.py analytics/src/earthship_energy/scheduled.py analytics/tests/test_ui_publish.py analytics/tests/test_scheduled.py analytics/tests/test_systemd_units.py deploy/systemd/user/energy-ui-publish.service deploy/systemd/user/energy-ui-publish.timer
git commit -m "feat: publish analytics snapshot to OpenHAB"
```

### Task 4: Receipt-bound analytics Item provisioning

**Files:**
- Create in earthship-ui: `scripts/energy-analytics-config.mjs`
- Create in earthship-ui: `tests/energy-analytics-config.test.js`
- Create in earthship-ui: `openhab/energy-analytics-item.json`

**Interfaces:**
- Produces: exact Item manifest and commands `snapshot`, `plan`, `rehearse`, `apply`, `verify`, `rollback`, `settle`, and `close` for one Item only.

- [ ] **Step 1: Write manifest/allowlist/receipt RED tests**

Assert the exact Item DTO, exact GET/PUT/DELETE allowlist, denial of Item-state
writes, unrelated resources, body drift, corrupt receipts, concurrent locks,
snapshot drift, interrupted writes, and rollback outside the receipt.

- [ ] **Step 2: Run RED**

Run `npm test -- --run tests/energy-analytics-config.test.js` in earthship-ui.
Expected: module-not-found failure.

- [ ] **Step 3: Implement the narrow transaction tool**

Reuse the receipt invariants from `thermal-model-config.mjs`, but keep a distinct
schema `earthship-energy-analytics-config-receipt/v1`, exact item name, and no
publisher/state operation. Rehearsal must use an in-memory transport and leave
the real receipt bytes unchanged.

- [ ] **Step 4: Run GREEN and commit in earthship-ui**

Run `npm test -- --run tests/energy-analytics-config.test.js`.
Expected: all selected tests pass.

```bash
git add scripts/energy-analytics-config.mjs tests/energy-analytics-config.test.js openhab/energy-analytics-item.json
git commit -m "feat: provision observational energy analytics item"
```

### Task 5: Closed UI parser and operator presentation

**Files:**
- Create in earthship-ui: `src/lib/energy/analyticsResult.js`
- Create in earthship-ui: `tests/energy-analytics-result.test.js`
- Create in earthship-ui: `src/lib/ui/EnergyAnalyticsDetail.svelte`
- Create in earthship-ui: `tests/ui/EnergyAnalyticsDetail.test.js`
- Modify in earthship-ui: `src/screens/Energy.svelte`
- Modify in earthship-ui: `tests/e2e/energy-layout.spec.js`

**Interfaces:**
- Produces: `parseEnergyAnalyticsResult(raw, nowMs=Date.now())` with states `ready`, `degraded`, and `unavailable`; a bounded detail dialog; and compact Energy-page summary.

- [ ] **Step 1: Write parser RED tests**

Assert exact schema, closed keys, aware chronology, finite values, byte-before-
trim counting, stale/future rejection, explicit unknowns, no HTML interpretation,
and unsupported version failure.

- [ ] **Step 2: Run RED**

Run `npm test -- --run tests/energy-analytics-result.test.js`.
Expected: module-not-found failure.

- [ ] **Step 3: Implement the parser and summary projection**

Return frozen display-ready fields only after full validation. Retain explicit
reason codes and never fall back from invalid analytics to fabricated numbers.

- [ ] **Step 4: Write component/layout RED tests**

Assert keyboard dialog behavior, unavailable/degraded copy, correct units and
evidence labels, no control elements, no page scroll, no overflowing cells, and
both history plots at least 64 px high on 1340x800 and 1280x720.

- [ ] **Step 5: Implement the compact card and detail dialog**

Integrate `Energy_Analytics_JSON` through `$items`; keep existing SoC/PV history
charts and use JSON summaries only for analytics evidence. The detail surface
shows battery, energy, winter, lifecycle, forecast, and health sections.

- [ ] **Step 6: Run GREEN and commit in earthship-ui**

Run `npm test -- --run tests/energy-analytics-result.test.js tests/ui/EnergyAnalyticsDetail.test.js` and `npx playwright test tests/e2e/energy-layout.spec.js`.
Expected: all selected tests pass at both viewports.

```bash
git add src/lib/energy/analyticsResult.js src/lib/ui/EnergyAnalyticsDetail.svelte src/screens/Energy.svelte tests/energy-analytics-result.test.js tests/ui/EnergyAnalyticsDetail.test.js tests/e2e/energy-layout.spec.js
git commit -m "feat: present stable energy analytics in the console"
```

### Task 6: Documentation, deployment, and end-to-end verification

**Files:**
- Modify: `docs/architecture/cross-repo-contracts.md`
- Modify: `docs/operations/openhab-energy-monitoring.md`
- Modify: `docs/operations/scheduled-jobs.md`
- Modify: `docs/operations/recovery-and-backup.md`
- Modify in earthship-ui: `docs/design.md`
- Create in earthship-ui: `docs/operations/energy-analytics.md`

**Interfaces:**
- Produces: operator runbook, rollback instructions, explicit backup deferral, and verified production receipt references.

- [ ] **Step 1: Update docs and doc-contract tests**

Document source ownership, payload schema, five-minute cadence, exact rollback,
state freshness, UI failure behavior, no-actuation boundary, same-host restore
point, and intentionally Actionable off-host status.

- [ ] **Step 2: Run full offline verification**

Run `pytest -q` in Solar_PV analytics, then in earthship-ui run
`npm test -- --run`, all thermal/forecast pytest files, `npm run build`, and the
Energy Playwright spec. Expected: all suites pass with clean output.

- [ ] **Step 3: Deploy with receipts and readback**

Back up the exact live Item state/configuration, run snapshot/plan/rehearse/apply/
verify/close, install reviewed systemd units atomically, daemon-reload, enable
the timer, start one publisher run, and verify exact Item plus UI-proxy readback.
No rule, Thing, link, persistence policy, actuator Item, or service restart is
part of this deployment.

- [ ] **Step 4: Commit docs in each repository**

```bash
git add docs
git commit -m "docs: operate stable energy analytics publication"
```

- [ ] **Step 5: Merge and publish both repositories**

Verify clean branches and fresh full tests, merge each feature branch into local
`main`, push `main` to `origin`, fetch, and prove local/remote commit equality.

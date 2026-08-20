# Stage 0 Cross-Repository Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [x]`) syntax for tracking. Multi-agent execution is not
> authorized for this run.

**Goal:** Produce a verified, read-only dependency inventory before any shared
Earthship/OpenHAB interface changes.

**Architecture:** Combine account-wide GitHub code search with targeted local
checkouts and live read-only inspection of OpenHAB, PostgreSQL, systemd, and
process state. Store one canonical CSV tracker plus a narrative contract map in
`Solar_PV`.

**Tech Stack:** Git, GitHub CLI, ripgrep, OpenHAB REST, PostgreSQL 16, systemd,
Markdown, CSV.

## Global Constraints

- Do not mutate OpenHAB, PostgreSQL, services, hardware, or external consumers.
- Do not expose credentials or protected configuration values.
- Live state outranks repository documentation and memory.
- Treat mining as dormant unless live evidence proves otherwise.
- Preserve all feeder semantics and interfaces.

---

### Task 1: Repository and deployment inventory

**Files:**
- Create: `docs/audit/cross-repo-dependency-inventory.csv`

**Interfaces:**
- Consumes: GitHub repository listings and account-wide code-search results.
- Produces: one classification row per relevant repository or deployed service.

- [x] **Step 1: List accessible repositories**

Run:

```bash
gh repo list santyr --limit 200 --json nameWithOwner,defaultBranchRef,visibility,isArchived,updatedAt
gh repo list lightning-goats --limit 200 --json nameWithOwner,defaultBranchRef,visibility,isArchived,updatedAt
```

Expected: both owners are enumerated without repository writes.

- [x] **Step 2: Run account-wide dependency searches**

Run owner-scoped searches for `openhab`, `OPENHAB_URL`, `rest/items`,
`rest/rules`, `BatterySoC`, `BMS_SOC`, `DCData_`, `PV_Power`,
`ChargerStatus`, `BatteryChargingStatus`, `FeederOverride`, `Miner_Power`,
`PostgreSQL`, and `hexmem`.

Expected: identified paths are attributable to a repository and search term.

- [x] **Step 3: Classify deployment state**

Run:

```bash
systemctl status openhab.service
systemctl --user status earthship-ui.service opengoat-hexmem.service
systemctl status lightning_goats.service lnbits.service
systemctl list-units --all
systemctl --user list-units --all
ps -eo pid,comm,args
docker ps
```

Expected: current, inactive, dormant, and unknown deployments are distinguished.

### Task 2: Exact OpenHAB and PostgreSQL contracts

**Files:**
- Modify: `docs/audit/cross-repo-dependency-inventory.csv`
- Create: `docs/architecture/cross-repo-contracts.md`

**Interfaces:**
- Consumes: authenticated read-only OpenHAB metadata, public sanitized UI REST
  views, protected JDBC configuration, and current source.
- Produces: exact write surfaces, live rule ownership, persistence ownership,
  and compatibility constraints.

- [x] **Step 1: Inventory live OpenHAB**

Read `/rest/`, `/rest/items`, `/rest/things`, `/rest/rules`, and the identified
rules without invoking `/runnow` or any Item write endpoint.

Expected: runtime version, live rule IDs/status/triggers, relevant Items, and
Thing health are captured without secret-bearing Thing configuration.

- [x] **Step 2: Compare live owner rules with deployed source**

Run:

```bash
sha256sum openhab/rules/feeder-owner.js openhab/rules/southoutlet-cycle.js openhab/rules/night-load-owner.js
```

Expected: local hashes match authenticated live rule-script hashes.

- [x] **Step 3: Inventory PostgreSQL read-only**

Use the protected OpenHAB JDBC configuration through a subprocess environment
and wrap every query in `BEGIN READ ONLY` / `COMMIT`.

Expected: database/version/timezone, schema/table counts, and historical Item
mapping are captured without printing credentials or changing rows.

### Task 3: Write and review the canonical artifacts

**Files:**
- Modify: `docs/audit/cross-repo-dependency-inventory.csv`
- Modify: `docs/architecture/cross-repo-contracts.md`

**Interfaces:**
- Consumes: verified Task 1 and Task 2 evidence.
- Produces: Stage 1's compatibility and ownership baseline.

- [x] **Step 1: Record findings first**

Document drift, safety blockers, exact external consumer contracts, dormant
artifacts, and unknown deployment state before recommendations.

- [x] **Step 2: Self-review for scope and ambiguity**

Run:

```bash
rg -n 'TBD|TODO|unknown without evidence' docs/audit/cross-repo-dependency-inventory.csv docs/architecture/cross-repo-contracts.md
git diff --check
```

Expected: no placeholders, whitespace errors, or unqualified completion claims.

- [x] **Step 3: Validate CSV shape**

Run a read-only CSV parser and assert every row has the header's exact column
count and a non-empty evidence field.

Expected: all rows parse and the tracker remains machine-readable.

### Task 4: Stage 0 completion gate

**Files:**
- Modify: `docs/architecture/cross-repo-contracts.md`

**Interfaces:**
- Consumes: validated tracker and narrative.
- Produces: explicit Stage 1 go/no-go conditions.

- [x] **Step 1: Confirm no production mutations**

Re-read service/rule status and verify the documentation branch is the only
changed state.

- [x] **Step 2: Record Stage 1 blockers**

At minimum address the deployed UI/remote divergence, OpenHAB version guard,
feeder compatibility, dormant-history handling, and existing timer overlap.

- [x] **Step 3: Review branch diff**

Run:

```bash
git status --short
git diff --stat
git diff --check
```

Expected: only the four Stage 0 documentation files are changed.

# Stage 3 Production Validation — 2026-08-20

## Outcome

The stable observational analytics contract and Energy-page integration are
deployed. The browser has no PostgreSQL, Hexmem, SSH, or private credential
path. Publication adds no actuator authority.

## Published revisions

- `santyr/Solar_PV`: local `main` and `origin/main` at
  `c636d15efebd6c103ed9bd1d9f00a856d1f568a2`.
- `santyr/earthship-ui`: local `main` and `origin/main` at
  `cb9ac07b02c3d5e0ab7415174b61a9e3932df66b`.
- `earthship-ui.service`: active from `/home/sat/earthship-ui`.

## OpenHAB contract and receipt

- Sole Item: `Energy_Analytics_JSON`, type `String`.
- Payload schema: `earthship-energy-ui/v1`.
- Data path: bounded PostgreSQL analytics -> deterministic server-side
  publisher -> OpenHAB Item state -> REST/SSE browser consumer.
- Publisher cadence: enabled and active every five minutes; latest inspected
  service result was `success` with exit status `0`.
- The private receipt
  `~/.local/state/earthship-energy/deploy-receipts/energy-analytics-20260820-v1/receipt.json`
  is closed at desired state, mode `0600`, with exactly one configuration
  write and checksum
  `82a87141d0b805e4f02bd101f66ccb5953c88dd1f0ec63be74f3b34548718598`.
  Its pre-state proves the Item was absent, preserving exact delete rollback.

The live payload inspected at 2026-08-20T22:10:29Z was generated recently
and current through 2026-08-19. It exposed the current Discover epoch, battery
lifecycle and recharge status, energy totals, winter evidence state, forecast
issue/valid timestamps, and source health. Its overall status was truthfully
`degraded`: all 11 required latest-day sources were `ok`, while eight optional
sources remained `freshness_unverified`. Winter fields correctly reported
unavailable with zero winter observation days rather than synthesizing a
conclusion.

## UI behavior

The Energy page renders the versioned analytics payload as observational
status and detail only. It keeps analytics EFC separate from the Schneider
cycle counter and exposes explicit current, stale, malformed, and unavailable
states. Existing bounded controls continue through their prior OpenHAB owner
contracts.

Verification at the published revisions:

- Vitest: `998 passed` across 83 files.
- Production build: passed.
- Playwright: `18 passed`, including Energy analytics detail and the 1340x800
  and 1280x720 tablet/laptop viewports.
- Solar analytics: `143 passed`; `pyflakes`, `compileall`, and diff checks
  clean.

## Live safety and compatibility readback

- `BMS_SOC=99` from the authoritative live Item.
- `SouthOutlet_Outlet2_Switch=OFF`.
- `Thermal_Model_JSON` absent (`HTTP 404`); thermal Gate B was not crossed.
- No existing Item, rule, endpoint, or correlated feeder owner was renamed or
  removed.
- No mining or AGM analytics entered the live payload.
- OpenHAB, Codex, Hexmem, PostgreSQL, and the UI remain outside the electrical
  protection authority held by Discover and Schneider equipment.

## Remaining evidence boundary

Stage 3 is complete. The broader Stage 2-5 program still requires elapsed
natural daily/weekly/monthly scheduler evidence; those timers were installed
on 2026-08-20, so that evidence cannot yet exist. Off-host backup is explicitly
deferred by the operator and remains visibly Actionable in the backup checker.

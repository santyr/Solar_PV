# Stage 5 Production Validation — 2026-08-20

## Published and deployed revision

- Repository: `santyr/Solar_PV`
- Revision: `b8e16140ad01fa8314cf5f67987be1f41632a3ba`
- Local `main`, `origin/main`, and `/home/sat/Solar_PV` matched before unit
  installation.
- Scope: user-level systemd; no OpenHAB rule, Item state, hardware setting, or
  electrical protection change.

## Verification

- Analytics tests after gap closure: `114 passed`.
- `pyflakes src tests`: clean.
- All five service/timer pairs passed `systemd-analyze verify`.
- Source validation after gap closure: 21 resolved sources plus all configured
  required freshness companions, read-only.
- Migration dry run: zero pending migrations.
- Forecast canary: 1,428 immutable facts inserted from one OpenHAB detail
  snapshot; immediate replay inserted zero. One issue timestamp and bounded
  future valid timestamps were retained.
- Daily aggregate canary: 2026-08-19 materialized twice with four domain
  tables plus 21 source-quality rows and the same cumulative EFC
  `4.658455815604`.
- Data quality canary: Routine; source inventory present, aggregate current
  through 2026-08-19, all required live companion checks healthy, and forecast
  age below two hours.
- Backup canary: archive readable and restore evidence fresh; Actionable
  because storage remains same-host/same-filesystem, so disaster recovery is
  false.
- Monthly canary: July report written privately at mode `0600`, SHA-256
  `92e836a5ae7119e6d0247d67bdb1618fbb09f8c720a0b45555212dc4834c46ef`;
  an Interesting pending-review event was created without invoking Codex.

## Installed scheduler

All reviewed installed files matched `deploy/systemd/user/` byte-for-byte.
Manual service runs returned `Result=success` and `ExecMainStatus=0` (including
declared successful structured status 10/20). Journald contained structured
JSON for each run.

| Timer | Installed state | Next-run behavior |
| --- | --- | --- |
| `energy-data-quality.timer` | enabled/active | hourly at :20 |
| `energy-forecast-snapshot.timer` | enabled/active | every two hours at :10 |
| `energy-daily-aggregate.timer` | enabled/active | local 00:20 |
| `energy-backup-check.timer` | enabled/active | Sunday 03:30 |
| `energy-monthly-report.timer` | enabled/active | first day 07:15 |

Disable/re-enable rollback was exercised on
`energy-forecast-snapshot.timer`: disabled/inactive was observed, followed by
enabled/active restoration.

## Safety and compatibility readback

- `BMS_SOC=99` from the live authoritative Item.
- `SouthOutlet_Outlet2_Switch=OFF`.
- `Thermal_Model_JSON` remained absent; thermal Gate B was not crossed.
- The latest feeder request ledger entries remained `complete`; no feeder
  Item/rule was changed.
- Existing `openhab-sanity.timer` and `forecast-json.timer` remain the owners
  of live OpenHAB health and UI forecast refresh respectively.

The Stage 2 gap-closure validation added atomic `daily_source_quality`
materialization and made the hourly canary fail closed on missing or stale
required health companions. It did not add a control or action path.

## Long-term calendar checkpoints

- Existing calendar coverage was verified for the annual system-health review,
  the 2030 architecture review, 2034 migration readiness, and the 2038
  battery-technology/whole-system review.
- Added private, transparent checkpoint
  `dpn8gvm83jl81hc01h94kheuqs` for 2033-01-15: select the preferred migration
  architecture.
- Added private, transparent checkpoint
  `h4g6fr5r45l9heq49r1oo99018` for 2035-04-04: Schneider support-horizon
  readiness. Both new checkpoints use a one-week popup reminder.

## Open item requiring operator input

The backup scheduler is operational but intentionally reports Actionable.
An encrypted off-host or separately mounted destination, retention policy, and
automated restore cadence cannot be selected without the operator choosing the
destination and recovery requirements.

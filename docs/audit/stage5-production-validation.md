# Stage 5 Production Validation — 2026-08-20

## Published and deployed revision

- Repository: `santyr/Solar_PV`
- Revision: `b8e16140ad01fa8314cf5f67987be1f41632a3ba`
- Local `main`, `origin/main`, and `/home/sat/Solar_PV` matched before unit
  installation.
- Scope: user-level systemd; no OpenHAB rule, Item state, hardware setting, or
  electrical protection change.

## Verification

- Analytics tests: `86 passed`.
- `pyflakes src tests`: clean.
- All five service/timer pairs passed `systemd-analyze verify`.
- Source validation: 15 resolved sources, read-only.
- Migration dry run: zero pending migrations.
- Forecast canary: 1,428 immutable facts inserted from one OpenHAB detail
  snapshot; immediate replay inserted zero. One issue timestamp and bounded
  future valid timestamps were retained.
- Daily aggregate canary: 2026-08-19 materialized twice with four tables and
  the same cumulative EFC `4.658455815604287`.
- Data quality canary: Routine; source inventory present, aggregate current
  through 2026-08-19, forecast age below two hours.
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

## Open item requiring operator input

The backup scheduler is operational but intentionally reports Actionable.
An encrypted off-host or separately mounted destination, retention policy, and
automated restore cadence cannot be selected without the operator choosing the
destination and recovery requirements.

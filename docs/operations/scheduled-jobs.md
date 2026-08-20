# Scheduled Energy Jobs

The analytics scheduler is user-scoped systemd. OpenHAB remains responsible
for raw collection and deterministic electrical safety. Maintenance jobs read
raw history and write only `energy_analytics` or private files below
`~/.local/state/earthship-energy`. The dedicated UI publisher reads bounded
analytics and writes only `Energy_Analytics_JSON`. No energy job invokes Codex,
writes Hexmem, or controls hardware.

| Unit | Cadence | Purpose | Inputs | Outputs | Invokes Codex? | Severity handling | Manual run |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `energy-data-quality` | hourly at :20 | Check source inventory, current required-source health, previous-day quality-approved aggregate, forecast age | JDBC config, source contract and freshness companions | structured journal JSON; actionable pending event | No | Routine / Interesting / Actionable | `systemctl --user start energy-data-quality.service` |
| `energy-forecast-snapshot` | every 2 hours at :10 | Preserve the current additive OpenHAB forecast with issue/valid timestamps | `Forecast_10Day_JSON`, JDBC config | deduplicated `forecast_snapshots` rows | No | nonzero exit on malformed/unavailable input | `systemctl --user start energy-forecast-snapshot.service` |
| `energy-daily-aggregate` | 00:20 local | Idempotently materialize the previous local day | raw JDBC history, source/epoch contracts | four daily tables plus source quality | No | nonzero exit; pending migrations refuse the run | `systemctl --user start energy-daily-aggregate.service` |
| `energy-backup-check` | Sunday 03:30 | Check restore evidence freshness and archive readability | verified backup manifest/archive | structured result; actionable pending event | No | current same-host-only backup remains Actionable | `systemctl --user start energy-backup-check.service` |
| `energy-monthly-report` | first day 07:15 | Prepare the previous month for human/Codex review | compact daily products | private versioned JSON plus pending-review event | No | Interesting means review is pending | `systemctl --user start energy-monthly-report.service` |
| `energy-ui-publish` | every 5 minutes | Publish a closed observational UI snapshot | quality-approved analytics products | `Energy_Analytics_JSON` state only | No | nonzero exit; no write after validation failure | `systemctl --user start energy-ui-publish.service` |

The existing `openhab-sanity.timer` continues to own ten-minute live Item,
rule, algorithm, and persistence health. The existing `forecast-json.timer`
continues to refresh the OpenHAB/UI forecast every two hours. The analytics
snapshot runs afterward and does not replace either job.

The hourly health check resolves every required source and its persisted
companion. BMS status/device-present states must be healthy, Schneider update
timestamps must be no more than 120 seconds old, and the weather health state
must be `OK`. A missing companion, invalid timestamp, stale update, or
non-healthy state is Actionable. The daily aggregate checkpoint only advances
when battery, PV, load, and weather rows all have `quality=ok`.

## Installation and status

Reviewed units live in `deploy/systemd/user/`. Production expects the repo at
`/home/sat/Solar_PV`:

```bash
install -m 0644 deploy/systemd/user/energy-* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now energy-data-quality.timer \
  energy-forecast-snapshot.timer energy-daily-aggregate.timer \
  energy-backup-check.timer energy-monthly-report.timer \
  energy-ui-publish.timer
systemctl --user list-timers 'energy-*'
```

Inspect a run with:

```bash
systemctl --user status energy-data-quality.service
journalctl --user -u energy-data-quality.service --since today
journalctl --user -u 'energy-*' --since '7 days ago'
```

Each service uses `flock --nonblock` under `%t`, has a bounded timeout, a
private umask, and writes structured JSON to journald. Exit `10` means
Interesting and exit `20` means Actionable; relevant units declare those
statuses successful so expected review events do not look like crashes.
Unexpected failures remain failed units in journald.

## Pending investigations and Codex

Actionable quality/backup results and monthly review requests are durable,
deduplicated JSON below:

```text
~/.local/state/earthship-energy/pending-events/
~/.local/state/earthship-energy/reports/YYYY-MM/energy-monthly.json
```

Codex processes these during an attended review, verifies the conclusion from
the named report/query, and only then records a durable semantic conclusion in
Hexmem. Routine timer results remain in PostgreSQL/journald and never enter
Hexmem. AI downtime therefore cannot stop telemetry, aggregation, or safety.

## Backup limitation

The 2026-08-20 archive is checksum- and restore-verified but resides on the
same host and filesystem as PostgreSQL. The backup checker intentionally emits
Actionable until an encrypted off-host or separately mounted destination is
provided and verified. It does not claim disaster recovery and does not copy
data to an operator-unapproved destination.

## Disable and rollback

```bash
systemctl --user disable --now energy-data-quality.timer \
  energy-forecast-snapshot.timer energy-daily-aggregate.timer \
  energy-backup-check.timer energy-monthly-report.timer \
  energy-ui-publish.timer
systemctl --user daemon-reload
```

Disabling timers stops future runs without deleting analytics, reports, or
evidence. Unit removal is optional and should be done only after comparing the
installed files with the reviewed repository copies. Database products remain
rebuildable and raw `public.itemNNNN` tables are never modified.

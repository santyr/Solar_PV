# Recovery and Backup

Before production changes, preserve:

- OpenHAB configuration and JSONDB;
- PostgreSQL schema/data backups appropriate to the change;
- Schneider/Insight configuration exports;
- current firmware/manual artifacts;
- repository commit and deployment identity.

A recovery procedure is not validated until restoration/readback is tested.
Stage 2 owns database backup/restore validation; Stage 5 owns deterministic
backup-verification scheduling. Do not claim either is operational merely
because this runbook exists.

## 2026-08-20 analytics migration restore point

The first `energy_analytics` migration was gated by a PostgreSQL custom-format
dump and a complete isolated restore. Private host-local artifacts are under
`/home/sat/backups/earthship-energy/2026-08-20/` with mode `0600`:

- `openhab-pre-energy-analytics.dump` (2.0 GB compressed);
- `backup-manifest.json`;
- `restore-verification.json`.

The archive SHA-256 is
`3aaa0a7ed6c5a05bfbb1e0f29a56d9772e6a83630f2ff213a016dd939c70183c`.
The restore reproduced 418 `public` tables, 3 `thermal_intel` tables, 416 Item
mappings, and all 15 configured source histories. The temporary verification
database was dropped after those checks passed.

This restore point is on the same host and filesystem as PostgreSQL. It is a
verified migration rollback artifact, not disaster recovery. Stage 5 must add
an off-host or separately mounted encrypted destination, retention, automated
restore testing, and alerting before backup operations can be called complete.
`energy-backup-check.timer` now verifies freshness and archive readability
weekly and keeps this limitation Actionable; an off-host destination still
requires operator selection.

List an archive without restoring it:

```bash
pg_restore --list /home/sat/backups/earthship-energy/2026-08-20/openhab-pre-energy-analytics.dump
```

Never put the protected JDBC password on the command line or in this repository.

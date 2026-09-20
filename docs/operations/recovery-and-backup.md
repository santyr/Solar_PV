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

Historical receipt: superseded for scheduled monitoring by the September 20
full-database data rehearsal below. Retain the old archive for recovery history.

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

September 20 monitor correction: freshness requires a verification timestamp
between now minus the permitted age and now, never in the future. The check also
streams the archive's SHA256 and compares it with `archive_sha256` from the
restore manifest; listing the archive alone is insufficient. Missing/malformed
hashes, changed archives, symlinks, non-regular files and read errors cannot yield
verified integrity. Readability timeouts fail closed. The result exposes
`archive_integrity_verified` separately from historical `restore_verified`.
This does not turn a same-host copy into disaster recovery, qualify role/ACL
restoration, or refresh the age of an old restore exercise.

List an archive without restoring it:

```bash
pg_restore --list /home/sat/backups/earthship-energy/2026-08-20/openhab-pre-energy-analytics.dump
```

Never put the protected JDBC password on the command line or in this repository.

## September 20 full-database data restore point

The full archive under
`/home/sat/backups/earthship-energy/full-restore-0lnrkogj/` restored successfully
and all 510 tables matched fingerprints from the same exported production
snapshot at 18:59:53Z. The isolated container was removed. Directory mode 0700;
archive and manifest modes 0600. SHA256:
`6e6fba4f7608500a0964f453b57fb9a20b1f39fb857ed66563139f8b437d5e31`.
Independent monitor assessment confirms fresh/readable/restore-verified and
matching archive integrity. The versioned backup-check service now selects this
manifest. Same-host-only remains Actionable; off-host destination is deferred.
This no-owner/no-privileges rehearsal does not establish role/ACL, configuration,
OpenHAB restart or disaster recovery. No manual notification job is required to
adopt the new reference; retain the existing weekly timer.


## Energy analytics Item restore evidence

Before provisioning `Energy_Analytics_JSON`, the earthship-ui transaction tool
captures the exact prior Item configuration or verified absence in a private
receipt. Keep that receipt with its apply/readback/closure evidence; it is the
only authorized source for configuration rollback. The Item carries no control
authority and its state can be allowed to become stale after the publisher is
disabled.

The existing PostgreSQL restore point remains same-host only. The operator has
deferred an off-host destination, so `energy-backup-check` must continue to
report `Actionable`; neither the Item receipt nor analytics publication changes
that disaster-recovery limitation.

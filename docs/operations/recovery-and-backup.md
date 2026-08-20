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

# Live-health consumer correction

The atomic history reader release b08ae14 changed the shared SoC freshness
configuration to `atomic_bms_evidence`. Two existing scheduled live-health
consumers also loaded that configuration, but their policy evaluators did not
recognize the new policy. They therefore reported BMS fault/live-source failure
even when comms were OK. A successful publisher process exit did not establish
semantic payload correctness; the earlier release checks missed these consumers.

Hotfix6a992f0 introduces an explicit `live_health_source_config` transformation
for the quality-check and UI-publisher entry points. It preserves their existing
`BMS_Comms_Status`/`status_must_equal_OK` contract. Daily/hourly historical reads
retain atomic evidence. This is not a historical fallback and does not authorize
the separately scoped two-minute live-health/checker policy migration.

Verification before deployment:383tests passed in7.34seconds, including both
actual scheduled caller paths and preservation of the historical configuration.
Two old publisher tests used string-only config placeholders; they now load the
real configuration while retaining their database-close-before-write and no-write
on-failure assertions. The actual read-only comparison returned BMS fault before
the fix and OK with the explicit live contract; all other subsystem states
matched and `_live_sources_ok` returned true.

The hotfix was fast-forwarded into production main, pushed to origin/main and
verified using the deployed `read_quality_state` entry point. No timers, services,
thresholds, persistence configuration or notification code changed. No manual
publication or test DM was performed, and prior operational records were not
deleted or relabeled. Natural publisher payload readback remains the final
verification recorded below.

Natural readback passed: the17:20:29MDT publisher exited0 and emitted
`generatedAt=2026-09-10T23:20:29.113938+00:00`. BMS is now `ok`, and
`bms_live_health_not_ok` is absent. Other live subsystems are also OK. Overall
analytics remain degraded solely for `daily_source_quality_not_ok`; this
separate persisted-data limitation was not suppressed by the correction.

Separately, the outcome feature branch includes the current-revision/seven-night
projection294d0ab and this hotfix via mergeba55b3f. Its fullsuite441tests passed
in15.67seconds. Outcome migrations and live scoring remain undeployed.

# Qualified power accounting storage

Production activation supersedes the original source-only checkpoint: migration
5, restricted writer/reader roles and qualified daily/UI/quality jobs are live as
of September 20. Qualified monthly preparation was subsequently enabled from
`5fc878a`. See earthship-ui's `2026-09-20-power-production-activation.md` receipt
and [monthly consumer contract](2026-09-20-qualified-monthly.md). The first natural
completed-day snapshot remains unobserved; no historical rows were fabricated.

Migration0005 creates `daily_power_snapshots`, an append-only revision series.
It does not modify historical `daily_battery`, `daily_pv`, load, weather or
source-quality rows. Qualified daily composition is routed to this store;
explicit legacy composition retains its old storage path.

Identity is bank epoch, local date, accounting policy, exact evidence cutover
and canonical payload SHA256. Identical retries are idempotent. Changed daily
evidence creates another retained revision. Latest revision selection uses the
monotonic snapshot ID, not ambiguous wall-clock ordering. Retrying an old revision
does not select it again. The stored payload includes all daily sections and
per-source evidence quality; only the three named battery/PV power fields are
claimed qualified. Load and weather have their existing independent contracts.

The writer serializes each bank/policy/cutover series with a transaction-scoped
advisory lock, rejects autocommit, verifies readback, and calculates cumulative
EFC from the latest revision per day through the requested day. It never sums
other cutovers or legacy estimates. Partial-day observed qualified throughput
is retained; this counter is not an assertion of complete lifetime coverage.
Unknown accounting policies cannot fall through to the legacy writer.

Database triggers reject UPDATE, DELETE and TRUNCATE. Public permissions are
revoked. Application validation rejects malformed provenance, invalid/nonfinite
energy/EFC, bad windows, oversized payloads and unqualified AC-load balances.
PostgreSQL constraints independently bind payload identity and policy columns.

## Release gates

Backup/migration rehearsal, restricted roles, explicit cutover policy, daily
writer, v3 UI and qualified monthly consumer have been deployed and verified at
their respective configuration/readback boundaries. Natural completed-day and
monthly execution remain time-dependent evidence gates. Lifecycle/winter reports
and feature exports still need explicit qualified integration; they must not be
described as qualified merely because the writer is enabled. All readers must
expose policy, cutover and coverage and must not present the new series as a
continuous extension of historical estimated totals. Independent AC-load
qualification and full-day source/persistence validation remain outstanding.

Real isolated PostgreSQL tests cover retries, revisions, legacy isolation,
cutover isolation, mutation refusal, privilege separation and transactional
locking. Existing migration files remain unchanged; only0005 is new.

## Qualified report consumer

`energy-data report power --start YYYY-MM-DD --end YYYY-MM-DD
--power-evidence-policy analytics/config/power-evidence.json` reads only the
selected qualified series. The end is exclusive; one request is bounded to366
days using the dedicated read-only snapshot connection and its5-second SQL
timeout. JSON and Markdown include policy, exact cutover, as-of time, each day's
revision ID/digest/computed time and battery/PV daily coverage. Missing days stay
listed, empty history has null totals, and revisions are selected before quality
interpretation. Lower-coverage corrections cannot resurrect older larger totals.

Totals mean observed qualified throughput within the requested window, not bank
lifetime use or complete-day estimates. They do not include legacy EFC. Load and
balance are explicitly unavailable until AC-load evidence is qualified. This is
an additive explicit report kind; it does not silently change the historical
monthly/lifecycle/winter commands or activate the publisher. Those commands,
feature exports and the UI still need their own reader/provenance integration
before accounting activation. Unit and real disposable PostgreSQL tests cover
the new report path, missing dates, exact identity and latest-revision selection.

## Qualified UI producer (source-only)

The `energy-ui-publish` scheduled entry point accepts an explicit
`--power-evidence-policy` opt-in. Without it, the existing v2 path is unchanged.
With it, the dedicated bounded snapshot reader selects up to366completed local
days; the latest selected revision is retained even when partial. No legacy
daily table is read in this path. Daily health comes from the latest qualified
snapshot's source quality only when it represents yesterday; missing yesterday
is unavailable rather than replaced with older healthy evidence. Live subsystem
health, independent module samples and the forecast keep their existing readers.

Python validation/projection matches the frontend v3 contract in earthship-ui
`docs/operations/2026-09-20-qualified-energy-ui-contract.md`. Observed-window
charge/discharge/EFC are derived from selected revisions, with policy/cutover,
counts, latest revision digest and coverage. Latest partial-day energy is retained;
unqualified daily SoC summaries are withheld. Lifetime cumulative, unsupported
AC balance and unsupported winter summaries are not invented. Existing publisher
transport still validates then writes exactly the observational String Item.

All687analytics tests pass, including opt-in scheduler forwarding and no legacy
daily/quality fallback. Actual Python-encoded partial and empty projections were
accepted by the frontend JavaScript parser; partial retained2days/1missing and
empty retainednull totals. No live publisher flag, database migration or grant
has changed. Release still requires migration/backup rehearsal, restricted roles,
other consumer policy treatment, and completed-day writer qualification. In
particular, UI revisions must have been computed after their local day completed;
do not activate a writer that stores provisional current-day results as final.

Completed-day safeguards are now implemented: Python checks exact America/Denver
day bounds (including23/25-hour DST days) and refuses unfinished-day writes.
Migration0005, still undeployed, independently checks the same bounds in an
INSERT trigger and assigns revision time from the database clock. Supplying a
future `computed_at` cannot bypass completion. Readers reject revisions computed
before their represented window completed. Synthetic fixtures were moved to
historical August dates; the real collection cutover configuration is unchanged.
All693analytics tests pass, including direct-SQL bypass attempts and actual
PostgreSQL DST-day inserts. Production backup/rehearsal is in progress, not yet
verified by these tests.

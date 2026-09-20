# Qualified power accounting storage (source-only)

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

No live migration, grants or scheduler configuration has been applied. Before
production activation: rehearse backup/restore and migration, configure the
restricted writer/reader, wire explicit evidence policy and actual cutover,
and migrate daily report/export/UI readers to select the appropriate versioned
series. Readers must expose policy, cutover and coverage; do not present a new
qualified counter as a continuous extension of the historical estimate.
Do not enable the new writer while downstream readers still only inspect the
legacy daily tables. Collection may continue independently during this work.

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

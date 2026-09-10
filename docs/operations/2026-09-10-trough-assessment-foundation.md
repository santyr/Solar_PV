# Completed-night measurement foundation

This branch implements the measurement prerequisite of the approved September5
advisory-outcome design. It is not a deployed scorer or activated capture path.

`trough_assessment.assess_trough_measurement` accepts original bounded JDBC
observations and configured bank boundaries. It reuses the shared atomic BMS
interval builder and the existing recorded-timezone trough-window definition.
Before following-day11:00 it returns pending without consuming observations.
After completion, only at least90percent validated coverage yields a measured
minimum. Partial extrema remain explicitly diagnostic and cannot become a score.

The result includes version, target/window, assessment time, record/segment
counts, coverage, source, observed bounds and an evidence digest. Reassessment
time does not change evidence identity; all inputs to sequence validation do.
Observation and record-size limits fail closed. No causal reward, compliance,
action attribution, residual, diagnostic projection or learning update is made.

Verification:12new cases,393full analytics tests passed in7.76seconds using
`PYTHONPATH=/home/sat/earthship-ui/openhab/scripts:analytics/src`. Cases cover
January/July and both DST transitions, exact completion, expiry, duplicates,
90percent boundary, empty/oversized input and deterministic evidence identity.
Actual read-only PostgreSQL assessment of the September9 prediction's completed
night returned insufficient_data, coverage0, record_count0 and null minimum:
the new source did not yet exist and historical numeric carry is not substituted.
This is evidence of correct rejection, not a genuinely measured live outcome.

Remaining: origin-aware versioned outcome records/storage; bounded backlog and
frozen first accepted pre20:00 publication selection; deterministic diagnostic
projection preserving legacy arrays; other quantity/source and action evidence;
least-privilege runtime wiring, reviewed activation and a genuinely completed
post-activation live target. Prediction equations, thresholds,06:40 schedule,
notifications, controls and all learned state remain unchanged. Task82 is held.

## Immutable-origin association

`trough_outcomes.assess_trough_decision` now uses the same closed origin validator
as the append-only decision store. It rejects forged targets/extra fields,
wrong-bank attribution, issue times outside the bank, assessment before issue,
and out-of-range SoC predictions. Measured residuals use the exact recorded
prediction minus the validated minimum; pending/insufficient evidence has no
residual. Issue before target start is explicit, including strict rejection of
the exact20:00 boundary as a pre-window origin. Publication and action evidence
are not inferred, and bandit eligibility remains false.

Seven focused tests cover this association. This adds no persistence, frozen
publication selection, projection or runtime activation; those remain required.

## Append-only outcome storage

Migration0003 and `AdvisoryStore.put_trough_outcome` now persist completed,
bounded measured/insufficient outcomes. The adapter constructs the outcome from
the validated origin and evidence, then compares the entire canonical parent
with the stored decision. Identity is decision/version/evidence-digest. A retry
with unchanged evidence is a no-op, ignoring only the reassessment clock; changed
evidence creates an explicit revision. Existing rows are never updated/deleted.
Pending and over-limit inputs are reportable but not persisted as revisions.

An adversarial regression first exposed a retry gap: changing an origin field
not copied into the outcome could be mistaken for a replay. The retry lookup
now checks the complete parent too; the regression passes. Separate disposable
roles prove that capture cannot insert outcomes and assessment cannot insert
decisions. The new table has no PUBLIC grants and rejects UPDATE/DELETE/TRUNCATE
even from the owner through the existing append-only trigger.

Eleven new persistence cases cover exact and concurrent replay, revisions,
parent mismatch, separate privileges, mutation refusal, pending no-connect,
insufficient-data retention, and bounded lock timeout/rollback with no partial
row. Fullsuite:411passed in11.57seconds. PostgreSQL verification remains confined
to disposable test databases. Read-only production readback still shows only
migrations[1,2], and production code remains409630e. Migration0003 is deliberately
feature-branch-only: merging a pending migration prematurely would block the
existing daily aggregate job. No production migration or capture activation occurred.

Still required: frozen first-accepted publication selection and current-revision
queries, bounded backlog, deterministic diagnostic projection and legacy-state
preservation, remaining quantity/action evidence, runtime wiring/reviewed release,
and actual completed post-activation evidence. No outcome is bandit eligible.

## Frozen diagnostic origin

Migration0004 adds an append-only selection keyed by physical bank, prediction
day and `completed-night-v1`. A composite foreign key binds its publication
result to the same decision. Capture has no selection privilege; the separate
assessor can read candidate decisions/results and insert/read selections.

`choose_trough_origin` validates closed decision/result schemas and chronology.
Only post-cutover decisions issued strictly before target20:00 with an observed
accepted `Predicted_SoC_Trough_Tomorrow` publication qualify. Advisory acceptance
and notification success are not substitutes. Candidates order by recorded
accepted-publication time, then issue time and UUIDs for deterministic ties.
The result time must be no later than assessment time; this is acceptance
evidence, not proof of actual display or human receipt.

`freeze_trough_selection` does not connect before window completion. It reads at
most1001candidates and refuses overflow instead of selecting from truncated
evidence. A primary-key insert freezes the first choice atomically; retries
read the stored selection, including after later arrival of an earlier origin.
Changed cutover/timezone configuration conflicts rather than silently changing
meaning. Missing eligible evidence does not freeze a negative selection.

Eighteen new tests cover eligibility, result/parent chronology, cutoff bounds,
pending/limits, order independence, durable late-arrival behavior, concurrent
insertion and append-only/role constraints. Fullsuite429passed in13.84seconds.
Migrations0003/0004 remain feature-only, tested in disposable databases; no
production migration, capture/scorer activation, legacy state or DM change.
Current-revision queries, bounded assessment orchestration and deterministic
diagnostic projection remain the next integration steps.

## Current revisions and seven-night diagnostic

`trough_projection` now reads at most30frozen target nights and each selected
decision's latest committed assessment revision as of the report time. Quality
filtering occurs after latest-revision selection: a newer insufficient revision
cannot fall back to a previous measured value. Assessment-time/digest ordering
is deterministic, and future revisions/selections are excluded from as-of reads.

The pure projection rejects duplicate nights, mismatched origins/targets/banks,
invalid measurement ranges and inconsistent residuals. It rebuilds the mean
absolute error from the latest seven distinct verified nights without mutating
history or consumption markers. Output includes actual sample count/dates,
coverage, evidence identities and missing/insufficient/pending dates; unavailable
is explicit until there is a verified night. One sample is never labeled seven
days of evidence, and no causal reward or bandit eligibility is assigned.

Ten new tests include actual disposable PostgreSQL as-of/current revision
comparison. Fullsuite439passed in16.14seconds before merging the separate
live-health compatibility hotfix. No diagnostic Item write or outcome activation
has occurred; bounded orchestration and publication remain required.

## Bounded assessment orchestration

`trough_runner` now connects completed-day selection, original evidence reads,
origin-aware assessment, append-only storage, frozen selection and the diagnostic
projection. Its window is at most30completed prediction days, with1000decision
limit,10001-row overflow detection for telemetry and one-night-at-a-time caching.
At06:40 the preceding night's11:00 target is excluded; at completion it becomes
eligible. Older unassessed origins are explicitly counted as expired/unscored.

A dedicated read-only READ COMMITTED connection sees the separate store's
committed outcomes on subsequent projection reads. Each read has a two-second
statement timeout. A cooperative30-second budget is checked between operations,
including after the final read; exhaustion returns no publishable projection.
The runtime owner still must enforce a hard process deadline: this function
cannot preempt an in-flight operation. Store operations retain bounded timeouts
and no automatic retries. There is no OpenHAB, notifier or control dependency.

Twelve new tests include an end-to-end disposable PostgreSQL run: an incomplete
night reads no telemetry, a completed night stores both origins but projects one
frozen sample, and a later invocation inserts no duplicates. Row limits, expired
origins, invalid runtime options and both early/final time-budget exhaustion are
covered. Fullsuite453passed in18.99seconds after the one-night cache tightening.
Runtime hard timeout, reviewed activation and observational publication remain
unfinished; no production migration or scorer change occurred.

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

# Deployed analytics source publication — 2026-10-29

This publication brings the verified deployed reader source
`analytics-reader-release-2fd49d818476` and the current-product acquisition
service/timer onto remote main. The immutable reader release remains selected;
publication does not restart services or alter private writer/reader credentials.

The changes retain original issued-product identities, separate namespaces,
append-only snapshot acquisition, product-specific expiry and the explicit UI v5
reader path. Live health follows its supported current health fields without
turning independently degraded daily-source quality into healthy historical data.
The corresponding Earthship UI, native/sensitivity and sensor changes are
reconciled in `santyr/earthship-ui` under the OpenSpec change
`merge-deployed-repairs-to-main`.

The full maintained analytics suite passes **935 tests** against the exact
deployed Python source and its required Earthship helper imports. Original
failures and capped resource receipts are retained in the Earthship workspace's
`artifacts/merge-deployed-main-20261029.local/` directory. Private configuration,
telemetry and model artifacts are not published. The original dirty Solar_PV
checkout/index and newer remote electrical/fuse documentation are preserved.

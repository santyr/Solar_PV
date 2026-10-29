# Current forecast analytics acquisition and UI v5

Source-only repair, 2026-10-24. Activation requires the reader-first sequence below. This document does not assert deployment or observed scheduled capture.

`current_forecasts.py` acquires only fixed loopback authenticated GET of `Forecast_10Day_JSON` and the two owned private public-view caches at `~/.local/state/household-intel/{daily-pv-potential,energy-observation}.json`. It does not collect weather, execute models, import producer code, or publish. Existing v1/v2 decoding and historical rows remain unchanged. Namespaced metrics never enter existing `temperature_f` or `daily_pv_kwh` feature exports.

Every row retains original issue, exact-byte product hash, bounded curated provenance and original validity. Weather keeps raw provider, core and selected-production issue hashes separately, extended/nearTerm clocks and per-hour selected profile. A missing per-hour profile means the producer's original extended profile. Weather freshness is the explicit consumer policy of four hours from publication and at most 24 hours from source initialization, not a fabricated upstream expiry. Compatibility `releaseAuthorized` is retained verbatim.

PV retains the original remaining/full-day scope, Denver day bounds (including DST), all model/system/geometry/horizon identities, component support/fallback and false physical/actuation flags. An original preparation receipt remains `issued=false`. Confirmed publication additionally requires a genuine self-hashed emission bound to the exact public bytes, original receipt, native forecast hash/origin/issue and original publication deadline. Enumeration is capped at4096 entries, at most32 bounded emission reads and one8MiB receipt read; unresolved emissions remain explicitly unconfirmed. No receipt or cohort is invented. Household potential has a15-minute issue lifetime and an immutable public-view digest, exact24 ordered targets, original receipt and actual nullable cohort. Conditional captured potential is separate and nullable.

New sources and marker metrics are:

| Source | Marker |
|---|---|
| `weathernext3_selected_weather_v3` | `weathernext3.weather.publication` |
| `weathernext3_component_daily_pv_v4` | `weathernext3.daily_pv.publication` |
| `household_energy_potential_v1` | `household.energy.publication` |

`persist_current_forecasts` validates source/metric namespaces and appends with `ON CONFLICT DO NOTHING`. Exact duplicate evidence is a no-op; a conflicting identity rolls back the complete capture transaction. It never updates/deletes historical rows. `current-forecast-snapshot --dry-run` performs no database connection, publication or last-result write. Normal acquisition failures are summarized privately, separately from immutable forecast evidence. A write refusal/failure is sanitized and returns domain exit20; its detail cannot leak credentials. Inspect product-specific last-result and freshness, not just service exit state.

A dedicated reviewed JDBC role/config is mandatory; do not reuse the raw OpenHAB owner or the read-only power reader. `verify_current_writer` checks SELECT/INSERT, schema USAGE and identity-sequence USAGE; rejects UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER, schema CREATE, privileged role attributes, or mutation rights to any other application table/view. Provision the role outside the acquisition job. No schema migration is needed. Save its config0600 at `~/.config/hex/energy-current-forecast-writer.jdbc`; never log its contents. The mandatory `energy-current-forecast.env` contains only `PYTHONPATH=/absolute/reviewed/analytics-release/analytics/src`.

Quality always selects the latest as-of marker for each exact source/metric, with both issue and capture clocks bounded by now and deterministic issue/capture/ID ordering. It selects before assessing status/expiry. A newer unavailable product or invalid latest record never falls back to an older available issue. All three current products are needed for forecast health `ok`; science/calibration remains explicitly unqualified. Existing aggregate/BMS/AC policies remain independent.

UI publication is opt-in: `energy-ui-publish --current-forecasts` requires an existing qualified v4 base with accounting/AC validation, changes only the forecast protocol and associated forecast health, and emits `earthship-energy-ui/v5`. Default remains v4 for rollback. The closed v5 forecast has no legacy `pv24hKwh` alias or inferred morning SoC/full-day claims. Server and UI re-evaluate each product deadline. The Energy screen already reparses the retained Item every30seconds without refetch; expired parent analytics also suppresses all current-facing forecast numbers/booleans while retaining completed-day observations. V1-v4 remain accepted and receive the same stale suppression.

## Activation order and rollback

1. Record exact current unit/drop-in/config bytes and code-root digests privately. Qualify/activate the backward-compatible UI successor first; verify existing v1-v4 accounting and the new v5 fixture with browser tests. Keep sealed producer releases untouched.
2. Qualify a separate immutable analytics release containing this patch. Use only the supported Python3.12 with bytecode disabled before the outer bounded launcher. Validate exact-byte product/receipt/emission read-only dry-run and the dedicated writer's privilege report.
3. Install only the new `energy-current-forecast-snapshot.service/.timer` templates, binding PYTHONPATH to that release; retain every existing qualified power/AC/BMS configuration argument when repointing publisher/quality code roots. The five-minute timer runs at:02,:07,...,:47,:52; it follows normal household completion and catches the PV/weather hourly slot. It does not schedule or launch any producer.
4. Observe the first genuine capture and an exact repeated issue returning inserted0, preserving original issue clocks. Only then dry-run the existing publisher with `--current-forecasts`, inspect exact v5 payload and size, and enable its opt-in flag after deployed reader verification.
5. Observe scheduled capture/publisher/quality over a genuine hourly weather/PV slot and a household15-minute expiry case. Do not use synthetic rows, backdated issues or service success as these gates.

Rollback disables/removes only the new capture timer and its units, restores saved analytics code roots and publisher v4 arguments, then verifies emitted v4 before any reader removal. The compatible UI can remain. Keep every namespaced appended row immutable; old readers ignore their metrics. Never restore retired provider collection, change source clocks/receipts, alter electrical/financial controls, or delete history.

Task-specific exact commands, source BASE/HEADs and qualifications are recorded in the isolated repair workspace's `task-4-report.md`; deployment and natural scheduled observations are the parent operator's pending gates.

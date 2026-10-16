# PV forecasting and measurement boundaries

Current checkpoint: **2026-10-15**. This document records engineering meaning
and operating interpretation; the forecasting implementation is in
`earthship-ui`.

## Array and load configuration

The canonical [current-system record](../architecture/current-system.md#pv-array)
contains the 4.2 kW quoted DC array rating, approximately 165° azimuth and
57.4° panel tilt above horizontal. The operator's phone read 32.6° with
horizontal at 90°; preserve that convention when reproducing the conversion.
The tilt was chosen for December gain. Exact module model, strings and
shading remain unverified; do not invent them for a physical forecast.

The operator confirms that current household loads are AC; remaining DC
loads concern the battery and solar system. Use source-qualified inverter
output under its attested topology for household consumption. Battery charge
and discharge are separate storage flows. Controller PV output is an observed
quantity; DC overhead and conversion losses remain unknown.

## Forecast quantities

Potential array generation depends on available sunlight and the array's
receiving plane and performance. Captured energy additionally depends on
household demand, battery headroom, charging limits and losses. Lower starting
SoC can enable greater capture after a cloudy day, but does not increase the
solar resource. Never add recharge demand onto a forecast that already
includes the charge deficit.

PV and indoor temperature share solar inputs. Reuse the retained weather
forecast and Astro geometry, then apply separate response models. PV needs
panel-plane irradiance and module/electrical response; indoor temperature
needs glazing, shades, ventilation and thermal mass response. Forecast and
measured radiation remain distinct. The physical modeling sequence follows
[pvlib's documented ModelChain](https://pvlib-python.readthedocs.io/en/stable/reference/modelchain.html).

## Valley horizon and seasonal sunlight

The operator reports mountain shadows that shift effective direct sunlight
through the year. At the supplied site coordinates, an October 15 PVGIS 5.3
terrain-horizon request estimates skyline elevations of 4.2 degrees due east,
1.9 degrees southeast, 8.4 degrees southwest and 8.8 degrees west. These are
provisional map estimates, not measured sunlight times. The original response
is retained privately by `earthship-ui`, SHA-256
`284643f993d60d48165cb01ea77475dcfd1bc5836ec4d119780e76806d900846`.

[PVGIS terrain horizons](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-tools/horizon-profile_en)
use approximately 90 m terrain cells and do not resolve nearby trees or
buildings. Use the map as an initial skyline profile; compare repeated
irradiance observations by solar azimuth/elevation and validate corrections on
later days. Twelve retained October days have been examined; seven pass full
day receipt coverage checks. Coverage does not prove clear skies, calibrated
irradiance or a validated annual horizon. Clouds, station obstructions and
curtailed PV output must not become false mountain labels.

Share the provisional terrain input between solar-dependent models while
keeping window/panel/station obstructions distinct. Terrain blocks direct
beam while diffuse light remains; do not zero all generation in mountain
shade. Keep native Astro sunrise/sunset events and owner daylight rules
unchanged. A provisional terrain-aware observer is now deployed separately
from the existing daily predictor; physical horizon validation remains open.
Evidence and integration boundaries are in
`earthship-ui/docs/operations/2026-10-15-terrain-horizon-diagnosis.md`.

## Current implementation and remaining work

`earthship-ui/openhab/household-pv-system.json` retains source-bound geometry
configuration for the deployed provisional observer. The power-flow observer separates
consumption and storage alongside the unchanged original household plan.
A provisional geometry/terrain-aware PV observer was deployed from
`earthship-ui` source `522241e` on October 15 at 15:46:45Z. Its first scheduled
15:50:15Z receipt and exact deployed CLI replay match. It integrates the
retained forecast/native geometry with the 4.2 kW, approximately 165-degree,
57.4-degree array and the provisional map horizon; mountain masking preserves
diffuse sky light. Missing/unusable horizon withholds only this new PV/storage
projection. No service restart, refit or actuator change was performed.

The new private receipt separates next-24-hour array potential from a
conditional captured-energy/nominal-SoC scenario holding current AC load
constant. It explicitly assumes efficiencies, zero system DC overhead and no
charge-rate/taper limits. It is not calibrated usable energy, a learned load
forecast or proven forecasting skill.

An operational update from `earthship-ui` source `a539742` now publishes a
curated 24-hour potential/capture/nominal-SoC chart beneath the existing
Earthship content. Its normal 16:50:15Z original and exact staged replay match;
laptop/tablet layouts and fixed GET transport are verified. It retains a
separate matched SoC comparison against the original independently rederived
net-power reference and hold-SoC at 1/6/12/24 hours. The ordinary16:58:20Z opportunity produced its first one-hour comparison:98%
measured versus98.1210% scenario,96.5020% original constant-power and87%
hold-SoC. Original-document/exact-stage replay and the public matched table
are verified. This is one original from one day; general production skill is
not established and longer horizons remain collecting.
PV energy accuracy stays unavailable until potential DC, accepted generation
and the actual energy-meter scope can be compared correctly. Full PR #3,
learned load profiles, calibration and action qualification remain incomplete.
See `earthship-ui/docs/operations/2026-10-15-solar-storage-monitoring.md`.

An approved follow-on in `earthship-ui` now implements a fourteen-completed-day
hourly inverter-AC demand profile in its existing morning job. It retains strict
original AC packets, coverage and excluded days, uses the median of independent
daily clock-hour means, and preserves DST and missing observations. Historical
training targets inverter AC output; it does not retrospectively apply the
October 15 household-DC scope declaration to older measurements.

A separately versioned read-only storage scenario uses that frozen profile while
keeping the deployed constant-load PV/storage forecast and its pending outcomes
unchanged. Matched AC-energy errors compare the qualified hour ending at each
1/6/12/24-hour lead against current-load persistence. Matched SoC comparisons retain
the learned-load scenario, original constant-load PV scenario, constant battery
power and held SoC. Daily trained versions retain individual pins; rolling
as-issued algorithm comparisons explicitly count versions and origin days.
The load update is deployed from `earthship-ui` source `c71f14e` at
18:51:34 UTC on October 15. The complete thermal model remains unchanged; owned
service definitions, timers and the laptop/tablet collecting view pass readback.
No production fit or forecast was manually triggered. The first load profile
will be prepared by the normal October 16 06:50 MDT morning job; learned-load
numerics and matched skill remain collecting until that scheduled work and
subsequent outcomes mature. Each scoring opportunity retains bounded progress,
and a new unavailable forecast does not revoke older eligible outcomes. See
`earthship-ui/docs/operations/2026-10-15-hourly-ac-load-model.md`.

A later read-only shadow-plan update from `earthship-ui` source `521762d`
activated at 19:36:36 UTC. It consumes the same-issue nominal PV/storage trajectory,
using a valid learned-load scenario when present and the original constant-load
scenario otherwise. The normal 19:40:15 UTC receipt generated hypothetical
surplus-greywater and low-SoC night-load OFF candidates. All original coordination
and reserve gates remain unchanged; unknown effects keep the selected action set
empty. Exact activated CLI replay and original v1 forecast replay match. This
changes no forecast, outcome score, owner rule or actuator authority. Details are
in `earthship-ui/docs/operations/2026-10-15-trajectory-shadow-plan.md`.

A separately versioned captured-PV scorer from `earthship-ui` source
`dd16b98` activated at 2026-10-15T23:51:39.876899+00:00. It compares the
original constant-load and optional learned-load captured-DC scenarios with
qualified controller-output history at the hour ending1/6/12/24h after issue.
The actual cutover, raw packets, stream epoch, expiry and gaps remain explicit;
99% coverage is required, and every prediction/reference uses the same measured
duration. Potential array yield remains unscored. The first normal report at
2026-10-15T23:58:26.424973+00:00 compares 2.511182kWh measured controller output
with 2.846700kWh modeled capture and 2.474801kWh current-output persistence.
Exact activated CLI replay matches retained originals. One origin/day does not
establish general skill or physical calibration; actuator requests remain
disabled. See `earthship-ui/docs/operations/2026-10-15-captured-pv-outcomes.md`.

The approved captured-PV accuracy table is now deployed in Earthship monitoring
from UI source `032b12c`, at 2026-10-16T01:05:45Z. Its fixed read-only GET
`/api/household-captured-pv-performance` serves the bounded curated report;
private originals stay private. Laptop/tablet rendering is verified. Each lead
and constant/learned AC scenario keeps its own paired model/persistence MAE,
RMSE skill, coverage requirement, sample count and independent origin days.
Freshness comes from the original report clock; empty and stale states remain
explicit. This UI update changes no model, scoring, schedule, electrical setting,
permission or actuator authority. See the Earthship captured-PV outcomes document
for validation and deployment evidence.

Earthship source `46a6543` adds an approved read-only comparison of the
original greywater owner block with the same issued shadow plan. It activated
at 2026-10-16T12:46:42Z; the first natural 12:50:27Z view and exact deployed
CLI replay match. Laptop/tablet presentation is verified. An after-dark block
is retained even when no greywater proposal exists; it does not imply solar
surplus, action eligibility, policy performance or energy benefit. Original
policy hashes and expiry remain visible. This changes no PV/load forecast,
matched score, owner rule or actuator permission. Verification and remaining
qualification are in
`earthship-ui/docs/operations/2026-10-16-policy-block-comparison.md`.

The normal October 16 06:50 MDT morning job completed at 06:54:07 and
activated thermal artifact `284139ee` and hourly AC profile `31bab20b`, both
trained through local midnight. All 24 hourly bins have at least 11 supporting
days from 14 retained local days. Following one busy-preparer rollover gap,
the normal 06:58 preparer succeeded and the 07:00:15 issue published the first
conditional learned-load PV/storage scenario; its retained original matches
the learned artifact. Thermal publication recovered to provisional. Actual
laptop/tablet rendering passes. This establishes live use, not forecast skill,
calibrated capacity or prediction intervals. Native scoring deadline and
retained legacy pressure refusals remain open. No fit or forecast was manually
triggered; full household qualification and actuator release remain incomplete.

At the operator's request, scheduled legacy v1 scoring was retired in
Earthship source `a9ee9b2`, deployed at 2026-10-16T13:31:43Z. Its last forecast
was issued October 14 at04:35:15UTC, so every future 24-hour outcome window had
elapsed by October 15 at04:40:15UTC. Originals and historical reports remain for
replay. Native current scoring keeps minutes1/11; native history now uses6/16,
and independent battery/PV/load outcomes keep8/18 at second20. No additional
jobs, model changes, relaxed limits or actuator permissions were introduced.
Effective readback passes; the first automatic current slot completed in26s.
The old legacy pressure monitor was retired from scheduling, not patched.
See `earthship-ui/docs/operations/2026-10-16-native-scoring-cutover.md`.

The existing daily predictor still uses its original resource/demand formula;
its gain is capped at 1.3 and qualified automatic PV calibration remains disabled.
Do not compare the new next-24-hour potential with the existing whole-day
captured-energy prediction as if they were the same quantity and interval.

The implementation diagnosis and primary-source research are in
`earthship-ui/docs/operations/2026-10-15-pv-forecast-practice.md`; full PR #3
progress remains in `earthship-ui/docs/operations/household-program-progress.json`.
The research recommends hourly panel-plane generation followed by explicit
load/storage acceptance, with chronological comparisons to retained forecasts
and simple references. Verified curtailed output must not train potential
solar yield as if it measured all available sunlight.

Report sample counts, missingness, signed bias and MAE/RMSE at matched issue
leads and horizons; use the same scored pairs for reference skill. The
[Solar Forecast Arbiter metrics](https://forecastarbiter.epri.com/metrics/)
provide the evaluation definitions. A daily percentage-error display alone
cannot establish forecasting skill. Preserve original forecasts and measured
energy; do not replace them with a retrospective estimate or an operator guess.

This work changes no electrical protection, charge settings, actuator ownership,
telemetry schema or database permissions.

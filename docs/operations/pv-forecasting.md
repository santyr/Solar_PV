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
net-power reference and hold-SoC at 1/6/12/24 hours. The first mature scheduled
comparison is still pending at this checkpoint; no production skill is claimed.
PV energy accuracy stays unavailable until potential DC, accepted generation
and the actual energy-meter scope can be compared correctly. Full PR #3,
learned load profiles, calibration and action qualification remain incomplete.
See `earthship-ui/docs/operations/2026-10-15-solar-storage-monitoring.md`.

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

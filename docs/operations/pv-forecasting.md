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

## Current implementation and remaining work

`earthship-ui/openhab/household-pv-system.json` retains source-bound geometry
configuration for the next model. The deployed power-flow observer separates
consumption and storage alongside the unchanged original household plan.
A new geometry-aware PV forecast has **not** been deployed by this documentation
update. The daily predictor still uses its original resource/demand formula;
its gain is capped at 1.3 and qualified automatic PV calibration remains disabled.

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

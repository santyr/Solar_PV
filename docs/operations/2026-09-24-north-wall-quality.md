# North-wall daily quality: staged, not activated

The daily aggregate now has paired optional `--temperature-evidence-policy`
and `--temperature-evidence-db-config` flags. Without both, source quality is
unchanged and the north-wall row remains
`freshness_unverified`. With the flag, only the `north_wall` stream of the
shared `Weather_Temperature_Evidence_JSON` reader may qualify
`thermal.north_wall_temperature_c`. The reader requires AmbientWeather-WH31E
sensor ID 193, an elapsed local day, original persisted receipt times, a
bounded repeatable-read transaction and exact closed-window coverage. Numeric
Item rows provide row statistics only; they cannot authorize freshness.
Missing rights, history or policy identity fail the aggregate rather than
silently falling back to a held temperature.

On September 24, the existing restricted temperature reader found September
23 coverage of 85,954.173886/86,400 seconds, three gaps and a maximum gap of
373.823224 seconds. This would score `ok` under the existing 90% daily source
threshold while retaining the gap count and exact coverage in provenance; it
does **not** assert full-day temperature learning eligibility.

The staged path is not a live quality change. The scheduled service has not
been given the new flags or the shared OpenHAB script path. The
`energy_power_writer` role lacks SELECT on `public.item0646`, but no grant is
needed: the adapter now uses the existing private, read-only
`weather_temperature_reader` credential and its strict loader. Activation:

1. Run a read-only `energy-data aggregate --dry-run` for a completed day with
   both explicit paths, and compare coverage/gaps to the restricted reader.
2. Add the shared OpenHAB scripts path and both optional flags to the daily
   service, with a rollback copy of the prior unit; verify the next natural
   daily aggregate and publisher before calling the row live-qualified.

Verification before staging: 858 Solar_PV analytics tests passed; the
subsequent scheduled-flag and shared-window focus passed 52 tests. No
production aggregate, source-quality row or UI payload was rewritten.

The full September 23 `energy-data aggregate --dry-run` then succeeded using
the existing private `weather_temperature_reader` credential. Its north-wall
row reported 133 numeric Item changes for row statistics, 0.9948399755
receipt coverage, three gaps, a 373.823224-second maximum gap and quality
`ok`. No new database grant or aggregate write was made. After the restricted
credential follow-up, all 858 analytics tests passed again.

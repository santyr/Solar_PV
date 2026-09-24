# North-wall daily quality: deployed for the next natural aggregate

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

The source-only stage was not a live quality change. The
`energy_power_writer` role lacks SELECT on `public.item0646`, but no grant is
needed: the adapter now uses the existing private, read-only
`weather_temperature_reader` credential and its strict loader. Activation
was completed without a database grant or control restart:

1. Run a read-only `energy-data aggregate --dry-run` for a completed day with
   both explicit paths, and compare coverage/gaps to the restricted reader.
2. Add the shared OpenHAB scripts path and both optional flags to the daily
   service. The new repo-managed drop-in is a reversible unit-level change;
   the prior base and qualified-power units remain untouched. Verify the next
   natural daily aggregate and publisher before calling the row live-qualified.

Verification before staging: 858 Solar_PV analytics tests passed; the
subsequent scheduled-flag and shared-window focus passed 52 tests. No
production aggregate, source-quality row or UI payload was rewritten.

The full September 23 `energy-data aggregate --dry-run` then succeeded using
the existing private `weather_temperature_reader` credential. Its north-wall
row reported 133 numeric Item changes for row statistics, 0.9948399755
receipt coverage, three gaps, a 373.823224-second maximum gap and quality
`ok`. No new database grant or aggregate write was made. After the restricted
credential follow-up, all 858 analytics tests passed again.

The drop-in was installed and `systemctl --user daemon-reload` readback
confirmed both flags, the shared module path, an idle service and matching
source/installed SHA-256
`79783e6f031372a31cf1e947153bae68ca7fc347852b9feb7a093add06b58b48`.
The timer's next natural fire is September 25 00:21 MDT. No aggregate or UI
publisher was run early, so production still reflects the previous snapshot
until that natural writer and subsequent publisher succeed. Rollback removes
only the new `qualified-temperature.conf` drop-in, reloads the user manager,
and verifies the original qualified-power ExecStart is restored.

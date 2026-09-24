# North-wall daily quality: staged, not activated

The daily aggregate now has an optional `--temperature-evidence-policy` flag.
Without it, source quality is unchanged and the north-wall row remains
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
been given the new flag or the shared OpenHAB script path. The
`energy_power_writer` role currently lacks SELECT on `public.item0646`;
authorization for that exact read-only grant is pending. After approval:

1. Grant only SELECT on `public.item0646` and read back the privilege.
2. Run a read-only `energy-data aggregate --dry-run` for a completed day with
   the explicit policy, and compare coverage/gaps to the restricted reader.
3. Add the shared OpenHAB scripts path and optional policy flag to the daily
   service, with a rollback copy of the prior unit; verify the next natural
   daily aggregate and publisher before calling the row live-qualified.

Verification before staging: 858 Solar_PV analytics tests passed; the
subsequent scheduled-flag and shared-window focus passed 52 tests. No
production aggregate, source-quality row or UI payload was rewritten.

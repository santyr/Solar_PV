# Astro daily source-quality correction

The `Sun_Rise_End` and `Sun_Set_Start` Items are deterministic Astro schedules,
not sensor heartbeats. Their persisted DateTime values identify the event's
Denver local day. The previous daily quality path labeled both
`freshness_unverified` because neither had a separate companion Item, despite
the source contract already specifying `local_date_must_match`.

The source contract now names each Item as its own freshness basis. The pure
quality evaluator authorizes only intervals after an original persisted row
whose schedule value parses as an aware DateTime for the requested Denver day;
a carry older than 30 hours, wrong-day value, missing row or the interval
before the first same-day row remains uncovered. Configuration validation
restricts this policy to a derived datetime Item using itself as evidence.
It does not assert that unrelated Zigbee, RF or TP-Link sensors are fresh.

The full analytics suite passed 855 tests, including wrong-day/stale-carry and
25-hour Denver DST-day cases. A restricted, read-only September 23 dry-run
using production persistence measured sunrise coverage 0.99999047 and sunset
coverage 0.99999044, each leaving the first roughly 0.8 seconds of the day
uncovered. Of 21 source-quality rows, 15 would be `ok` and the other six
optional room, north-wall and switch sources remain `freshness_unverified`.
No daily snapshot revision or UI payload was written by this verification.

The scheduled daily aggregate service imports this source tree directly.
The next natural completed-day aggregate must confirm the two Astro rows in
its append-only qualified snapshot and the subsequent UI publication. Do not
retroactively rewrite older quality rows solely to change a health badge.

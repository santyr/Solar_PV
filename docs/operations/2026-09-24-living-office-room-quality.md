# Living Office daily source quality: code ready, natural writer pending

The three optional Living Office Zigbee signals (illuminance, occupancy and
temperature) previously reported `freshness_unverified` because their Item
histories are change-only. The daily reader now uses original persisted
`LivingOffice_Shade_Temperature` update times as a same-device sample clock.
Each valid Fahrenheit sample authorizes at most 30 minutes, intersected with
an existing, valid primary Item state. A missing primary state, invalid
value, absent sample, expired sample or pre-first-observation interval remains
uncovered. This is a bounded source-quality estimate, not proof that the
sensor hardware was independently alive at every instant.

The policy is restricted at configuration load and evaluation to the exact
three Living Office Item identities, the temperature freshness Item and the
1,800-second TTL. Other optional switch sensors remain unverified until they
have their own evidence contract.

Before publication, all 862 analytics tests passed. A read-only September 23
aggregate dry-run using the deployed qualified-power and north-wall evidence
flags scored each room row `ok` with 85,815.805885/86,400 seconds of bounded
coverage (99.3238494%). The illuminance, occupancy and room-temperature
row counts were 302, 128 and 178 respectively. No completed-day snapshot or
UI payload was rewritten by the dry-run.

The source tree is loaded by the installed daily aggregate service. The next
natural aggregate is scheduled for September 25 at 00:21 MDT. Verify the
new append-only snapshot and subsequent publisher before describing these
rows as live-qualified. If that gate fails, revert this code/config change;
do not backfill historical quality badges from the dry-run alone.

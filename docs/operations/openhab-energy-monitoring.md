# OpenHAB Energy Monitoring

OpenHAB 5.2.1 is the live integration and deterministic automation layer as of
the 2026-08-20 audit.

Current battery authority includes `BMS_SOC`, `BMS_Comms_Status`,
`DCData_Voltage`, and `DCData_Current`. Schneider and MPPT Things were
online at the audit snapshot. PostgreSQL persistence maps Item names through
`public.items` to per-Item history tables.

Before changing an Item, rule, REST path, persistence policy, or UI proxy:

1. read [cross-repository contracts](../architecture/cross-repo-contracts.md);
2. export/backup the affected OpenHAB configuration and JSONDB;
3. compare deployed rule content with version-controlled source;
4. inventory all consumers;
5. validate read-only before any separately authorized write;
6. test owner-rule results, stale/error behavior, and rollback.

The deployed UI tooling currently has an exact OpenHAB 5.2.0 guard while the
runtime is 5.2.1. Resolve and test that guard before managed deployments.


## Stable UI analytics publication

`Solar_PV` is the quantitative owner of `earthship-energy-ui/v1`. Every five
minutes it reads only bounded, quality-approved `energy_analytics` products,
closes the database connection, validates and encodes a payload below 16 KiB,
and writes exactly `PUT /rest/items/Energy_Analytics_JSON/state`. It does not
modify Item configuration, rules, Things, links, persistence, or actuators.

Provision the String Item only with the receipt-bound tool in earthship-ui and
retain its private snapshot/readback. Verify the publisher through the UI proxy
and treat missing, malformed, stale (over 15 minutes), or future-dated evidence
as unavailable. Rollback begins by disabling `energy-ui-publish.timer`; Item
configuration rollback uses only the exact closed deployment receipt.

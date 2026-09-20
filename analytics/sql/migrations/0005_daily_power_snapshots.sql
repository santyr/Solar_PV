-- Qualified accounting is a separate, append-only revision series. No legacy
-- daily rows or cumulative counters are rewritten by this migration.
CREATE TABLE energy_analytics.daily_power_snapshots (
    snapshot_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    local_date date NOT NULL,
    epoch_id text NOT NULL REFERENCES energy_analytics.system_epochs(epoch_id),
    policy text NOT NULL CHECK (policy = 'qualified_power_evidence_v1'),
    cutover_at timestamptz NOT NULL,
    payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    payload jsonb NOT NULL,
    computed_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (epoch_id, local_date, policy, cutover_at, payload_sha256),
    CHECK (jsonb_typeof(payload) = 'object' AND octet_length(payload::text) <= 65536),
    CHECK ((payload->>'local_date' = local_date::text) IS TRUE),
    CHECK ((payload->>'status' = 'ok') IS TRUE),
    CHECK ((payload->>'mode' = 'read_only_dry_run') IS TRUE),
    CHECK ((payload->'power_accounting'->>'policy' = policy) IS TRUE),
    CHECK ((payload->'power_accounting'->'version' = '1'::jsonb) IS TRUE),
    CHECK (((payload->'power_accounting'->>'cutover')::timestamptz = cutover_at) IS TRUE),
    CHECK (((payload->>'window_end')::timestamptz > cutover_at) IS TRUE),
    CHECK ((jsonb_typeof(payload->'battery'->'daily_efc') = 'number'
            AND (payload->'battery'->>'daily_efc')::numeric >= 0) IS TRUE)
);

CREATE INDEX daily_power_snapshots_latest_idx ON energy_analytics.daily_power_snapshots
    (epoch_id, policy, cutover_at, local_date, snapshot_id DESC);

CREATE FUNCTION energy_analytics.reject_daily_power_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'daily power snapshots are append-only';
END;
$$;

CREATE TRIGGER daily_power_snapshots_append_only
    BEFORE UPDATE OR DELETE OR TRUNCATE ON energy_analytics.daily_power_snapshots
    FOR EACH STATEMENT EXECUTE FUNCTION energy_analytics.reject_daily_power_mutation();

REVOKE ALL ON energy_analytics.daily_power_snapshots FROM PUBLIC;

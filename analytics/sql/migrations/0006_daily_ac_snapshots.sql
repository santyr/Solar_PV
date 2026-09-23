-- AC output is independent of the bank-epoch power series. These immutable
-- observations never create a DC-to-AC surplus or a full-day extrapolation.
CREATE TABLE energy_analytics.daily_ac_snapshots (
    snapshot_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    local_date date NOT NULL,
    policy text NOT NULL CHECK (policy = 'qualified_inverter_ac_output_v1'),
    cutover_at timestamptz NOT NULL,
    topology_from timestamptz NOT NULL,
    payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    payload jsonb NOT NULL,
    computed_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (local_date, policy, cutover_at, topology_from, payload_sha256),
    CHECK (topology_from >= cutover_at),
    CHECK (jsonb_typeof(payload) = 'object' AND octet_length(payload::text) <= 65536),
    CHECK ((payload->>'local_date' = local_date::text) IS TRUE),
    CHECK (((payload->>'ac_cutover')::timestamptz = cutover_at) IS TRUE),
    CHECK (((payload->>'topology_from')::timestamptz = topology_from) IS TRUE),
    CHECK ((payload->>'ac_item' = 'Inverter_AC_Evidence_JSON') IS TRUE),
    CHECK ((payload->>'basis' = 'inverter_output_observed_with_attested_topology') IS TRUE),
    CHECK ((payload->'balance_kwh' = 'null'::jsonb) IS TRUE),
    CHECK (((payload->>'ac_coverage')::numeric BETWEEN 0 AND 1) IS TRUE),
    CHECK (((payload->>'common_coverage')::numeric BETWEEN 0 AND 1) IS TRUE)
);

CREATE INDEX daily_ac_snapshots_latest_idx ON energy_analytics.daily_ac_snapshots
    (policy, cutover_at, topology_from, local_date, snapshot_id DESC);

CREATE FUNCTION energy_analytics.validate_daily_ac_completion() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.computed_at := clock_timestamp();
    IF (NEW.payload->>'window_start')::timestamptz IS DISTINCT FROM
           (NEW.local_date::timestamp AT TIME ZONE 'America/Denver')
       OR (NEW.payload->>'window_end')::timestamptz IS DISTINCT FROM
           ((NEW.local_date + 1)::timestamp AT TIME ZONE 'America/Denver') THEN
        RAISE EXCEPTION 'AC window must match the complete site-local day';
    END IF;
    IF (NEW.payload->>'window_end')::timestamptz > NEW.computed_at THEN
        RAISE EXCEPTION 'cannot persist an unfinished AC day';
    END IF;
    IF NEW.cutover_at > (NEW.payload->>'window_start')::timestamptz
       OR NEW.topology_from > (NEW.payload->>'window_start')::timestamptz
       OR (NEW.payload->>'topology_until') IS NOT NULL AND
          (NEW.payload->>'topology_until')::timestamptz <
          (NEW.payload->>'window_end')::timestamptz THEN
        RAISE EXCEPTION 'AC day outside evidence or topology period';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER daily_ac_snapshots_completed_day
    BEFORE INSERT ON energy_analytics.daily_ac_snapshots
    FOR EACH ROW EXECUTE FUNCTION energy_analytics.validate_daily_ac_completion();

CREATE FUNCTION energy_analytics.reject_daily_ac_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'daily AC snapshots are append-only';
END;
$$;

CREATE TRIGGER daily_ac_snapshots_append_only
    BEFORE UPDATE OR DELETE OR TRUNCATE ON energy_analytics.daily_ac_snapshots
    FOR EACH STATEMENT EXECUTE FUNCTION energy_analytics.reject_daily_ac_mutation();

REVOKE ALL ON energy_analytics.daily_ac_snapshots FROM PUBLIC;

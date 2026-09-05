CREATE TABLE energy_analytics.advisory_decisions (
    decision_id uuid PRIMARY KEY,
    issued_at timestamptz NOT NULL,
    bank_epoch text NOT NULL REFERENCES energy_analytics.system_epochs(epoch_id),
    payload jsonb NOT NULL,
    UNIQUE (decision_id, issued_at),
    CHECK (jsonb_typeof(payload) = 'object'),
    CHECK (octet_length(payload::text) <= 16384),
    CHECK (((payload->>'decision_id')::uuid = decision_id) IS TRUE),
    CHECK (((payload->>'issued_at')::timestamptz = issued_at) IS TRUE),
    CHECK ((payload->>'bank_epoch' = bank_epoch) IS TRUE)
);

CREATE TABLE energy_analytics.advisory_results (
    result_id uuid PRIMARY KEY,
    decision_id uuid NOT NULL,
    parent_issued_at timestamptz NOT NULL,
    observed_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    FOREIGN KEY (decision_id, parent_issued_at)
        REFERENCES energy_analytics.advisory_decisions(decision_id, issued_at),
    CHECK (observed_at >= parent_issued_at),
    CHECK (jsonb_typeof(payload) = 'object'),
    CHECK (octet_length(payload::text) <= 16384),
    CHECK (((payload->>'result_id')::uuid = result_id) IS TRUE),
    CHECK (((payload->>'decision_id')::uuid = decision_id) IS TRUE),
    CHECK (((payload->>'observed_at')::timestamptz = observed_at) IS TRUE)
);

CREATE INDEX advisory_results_decision_idx
    ON energy_analytics.advisory_results(decision_id, observed_at);

CREATE FUNCTION energy_analytics.reject_advisory_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'advisory evidence is append only' USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER advisory_decisions_append_only
    BEFORE UPDATE OR DELETE OR TRUNCATE ON energy_analytics.advisory_decisions
    FOR EACH STATEMENT EXECUTE FUNCTION energy_analytics.reject_advisory_mutation();
CREATE TRIGGER advisory_results_append_only
    BEFORE UPDATE OR DELETE OR TRUNCATE ON energy_analytics.advisory_results
    FOR EACH STATEMENT EXECUTE FUNCTION energy_analytics.reject_advisory_mutation();

REVOKE ALL ON energy_analytics.advisory_decisions,
              energy_analytics.advisory_results FROM PUBLIC;

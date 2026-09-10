CREATE TABLE energy_analytics.advisory_trough_outcomes (
    decision_id uuid NOT NULL REFERENCES energy_analytics.advisory_decisions(decision_id),
    assessment_version text NOT NULL CHECK (assessment_version = 'atomic-soc-trough-v1'),
    evidence_digest text NOT NULL CHECK (evidence_digest ~ '^[0-9a-f]{64}$'),
    assessed_at timestamptz NOT NULL,
    target_start timestamptz NOT NULL,
    target_end timestamptz NOT NULL,
    status text NOT NULL CHECK (status IN ('measured', 'insufficient_data')),
    payload jsonb NOT NULL,
    PRIMARY KEY (decision_id, assessment_version, evidence_digest),
    CHECK (target_end > target_start AND assessed_at >= target_end),
    CHECK (jsonb_typeof(payload) = 'object' AND octet_length(payload::text) <= 16384),
    CHECK (((payload->>'decision_id')::uuid = decision_id) IS TRUE),
    CHECK ((payload->'measurement'->>'assessment_version' = assessment_version) IS TRUE),
    CHECK ((payload->'measurement'->>'evidence_digest' = evidence_digest) IS TRUE),
    CHECK (((payload->'measurement'->>'assessed_at')::timestamptz = assessed_at) IS TRUE),
    CHECK (((payload->'measurement'->>'window_start')::timestamptz = target_start) IS TRUE),
    CHECK (((payload->'measurement'->>'window_end')::timestamptz = target_end) IS TRUE),
    CHECK ((payload->'measurement'->>'status' = status) IS TRUE),
    CHECK ((payload->'bandit_eligible' = 'false'::jsonb) IS TRUE)
);

CREATE INDEX advisory_trough_outcomes_current_idx
    ON energy_analytics.advisory_trough_outcomes
       (decision_id, assessment_version, assessed_at DESC, evidence_digest DESC);

CREATE TRIGGER advisory_trough_outcomes_append_only
    BEFORE UPDATE OR DELETE OR TRUNCATE ON energy_analytics.advisory_trough_outcomes
    FOR EACH STATEMENT EXECUTE FUNCTION energy_analytics.reject_advisory_mutation();

REVOKE ALL ON energy_analytics.advisory_trough_outcomes FROM PUBLIC;

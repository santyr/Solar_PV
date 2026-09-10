CREATE UNIQUE INDEX advisory_results_parent_identity_idx
    ON energy_analytics.advisory_results(result_id, decision_id);

CREATE INDEX advisory_decisions_trough_candidates_idx
    ON energy_analytics.advisory_decisions(bank_epoch, (payload->>'prediction_day'), issued_at);

CREATE TABLE energy_analytics.advisory_trough_selection (
    bank_epoch text NOT NULL REFERENCES energy_analytics.system_epochs(epoch_id),
    prediction_day date NOT NULL,
    selection_version text NOT NULL CHECK (selection_version = 'completed-night-v1'),
    decision_id uuid NOT NULL,
    publication_result_id uuid NOT NULL,
    cutover_at timestamptz NOT NULL,
    selected_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (bank_epoch, prediction_day, selection_version),
    FOREIGN KEY (publication_result_id, decision_id)
        REFERENCES energy_analytics.advisory_results(result_id, decision_id),
    CHECK (selected_at >= cutover_at),
    CHECK (jsonb_typeof(payload) = 'object' AND octet_length(payload::text) <= 4096),
    CHECK ((payload->>'bank_epoch' = bank_epoch) IS TRUE),
    CHECK (((payload->>'prediction_day')::date = prediction_day) IS TRUE),
    CHECK ((payload->>'selection_version' = selection_version) IS TRUE),
    CHECK (((payload->>'decision_id')::uuid = decision_id) IS TRUE),
    CHECK (((payload->>'publication_result_id')::uuid = publication_result_id) IS TRUE),
    CHECK (((payload->>'cutover_at')::timestamptz = cutover_at) IS TRUE),
    CHECK ((payload->>'status' = 'selected') IS TRUE)
);

CREATE TRIGGER advisory_trough_selection_append_only
    BEFORE UPDATE OR DELETE OR TRUNCATE ON energy_analytics.advisory_trough_selection
    FOR EACH STATEMENT EXECUTE FUNCTION energy_analytics.reject_advisory_mutation();

REVOKE ALL ON energy_analytics.advisory_trough_selection FROM PUBLIC;

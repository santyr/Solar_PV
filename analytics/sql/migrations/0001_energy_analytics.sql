CREATE SCHEMA IF NOT EXISTS energy_analytics;

CREATE TABLE energy_analytics.schema_migrations (
    version integer PRIMARY KEY,
    name text NOT NULL,
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE energy_analytics.metric_sources (
    canonical_name text PRIMARY KEY,
    item_name text NOT NULL UNIQUE,
    source_config jsonb NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE energy_analytics.system_epochs (
    epoch_id text PRIMARY KEY,
    start_local_date date,
    end_local_date_exclusive date,
    current_analytics boolean NOT NULL,
    nominal_capacity_ah double precision,
    nominal_usable_kwh double precision,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    CHECK (end_local_date_exclusive IS NULL OR start_local_date IS NULL
           OR end_local_date_exclusive > start_local_date)
);

CREATE TABLE energy_analytics.snow_events (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at timestamptz NOT NULL,
    state text NOT NULL CHECK (state IN ('snow_covered', 'snow_cleared')),
    method text NOT NULL,
    confidence double precision NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    note text,
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (occurred_at, state, method)
);

CREATE TABLE energy_analytics.system_events (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_kind text NOT NULL,
    state text NOT NULL,
    started_at timestamptz NOT NULL,
    ended_at timestamptz,
    method text NOT NULL,
    method_version text NOT NULL,
    confidence double precision NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    operator_confirmed boolean NOT NULL DEFAULT false,
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    CHECK (ended_at IS NULL OR ended_at >= started_at),
    UNIQUE (event_kind, started_at, method, method_version)
);

CREATE TABLE energy_analytics.forecast_snapshots (
    snapshot_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source text NOT NULL,
    issued_at timestamptz NOT NULL,
    valid_for timestamptz NOT NULL,
    metric text NOT NULL,
    value double precision,
    unit text,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    captured_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source, issued_at, valid_for, metric)
);

CREATE TABLE energy_analytics.lynk_import_batches (
    batch_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sha256 text NOT NULL UNIQUE CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    source_name text NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT now(),
    row_count integer NOT NULL CHECK (row_count >= 0),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE energy_analytics.battery_module_samples (
    batch_id bigint NOT NULL REFERENCES energy_analytics.lynk_import_batches(batch_id),
    module_id text NOT NULL,
    sampled_at timestamptz NOT NULL,
    soc_pct double precision,
    voltage_v double precision,
    current_a double precision,
    temperature_c double precision,
    cell_spread_mv double precision,
    charge_kwh double precision,
    discharge_kwh double precision,
    faults jsonb NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (batch_id, module_id, sampled_at)
);

CREATE TABLE energy_analytics.daily_battery (
    local_date date NOT NULL,
    epoch_id text NOT NULL REFERENCES energy_analytics.system_epochs(epoch_id),
    min_soc_pct double precision,
    max_soc_pct double precision,
    mean_soc_pct double precision,
    sunrise_soc_pct double precision,
    sunset_soc_pct double precision,
    overnight_soc_drop_pct double precision,
    depth_of_discharge_pct double precision,
    hours_above_90 double precision,
    hours_above_95 double precision,
    hours_below_50 double precision,
    hours_below_25 double precision,
    charge_kwh double precision,
    discharge_kwh double precision,
    net_kwh double precision,
    daily_efc double precision,
    cumulative_efc double precision,
    min_temperature_c double precision,
    max_temperature_c double precision,
    mean_temperature_c double precision,
    reached_95 boolean,
    reached_99 boolean,
    reached_100 boolean,
    first_reached_99_at timestamptz,
    days_since_99 integer,
    consecutive_days_without_99 integer,
    coverage double precision NOT NULL CHECK (coverage BETWEEN 0 AND 1),
    quality text NOT NULL,
    computed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (local_date, epoch_id)
);

CREATE TABLE energy_analytics.daily_pv (
    local_date date NOT NULL,
    epoch_id text NOT NULL REFERENCES energy_analytics.system_epochs(epoch_id),
    pv_kwh double precision,
    peak_w double precision,
    productive_hours double precision,
    first_productive_at timestamptz,
    last_productive_at timestamptz,
    before_solar_noon_kwh double precision,
    after_solar_noon_kwh double precision,
    mppt_output_kwh double precision,
    mppt_efficiency double precision,
    coverage double precision NOT NULL CHECK (coverage BETWEEN 0 AND 1),
    quality text NOT NULL,
    computed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (local_date, epoch_id)
);

CREATE TABLE energy_analytics.daily_load (
    local_date date NOT NULL,
    epoch_id text NOT NULL REFERENCES energy_analytics.system_epochs(epoch_id),
    load_kwh double precision,
    peak_w double precision,
    pv_load_ratio double precision,
    surplus_deficit_kwh double precision,
    active_loads jsonb NOT NULL DEFAULT '{}'::jsonb,
    coverage double precision NOT NULL CHECK (coverage BETWEEN 0 AND 1),
    quality text NOT NULL,
    computed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (local_date, epoch_id)
);

CREATE TABLE energy_analytics.daily_weather (
    local_date date NOT NULL,
    epoch_id text NOT NULL REFERENCES energy_analytics.system_epochs(epoch_id),
    min_temperature_c double precision,
    max_temperature_c double precision,
    mean_temperature_c double precision,
    irradiance_wh_m2 double precision,
    peak_irradiance_w_m2 double precision,
    precipitation_mm double precision,
    snow_state text,
    coverage double precision NOT NULL CHECK (coverage BETWEEN 0 AND 1),
    quality text NOT NULL,
    computed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (local_date, epoch_id)
);

CREATE TABLE energy_analytics.daily_source_quality (
    local_date date NOT NULL,
    canonical_name text NOT NULL,
    row_count bigint NOT NULL CHECK (row_count >= 0),
    first_at timestamptz,
    last_at timestamptz,
    coverage double precision NOT NULL CHECK (coverage BETWEEN 0 AND 1),
    stale_intervals integer NOT NULL DEFAULT 0 CHECK (stale_intervals >= 0),
    quality text NOT NULL,
    detail jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (local_date, canonical_name)
);

CREATE TABLE energy_analytics.analysis_runs (
    run_id uuid PRIMARY KEY,
    analysis_kind text NOT NULL,
    window_start timestamptz,
    window_end timestamptz,
    code_version text NOT NULL,
    schema_version integer NOT NULL,
    status text NOT NULL,
    summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at timestamptz NOT NULL,
    completed_at timestamptz,
    CHECK (window_end IS NULL OR window_start IS NULL OR window_end >= window_start),
    CHECK (completed_at IS NULL OR completed_at >= started_at)
);

CREATE INDEX forecast_snapshots_valid_for_idx
    ON energy_analytics.forecast_snapshots (valid_for, issued_at);
CREATE INDEX system_events_kind_started_idx
    ON energy_analytics.system_events (event_kind, started_at);
CREATE INDEX battery_module_samples_at_idx
    ON energy_analytics.battery_module_samples (sampled_at);

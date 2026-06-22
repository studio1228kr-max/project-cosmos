BEGIN;

CREATE TABLE IF NOT EXISTS raw_macro_data (
    id                      BIGSERIAL PRIMARY KEY,
    source                  TEXT NOT NULL,
    stat_code               TEXT NOT NULL,
    data_frequency          TEXT,
    period                  TEXT NOT NULL,
    raw_payload             JSONB NOT NULL,
    payload_hash            TEXT NOT NULL UNIQUE,
    fetched_at              TIMESTAMPTZ NOT NULL,
    is_normalized           BOOLEAN NOT NULL DEFAULT FALSE,
    normalized_at           TIMESTAMPTZ,
    normalize_error         TEXT,
    normalization_status    TEXT NOT NULL DEFAULT 'PENDING',
    normalization_run_id    TEXT,
    normalization_started_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_raw_macro_data_source_stat
    ON raw_macro_data (source, stat_code, period);

CREATE INDEX IF NOT EXISTS idx_raw_macro_data_pending
    ON raw_macro_data (source, is_normalized, normalization_status, fetched_at)
    WHERE is_normalized = FALSE;

CREATE TABLE IF NOT EXISTS normalized_macro_series (
    id                BIGSERIAL PRIMARY KEY,
    source            TEXT NOT NULL,
    stat_code         TEXT NOT NULL,
    metric_name       TEXT NOT NULL,
    period_raw        TEXT,
    as_of_date        DATE NOT NULL,
    value             DOUBLE PRECISION NOT NULL,
    delta_mom         DOUBLE PRECISION,
    nlp_insight       TEXT,
    unit              TEXT,
    data_frequency    TEXT,
    confidence_score  DOUBLE PRECISION,
    last_seen_at      TIMESTAMPTZ,
    updated_at        TIMESTAMPTZ,
    UNIQUE (source, metric_name, as_of_date)
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id                BIGSERIAL PRIMARY KEY,
    source            TEXT NOT NULL,
    pipeline_stage    TEXT NOT NULL DEFAULT 'INGEST',
    run_at            TIMESTAMPTZ NOT NULL,
    status            TEXT NOT NULL,
    records_fetched   INTEGER NOT NULL DEFAULT 0,
    records_inserted  INTEGER NOT NULL DEFAULT 0,
    records_processed INTEGER NOT NULL DEFAULT 0,
    records_failed    INTEGER NOT NULL DEFAULT 0,
    error_message     TEXT
);

COMMIT;

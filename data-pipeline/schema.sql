-- ============================================================
-- COSMOS Data Pipeline — Signal Contract Schema v1.0
-- 같은 Railway Postgres(DATABASE_URL) 내. 100% 추가형, 재실행 안전.
-- ============================================================
BEGIN;

CREATE TABLE IF NOT EXISTS raw_source_events (
  id              SERIAL PRIMARY KEY,
  source          TEXT NOT NULL,
  source_ref_id   TEXT,
  source_url      TEXT,
  observed_at     TIMESTAMPTZ,
  ingested_at     TIMESTAMPTZ DEFAULT NOW(),
  entity_name     TEXT,
  entity_id       TEXT,
  entity_type     TEXT,
  raw_content     TEXT,
  dedupe_key      TEXT UNIQUE,
  scanner_version TEXT,
  processed       BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_rse_source ON raw_source_events(source);
CREATE INDEX IF NOT EXISTS idx_rse_entity ON raw_source_events(entity_name);

CREATE TABLE IF NOT EXISTS normalized_signals (
  id                 SERIAL PRIMARY KEY,
  raw_event_id       INTEGER REFERENCES raw_source_events(id),
  source             TEXT NOT NULL,
  entity_name        TEXT,
  entity_id          TEXT,
  signal_type        TEXT NOT NULL,
  signal_subtype     TEXT,
  normalized_summary TEXT,
  severity           TEXT CHECK (severity IN ('INFO','WATCH','REVIEW','CRITICAL','FATAL')),
  confidence         NUMERIC(3,2),
  evidence_quality   TEXT CHECK (evidence_quality IN ('PUBLIC','OFFICIAL','VENDOR','MANUAL','UNVERIFIED')),
  observed_at        TIMESTAMPTZ,
  created_at         TIMESTAMPTZ DEFAULT NOW(),
  redis_published    BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_ns_entity ON normalized_signals(entity_name);
CREATE INDEX IF NOT EXISTS idx_ns_type ON normalized_signals(signal_type);

CREATE TABLE IF NOT EXISTS scored_signals (
  id                          SERIAL PRIMARY KEY,
  normalized_signal_id        INTEGER REFERENCES normalized_signals(id),
  entity_name                 TEXT,
  entity_id                   TEXT,
  score_credit_deterioration  INTEGER DEFAULT 0,
  score_refinancing_pressure  INTEGER DEFAULT 0,
  score_collateral_coverage   INTEGER DEFAULT 0,
  score_enforcement_pathway   INTEGER DEFAULT 0,
  score_sector_cycle          INTEGER DEFAULT 0,
  aggregate_score             INTEGER DEFAULT 0,
  suggested_deal_type         TEXT,
  urgency                     TEXT CHECK (urgency IN ('CRITICAL_72H','WATCH_2W','MONITOR')),
  reason_codes                JSONB DEFAULT '[]',
  thesis_suggestion           TEXT,
  scoring_version             TEXT,
  scored_at                   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ss_entity ON scored_signals(entity_name);
-- 멱등 스코어링: 동일 normalized 신호 중복 채점 방지 (Redis 재전달/재시작 안전)
CREATE UNIQUE INDEX IF NOT EXISTS uq_scored_norm ON scored_signals(normalized_signal_id);

CREATE TABLE IF NOT EXISTS signal_model_results (
  id                SERIAL PRIMARY KEY,
  scored_signal_id  INTEGER REFERENCES scored_signals(id),
  model_name        TEXT NOT NULL,
  score             INTEGER,
  input_events      JSONB,
  feature_values    JSONB,
  explanation_text  TEXT,
  reason_codes      JSONB,
  generated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_smr_scored ON signal_model_results(scored_signal_id);

CREATE TABLE IF NOT EXISTS signal_dedupe_map (
  dedupe_key       TEXT PRIMARY KEY,
  first_seen_at    TIMESTAMPTZ DEFAULT NOW(),
  last_seen_at     TIMESTAMPTZ DEFAULT NOW(),
  occurrence_count INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS morning_brief_runs (
  id          SERIAL PRIMARY KEY,
  run_date    DATE NOT NULL,
  top_signals JSONB,
  stats       JSONB,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- guardrail 거부 사유 (spec §5)
CREATE TABLE IF NOT EXISTS guardrail_rejections (
  id           SERIAL PRIMARY KEY,
  dedupe_key   TEXT,
  entity_name  TEXT,
  reason       TEXT NOT NULL,
  scanner      TEXT,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

COMMIT;

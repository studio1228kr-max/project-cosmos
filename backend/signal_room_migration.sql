-- ============================================================
-- COSMOS Signal Room — project-cosmos(운용계) DB 테이블
-- data-pipeline scored_signals → 이 테이블로 ingest
-- ============================================================
BEGIN;

CREATE TABLE IF NOT EXISTS signal_room (
  id                  SERIAL PRIMARY KEY,
  external_signal_id  INTEGER,
  entity_name         TEXT,
  entity_id           TEXT,
  signal_type         TEXT,
  aggregate_score     INTEGER,
  suggested_deal_type TEXT,
  urgency             TEXT,
  thesis_suggestion   TEXT,
  reason_summary      TEXT,
  status              TEXT DEFAULT 'NEW' CHECK (status IN ('NEW','WATCHING','CONVERTED','DISMISSED')),
  deal_id             INTEGER REFERENCES deal_master(id),
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sr_status ON signal_room(status);
CREATE INDEX IF NOT EXISTS idx_sr_urgency ON signal_room(urgency);
-- 동일 외부 신호 중복 ingest 방지 (ON CONFLICT 용)
CREATE UNIQUE INDEX IF NOT EXISTS uq_sr_external ON signal_room(external_signal_id);

COMMIT;

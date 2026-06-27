-- ============================================================
-- COSMOS Morning Brief — project-cosmos(운용계) DB 테이블
-- data-pipeline(HERMES) morning_brief → /api/brief/today 로 ingest
-- run_date 당 1행 upsert (당일 재실행 시 갱신)
-- ============================================================
BEGIN;

CREATE TABLE IF NOT EXISTS morning_brief (
  id              SERIAL PRIMARY KEY,
  run_date        DATE NOT NULL UNIQUE,
  brief_text      TEXT,
  cards           JSONB DEFAULT '[]',
  stats           JSONB DEFAULT '{}',
  critical_count  INTEGER DEFAULT 0,
  watch_count     INTEGER DEFAULT 0,
  monitor_count   INTEGER DEFAULT 0,
  model           TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mb_run_date ON morning_brief(run_date DESC);

COMMIT;

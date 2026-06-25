-- ============================================================
-- COSMOS Kill Check v1.0 — deal_master 확장 + kill check 로그
-- 100% 추가형. 재실행 안전.
-- ============================================================
BEGIN;

ALTER TABLE deal_master
  ADD COLUMN IF NOT EXISTS kill_check_status TEXT DEFAULT 'PENDING',
  ADD COLUMN IF NOT EXISTS kill_check_at     TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS kill_check_drops  JSONB DEFAULT '[]';

DO $$ BEGIN
  ALTER TABLE deal_master ADD CONSTRAINT deal_master_kill_check_status_check
    CHECK (kill_check_status IN ('PENDING','PASS','DROP'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS deal_kill_check_log (
  id            SERIAL PRIMARY KEY,
  deal_id       INTEGER NOT NULL REFERENCES deal_master(id) ON DELETE CASCADE,
  result        TEXT NOT NULL CHECK (result IN ('PASS','DROP')),
  drop_reasons  JSONB DEFAULT '[]',
  checked_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dkcl_deal ON deal_kill_check_log(deal_id);

COMMIT;

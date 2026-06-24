-- ============================================================
-- COSMOS Deal Intake v1.0 — deal_master 확장 + 소싱/킬 테이블
-- 100% 추가형. 재실행 안전.
-- ============================================================
BEGIN;

-- 1-1) deal_master 컬럼 추가
ALTER TABLE deal_master
  ADD COLUMN IF NOT EXISTS sourcing_channel    TEXT,
  ADD COLUMN IF NOT EXISTS thesis              TEXT,
  ADD COLUMN IF NOT EXISTS target_irr          TEXT,
  ADD COLUMN IF NOT EXISTS counterparty_motive TEXT,
  ADD COLUMN IF NOT EXISTS info_edge           TEXT,
  ADD COLUMN IF NOT EXISTS counterparty_tier   TEXT,
  ADD COLUMN IF NOT EXISTS sector              TEXT,
  ADD COLUMN IF NOT EXISTS complexity          TEXT,
  ADD COLUMN IF NOT EXISTS ic_memo             TEXT,
  ADD COLUMN IF NOT EXISTS registered_at       TIMESTAMPTZ DEFAULT NOW();

-- CHECK 제약은 ADD COLUMN ... CHECK 이 IF NOT EXISTS 재실행 시 중복 추가되므로 분리(존재 시 skip)
DO $$ BEGIN
  ALTER TABLE deal_master ADD CONSTRAINT deal_master_counterparty_tier_check
    CHECK (counterparty_tier IN ('T1','T2','T3'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE deal_master ADD CONSTRAINT deal_master_complexity_check
    CHECK (complexity IN ('단순','중간','복잡'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 1-2) deal_sourcing_detail
CREATE TABLE IF NOT EXISTS deal_sourcing_detail (
  id              SERIAL PRIMARY KEY,
  deal_id         INTEGER NOT NULL REFERENCES deal_master(id) ON DELETE CASCADE,
  channel_key     TEXT NOT NULL,
  discovery_path  TEXT,
  discovery_note  TEXT,
  discovery_date  TEXT,
  broker_name     TEXT,
  broker_company  TEXT,
  broker_contact  TEXT,
  broker_history  TEXT,
  broker_fee      TEXT,
  referrer_name   TEXT,
  referrer_org    TEXT,
  referrer_type   TEXT,
  exclusive_share BOOLEAN DEFAULT FALSE,
  platform_name   TEXT,
  platform_type   TEXT,
  etc_note        TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dsd_deal ON deal_sourcing_detail(deal_id);

-- 1-3) deal_kill_criteria
CREATE TABLE IF NOT EXISTS deal_kill_criteria (
  id          SERIAL PRIMARY KEY,
  deal_id     INTEGER NOT NULL REFERENCES deal_master(id) ON DELETE CASCADE,
  criteria    TEXT NOT NULL,
  is_custom   BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dkc_deal ON deal_kill_criteria(deal_id);

COMMIT;

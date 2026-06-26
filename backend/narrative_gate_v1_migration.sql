-- ============================================================
-- COSMOS P0 — Narrative Gate v1
-- 100% 추가형. 재실행 안전.
-- ============================================================
BEGIN;

CREATE TABLE IF NOT EXISTS narrative_gate_results (
  id                 SERIAL PRIMARY KEY,
  deal_id            INTEGER REFERENCES deal_master(id),
  thesis_type        TEXT,
  gate_result        TEXT CHECK (gate_result IN ('CONFIRMED','WEAK','BROKEN')),
  supported_count    INTEGER,
  contradicted_items JSONB,
  missing_evidence   JSONB,
  auto_reason        TEXT,
  created_at         TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ngr_deal ON narrative_gate_results(deal_id);

CREATE TABLE IF NOT EXISTS deal_thesis_history (
  id              SERIAL PRIMARY KEY,
  deal_id         INTEGER REFERENCES deal_master(id),
  old_thesis_type TEXT,
  new_thesis_type TEXT,
  changed_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dth_deal ON deal_thesis_history(deal_id);

-- deal_checklist_item: 내러티브 게이트용 확인상태 (기존 status와 별개)
ALTER TABLE deal_checklist_item
  ADD COLUMN IF NOT EXISTS item_status TEXT DEFAULT 'PENDING';
DO $$ BEGIN
  ALTER TABLE deal_checklist_item ADD CONSTRAINT deal_checklist_item_item_status_check
    CHECK (item_status IN ('PENDING','CONFIRMED','NOT_AVAILABLE'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 딜의 현재 thesis_type (변경 추적 + gate 입력)
ALTER TABLE deal_master ADD COLUMN IF NOT EXISTS thesis_type TEXT;

COMMIT;

-- ============================================================
-- COSMOS P0 — SDD AUTO 연결 v1
-- 100% 추가형. 재실행 안전.
-- ============================================================
BEGIN;

-- AUTO 항목 품질 메타 (item_status는 Narrative Gate에서 이미 추가됨)
ALTER TABLE deal_checklist_item
  ADD COLUMN IF NOT EXISTS data_as_of   TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS data_source  TEXT,
  ADD COLUMN IF NOT EXISTS ttl_days     INTEGER;

-- DART fetch용 corp_code (auto-populate가 사용)
ALTER TABLE deal_master ADD COLUMN IF NOT EXISTS dart_corp_code TEXT;

COMMIT;

-- 010_deal_legacy_link.sql
-- 신규 온톨로지 deal ↔ 기존 deal_master 연결용 컬럼 추가.
-- deal.legacy_deal_master_id 로 기존 deal_master.id 를 가리킨다(신·구 딜 매핑).
-- 멱등: ADD COLUMN IF NOT EXISTS.
SET lock_timeout = '5s';
SET statement_timeout = '60s';

ALTER TABLE deal
  ADD COLUMN IF NOT EXISTS legacy_deal_master_id INTEGER;

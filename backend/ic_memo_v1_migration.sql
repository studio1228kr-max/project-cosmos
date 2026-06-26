-- ============================================================
-- COSMOS P0 — IC Memo Claude 연결 v1 (섹션 6 + 섹션 9 DB)
-- 100% 추가형. 재실행 안전.
-- ============================================================
BEGIN;

CREATE TABLE IF NOT EXISTS ic_memos (
  id              SERIAL PRIMARY KEY,
  deal_id         INTEGER NOT NULL REFERENCES deal_master(id) ON DELETE CASCADE,
  -- Claude 생성 섹션 (S1~S8) + 코드 생성 S11
  sections        JSONB   NOT NULL DEFAULT '{}'::jsonb,
  -- 생성 시점 7개 input 스냅샷
  inputs          JSONB   NOT NULL DEFAULT '{}'::jsonb,
  -- 잠금 해제 조건 5가지 평가 스냅샷
  unlock_status   JSONB   NOT NULL DEFAULT '{}'::jsonb,
  -- S9 딜 구조: 딜타입별 term 레이블 (숫자 공란 — Claude 생성 금지)
  s9_terms        JSONB   NOT NULL DEFAULT '[]'::jsonb,
  s9_user_input   JSONB   NOT NULL DEFAULT '{}'::jsonb,   -- 민우 숫자 입력
  -- S10 판단 의견 (Claude 생성 금지 — 민우 직접 작성)
  s10_user_input  TEXT,
  s10_recommendation TEXT,                                -- PROMOTE | CONDITIONAL | HOLD
  -- 감사 추적
  gate_result     TEXT,
  sdd_completion  JSONB,
  prompt_version  TEXT,
  model           TEXT,
  generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ic_memos_deal ON ic_memos(deal_id, generated_at DESC);

COMMIT;

-- ============================================================
-- COSMOS — DD Tier (SDD/CDD/EDD) Diligence Module  v0.2
-- 100% ADDITIVE: no DROP / no RENAME / no change to existing columns or constraints.
-- Existing fn_create_deal_checklist(int,text) is PRESERVED; a 3-arg overload is added.
-- Tier model: CUMULATIVE  (EDD ⊇ CDD ⊇ SDD).
-- Safe to re-run (idempotent: IF NOT EXISTS / ON CONFLICT / WHERE dd_tier IS NULL).
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1) 티어 어휘 (cumulative 순서 정의)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dd_tier_registry (
    dd_tier     TEXT PRIMARY KEY,
    tier_rank   SMALLINT NOT NULL UNIQUE,        -- 1<2<3, 누적 비교용
    tier_label  TEXT NOT NULL,
    description TEXT
);
INSERT INTO dd_tier_registry (dd_tier, tier_rank, tier_label, description) VALUES
  ('SDD', 1, 'Simplified DD', '스크리닝/인테이크 go-no-go 최소 증빙'),
  ('CDD', 2, 'Core DD',       '표준 언더라이팅 증빙 세트'),
  ('EDD', 3, 'Enhanced DD',   '고위험·Control·특수상황 심화 증빙')
ON CONFLICT (dd_tier) DO NOTHING;

-- ------------------------------------------------------------
-- 2) 템플릿/인스턴스/딜본체에 dd_tier 축 추가 (모두 nullable add)
-- ------------------------------------------------------------
ALTER TABLE evidence_gate_template
  ADD COLUMN IF NOT EXISTS dd_tier TEXT REFERENCES dd_tier_registry(dd_tier);

ALTER TABLE deal_evidence_checklist
  ADD COLUMN IF NOT EXISTS dd_tier TEXT REFERENCES dd_tier_registry(dd_tier);

ALTER TABLE deal_master
  ADD COLUMN IF NOT EXISTS dd_tier TEXT DEFAULT 'CDD' REFERENCES dd_tier_registry(dd_tier);

-- ------------------------------------------------------------
-- 3) 템플릿 40항목 → SDD/CDD/EDD 정밀 매핑
--    원칙) SDD=자산정체성·등기/선순위·payoff(go-no-go)
--          CDD=감정·임대차·약정·상환재원(표준 언더라이팅)
--          EDD=전수 압류조사·지배구조·Control lever·차주재무·정보유출통제
-- ------------------------------------------------------------

-- SDD
UPDATE evidence_gate_template SET dd_tier='SDD' WHERE (deal_type_code, evidence_item_code) IN (
  ('BRIDGE_REFI','EXISTING_LIEN_STATUS'),
  ('BRIDGE_REFI','EXISTING_PAYOFF_LETTER'),
  ('CAPEX_BRIDGE_NOTE','CAP_STACK_CURRENT'),
  ('NPL_PURCHASE','AUCTION_STATUS'),
  ('NPL_PURCHASE','LOAN_LEDGER'),
  ('SECURED_CREDIT_ACQUISITION','REGISTRY_CURRENT'),
  ('SECURED_CREDIT_ACQUISITION','SENIOR_LIEN_CONFIRM'),
  ('SECURED_CREDIT_ACQUISITION','PAYOFF_STATEMENT'),
  ('SPECIAL_SITUATIONS_CONTROL','REGISTRY_CURRENT'),
  ('SPECIAL_SITUATIONS_CONTROL','LOAN_LEDGER'),
  ('SPONSOR_COOPERATIVE_RECAP','EXISTING_LOAN_BALANCE')
);

-- CDD
UPDATE evidence_gate_template SET dd_tier='CDD' WHERE (deal_type_code, evidence_item_code) IN (
  ('BRIDGE_REFI','NEW_LENDER_TERMS'),
  ('BRIDGE_REFI','REPAYMENT_SOURCE'),
  ('BRIDGE_REFI','CLOSING_CP'),
  ('CAPEX_BRIDGE_NOTE','CAPEX_QUOTE'),
  ('CAPEX_BRIDGE_NOTE','EXISTING_LENDER_CONSENT'),
  ('CAPEX_BRIDGE_NOTE','VALUE_UP_ANALYSIS'),
  ('NPL_PURCHASE','APPRAISAL_REPORT'),
  ('NPL_PURCHASE','LOAN_SALE_AGREEMENT'),
  ('SECURED_CREDIT_ACQUISITION','APPRAISAL_REPORT'),
  ('SECURED_CREDIT_ACQUISITION','BUILDING_LEDGER'),
  ('SECURED_CREDIT_ACQUISITION','LEASE_STATUS'),
  ('SECURED_CREDIT_ACQUISITION','LOAN_AGREEMENT'),
  ('SPECIAL_SITUATIONS_CONTROL','BUILDING_LEDGER'),
  ('SPECIAL_SITUATIONS_CONTROL','TENANT_OCCUPANCY_RIGHTS'),
  ('SPECIAL_SITUATIONS_CONTROL','CONTROL_LEVER_DOC'),
  ('SPONSOR_COOPERATIVE_RECAP','APPRAISAL_REPORT'),
  ('SPONSOR_COOPERATIVE_RECAP','LEASE_STATUS'),
  ('SPONSOR_COOPERATIVE_RECAP','USE_OF_PROCEEDS')
);

-- EDD
UPDATE evidence_gate_template SET dd_tier='EDD' WHERE (deal_type_code, evidence_item_code) IN (
  ('BRIDGE_REFI','BORROWER_CONSENT'),
  ('CAPEX_BRIDGE_NOTE','CONSTRUCTION_PERMIT'),
  ('NPL_PURCHASE','JUNIOR_RIGHTS_SURVEY'),
  ('NPL_PURCHASE','BORROWER_CREDIT'),
  ('SECURED_CREDIT_ACQUISITION','TAX_SEIZURE_CHECK'),
  ('SECURED_CREDIT_ACQUISITION','BORROWER_FINANCIALS'),
  ('SPECIAL_SITUATIONS_CONTROL','SEIZURE_FULL_SURVEY'),
  ('SPECIAL_SITUATIONS_CONTROL','BORROWER_GOVERNANCE'),
  ('SPECIAL_SITUATIONS_CONTROL','INFO_LEAK_PROTOCOL'),
  ('SPONSOR_COOPERATIVE_RECAP','BORROWER_FINANCIALS_3Y'),
  ('SPONSOR_COOPERATIVE_RECAP','SPONSOR_TRACK_RECORD')
);

-- 안전망: 위에서 누락된 항목이 있으면 requirement_level 기준으로 채움
UPDATE evidence_gate_template SET dd_tier='CDD'
  WHERE dd_tier IS NULL AND requirement_level='MANDATORY';
UPDATE evidence_gate_template SET dd_tier='EDD'
  WHERE dd_tier IS NULL;

-- 모든 행이 채워졌으므로 NOT NULL 강제
ALTER TABLE evidence_gate_template ALTER COLUMN dd_tier SET NOT NULL;

-- ------------------------------------------------------------
-- 4) 3-arg 오버로드 (누적 선택). 기존 2-arg(int,text)는 그대로 둠.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_create_deal_checklist(
    p_deal_master_id INTEGER,
    p_deal_type_code TEXT,
    p_dd_tier        TEXT
) RETURNS INTEGER LANGUAGE plpgsql AS $$
DECLARE v_count INTEGER; v_rank SMALLINT;
BEGIN
    SELECT tier_rank INTO v_rank FROM dd_tier_registry WHERE dd_tier = p_dd_tier;
    IF v_rank IS NULL THEN
        RAISE EXCEPTION 'unknown dd_tier %', p_dd_tier;
    END IF;

    INSERT INTO deal_evidence_checklist
        (deal_master_id, evidence_item_code, deal_type_code, evidence_item_label,
         requirement_level, gate_blocking, dd_tier)
    SELECT p_deal_master_id, egt.evidence_item_code, egt.deal_type_code, egt.evidence_item_label,
           egt.requirement_level, egt.gate_blocking, egt.dd_tier
    FROM evidence_gate_template egt
    JOIN dd_tier_registry tr ON tr.dd_tier = egt.dd_tier
    WHERE egt.deal_type_code = p_deal_type_code
      AND tr.tier_rank <= v_rank              -- CUMULATIVE: EDD ⊇ CDD ⊇ SDD
    ON CONFLICT (deal_master_id, evidence_item_code) DO NOTHING;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END $$;

-- 조회 편의 인덱스
CREATE INDEX IF NOT EXISTS idx_egt_type_tier ON evidence_gate_template(deal_type_code, dd_tier);
CREATE INDEX IF NOT EXISTS idx_dec_tier ON deal_evidence_checklist(deal_master_id, dd_tier);

COMMIT;

-- ============================================================
-- 검증 쿼리 (적용 후 수동 확인용)
-- ============================================================
-- SELECT deal_type_code, dd_tier, COUNT(*) FROM evidence_gate_template
--   GROUP BY 1,2 ORDER BY 1, CASE dd_tier WHEN 'SDD' THEN 1 WHEN 'CDD' THEN 2 ELSE 3 END;
-- 예상 누적 카운트: SECURED_CREDIT_ACQUISITION  SDD=3, CDD=7(3+4), EDD=9(7+2)

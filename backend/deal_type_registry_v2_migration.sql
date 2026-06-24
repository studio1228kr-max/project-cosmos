-- ============================================================
-- deal_type_registry 교체: 구 6타입 → 신 5타입
-- 기존 딜 3개 + 체크리스트 23행은 신 타입으로 재매핑(데이터 보존).
-- 구 타입 evidence_gate_template(40행)은 삭제(신 타입 템플릿은 별도 정의 필요).
-- 전 과정 단일 트랜잭션.
-- ============================================================
BEGIN;

-- 1) 신 5타입 INSERT (체크리스트 remap이 이 코드를 FK 참조하므로 먼저)
INSERT INTO deal_type_registry (deal_type_code, deal_type_label, typical_posture, description) VALUES
 ('DIRECT_LENDING',      '직접 신규 여신',     'COOPERATIVE', '내가 처음으로 직접 돈을 빌려주는 딜. 차주 신용/사업성 DD가 핵심.'),
 ('DEBT_PURCHASE',       '채권/대출채권 매입', 'MIXED',       '기존에 누군가 빌려준 걸 내가 사는 딜. 채권 유효성 + 담보 DD가 핵심.'),
 ('STRUCTURED_TRANCHE',  '구조화 참여/트랜치', 'COOPERATIVE', '선순위/후순위 트랜치, 클럽딜, ABF 참여. 워터폴 + 인터크레디터 DD가 핵심.'),
 ('DISTRESSED_SPECIAL',  '부실/특수상황',      'ADVERSARIAL', 'NPL, 회생, 경매, 법적 분쟁 중 채권. 법적 집행가능성 + 회수경로 DD가 핵심.'),
 ('EQUITY_LINKED_CREDIT','주식연계 신용',      'MIXED',       'CB, BW, 전환사채, 메자닌. 기업가치 + 전환조건 + 희석 DD가 핵심.');

-- 2) 기존 딜 + 체크리스트 재매핑
--    SECURED_CREDIT_ACQUISITION            → DEBT_PURCHASE
--    NPL_PURCHASE, SPECIAL_SITUATIONS_CONTROL → DISTRESSED_SPECIAL
UPDATE deal_master SET deal_type='DEBT_PURCHASE', updated_at=now()
  WHERE deal_type='SECURED_CREDIT_ACQUISITION';
UPDATE deal_master SET deal_type='DISTRESSED_SPECIAL', updated_at=now()
  WHERE deal_type IN ('NPL_PURCHASE','SPECIAL_SITUATIONS_CONTROL');

UPDATE deal_evidence_checklist SET deal_type_code='DEBT_PURCHASE', updated_at=now()
  WHERE deal_type_code='SECURED_CREDIT_ACQUISITION';
UPDATE deal_evidence_checklist SET deal_type_code='DISTRESSED_SPECIAL', updated_at=now()
  WHERE deal_type_code IN ('NPL_PURCHASE','SPECIAL_SITUATIONS_CONTROL');

-- 3) 구 타입 evidence_gate_template 삭제 (registry DELETE의 FK 차단 해제)
DELETE FROM evidence_gate_template
  WHERE deal_type_code IN ('BRIDGE_REFI','CAPEX_BRIDGE_NOTE','NPL_PURCHASE',
                           'SECURED_CREDIT_ACQUISITION','SPECIAL_SITUATIONS_CONTROL','SPONSOR_COOPERATIVE_RECAP');

-- 4) 구 6타입 삭제
DELETE FROM deal_type_registry
  WHERE deal_type_code IN ('BRIDGE_REFI','CAPEX_BRIDGE_NOTE','NPL_PURCHASE',
                           'SECURED_CREDIT_ACQUISITION','SPECIAL_SITUATIONS_CONTROL','SPONSOR_COOPERATIVE_RECAP');

COMMIT;

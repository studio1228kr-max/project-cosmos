-- ============================================================
-- COSMOS SDD Checklist Seed v1.0
-- evidence_gate_template 에 5개 딜타입 × SDD 항목 seed (140행)
-- + fn_create_sdd_checklist (template → deal_checklist_item)
-- 기존 시스템 보존: 구 컬럼 nullable화 후 신규 seed, 이후 구 컬럼 백필
-- ============================================================
BEGIN;

-- 1) evidence_gate_template 신규 컬럼 + 구 NOT NULL 완화
ALTER TABLE evidence_gate_template
  ADD COLUMN IF NOT EXISTS item_code     TEXT,
  ADD COLUMN IF NOT EXISTS item_name     TEXT,
  ADD COLUMN IF NOT EXISTS item_type     TEXT,
  ADD COLUMN IF NOT EXISTS is_required   BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 0;
ALTER TABLE evidence_gate_template ALTER COLUMN evidence_item_code  DROP NOT NULL;
ALTER TABLE evidence_gate_template ALTER COLUMN evidence_item_label DROP NOT NULL;
ALTER TABLE evidence_gate_template ALTER COLUMN requirement_level   DROP NOT NULL;

-- deal_checklist_item 정렬용 컬럼
ALTER TABLE deal_checklist_item ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 0;

-- 2) 기존 SDD 항목 제거
DELETE FROM evidence_gate_template WHERE dd_tier = 'SDD';

-- 3) SDD seed (item_type: AUTO/DOC_EXISTENCE/MANUAL/RULE)
-- 2-1. DIRECT_LENDING (22)
INSERT INTO evidence_gate_template (deal_type_code, dd_tier, item_code, item_name, item_type, is_required, display_order) VALUES
('DIRECT_LENDING','SDD','DL_A01','법인 존속 여부 (법인등기)','AUTO',TRUE,1),
('DIRECT_LENDING','SDD','DL_A02','대표자 확인 (법인등기)','AUTO',TRUE,2),
('DIRECT_LENDING','SDD','DL_A03','사업자 상태 (사업자등록)','AUTO',TRUE,3),
('DIRECT_LENDING','SDD','DL_A04','업종/사업목적 (법인등기)','AUTO',TRUE,4),
('DIRECT_LENDING','SDD','DL_A05','설립연도/업력 (법인등기)','AUTO',FALSE,5),
('DIRECT_LENDING','SDD','DL_A06','DART 공시 여부','AUTO',FALSE,6),
('DIRECT_LENDING','SDD','DL_A07','차주 실제 영업 여부 한 줄','MANUAL',TRUE,7),
('DIRECT_LENDING','SDD','DL_B01','요청 금액','MANUAL',TRUE,8),
('DIRECT_LENDING','SDD','DL_B02','요청 만기 rough (단기/중기/장기)','MANUAL',FALSE,9),
('DIRECT_LENDING','SDD','DL_B03','자금 사용 목적 한 줄','MANUAL',TRUE,10),
('DIRECT_LENDING','SDD','DL_B04','상환 재원 스토리','MANUAL',TRUE,11),
('DIRECT_LENDING','SDD','DL_B05','기존 차입 규모 rough','MANUAL',FALSE,12),
('DIRECT_LENDING','SDD','DL_B06','담보 제공 의향 (있음/없음/미정)','MANUAL',FALSE,13),
('DIRECT_LENDING','SDD','DL_C01','DART 최근 매출 존재 여부','AUTO',FALSE,14),
('DIRECT_LENDING','SDD','DL_C02','매출 규모 rough','MANUAL',TRUE,15),
('DIRECT_LENDING','SDD','DL_C03','영업이익/EBITDA rough','MANUAL',TRUE,16),
('DIRECT_LENDING','SDD','DL_C04','주요 고객/매출처 성격 (B2B/B2G/B2C)','MANUAL',FALSE,17),
('DIRECT_LENDING','SDD','DL_C05','업종 내 경쟁 지위 한 줄','MANUAL',FALSE,18),
('DIRECT_LENDING','SDD','DL_D01','법인등기 Dissolved/Liquidation 여부','RULE',TRUE,19),
('DIRECT_LENDING','SDD','DL_D02','사업자 Closed/Suspended 여부','RULE',TRUE,20),
('DIRECT_LENDING','SDD','DL_D03','대표자 변경 3개월 내 + 설명 회피 여부','RULE',TRUE,21),
('DIRECT_LENDING','SDD','DL_D04','자금목적 설명 불가 여부','RULE',TRUE,22);

-- 2-2. DEBT_PURCHASE (35)
INSERT INTO evidence_gate_template (deal_type_code, dd_tier, item_code, item_name, item_type, is_required, display_order) VALUES
('DEBT_PURCHASE','SDD','DP_A01','매도자 명칭','MANUAL',TRUE,1),
('DEBT_PURCHASE','SDD','DP_A02','매도자 유형 (은행/캐피탈/AMC/servicer/기타)','MANUAL',TRUE,2),
('DEBT_PURCHASE','SDD','DP_A03','매입 대상 구분 (단일/포트폴리오/지분참여)','MANUAL',TRUE,3),
('DEBT_PURCHASE','SDD','DP_A04','매입 구조 구분 (채권양도/수익권/지분양수/기타)','MANUAL',TRUE,4),
('DEBT_PURCHASE','SDD','DP_A05','UPB 존재 여부','MANUAL',TRUE,5),
('DEBT_PURCHASE','SDD','DP_A06','Ask price 존재 여부','MANUAL',TRUE,6),
('DEBT_PURCHASE','SDD','DP_A07','매각 사유 한 줄','MANUAL',FALSE,7),
('DEBT_PURCHASE','SDD','DP_B01','채권 원인 유형','MANUAL',TRUE,8),
('DEBT_PURCHASE','SDD','DP_B02','채권원인서류 존재 여부 (있음/없음/미확인/회피)','DOC_EXISTENCE',TRUE,9),
('DEBT_PURCHASE','SDD','DP_B03','실제 자금 집행 여부 매도자 설명','MANUAL',TRUE,10),
('DEBT_PURCHASE','SDD','DP_B04','현재 원금잔액 대략 규모','MANUAL',TRUE,11),
('DEBT_PURCHASE','SDD','DP_B05','이자/연체이자 존재 여부','MANUAL',FALSE,12),
('DEBT_PURCHASE','SDD','DP_B06','잔액 기준일 존재 여부','MANUAL',FALSE,13),
('DEBT_PURCHASE','SDD','DP_C01','기존 담보권 존재 여부 (있음/없음/미확인)','MANUAL',TRUE,14),
('DEBT_PURCHASE','SDD','DP_C02','담보 유형','MANUAL',FALSE,15),
('DEBT_PURCHASE','SDD','DP_C03','담보 설정 방식','MANUAL',FALSE,16),
('DEBT_PURCHASE','SDD','DP_C04','담보권자 유형','MANUAL',FALSE,17),
('DEBT_PURCHASE','SDD','DP_C05','담보권 이전 관련 매도자 진술','MANUAL',FALSE,18),
('DEBT_PURCHASE','SDD','DP_C06','담보 식별정보 존재 여부','MANUAL',FALSE,19),
('DEBT_PURCHASE','SDD','DP_D01','채무자 법인 존속 (법인등기)','AUTO',TRUE,20),
('DEBT_PURCHASE','SDD','DP_D02','채무자 유형 (법인등기)','AUTO',TRUE,21),
('DEBT_PURCHASE','SDD','DP_D03','채무자 업종 (사업자등록)','AUTO',FALSE,22),
('DEBT_PURCHASE','SDD','DP_D04','매도자 기준 채무자 상태','MANUAL',TRUE,23),
('DEBT_PURCHASE','SDD','DP_D05','보증인 존재 여부','MANUAL',FALSE,24),
('DEBT_PURCHASE','SDD','DP_D06','담보제공자 존재 여부','MANUAL',FALSE,25),
('DEBT_PURCHASE','SDD','DP_E01','매도자 = 현재 채권자 여부','MANUAL',TRUE,26),
('DEBT_PURCHASE','SDD','DP_E02','매도자 지위 (원대주/양수인/servicer/AMC/대리인)','MANUAL',TRUE,27),
('DEBT_PURCHASE','SDD','DP_E03','매도자-채권자 연결 설명 존재 여부','MANUAL',TRUE,28),
('DEBT_PURCHASE','SDD','DP_E04','매도자-담보권자 연결 설명 존재 여부','MANUAL',TRUE,29),
('DEBT_PURCHASE','SDD','DP_F01','매도자 진술상 양도 제한 여부','MANUAL',TRUE,30),
('DEBT_PURCHASE','SDD','DP_F02','채무자 동의 필요 여부 (Consent/Notice/None/미확인)','MANUAL',TRUE,31),
('DEBT_PURCHASE','SDD','DP_F03','담보권 이전 관련 제약 진술','MANUAL',FALSE,32),
('DEBT_PURCHASE','SDD','DP_F04','신탁/수익권/사모채 구조상 제한 가능성','MANUAL',FALSE,33),
('DEBT_PURCHASE','SDD','DP_G01','채권 원인 설명 불가 여부','RULE',TRUE,34),
('DEBT_PURCHASE','SDD','DP_G02','매도자-채권자 연결 불가 여부','RULE',TRUE,35);

-- 2-3. STRUCTURED_TRANCHE (28)
INSERT INTO evidence_gate_template (deal_type_code, dd_tier, item_code, item_name, item_type, is_required, display_order) VALUES
('STRUCTURED_TRANCHE','SDD','ST_A01','발행사/차주 법인 존속 (법인등기)','AUTO',TRUE,1),
('STRUCTURED_TRANCHE','SDD','ST_A02','거래 구조 유형 (선/후순위/클럽딜/ABF/유동화/기타)','MANUAL',TRUE,2),
('STRUCTURED_TRANCHE','SDD','ST_A03','기초자산 또는 상환원 유형','MANUAL',TRUE,3),
('STRUCTURED_TRANCHE','SDD','ST_A04','전체 딜 규모 rough','MANUAL',TRUE,4),
('STRUCTURED_TRANCHE','SDD','ST_A05','우리 참여 트랜치 및 규모','MANUAL',TRUE,5),
('STRUCTURED_TRANCHE','SDD','ST_A06','선순위 투자자 존재 여부 + 유형','MANUAL',TRUE,6),
('STRUCTURED_TRANCHE','SDD','ST_A07','공동 투자자 존재 여부 + 유형 rough','MANUAL',FALSE,7),
('STRUCTURED_TRANCHE','SDD','ST_B01','워터폴 구조 존재 여부 (있음/없음/미확인)','MANUAL',TRUE,8),
('STRUCTURED_TRANCHE','SDD','ST_B02','인터크레디터 약정 존재 여부 (있음/없음/미확인)','MANUAL',TRUE,9),
('STRUCTURED_TRANCHE','SDD','ST_B03','우리 트랜치 순위 rough (1순위/2순위/메자닌/Equity)','MANUAL',TRUE,10),
('STRUCTURED_TRANCHE','SDD','ST_B04','손실흡수 순서 rough 확인','MANUAL',TRUE,11),
('STRUCTURED_TRANCHE','SDD','ST_B05','cash trap / reserve 존재 여부 rough','MANUAL',FALSE,12),
('STRUCTURED_TRANCHE','SDD','ST_B06','담보 구조 존재 여부','MANUAL',FALSE,13),
('STRUCTURED_TRANCHE','SDD','ST_B07','주요 수익 구조 (이자/배당/수익권)','MANUAL',TRUE,14),
('STRUCTURED_TRANCHE','SDD','ST_B08','만기 구조 (단일/분할/순차)','MANUAL',FALSE,15),
('STRUCTURED_TRANCHE','SDD','ST_C01','리드 어레인저 또는 주관사 확인','MANUAL',TRUE,16),
('STRUCTURED_TRANCHE','SDD','ST_C02','딜 조성 이유 한 줄','MANUAL',TRUE,17),
('STRUCTURED_TRANCHE','SDD','ST_C03','우리가 이 트랜치에 들어가는 이유 한 줄','MANUAL',TRUE,18),
('STRUCTURED_TRANCHE','SDD','ST_C04','우리가 받는 cashflow 원천 설명 가능 여부','MANUAL',TRUE,19),
('STRUCTURED_TRANCHE','SDD','ST_C05','시장 평균 대비 수익률 rough 태깅','RULE',FALSE,20),
('STRUCTURED_TRANCHE','SDD','ST_D01','트랜치 순위 확인 불가 여부','RULE',TRUE,21),
('STRUCTURED_TRANCHE','SDD','ST_D02','워터폴 없음 + 후순위/메자닌 참여 여부','RULE',TRUE,22),
('STRUCTURED_TRANCHE','SDD','ST_D03','cashflow 원천 설명 불가 여부','RULE',TRUE,23),
('STRUCTURED_TRANCHE','SDD','ST_D04','손실흡수 순서 설명 불가 (후순위)','RULE',TRUE,24),
('STRUCTURED_TRANCHE','SDD','ST_D05','인터크레디터 미확인 (후순위/메자닌)','RULE',TRUE,25),
('STRUCTURED_TRANCHE','SDD','ST_E01','Thesis 자동 표시 (딜 등록 연동)','AUTO',TRUE,26),
('STRUCTURED_TRANCHE','SDD','ST_E02','Thesis vs SDD 일치 여부 판정','RULE',TRUE,27),
('STRUCTURED_TRANCHE','SDD','ST_E03','Thesis 재작성 또는 HOLD 선택','MANUAL',FALSE,28);

-- 2-4. DISTRESSED_SPECIAL (25)
INSERT INTO evidence_gate_template (deal_type_code, dd_tier, item_code, item_name, item_type, is_required, display_order) VALUES
('DISTRESSED_SPECIAL','SDD','DS_A01','채무자 법인 존속 (법인등기)','AUTO',TRUE,1),
('DISTRESSED_SPECIAL','SDD','DS_A02','DART 공시 상 회생/파산 여부 (flag)','AUTO',FALSE,2),
('DISTRESSED_SPECIAL','SDD','DS_A03','채권 유형 (대출/사채/판결채권/구상채권/기타)','MANUAL',TRUE,3),
('DISTRESSED_SPECIAL','SDD','DS_A04','담보부/무담보 구분 (담보부/무담보/미확인)','MANUAL',TRUE,4),
('DISTRESSED_SPECIAL','SDD','DS_A05','채권 매입 vs 구조조정 참여 구분','MANUAL',TRUE,5),
('DISTRESSED_SPECIAL','SDD','DS_A06','채무자 현재 상태 (NPL/회생/파산/경매/정상)','MANUAL',TRUE,6),
('DISTRESSED_SPECIAL','SDD','DS_A07','채권 규모 rough','MANUAL',TRUE,7),
('DISTRESSED_SPECIAL','SDD','DS_A08','현재 채권자 확인','MANUAL',TRUE,8),
('DISTRESSED_SPECIAL','SDD','DS_B01','EOD 선언 여부','MANUAL',TRUE,9),
('DISTRESSED_SPECIAL','SDD','DS_B02','회생/파산 신청 여부','MANUAL',TRUE,10),
('DISTRESSED_SPECIAL','SDD','DS_B03','경매 신청/개시 여부','MANUAL',TRUE,11),
('DISTRESSED_SPECIAL','SDD','DS_B04','소송/분쟁 존재 여부 (있음/없음/미확인)','MANUAL',FALSE,12),
('DISTRESSED_SPECIAL','SDD','DS_B05','권리 행사 주체 확인 (채권자/담보권자/수탁자)','MANUAL',TRUE,13),
('DISTRESSED_SPECIAL','SDD','DS_B06','담보권 존재 여부 (담보부인 경우)','MANUAL',FALSE,14),
('DISTRESSED_SPECIAL','SDD','DS_B07','담보 유형 rough','MANUAL',FALSE,15),
('DISTRESSED_SPECIAL','SDD','DS_C01','현실적 회수 경로 한 줄 (경매/협상/회생/매각)','MANUAL',TRUE,16),
('DISTRESSED_SPECIAL','SDD','DS_C02','회수 control point 확인 (경매신청권/의결권/담보권/leverage)','MANUAL',TRUE,17),
('DISTRESSED_SPECIAL','SDD','DS_C03','예상 회수 타임라인 rough','MANUAL',FALSE,18),
('DISTRESSED_SPECIAL','SDD','DS_C04','선순위 채권 존재 여부','MANUAL',TRUE,19),
('DISTRESSED_SPECIAL','SDD','DS_C05','선순위 rough 규모 vs 담보가치 (명백 underwater 여부)','RULE',FALSE,20),
('DISTRESSED_SPECIAL','SDD','DS_D01','채권 존재 설명 불가 여부','RULE',TRUE,21),
('DISTRESSED_SPECIAL','SDD','DS_D02','현재 채권자 확인 불가 여부','RULE',TRUE,22),
('DISTRESSED_SPECIAL','SDD','DS_D03','파산 종결 + 배당 완료 상태 여부','RULE',TRUE,23),
('DISTRESSED_SPECIAL','SDD','DS_D04','회수 경로 현실적 전무 여부','RULE',TRUE,24),
('DISTRESSED_SPECIAL','SDD','DS_D05','우리 권리와 회수경로 연결 불가 여부','RULE',TRUE,25);

-- 2-5. EQUITY_LINKED_CREDIT (30)
INSERT INTO evidence_gate_template (deal_type_code, dd_tier, item_code, item_name, item_type, is_required, display_order) VALUES
('EQUITY_LINKED_CREDIT','SDD','EL_A01','발행사 법인 존속 (법인등기)','AUTO',TRUE,1),
('EQUITY_LINKED_CREDIT','SDD','EL_A02','DART 공시 여부','AUTO',FALSE,2),
('EQUITY_LINKED_CREDIT','SDD','EL_A03','최근 감사보고서 존재 + 감사의견','AUTO',TRUE,3),
('EQUITY_LINKED_CREDIT','SDD','EL_A04','발행사 업종/사업 한 줄','MANUAL',TRUE,4),
('EQUITY_LINKED_CREDIT','SDD','EL_A05','주요 주주 구조 rough','MANUAL',FALSE,5),
('EQUITY_LINKED_CREDIT','SDD','EL_B01','증권 유형 (CB/BW/RCPS/메자닌/기타)','MANUAL',TRUE,6),
('EQUITY_LINKED_CREDIT','SDD','EL_B02','발행 규모','MANUAL',TRUE,7),
('EQUITY_LINKED_CREDIT','SDD','EL_B03','만기','MANUAL',TRUE,8),
('EQUITY_LINKED_CREDIT','SDD','EL_B04','표면금리/이자 구조','MANUAL',TRUE,9),
('EQUITY_LINKED_CREDIT','SDD','EL_B05','전환가액 존재 여부','MANUAL',TRUE,10),
('EQUITY_LINKED_CREDIT','SDD','EL_B06','전환 가능 시점 rough','MANUAL',FALSE,11),
('EQUITY_LINKED_CREDIT','SDD','EL_B07','조기상환청구권 존재 여부 (있음/없음/미확인)','MANUAL',TRUE,12),
('EQUITY_LINKED_CREDIT','SDD','EL_B08','콜옵션 존재 여부 (있음/없음/미확인)','MANUAL',FALSE,13),
('EQUITY_LINKED_CREDIT','SDD','EL_B09','Refixing 조항 존재 여부','MANUAL',TRUE,14),
('EQUITY_LINKED_CREDIT','SDD','EL_B10','Refixing Floor 여부 (있는 경우)','MANUAL',FALSE,15),
('EQUITY_LINKED_CREDIT','SDD','EL_B11','Refixing Reset 주기 rough (있는 경우)','MANUAL',FALSE,16),
('EQUITY_LINKED_CREDIT','SDD','EL_B12','담보/보증 여부 (있음/없음/미확인)','MANUAL',TRUE,17),
('EQUITY_LINKED_CREDIT','SDD','EL_C01','DART 최근 매출 존재 여부','AUTO',FALSE,18),
('EQUITY_LINKED_CREDIT','SDD','EL_C02','최근 매출 rough','MANUAL',TRUE,19),
('EQUITY_LINKED_CREDIT','SDD','EL_C03','최근 영업이익/순이익 rough','MANUAL',TRUE,20),
('EQUITY_LINKED_CREDIT','SDD','EL_C04','최근 라운드/시총/순자산 등 비교기준 존재 여부','MANUAL',TRUE,21),
('EQUITY_LINKED_CREDIT','SDD','EL_C05','전환가 vs 비교기준 rough 태깅 (Low/적정/High)','RULE',FALSE,22),
('EQUITY_LINKED_CREDIT','SDD','EL_C06','기존 메자닌/CB 과다 발행 이력 여부','MANUAL',FALSE,23),
('EQUITY_LINKED_CREDIT','SDD','EL_D01','발행사 법인 Dissolved/Liquidation 여부','RULE',TRUE,24),
('EQUITY_LINKED_CREDIT','SDD','EL_D02','감사의견 부적정/의견거절 여부','RULE',TRUE,25),
('EQUITY_LINKED_CREDIT','SDD','EL_D03','전환가액 전혀 없음 여부','RULE',TRUE,26),
('EQUITY_LINKED_CREDIT','SDD','EL_D04','Refixing Floor 없음 + 월단위 Reset 여부','RULE',TRUE,27),
('EQUITY_LINKED_CREDIT','SDD','EL_D05','조기상환청구권 없음 + 하방보호 전무 여부','RULE',TRUE,28),
('EQUITY_LINKED_CREDIT','SDD','EL_D06','기존 CB 과다 + 이자 미지급 이력 설명 불가','RULE',TRUE,29),
('EQUITY_LINKED_CREDIT','SDD','EL_D07','대주주 명시적 희석 거부 의사 여부','RULE',TRUE,30);

-- 4) 구 컬럼 백필 (구 fn_create_deal_checklist 및 UNIQUE 호환 유지)
UPDATE evidence_gate_template
SET evidence_item_code  = item_code,
    evidence_item_label = item_name,
    requirement_level   = CASE WHEN is_required THEN 'MANDATORY' ELSE 'CONDITIONAL' END,
    gate_blocking       = is_required
WHERE dd_tier = 'SDD' AND item_code IS NOT NULL;

-- 5) fn_create_sdd_checklist: template → deal_checklist_item
--    DOC_EXISTENCE → DOC 매핑(deal_checklist_item CHECK 호환), engine_connected=FALSE
CREATE OR REPLACE FUNCTION fn_create_sdd_checklist(
  p_deal_id INTEGER,
  p_deal_type TEXT
) RETURNS INTEGER AS $$
DECLARE v_count INTEGER;
BEGIN
  INSERT INTO deal_checklist_item
    (deal_id, dd_tier, item_code, item_name, item_type, status, display_order, engine_connected)
  SELECT
    p_deal_id, 'SDD', item_code, item_name,
    CASE WHEN item_type = 'DOC_EXISTENCE' THEN 'DOC' ELSE item_type END,
    'PENDING', display_order, FALSE
  FROM evidence_gate_template
  WHERE deal_type_code = p_deal_type AND dd_tier = 'SDD'
  ON CONFLICT (deal_id, dd_tier, item_code) DO NOTHING;
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$$ LANGUAGE plpgsql;

COMMIT;

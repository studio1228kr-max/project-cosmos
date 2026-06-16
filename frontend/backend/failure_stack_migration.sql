
-- COSMOS v0.2 — Core Failure Diagnostic Engine
-- Asset-class agnostic. ANH는 첫 번째 테스트 케이스일 뿐.

-- 1. failure_analysis — 딜 진단 결과 헤더
CREATE TABLE IF NOT EXISTS failure_analysis (
    id                  SERIAL PRIMARY KEY,
    deal_master_id      INTEGER REFERENCES deal_master(id) ON DELETE CASCADE,
    analysis_version    TEXT DEFAULT 'v1',
    asset_class         TEXT,                          -- CRE / CORPORATE / SPECIAL_SITS
    module_code         TEXT,                          -- CRE_SECURED_CREDIT / CORP_DIRECT_LENDING
    overall_severity    TEXT NOT NULL,                 -- CRITICAL / MODERATE / CLEAR
    gate_derived        TEXT NOT NULL,                 -- HOLD / RESTRUCTURE / ADVANCE / REJECT
    provisional_gate    TEXT,
    critical_count      INTEGER DEFAULT 0,
    moderate_count      INTEGER DEFAULT 0,
    deferred_count      INTEGER DEFAULT 0,
    total_failures      INTEGER DEFAULT 0,
    analyst             TEXT DEFAULT 'COSMOS',
    policy_version      TEXT,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- 2. failure_items — 개별 실패 항목
CREATE TABLE IF NOT EXISTS failure_items (
    id                    SERIAL PRIMARY KEY,
    failure_analysis_id   INTEGER REFERENCES failure_analysis(id) ON DELETE CASCADE,
    deal_master_id        INTEGER REFERENCES deal_master(id),

    -- 실패 분류 (5개 차원 — 에셋클래스 무관)
    failure_dimension     TEXT NOT NULL,
    -- EVIDENCE   : 증거 미비 / 신뢰도 부족
    -- FINANCIAL  : 수치 기준 미달
    -- STRUCTURAL : 거래 구조 닫히지 않음
    -- LEGAL      : 역할/권리/절차 미정리
    -- MARKET     : 매크로/섹터/출구 리스크

    failure_code          TEXT NOT NULL,
    -- 예: EVIDENCE_COLLATERAL_UNVERIFIED
    --     FINANCIAL_DSCR_BELOW_THRESHOLD
    --     STRUCTURAL_SENIOR_LIEN_UNCLEAR
    --     LEGAL_ROLE_BOUNDARY_UNDEFINED
    --     MARKET_SECTOR_STRESS_TAIL

    failure_label         TEXT NOT NULL,
    severity              TEXT NOT NULL,
    -- CRITICAL  : 이게 있으면 무조건 HOLD
    -- MODERATE  : RESTRUCTURE 트리거
    -- DEFERRED  : 기록하되 Gate 미반영

    description           TEXT,

    -- 수치 관련 (FINANCIAL 차원에서 주로 사용)
    metric_name           TEXT,       -- 예: dscr, ltv_net, icr
    metric_value          NUMERIC,    -- 실제 값
    threshold_value       NUMERIC,    -- 기준값
    breach_amount         NUMERIC,    -- 초과/미달 폭

    -- 해소 추적
    resolution_status     TEXT DEFAULT 'OPEN',
    -- OPEN / IN_PROGRESS / RESOLVED

    resolution_note       TEXT,
    resolved_by           TEXT,
    resolved_at           TIMESTAMP,

    -- 연결
    evidence_id           INTEGER REFERENCES deal_evidence(id) ON DELETE SET NULL,
    asset_class           TEXT,       -- NULL=Core공통, 'CRE'=모듈전용

    created_at            TIMESTAMP DEFAULT NOW()
);

-- 3. failure_actions — 실패항목별 해결 과제
CREATE TABLE IF NOT EXISTS failure_actions (
    id                  SERIAL PRIMARY KEY,
    failure_item_id     INTEGER REFERENCES failure_items(id) ON DELETE CASCADE,
    deal_master_id      INTEGER REFERENCES deal_master(id),

    action_code         TEXT,
    action_label        TEXT NOT NULL,

    -- 누가 해야 하나 (특정 이름 아니라 역할)
    counterparty_role   TEXT,
    -- EXISTING_SENIOR_LENDER
    -- POTENTIAL_TAKEOUT_LENDER
    -- BORROWER
    -- LEGAL_COUNSEL
    -- APPRAISER
    -- INTERNAL_COSMOS

    owner               TEXT,
    status              TEXT DEFAULT 'PENDING',
    -- PENDING / IN_PROGRESS / COMPLETE / BLOCKED

    due_date            DATE,
    completed_at        TIMESTAMP,
    blocking_reason     TEXT,

    created_at          TIMESTAMP DEFAULT NOW()
);

-- 4. deal_master에 asset_class 추가 (비파괴적)
ALTER TABLE deal_master
    ADD COLUMN IF NOT EXISTS asset_class  TEXT DEFAULT 'CRE',
    ADD COLUMN IF NOT EXISTS module_code  TEXT DEFAULT 'CRE_SECURED_CREDIT',
    ADD COLUMN IF NOT EXISTS use_for_sourcing_model    BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS use_for_execution_model   BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS use_for_risk_calibration  BOOLEAN DEFAULT TRUE;

-- 5. scenario_library에 scope 추가
ALTER TABLE scenario_library
    ADD COLUMN IF NOT EXISTS scope       TEXT DEFAULT 'ASSET_CLASS',
    -- CORE = 에셋클래스 무관 (GFC, IMF 등)
    -- ASSET_CLASS = 특정 모듈 전용
    ADD COLUMN IF NOT EXISTS asset_class TEXT,
    ADD COLUMN IF NOT EXISTS module_code TEXT;

-- Core 공통 시나리오 업데이트 (Historical tail은 Core)
UPDATE scenario_library SET scope='CORE', asset_class=NULL
WHERE scenario_id IN ('IMF_1997','GFC_2008','COVID_2020','PF_2023');

-- CRE 전용 시나리오 업데이트
UPDATE scenario_library SET scope='ASSET_CLASS', asset_class='CRE', module_code='CRE_SECURED_CREDIT'
WHERE scenario_id IN ('BASE','NOI_MINUS_10','NOI_MINUS_20','NOI_MINUS_30',
                      'RATE_PLUS_100','RATE_PLUS_200','VALUE_MINUS_25','COMBINED');

-- 6. gate_policy에 scope 추가
ALTER TABLE gate_policy
    ADD COLUMN IF NOT EXISTS scope       TEXT DEFAULT 'MODULE',
    ADD COLUMN IF NOT EXISTS asset_class TEXT DEFAULT 'CRE',
    ADD COLUMN IF NOT EXISTS module_code TEXT DEFAULT 'CRE_SECURED_CREDIT';

UPDATE gate_policy SET scope='MODULE', asset_class='CRE', module_code='CRE_SECURED_CREDIT'
WHERE policy_id='LUSKA_GATE_V0_1';

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_fa_deal      ON failure_analysis(deal_master_id);
CREATE INDEX IF NOT EXISTS idx_fi_analysis  ON failure_items(failure_analysis_id);
CREATE INDEX IF NOT EXISTS idx_fi_dimension ON failure_items(failure_dimension, severity);
CREATE INDEX IF NOT EXISTS idx_fi_status    ON failure_items(resolution_status);
CREATE INDEX IF NOT EXISTS idx_faction_item ON failure_actions(failure_item_id);
CREATE INDEX IF NOT EXISTS idx_faction_role ON failure_actions(counterparty_role);

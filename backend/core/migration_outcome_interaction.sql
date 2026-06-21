-- COSMOS Core — 신규 테이블 마이그레이션
-- deal_outcome_log: 예측 vs 실측 (니치 캘리브레이션 모트의 데이터 소스)
-- interaction_log: 행동 신호 원시 로그 (behavioral_risk_engine의 입력)

CREATE TABLE IF NOT EXISTS deal_outcome_log (
    id SERIAL PRIMARY KEY,
    deal_master_id INT REFERENCES deal_master(id),
    logged_at TIMESTAMP DEFAULT NOW(),

    -- 예측치 (모형 산출 시점 — quant 엔진의 EngineResult.metrics 그대로 복사)
    predicted_pd FLOAT,
    predicted_lgd FLOAT,
    predicted_ead NUMERIC,
    predicted_el NUMERIC,
    predicted_at TIMESTAMP,
    model_version TEXT,

    -- 실측치 (사건 발생 후 채워짐, NULL 허용 — 딜 종료 전까지는 비어있음)
    actual_default_occurred BOOLEAN,
    actual_default_date DATE,
    actual_recovery_amount NUMERIC,
    actual_recovery_date DATE,
    actual_lgd FLOAT,
    resolution_type TEXT,           -- 'CURE' | 'LIQUIDATION' | 'REFI' | 'PAYOFF'

    asset_class TEXT,
    deal_segment TEXT,              -- 니치 태그, 예: '한국 소형 CRE 선채권'
    notes TEXT
);

CREATE TABLE IF NOT EXISTS interaction_log (
    id SERIAL PRIMARY KEY,
    deal_master_id INT REFERENCES deal_master(id),
    interaction_type TEXT,          -- 'CALL' | 'EMAIL' | 'DOC_REQUEST' | 'DOC_SUBMIT' | 'MEETING'
    counterparty TEXT,               -- 차주/임차인/대주 등
    requested_at TIMESTAMP,
    promised_at TIMESTAMP,            -- 상대가 약속한 시점
    actual_at TIMESTAMP,              -- 실제 발생/제출 시점
    delay_days FLOAT,                 -- actual_at - promised_at, 앱에서 계산해서 저장
    content_summary TEXT,
    nlp_flags JSONB,                  -- Claude NLP가 추출한 행동 신호 태그
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outcome_deal ON deal_outcome_log(deal_master_id);
CREATE INDEX IF NOT EXISTS idx_interaction_deal ON interaction_log(deal_master_id);
CREATE INDEX IF NOT EXISTS idx_interaction_type ON interaction_log(interaction_type);

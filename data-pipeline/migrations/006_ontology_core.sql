-- 006_ontology_core.sql
-- 온톨로지 코어 6테이블 신규 생성: policy_rule / borrower / deal / collateral / valuation / agent_action_log.
-- 생성 순서는 FK 의존성을 따른다: 참조 대상이 먼저.
--   policy_rule  ← agent_action_log, deal 이 참조하므로 최우선.
--   borrower     ← deal 이 참조하므로 deal 보다 먼저.
--   deal → borrower, policy_rule
--   collateral → deal
--   valuation → collateral, deal
--   agent_action_log → deal, policy_rule
-- 공통: 모든 테이블에 es_sync_token BIGINT DEFAULT 1 (Elasticsearch 동기화 토큰).
SET lock_timeout = '5s';
SET statement_timeout = '60s';

-- ── policy_rule ──────────────────────────────────────────────
-- 게이트/정책 룰 레지스트리. 다른 테이블(deal, agent_action_log)이 참조한다.
CREATE TABLE IF NOT EXISTS policy_rule (
    id              BIGSERIAL PRIMARY KEY,

    rule_code       TEXT NOT NULL,
    rule_category   TEXT,
    rule_name       TEXT NOT NULL,
    severity        TEXT,
    gate_action     TEXT,
    trigger_condition TEXT,
    rationale       TEXT,
    status          TEXT NOT NULL DEFAULT 'active',
    rule_version    TEXT,

    rule_key        TEXT NOT NULL,
    rule_kind       TEXT NOT NULL,
    scope           TEXT NOT NULL DEFAULT 'global',
    version         INT  NOT NULL DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    rule_body       JSONB NOT NULL DEFAULT '{}'::jsonb,

    es_sync_token   BIGINT NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_policy_rule_key_version UNIQUE (rule_key, version),

    CONSTRAINT chk_policy_rule_severity
    CHECK (severity IS NULL OR severity IN ('INFO','LOW','MEDIUM','HIGH','CRITICAL'))
);

-- ── borrower ─────────────────────────────────────────────────
-- 차주(채무자) 엔티티. deal 이 참조한다.
CREATE TABLE IF NOT EXISTS borrower (
    id              BIGSERIAL PRIMARY KEY,

    borrower_code   TEXT NOT NULL,
    name            TEXT NOT NULL,
    entity_type     TEXT,
    dart_corp_code  TEXT,
    country         TEXT DEFAULT 'KR',
    sector          TEXT,

    properties      JSONB NOT NULL DEFAULT '{}'::jsonb,
    provenance      JSONB NOT NULL DEFAULT '{}'::jsonb,

    es_sync_token   BIGINT NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_borrower_code UNIQUE (borrower_code)
);

-- ── deal ─────────────────────────────────────────────────────
-- 딜 코어 엔티티. gate_status 기본값은 HOLD (C-07: 미지·미검증은 HOLD 강제).
CREATE TABLE IF NOT EXISTS deal (
    id              BIGSERIAL PRIMARY KEY,

    deal_code       TEXT NOT NULL,
    deal_name       TEXT,
    deal_type       TEXT,
    stage           TEXT,

    borrower_id     BIGINT REFERENCES borrower(id),
    gate_policy_rule_id BIGINT REFERENCES policy_rule(id),

    -- C-07: 기본 게이트는 HOLD. 게이트 전이는 룰테이블이 결정한다(C-12).
    gate_status     TEXT NOT NULL DEFAULT 'HOLD',

    exposure_amount BIGINT,
    currency        TEXT NOT NULL DEFAULT 'KRW',
    maturity_date   DATE,

    properties      JSONB NOT NULL DEFAULT '{}'::jsonb,
    provenance      JSONB NOT NULL DEFAULT '{}'::jsonb,

    es_sync_token   BIGINT NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_deal_code UNIQUE (deal_code),

    CONSTRAINT chk_deal_gate_status
    CHECK (gate_status IN ('GO','HOLD','KILL'))
);

-- ── collateral ───────────────────────────────────────────────
-- 담보 자산. deal 에 종속.
CREATE TABLE IF NOT EXISTS collateral (
    id              BIGSERIAL PRIMARY KEY,

    collateral_code TEXT,
    deal_id         BIGINT NOT NULL REFERENCES deal(id) ON DELETE CASCADE,

    collateral_type TEXT,
    lien_position   TEXT,
    description     TEXT,
    asset_address   TEXT,

    es_sync_token   BIGINT NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_collateral_code UNIQUE (collateral_code)
);

-- ── valuation ────────────────────────────────────────────────
-- 담보 평가값. 출처 추적 필수: 엔진 산출(engine_run_id) 또는 원문 문서(source_doc_id) 중 최소 하나.
CREATE TABLE IF NOT EXISTS valuation (
    id              BIGSERIAL PRIMARY KEY,

    collateral_id   BIGINT REFERENCES collateral(id) ON DELETE CASCADE,
    deal_id         BIGINT REFERENCES deal(id) ON DELETE CASCADE,

    subject_type    TEXT,
    subject_id      BIGINT,

    valuation_method TEXT,
    value_amount    NUMERIC,
    currency        TEXT NOT NULL DEFAULT 'KRW',
    as_of_date      DATE,

    cases           JSONB NOT NULL DEFAULT '[]'::jsonb,
    primary_case    TEXT NOT NULL DEFAULT 'downside',
    confidence      TEXT NOT NULL DEFAULT 'UNVERIFIED',

    engine_run_id   TEXT,
    source_doc_id   TEXT,
    provenance      JSONB NOT NULL DEFAULT '{}'::jsonb,

    es_sync_token   BIGINT NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 출처 없는 평가값 금지: 엔진 산출 / 원문 문서 / provenance JSONB 중 최소 하나.
    CONSTRAINT chk_valuation_provenance
    CHECK (
        engine_run_id IS NOT NULL
        OR source_doc_id IS NOT NULL
        OR (provenance IS NOT NULL AND provenance != '{}'::jsonb)
    )
);

-- ── agent_action_log ─────────────────────────────────────────
-- 에이전트 행위 원장. 어떤 정책 룰(policy_rule)에 따라 무슨 행위를 했는지 기록.
CREATE TABLE IF NOT EXISTS agent_action_log (
    id              BIGSERIAL PRIMARY KEY,

    deal_id         BIGINT REFERENCES deal(id) ON DELETE CASCADE,
    policy_rule_id  BIGINT REFERENCES policy_rule(id),

    agent_name      TEXT,
    action_type     TEXT,
    gate_status     TEXT,
    allowed         BOOLEAN,
    rationale       TEXT,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,

    es_sync_token   BIGINT NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- FK 인덱스 (조회/조인 성능). foundation 단계라 비-CONCURRENTLY로 트랜잭션 내 생성.
CREATE INDEX IF NOT EXISTS idx_deal_borrower_id          ON deal(borrower_id);
CREATE INDEX IF NOT EXISTS idx_deal_gate_policy_rule_id  ON deal(gate_policy_rule_id);
CREATE INDEX IF NOT EXISTS idx_deal_gate_status          ON deal(gate_status);
CREATE INDEX IF NOT EXISTS idx_collateral_deal_id        ON collateral(deal_id);
CREATE INDEX IF NOT EXISTS idx_valuation_collateral_id   ON valuation(collateral_id);
CREATE INDEX IF NOT EXISTS idx_valuation_deal_id         ON valuation(deal_id);
CREATE INDEX IF NOT EXISTS idx_aal_deal_id               ON agent_action_log(deal_id);
CREATE INDEX IF NOT EXISTS idx_aal_policy_rule_id        ON agent_action_log(policy_rule_id);

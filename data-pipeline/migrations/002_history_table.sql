-- 002_history_table.sql
-- 충돌 반영: entity_id는 corp_code라 TEXT, feature 컬럼은 실제 ratio 스키마.
-- append-only 원장. z_zone은 z_score 파생 generated.
CREATE TABLE IF NOT EXISTS entity_financial_feature_versions (
    version_id      BIGSERIAL PRIMARY KEY,

    entity_id       TEXT NOT NULL,
    period_end      DATE NOT NULL,
    report_type     VARCHAR(10) NOT NULL,

    reprt_code      VARCHAR(10),
    statement_end   DATE,
    period_months   SMALLINT,
    is_accumulated  BOOLEAN NOT NULL DEFAULT TRUE,

    fetched_at      TIMESTAMPTZ NOT NULL,
    batch_id        UUID NOT NULL,
    source_hash     CHAR(64) NOT NULL,
    feature_quality JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Altman X1~X5 ratio + 파생 지표 (current 테이블과 동일 스키마)
    working_capital_ratio   NUMERIC,
    retained_earnings_ratio NUMERIC,
    ebit_ratio              NUMERIC,
    equity_to_debt_ratio    NUMERIC,
    sales_ratio             NUMERIC,
    z_score                 NUMERIC,
    ebit                    NUMERIC,
    interest_expense        NUMERIC,
    icr                     NUMERIC,
    ocf                     NUMERIC,
    short_term_debt         NUMERIC,

    z_zone TEXT GENERATED ALWAYS AS (
        CASE
            WHEN z_score IS NULL THEN NULL
            WHEN z_score < 1.23  THEN 'DISTRESS'
            WHEN z_score < 2.90  THEN 'GREY'
            ELSE 'SAFE'
        END
    ) STORED,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_eff_versions_report_type
    CHECK (report_type IN ('annual','q3','half','q1')),

    CONSTRAINT chk_eff_versions_period_months
    CHECK (period_months IS NULL OR period_months IN (3,6,9,12))
);

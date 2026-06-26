-- 001_foundation.sql
-- 충돌 반영: entity_financial_features는 Altman X1~X5 ratio 스키마.
-- z_zone은 z_score 파생 generated 컬럼으로 전환(Mythos 수치 파이프라인이 TEXT를 안 다룸).
SET lock_timeout = '5s';
SET statement_timeout = '60s';

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE entity_financial_features ADD COLUMN IF NOT EXISTS report_type    VARCHAR(10) DEFAULT 'annual' NOT NULL;
ALTER TABLE entity_financial_features ADD COLUMN IF NOT EXISTS reprt_code     VARCHAR(10);
ALTER TABLE entity_financial_features ADD COLUMN IF NOT EXISTS statement_end  DATE;
ALTER TABLE entity_financial_features ADD COLUMN IF NOT EXISTS period_months  SMALLINT;
ALTER TABLE entity_financial_features ADD COLUMN IF NOT EXISTS is_accumulated BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE entity_financial_features ADD COLUMN IF NOT EXISTS fetched_at     TIMESTAMPTZ DEFAULT NOW() NOT NULL;
ALTER TABLE entity_financial_features ADD COLUMN IF NOT EXISTS batch_id       UUID DEFAULT gen_random_uuid() NOT NULL;
ALTER TABLE entity_financial_features ADD COLUMN IF NOT EXISTS source_hash    CHAR(64);
ALTER TABLE entity_financial_features ADD COLUMN IF NOT EXISTS feature_quality JSONB DEFAULT '{}'::jsonb NOT NULL;
ALTER TABLE entity_financial_features ADD COLUMN IF NOT EXISTS current_version_id BIGINT;
ALTER TABLE entity_financial_features ADD COLUMN IF NOT EXISTS updated_at     TIMESTAMPTZ DEFAULT NOW() NOT NULL;

-- z_zone: plain TEXT(+CHECK) → z_score 파생 generated 로 교체 (Mythos가 z_zone을 직접 쓰지 않음)
ALTER TABLE entity_financial_features DROP CONSTRAINT IF EXISTS entity_financial_features_z_zone_check;
ALTER TABLE entity_financial_features DROP COLUMN IF EXISTS z_zone;
ALTER TABLE entity_financial_features ADD COLUMN z_zone TEXT GENERATED ALWAYS AS (
    CASE
        WHEN z_score IS NULL      THEN NULL
        WHEN z_score < 1.23       THEN 'DISTRESS'
        WHEN z_score < 2.90       THEN 'GREY'
        ELSE 'SAFE'
    END
) STORED;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='chk_eff_current_report_type' AND conrelid='entity_financial_features'::regclass) THEN
        ALTER TABLE entity_financial_features
        ADD CONSTRAINT chk_eff_current_report_type
        CHECK (report_type IN ('annual','q3','half','q1')) NOT VALID;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='chk_eff_current_period_months' AND conrelid='entity_financial_features'::regclass) THEN
        ALTER TABLE entity_financial_features
        ADD CONSTRAINT chk_eff_current_period_months
        CHECK (period_months IS NULL OR period_months IN (3,6,9,12)) NOT VALID;
    END IF;
END $$;

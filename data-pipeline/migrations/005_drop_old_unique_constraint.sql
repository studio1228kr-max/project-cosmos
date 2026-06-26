-- 005_drop_old_unique_constraint.sql
-- 기존 UNIQUE(entity_id, period_end) 제거 + 신규 UNIQUE(entity_id, period_end, report_type) swap.
BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT c.conname
        FROM pg_constraint c
        JOIN LATERAL (
            SELECT array_agg(a.attname ORDER BY u.ord) AS cols
            FROM unnest(c.conkey) WITH ORDINALITY AS u(attnum, ord)
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = u.attnum
        ) x ON TRUE
        WHERE c.conrelid = 'entity_financial_features'::regclass
          AND c.contype = 'u'
          AND x.cols::text[] = ARRAY['entity_id','period_end']
    LOOP
        EXECUTE format('ALTER TABLE entity_financial_features DROP CONSTRAINT %I', r.conname);
    END LOOP;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='uq_eff_current_entity_period_report' AND conrelid='entity_financial_features'::regclass) THEN
        ALTER TABLE entity_financial_features
        ADD CONSTRAINT uq_eff_current_entity_period_report
        UNIQUE USING INDEX idx_eff_current_entity_period_report_unique;
    END IF;
END $$;

COMMIT;

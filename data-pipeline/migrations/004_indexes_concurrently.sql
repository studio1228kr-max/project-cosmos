-- 004_indexes_concurrently.sql
-- DO NOT WRAP IN BEGIN/COMMIT. 각 문장 autocommit 실행.

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_eff_versions_natural_hash_unique
ON entity_financial_feature_versions (entity_id, period_end, report_type, source_hash);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_eff_versions_pit_lookup
ON entity_financial_feature_versions (entity_id, period_end, report_type, fetched_at DESC, version_id DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_eff_versions_batch
ON entity_financial_feature_versions (batch_id, entity_id, period_end);

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_eff_current_entity_period_report_unique
ON entity_financial_features (entity_id, period_end, report_type);

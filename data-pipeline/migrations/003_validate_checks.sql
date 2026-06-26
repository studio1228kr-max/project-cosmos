-- 003_validate_checks.sql
SET lock_timeout = '5s';
SET statement_timeout = '0';

ALTER TABLE entity_financial_features VALIDATE CONSTRAINT chk_eff_current_report_type;
ALTER TABLE entity_financial_features VALIDATE CONSTRAINT chk_eff_current_period_months;

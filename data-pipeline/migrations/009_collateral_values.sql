-- 009_collateral_values.sql
-- collateral 테이블에 평가 수치 컬럼 3개 추가 (gate_evaluator 의 collateral.<field> 비교용).
-- 멱등: ADD COLUMN IF NOT EXISTS.
SET lock_timeout = '5s';
SET statement_timeout = '60s';

ALTER TABLE collateral
  ADD COLUMN IF NOT EXISTS appraised_value      NUMERIC,
  ADD COLUMN IF NOT EXISTS first_lien_value     NUMERIC,
  ADD COLUMN IF NOT EXISTS net_collateral_value NUMERIC;

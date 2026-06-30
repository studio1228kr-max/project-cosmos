-- 008_seed_patch.sql
-- policy_rule 시드 패치:
--   1) threshold.all(v1) rule_body 에 stale_tolerance_days / computed_eligible_paths /
--      distressed_special_overrides 를 jsonb concat(||)으로 덮어쓰기·추가.
--   2) rbac 룰 2건 신규 적재 (AdoptComputedValue / VerifyProperty).
-- 멱등: rbac INSERT 는 ON CONFLICT (rule_key, version) DO NOTHING.
--       threshold UPDATE 는 동일 key 덮어쓰기라 재실행 안전.
-- NOTE: rule_kind 는 NOT NULL 이므로 rbac 행에 'rbac' 를 채운다(원 지시에 미명시).
SET lock_timeout = '5s';
SET statement_timeout = '60s';

-- 1. threshold.all 패치 (version 1)
UPDATE policy_rule
SET rule_body = rule_body
  || jsonb_build_object(
    'stale_tolerance_days', jsonb_build_object('default', 60, 'overrides', jsonb_build_object('valuation.merton_kmv.primary_case', 90)),
    'computed_eligible_paths', jsonb_build_array('deal.properties.dscr','deal.properties.ltv','deal.properties.irr_downside','valuation.merton_kmv.primary_case','valuation.cashflow_waterfall.primary_case'),
    'distressed_special_overrides', jsonb_build_object('valuation.liquidation.primary_case', jsonb_build_object('eligibility','adopted_or_external_only'))
  )
WHERE rule_key = 'threshold.all' AND version = 1;

-- 2. rbac.adopt_computed
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('rbac.adopt_computed', 'rbac.adopt_computed', 'RBAC - Adopt Computed Value', 'rbac_permission', 'global', 1, TRUE,
$rb${"action_type":"AdoptComputedValue","allowed_roles":["gp_partner","risk_officer"],"forbidden_for_agents":true,"requires_lineage":true}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

-- 3. rbac.verify_property
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('rbac.verify_property', 'rbac.verify_property', 'RBAC - Verify Property', 'rbac_permission', 'global', 1, TRUE,
$rb${"action_type":"VerifyProperty","allowed_roles":["gp_partner","risk_officer"],"forbidden_for_agents":true,"requires_evidence_doc":true}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

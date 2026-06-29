-- 007_policy_rule_seed.sql
-- policy_rule 시드: 정책/게이트 룰 초기 데이터 적재.
-- 적재 순서: enum_registry → threshold → p0_input_set(딜타입 5종) → gate_table(딜타입 5종).
-- 멱등: ON CONFLICT (rule_key, version) DO NOTHING.
--
-- NOTE: 006 policy_rule 스키마 정합을 위해 INSERT 시그니처를 맞춤.
--   - created_by 컬럼은 006 에 없으므로 제외.
--   - rule_code(NOT NULL)=rule_key, rule_name(NOT NULL)=라벨을 채운다.
-- rule_body 는 작은따옴표(deal_type='...')를 포함하므로 달러 인용($rb$...$rb$)으로 감싼다.
SET lock_timeout = '5s';
SET statement_timeout = '60s';

-- 1. registry.deal_type
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('registry.deal_type', 'registry.deal_type', 'Deal Type Registry', 'enum_registry', 'global', 1, TRUE,
$rb${"enum":["direct_lending","debt_purchase","structured_tranche","distressed_special","equity_linked_credit"]}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

-- 2. threshold.all
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('threshold.all', 'threshold.all', 'Global Threshold Set', 'threshold', 'global', 1, TRUE,
$rb${"dscr_floor":{"direct_lending":1.20,"structured_tranche":1.10,"equity_linked_credit":1.00,"debt_purchase":null,"distressed_special":null},"ltv_cap":{"direct_lending":0.70,"structured_tranche":0.80,"equity_linked_credit":0.75,"debt_purchase":null,"distressed_special":null},"irr_hurdle":{"direct_lending":0.10,"debt_purchase":0.15,"structured_tranche":0.09,"distressed_special":0.18,"equity_linked_credit":0.12},"discount_floor_factor":{"debt_purchase":1.00},"junior_loss_tolerance":{"structured_tranche":0.30},"stale_tolerance_days":{"default":60,"overrides":{"valuation.merton_kmv.primary_case":90}},"computed_eligible_paths":["deal.properties.dscr","deal.properties.ltv","deal.properties.irr_downside","valuation.merton_kmv.primary_case","valuation.cashflow_waterfall.primary_case"],"human_only_paths":["deal.properties.principal","deal.properties.tenor_m","deal.properties.coupon","deal.properties.conversion_price"]}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

-- 3. p0.direct_lending
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('p0.direct_lending', 'p0.direct_lending', 'P0 Input Set - Direct Lending', 'p0_input_set', 'global', 1, TRUE,
$rb${"p0_inputs":[{"path":"borrower.properties.revenue","confidence_min":"HIGH"},{"path":"borrower.properties.ebitda","confidence_min":"HIGH"},{"path":"borrower.properties.total_debt","confidence_min":"HIGH"},{"path":"deal.properties.dscr","confidence_min":"HIGH"},{"path":"deal.properties.ltv","confidence_min":"HIGH"},{"path":"deal.properties.principal","confidence_min":"VERIFIED"},{"path":"deal.properties.tenor_m","confidence_min":"VERIFIED"},{"path":"collateral.first_lien_value","confidence_min":"HIGH"}]}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

-- 4. p0.debt_purchase
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('p0.debt_purchase', 'p0.debt_purchase', 'P0 Input Set - Debt Purchase', 'p0_input_set', 'global', 1, TRUE,
$rb${"p0_inputs":[{"path":"deal.properties.principal","confidence_min":"VERIFIED"},{"path":"deal.properties.target_price","confidence_min":"HIGH"},{"path":"valuation.liquidation.primary_case","confidence_min":"HIGH"},{"path":"deal.properties.irr_downside","confidence_min":"HIGH"},{"path":"borrower.properties.total_debt","confidence_min":"HIGH"}]}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

-- 5. p0.structured_tranche
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('p0.structured_tranche', 'p0.structured_tranche', 'P0 Input Set - Structured Tranche', 'p0_input_set', 'global', 1, TRUE,
$rb${"p0_inputs":[{"path":"deal.properties.principal","confidence_min":"VERIFIED"},{"path":"deal.properties.tranche_details","confidence_min":"HIGH"},{"path":"valuation.cashflow_waterfall.primary_case","confidence_min":"HIGH"},{"path":"deal.properties.ltv","confidence_min":"HIGH"},{"path":"deal.properties.irr_downside","confidence_min":"HIGH"},{"path":"collateral.first_lien_value","confidence_min":"HIGH"}]}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

-- 6. p0.distressed_special
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('p0.distressed_special', 'p0.distressed_special', 'P0 Input Set - Distressed Special', 'p0_input_set', 'global', 1, TRUE,
$rb${"p0_inputs":[{"path":"valuation.liquidation.primary_case","confidence_min":"HIGH","eligibility":"adopted_or_external_only"},{"path":"deal.properties.target_price","confidence_min":"HIGH"},{"path":"deal.properties.irr_downside","confidence_min":"HIGH"},{"path":"valuation.merton_kmv.primary_case","confidence_min":"MEDIUM"}]}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

-- 7. p0.equity_linked_credit
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('p0.equity_linked_credit', 'p0.equity_linked_credit', 'P0 Input Set - Equity Linked Credit', 'p0_input_set', 'global', 1, TRUE,
$rb${"p0_inputs":[{"path":"deal.properties.principal","confidence_min":"VERIFIED"},{"path":"deal.properties.coupon","confidence_min":"VERIFIED"},{"path":"deal.properties.conversion_price","confidence_min":"VERIFIED"},{"path":"deal.properties.irr_downside","confidence_min":"HIGH"},{"path":"borrower.properties.ebitda","confidence_min":"HIGH"},{"path":"borrower.properties.total_debt","confidence_min":"HIGH"}]}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

-- 8. gate.direct_lending
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('gate.direct_lending', 'gate.direct_lending', 'Gate Table - Direct Lending', 'gate_table', 'global', 1, TRUE,
$rb${"evaluation":[{"priority":1,"if":"any_p0_uncertain(deal_type='direct_lending')","then":"HOLD","reason":"C-07: P0 미확정"},{"priority":2,"if":"deal.properties.dscr < threshold('dscr_floor','direct_lending')","then":"KILL","reason":"DSCR floor 미달"},{"priority":3,"if":"deal.properties.ltv > threshold('ltv_cap','direct_lending')","then":"KILL","reason":"LTV cap 초과"},{"priority":4,"if":"deal.properties.irr_downside < threshold('irr_hurdle','direct_lending')","then":"HOLD","reason":"IRR hurdle 미달"},{"priority":5,"if":"narrative_gate == 'BROKEN'","then":"KILL"},{"priority":6,"if":"narrative_gate == 'WEAK'","then":"HOLD"},{"priority":7,"if":"aml_alert.status == 'open'","then":"HOLD","reason":"미해소 AML"},{"priority":8,"else":true,"then":"GO"}]}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

-- 9. gate.debt_purchase
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('gate.debt_purchase', 'gate.debt_purchase', 'Gate Table - Debt Purchase', 'gate_table', 'global', 1, TRUE,
$rb${"evaluation":[{"priority":1,"if":"any_p0_uncertain(deal_type='debt_purchase')","then":"HOLD","reason":"C-07: P0 미확정"},{"priority":2,"if":"deal.properties.irr_downside < threshold('irr_hurdle','debt_purchase')","then":"KILL","reason":"IRR hurdle 미달"},{"priority":3,"if":"deal.properties.target_price > valuation.liquidation.primary_case * threshold('discount_floor_factor','debt_purchase')","then":"HOLD","reason":"청산가치 대비 매입가 할인율 부족"},{"priority":4,"if":"narrative_gate == 'BROKEN'","then":"KILL"},{"priority":5,"if":"narrative_gate == 'WEAK'","then":"HOLD"},{"priority":6,"if":"aml_alert.status == 'open'","then":"HOLD"},{"priority":7,"else":true,"then":"GO"}]}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

-- 10. gate.structured_tranche
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('gate.structured_tranche', 'gate.structured_tranche', 'Gate Table - Structured Tranche', 'gate_table', 'global', 1, TRUE,
$rb${"evaluation":[{"priority":1,"if":"any_p0_uncertain(deal_type='structured_tranche')","then":"HOLD","reason":"C-07: P0 미확정"},{"priority":2,"if":"deal.properties.ltv > threshold('ltv_cap','structured_tranche')","then":"KILL","reason":"LTV cap 초과"},{"priority":3,"if":"cashflow_waterfall_result.junior_loss_rate > threshold('junior_loss_tolerance','structured_tranche')","then":"HOLD","reason":"후순위 손실율 임계 초과"},{"priority":4,"if":"deal.properties.irr_downside < threshold('irr_hurdle','structured_tranche')","then":"HOLD","reason":"IRR hurdle 미달"},{"priority":5,"if":"narrative_gate == 'BROKEN'","then":"KILL"},{"priority":6,"if":"narrative_gate == 'WEAK'","then":"HOLD"},{"priority":7,"if":"aml_alert.status == 'open'","then":"HOLD"},{"priority":8,"else":true,"then":"GO"}]}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

-- 11. gate.distressed_special
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('gate.distressed_special', 'gate.distressed_special', 'Gate Table - Distressed Special', 'gate_table', 'global', 1, TRUE,
$rb${"evaluation":[{"priority":1,"if":"any_p0_uncertain(deal_type='distressed_special')","then":"HOLD","reason":"C-07: P0 미확정"},{"priority":2,"if":"deal.properties.irr_downside < threshold('irr_hurdle','distressed_special')","then":"KILL","reason":"IRR hurdle 미달"},{"priority":3,"if":"deal.properties.target_price > valuation.liquidation.primary_case","then":"HOLD","reason":"매입가가 청산가치 초과"},{"priority":4,"if":"narrative_gate == 'BROKEN'","then":"KILL"},{"priority":5,"if":"narrative_gate == 'WEAK'","then":"HOLD"},{"priority":6,"if":"aml_alert.status == 'open'","then":"HOLD"},{"priority":7,"else":true,"then":"GO"}]}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

-- 12. gate.equity_linked_credit
INSERT INTO policy_rule
(rule_key, rule_code, rule_name, rule_kind, scope, version, is_active, rule_body)
VALUES ('gate.equity_linked_credit', 'gate.equity_linked_credit', 'Gate Table - Equity Linked Credit', 'gate_table', 'global', 1, TRUE,
$rb${"evaluation":[{"priority":1,"if":"any_p0_uncertain(deal_type='equity_linked_credit')","then":"HOLD","reason":"C-07: P0 미확정"},{"priority":2,"if":"deal.properties.irr_downside < threshold('irr_hurdle','equity_linked_credit')","then":"HOLD","reason":"IRR hurdle 미달"},{"priority":3,"if":"borrower.properties.ebitda < 0","then":"HOLD","reason":"EBITDA 음수"},{"priority":4,"if":"narrative_gate == 'BROKEN'","then":"KILL"},{"priority":5,"if":"narrative_gate == 'WEAK'","then":"HOLD"},{"priority":6,"if":"aml_alert.status == 'open'","then":"HOLD"},{"priority":7,"else":true,"then":"GO"}]}$rb$::jsonb)
ON CONFLICT (rule_key, version) DO NOTHING;

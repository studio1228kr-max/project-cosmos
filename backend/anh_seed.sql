
INSERT INTO deal_master (deal_code,deal_name,deal_type,stage,source_type,source_replicability,source_note,asset_address,asset_type,borrower,sponsor_owner,current_lender,proposed_lender,maturity_date)
VALUES ('LSK-2026-7003EE','ANH 봉은사로455 신한 선순위 크레딧','SPECIAL_SITUATIONS','LIVE_EXECUTION','INTERNAL_PERSONNEL','LOW','SPC 대표 경로 통한 내부 접촉. 재현 불가 채널.','서울시 강남구 봉은사로 455','COMMERCIAL_RE','ANH로지스틱스','Suntrans International','신한은행','BNK경남은행','2028-12-31')
ON CONFLICT (deal_code) DO NOTHING;

INSERT INTO deal_evidence (deal_master_id,evidence_type,source_system,document_title,verification_status,confidence_level,verified_by,raw_excerpt,distribution_level)
SELECT id,'AUDIT_REPORT','금융감독원 DART','ANH로지스틱스 2024년 감사보고서','VERIFIED','HIGH','MINWOO','임대수익 1,402,000,000원 연간','INTERNAL'
FROM deal_master WHERE deal_code='LSK-2026-7003EE';

INSERT INTO deal_evidence (deal_master_id,evidence_type,source_system,document_title,verification_status,confidence_level,verified_by,raw_excerpt,distribution_level)
SELECT id,'NTS_SEIZURE','강남세무서','강남세무서장 압류 확인 추정','ESTIMATED','MEDIUM','MINWOO','국세청 압류 추정액 17.49억원. 말소 선행 조건.','COUNSEL_ONLY'
FROM deal_master WHERE deal_code='LSK-2026-7003EE';

INSERT INTO deal_evidence (deal_master_id,evidence_type,source_system,document_title,verification_status,confidence_level,verified_by,raw_excerpt,distribution_level)
SELECT id,'LOAN_AGREEMENT','신한은행','신한은행 선순위 담보대출 약정 추정','ESTIMATED','MEDIUM','MINWOO','신한은행 선순위 잔액 약 116.8억원. 취득 목표가 90억.','INTERNAL'
FROM deal_master WHERE deal_code='LSK-2026-7003EE';

INSERT INTO deal_financials (deal_master_id,snapshot_label,is_current,loan_amount,interest_rate,annual_interest,collateral_value_base,collateral_value_source,valuation_confidence,nts_seizure_amount,noi,rent_income,ltv_gross,ltv_net,dscr,debt_yield,evidence_refs,evidence_completeness,data_gate_status)
SELECT id,'base_input',TRUE,115,0.10,11.5,230,'INTERNAL_ESTIMATE','LOW',17.49,14.02,14.02,0.5000,0.5411,1.2191,0.1219,'{}',50.0,'PARTIAL'
FROM deal_master WHERE deal_code='LSK-2026-7003EE';

INSERT INTO risk_scenarios (deal_master_id,scenario_id,financials_id,stressed_noi,stressed_collateral_value,stressed_interest_rate,stressed_ltv_gross,stressed_ltv_net,stressed_dscr,stressed_debt_yield,cash_shortfall,recovery_value,loss_given_default,scenario_gate,breach_vector,gate_weight)
SELECT dm.id,s.scenario_id,df.id,
  14.02*(1-s.noi_haircut),
  230*(1-s.value_haircut),
  0.10+s.rate_shock,
  ROUND(115.0/(230*(1-s.value_haircut)),4),
  ROUND(115.0/((230*(1-s.value_haircut))-17.49),4),
  ROUND((14.02*(1-s.noi_haircut))/(115*(0.10+s.rate_shock)),4),
  ROUND((14.02*(1-s.noi_haircut))/115,4),
  GREATEST(0, 115*(0.10+s.rate_shock)-(14.02*(1-s.noi_haircut))),
  GREATEST(0,((230*(1-s.value_haircut))-17.49)*0.75),
  GREATEST(0,115-GREATEST(0,((230*(1-s.value_haircut))-17.49)*0.75)),
  CASE
    WHEN (14.02*(1-s.noi_haircut))/(115*(0.10+s.rate_shock)) < 0.80 THEN 'REJECT'
    WHEN ROUND(115.0/(230*(1-s.value_haircut)),4) > 0.80 THEN 'REJECT'
    WHEN (14.02*(1-s.noi_haircut))/(115*(0.10+s.rate_shock)) < 1.0
     AND ROUND(115.0/(230*(1-s.value_haircut)),4) > 0.65 THEN 'RESTRUCTURE'
    WHEN (14.02*(1-s.noi_haircut))/(115*(0.10+s.rate_shock)) < 1.0 THEN 'HOLD'
    WHEN ROUND(115.0/(230*(1-s.value_haircut)),4) > 0.65 THEN 'HOLD'
    ELSE 'ADVANCE'
  END,
  '[]',
  s.gate_weight
FROM deal_master dm
JOIN scenario_library s ON TRUE
JOIN deal_financials df ON df.deal_master_id=dm.id AND df.is_current=TRUE
WHERE dm.deal_code='LSK-2026-7003EE'
ON CONFLICT DO NOTHING;

INSERT INTO gate_results (deal_master_id,policy_id,financials_id,data_gate,structural_gate,credit_gate,final_gate,provisional_gate,hold_reasons,required_actions,breach_scenarios,tail_warnings)
SELECT dm.id,'LUSKA_GATE_V0_1',df.id,'PARTIAL','HOLD','HOLD','HOLD','RESTRUCTURE',
'["담보가치 미검증 감정평가서 필요","1순위 담보권 미확인","Combined Downside DSCR 0.89x < 1.0x"]',
'["최근 1년 이내 감정평가서 확인","등기부 현재 상태 확인","이자 Reserve 삽입 검토"]',
'["COMBINED -> RESTRUCTURE: DSCR 0.89x"]',
'["IMF_1997 -> REJECT 정보성","GFC_2008 -> REJECT 정보성","PF_2023 -> REJECT 정보성"]'
FROM deal_master dm
JOIN deal_financials df ON df.deal_master_id=dm.id AND df.is_current=TRUE
WHERE dm.deal_code='LSK-2026-7003EE'
ON CONFLICT DO NOTHING;

INSERT INTO lineage_event (entity_type,entity_id,action,reason,actor)
SELECT 'deal_master',id,'CREATE','ANH Railway 원장화','MINWOO'
FROM deal_master WHERE deal_code='LSK-2026-7003EE';

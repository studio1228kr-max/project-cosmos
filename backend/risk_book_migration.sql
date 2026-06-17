-- COSMOS Risk Book Migration v0.1
CREATE TABLE IF NOT EXISTS deal_master (
    id SERIAL PRIMARY KEY,
    deal_code TEXT UNIQUE NOT NULL,
    deal_name TEXT NOT NULL,
    deal_type TEXT NOT NULL DEFAULT 'PERFORMING_SECURED_CREDIT',
    stage TEXT NOT NULL DEFAULT 'SCREENING',
    source_type TEXT, source_replicability TEXT, source_note TEXT,
    asset_address TEXT, asset_type TEXT, borrower TEXT, sponsor_owner TEXT,
    current_lender TEXT, proposed_lender TEXT, maturity_date DATE,
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS deal_evidence (
    id SERIAL PRIMARY KEY,
    deal_master_id INTEGER REFERENCES deal_master(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL, source_system TEXT, source_url_or_ref TEXT,
    document_title TEXT, captured_at TIMESTAMP DEFAULT NOW(), effective_date DATE,
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
    confidence_level TEXT DEFAULT 'LOW', verified_by TEXT, verified_at TIMESTAMP,
    raw_excerpt TEXT, distribution_level TEXT DEFAULT 'INTERNAL',
    parser_version TEXT, created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS deal_financials (
    id SERIAL PRIMARY KEY,
    deal_master_id INTEGER REFERENCES deal_master(id) ON DELETE CASCADE,
    snapshot_label TEXT DEFAULT 'base_input', is_current BOOLEAN DEFAULT TRUE,
    loan_amount NUMERIC, senior_debt NUMERIC, junior_debt NUMERIC,
    interest_rate NUMERIC, annual_interest NUMERIC,
    collateral_value_low NUMERIC, collateral_value_base NUMERIC, collateral_value_high NUMERIC,
    collateral_value_source TEXT, valuation_confidence TEXT,
    nts_seizure_amount NUMERIC DEFAULT 0, other_liens NUMERIC DEFAULT 0,
    noi NUMERIC, rent_income NUMERIC, vacancy_rate NUMERIC DEFAULT 0,
    capex_reserve NUMERIC DEFAULT 0,
    ltv_gross NUMERIC, ltv_net NUMERIC, dscr NUMERIC, debt_yield NUMERIC, icr NUMERIC,
    evidence_refs JSONB DEFAULT '{}',
    evidence_completeness NUMERIC, data_gate_status TEXT,
    calculated_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS deal_financial_evidence_map (
    id SERIAL PRIMARY KEY,
    financials_id INTEGER REFERENCES deal_financials(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,
    evidence_id INTEGER REFERENCES deal_evidence(id) ON DELETE SET NULL,
    role TEXT DEFAULT 'PRIMARY', confidence_level TEXT DEFAULT 'LOW',
    note TEXT, created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(financials_id, field_name, evidence_id)
);
CREATE TABLE IF NOT EXISTS scenario_library (
    id SERIAL PRIMARY KEY, scenario_id TEXT UNIQUE NOT NULL,
    scenario_name TEXT NOT NULL, scenario_type TEXT NOT NULL,
    category TEXT, severity TEXT DEFAULT 'DOWNSIDE',
    gate_weight TEXT DEFAULT 'MANDATORY',
    noi_haircut NUMERIC DEFAULT 0, value_haircut NUMERIC DEFAULT 0,
    rate_shock NUMERIC DEFAULT 0, vacancy_shock NUMERIC DEFAULT 0,
    capex_shock NUMERIC DEFAULT 0, description TEXT,
    version TEXT DEFAULT 'v1', is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
INSERT INTO scenario_library (scenario_id,scenario_name,scenario_type,category,severity,gate_weight,noi_haircut,value_haircut,rate_shock,description) VALUES
('BASE','기본','PARAMETRIC','BASE','BASE','MANDATORY',0,0,0,'기본 케이스'),
('NOI_MINUS_10','NOI -10%','PARAMETRIC','DOWNSIDE','DOWNSIDE','MANDATORY',0.10,0,0,'NOI 10% 하락'),
('NOI_MINUS_20','NOI -20%','PARAMETRIC','DOWNSIDE','DOWNSIDE','MANDATORY',0.20,0,0,'NOI 20% 하락'),
('RATE_PLUS_100','금리 +100bp','PARAMETRIC','DOWNSIDE','DOWNSIDE','MANDATORY',0,0,0.01,'금리 100bp 상승'),
('VALUE_MINUS_25','담보 -25%','PARAMETRIC','DOWNSIDE','DOWNSIDE','MANDATORY',0,0.25,0,'담보가치 25% 하락'),
('NOI_MINUS_30','NOI -30%','PARAMETRIC','SEVERE','SEVERE','MANDATORY',0.30,0,0,'NOI 30% 하락'),
('RATE_PLUS_200','금리 +200bp','PARAMETRIC','SEVERE','SEVERE','MANDATORY',0,0,0.02,'금리 200bp 상승'),
('COMBINED','Combined Downside','PARAMETRIC','SEVERE','SEVERE','MANDATORY',0.20,0.20,0.01,'NOI-20%+담보-20%+금리+100bp'),
('IMF_1997','IMF 외환위기','HISTORICAL','HISTORICAL','TAIL','INFORMATIONAL',0.30,0.40,0.05,'1997 IMF 수준'),
('GFC_2008','글로벌 금융위기','HISTORICAL','HISTORICAL','TAIL','INFORMATIONAL',0.20,0.30,0.02,'2008 GFC 수준'),
('COVID_2020','코로나 쇼크','HISTORICAL','HISTORICAL','TAIL','INFORMATIONAL',0.15,0.15,-0.005,'2020 코로나 수준'),
('PF_2023','PF 부실 사이클','HISTORICAL','HISTORICAL','TAIL','INFORMATIONAL',0.25,0.30,0.015,'2023 PF 쇼크')
ON CONFLICT (scenario_id) DO NOTHING;
CREATE TABLE IF NOT EXISTS risk_scenarios (
    id SERIAL PRIMARY KEY,
    deal_master_id INTEGER REFERENCES deal_master(id) ON DELETE CASCADE,
    scenario_id TEXT REFERENCES scenario_library(scenario_id),
    financials_id INTEGER REFERENCES deal_financials(id),
    stressed_noi NUMERIC, stressed_collateral_value NUMERIC,
    stressed_interest_rate NUMERIC, stressed_ltv_gross NUMERIC,
    stressed_ltv_net NUMERIC, stressed_dscr NUMERIC, stressed_debt_yield NUMERIC,
    cash_shortfall NUMERIC, recovery_value NUMERIC, loss_given_default NUMERIC,
    scenario_gate TEXT, breach_vector JSONB DEFAULT '[]',
    gate_weight TEXT DEFAULT 'MANDATORY', model_version TEXT DEFAULT 'v1',
    calculated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(deal_master_id, scenario_id, financials_id)
);
CREATE TABLE IF NOT EXISTS gate_policy (
    id SERIAL PRIMARY KEY, policy_id TEXT UNIQUE NOT NULL,
    policy_name TEXT NOT NULL, policy_version TEXT NOT NULL DEFAULT 'v0.1',
    max_ltv_advance NUMERIC DEFAULT 0.60, max_ltv_restructure NUMERIC DEFAULT 0.65,
    min_dscr_advance NUMERIC DEFAULT 1.20, min_dscr_hold NUMERIC DEFAULT 1.00,
    min_debt_yield NUMERIC DEFAULT 0.10,
    require_noi_verified BOOLEAN DEFAULT TRUE,
    require_collateral_verified BOOLEAN DEFAULT TRUE,
    require_senior_lien_verified BOOLEAN DEFAULT TRUE,
    require_takeout_lender BOOLEAN DEFAULT FALSE,
    p0_unknown_forces_hold BOOLEAN DEFAULT TRUE,
    effective_from DATE DEFAULT CURRENT_DATE, effective_to DATE,
    is_current BOOLEAN DEFAULT TRUE, description TEXT,
    created_by TEXT DEFAULT 'MINWOO', created_at TIMESTAMP DEFAULT NOW()
);
INSERT INTO gate_policy (policy_id,policy_name,policy_version,max_ltv_advance,max_ltv_restructure,min_dscr_advance,min_dscr_hold,min_debt_yield,require_noi_verified,require_collateral_verified,require_senior_lien_verified,p0_unknown_forces_hold,description,created_by)
VALUES ('LUSKA_GATE_V0_1','Luska Secured Credit Gate','v0.1',0.60,0.65,1.20,1.00,0.10,TRUE,TRUE,TRUE,TRUE,'Luska Capital 1호 하우스 기준. ANH 딜 기반 캘리브레이션.','MINWOO')
ON CONFLICT (policy_id) DO NOTHING;
CREATE TABLE IF NOT EXISTS gate_results (
    id SERIAL PRIMARY KEY,
    deal_master_id INTEGER REFERENCES deal_master(id) ON DELETE CASCADE,
    policy_id TEXT REFERENCES gate_policy(policy_id),
    financials_id INTEGER REFERENCES deal_financials(id),
    data_gate TEXT, structural_gate TEXT, credit_gate TEXT,
    final_gate TEXT NOT NULL, provisional_gate TEXT,
    hold_reasons JSONB DEFAULT '[]', required_actions JSONB DEFAULT '[]',
    breach_scenarios JSONB DEFAULT '[]', tail_warnings JSONB DEFAULT '[]',
    model_version TEXT DEFAULT 'v1', gate_version TEXT DEFAULT 'v1',
    ic_ready BOOLEAN DEFAULT FALSE, ic_ready_at TIMESTAMP, ic_ready_by TEXT,
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS lineage_event (
    id SERIAL PRIMARY KEY, entity_type TEXT NOT NULL, entity_id INTEGER NOT NULL,
    action TEXT NOT NULL, field_name TEXT,
    value_before JSONB, value_after JSONB, reason TEXT,
    actor TEXT DEFAULT 'SYSTEM', model_version TEXT, policy_version TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dm_deal_code ON deal_master(deal_code);
CREATE INDEX IF NOT EXISTS idx_dm_stage ON deal_master(stage);
CREATE INDEX IF NOT EXISTS idx_de_master ON deal_evidence(deal_master_id);
CREATE INDEX IF NOT EXISTS idx_de_veri ON deal_evidence(verification_status);
CREATE INDEX IF NOT EXISTS idx_df_master ON deal_financials(deal_master_id);
CREATE INDEX IF NOT EXISTS idx_rs_master ON risk_scenarios(deal_master_id);
CREATE INDEX IF NOT EXISTS idx_gr_master ON gate_results(deal_master_id);
CREATE INDEX IF NOT EXISTS idx_gr_final ON gate_results(final_gate);
CREATE INDEX IF NOT EXISTS idx_le_entity ON lineage_event(entity_type, entity_id);

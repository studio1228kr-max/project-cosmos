-- COSMOS IRR Engine Test Seeds
-- deal: LSK-2026-7003EE (deal_master_id 확인 후 교체)
-- 생성일: 2026-06-22
-- 목적: irr_engine v1.1 smoke test
-- 주의: test 데이터, production 딜과 혼용 금지

DO $$
DECLARE
    v_deal_id INTEGER;
BEGIN
    SELECT id INTO v_deal_id FROM deal_master WHERE deal_code = 'LSK-2026-7003EE';

    IF v_deal_id IS NULL THEN
        RAISE EXCEPTION 'deal_code LSK-2026-7003EE not found';
    END IF;

    -- BASE: 현행 구조 (Floating, CD+450bps, Bullet, 3Y)
    INSERT INTO deal_cashflow_assumptions (
        deal_master_id, scenario_label, assumption_version,
        instrument_type, notional_eok, currency,
        rate_type, base_index, spread_bps,
        origination_date, maturity_date,
        amortization_type, interest_payment_frequency_months,
        upfront_fee_bps, day_count_convention
    ) VALUES (
        v_deal_id, 'BASE', 1,
        'CRE_SENIOR', 116.8, 'KRW',
        'FLOATING', 'CD_91', 450,
        '2026-01-15', '2029-01-15',
        'BULLET', 3,
        100, 'ACT/365'
    )
    ON CONFLICT (deal_master_id, scenario_label, assumption_version) DO UPDATE SET
        spread_bps = EXCLUDED.spread_bps,
        notional_eok = EXCLUDED.notional_eok;

    -- DOWNSIDE: 금리 +200bps 스트레스
    INSERT INTO deal_cashflow_assumptions (
        deal_master_id, scenario_label, assumption_version,
        instrument_type, notional_eok, currency,
        rate_type, base_index, spread_bps,
        origination_date, maturity_date,
        amortization_type, interest_payment_frequency_months,
        upfront_fee_bps, day_count_convention
    ) VALUES (
        v_deal_id, 'DOWNSIDE', 1,
        'CRE_SENIOR', 116.8, 'KRW',
        'FLOATING', 'CD_91', 650,
        '2026-01-15', '2029-01-15',
        'BULLET', 3,
        100, 'ACT/365'
    )
    ON CONFLICT (deal_master_id, scenario_label, assumption_version) DO UPDATE SET
        spread_bps = EXCLUDED.spread_bps;

    -- EXTENSION: 1년 연장 옵션 행사 가정
    INSERT INTO deal_cashflow_assumptions (
        deal_master_id, scenario_label, assumption_version,
        instrument_type, notional_eok, currency,
        rate_type, base_index, spread_bps,
        origination_date, maturity_date,
        amortization_type, interest_payment_frequency_months,
        upfront_fee_bps, day_count_convention
    ) VALUES (
        v_deal_id, 'EXTENSION', 1,
        'CRE_SENIOR', 116.8, 'KRW',
        'FLOATING', 'CD_91', 500,
        '2026-01-15', '2030-01-15',
        'BULLET', 3,
        50, 'ACT/365'
    )
    ON CONFLICT (deal_master_id, scenario_label, assumption_version) DO UPDATE SET
        spread_bps = EXCLUDED.spread_bps,
        maturity_date = EXCLUDED.maturity_date;

    RAISE NOTICE 'seed complete — deal_id=%', v_deal_id;
END $$;

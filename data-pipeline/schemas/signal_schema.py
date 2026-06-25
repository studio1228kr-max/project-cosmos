"""Signal Type Taxonomy + 딜타입 자동 분류 규칙."""

# signal_type → 기본 severity
SIGNAL_TYPES = {
    # DART 공시
    'DART_AUDIT_OPINION_CHANGE': 'CRITICAL',
    'DART_GOING_CONCERN':        'CRITICAL',
    'DART_LARGE_LOSS':           'REVIEW',
    'DART_REVENUE_DECLINE':      'WATCH',
    'DART_DEBT_ISSUANCE':        'WATCH',
    'DART_AMENDMENT':            'INFO',
    # 법원 (Phase 2)
    'COURT_REHABILITATION':      'CRITICAL',
    'COURT_BANKRUPTCY':          'FATAL',
    'COURT_AUCTION_START':       'CRITICAL',
    # OnBid (Phase 2)
    'ONBID_NEW_LISTING':         'REVIEW',
    'ONBID_PRICE_DROP':          'WATCH',
    # MOLIT (Phase 2)
    'MOLIT_PRICE_DECLINE':       'WATCH',
}

# 딜타입 자동 분류 규칙 (signal_engine.aggregate 에서 사용)
SIGNAL_TO_DEAL_TYPE = {
    'score_credit_deterioration_high + score_refinancing_pressure_high': 'DIRECT_LENDING',
    'score_collateral_coverage_low + DART_signal':                       'DEBT_PURCHASE',
    'score_enforcement_pathway_high':                                    'DISTRESSED_SPECIAL',
    'score_refinancing_pressure_high + complex_structure':               'STRUCTURED_TRANCHE',
}


def severity_for(signal_type: str) -> str:
    return SIGNAL_TYPES.get(signal_type, 'INFO')

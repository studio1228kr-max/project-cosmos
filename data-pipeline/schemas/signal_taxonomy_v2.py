"""Signal Taxonomy v2 — 딜타입별 severity 분리."""

SIGNAL_TAXONOMY_V2 = {
    # ── DART 기본 공시 ──
    'DART_AUDIT_OPINION_CHANGE': {
        'default': 'CRITICAL',
        'by_deal_type': {
            'DIRECT_LENDING': 'CRITICAL', 'DEBT_PURCHASE': 'CRITICAL',
            'DISTRESSED_SPECIAL': 'REVIEW', 'EQUITY_LINKED_CREDIT': 'CRITICAL',
            'STRUCTURED_TRANCHE': 'CRITICAL',
        },
    },
    'DART_GOING_CONCERN': {
        'default': 'CRITICAL',
        'by_deal_type': {
            'DIRECT_LENDING': 'CRITICAL', 'DEBT_PURCHASE': 'REVIEW',
            'DISTRESSED_SPECIAL': 'WATCH', 'EQUITY_LINKED_CREDIT': 'CRITICAL',
            'STRUCTURED_TRANCHE': 'CRITICAL',
        },
    },
    'DART_DEBT_ISSUANCE': {
        'default': 'WATCH',
        'by_deal_type': {
            'DIRECT_LENDING': 'REVIEW', 'DEBT_PURCHASE': 'WATCH',
            'DISTRESSED_SPECIAL': 'INFO', 'EQUITY_LINKED_CREDIT': 'REVIEW',
            'STRUCTURED_TRANCHE': 'INFO',
        },
    },
    # ── #4 신규 signal_type (부실/디폴트/유동성/지배구조) ──
    'DART_DEFAULT_EVENT': {
        'default': 'FATAL',
        'by_deal_type': {'DISTRESSED_SPECIAL': 'CRITICAL', 'DEBT_PURCHASE': 'CRITICAL'},
        'description': '부도/당좌거래정지/기한이익상실',
    },
    'DART_COURT_REHABILITATION': {'default': 'CRITICAL', 'description': '회생절차'},
    'DART_COURT_BANKRUPTCY': {'default': 'FATAL', 'description': '파산'},
    'DART_FRAUD_EMBEZZLEMENT': {'default': 'CRITICAL', 'description': '횡령·배임'},
    'DART_DEBT_GUARANTEE': {
        'default': 'REVIEW',
        'by_deal_type': {'DIRECT_LENDING': 'REVIEW', 'DEBT_PURCHASE': 'REVIEW'},
        'description': '채무보증/채무인수 — 우발채무',
    },
    'DART_LIQUIDITY_BORROWING': {
        'default': 'REVIEW',
        'by_deal_type': {'DIRECT_LENDING': 'CRITICAL', 'DEBT_PURCHASE': 'REVIEW'},
        'description': '특수관계인 자금차입/금전대여 — 은행 거절 프록시',
    },
    'DART_OWNERSHIP_CHANGE': {'default': 'REVIEW', 'description': '최대주주/경영권 변동'},
    'DART_EQUITY_RAISE': {'default': 'WATCH', 'description': '유상증자 — 자본확충 수요'},
    'DART_LARGE_CONTRACT': {'default': 'WATCH', 'description': '단일판매·공급계약'},
    'DART_SERIOUS_ACCIDENT': {'default': 'REVIEW', 'description': '중대재해 발생'},
    'DART_EQUITY_ACQUISITION': {'default': 'INFO', 'description': '타법인주식 취득/양수도'},
    'DART_LARGE_LOSS': {'default': 'REVIEW', 'description': '대규모 손실/손익구조 변경'},
    'DART_LAWSUIT_FILED': {
        'default': 'WATCH',
        'by_deal_type': {
            'DIRECT_LENDING': 'WATCH', 'DEBT_PURCHASE': 'REVIEW',
            'DISTRESSED_SPECIAL': 'REVIEW', 'EQUITY_LINKED_CREDIT': 'WATCH',
            'STRUCTURED_TRANCHE': 'WATCH',
        },
    },
    # ── Altman Z-score ──
    'DART_Z_SCORE_DISTRESS_ZONE': {'default': 'CRITICAL', 'description': 'Z-score Distress 진입'},
    'DART_Z_SCORE_GREY_ZONE_ENTRY': {'default': 'REVIEW', 'description': 'Z-score Grey Zone 진입'},
    'DART_Z_SCORE_FAST_DETERIORATION': {'default': 'REVIEW', 'description': 'Z-score 분기 -0.5 이상 하락'},
    # ── ICR ──
    'DART_ICR_BELOW_ONE': {'default': 'CRITICAL', 'description': '이자보상배율 1.0 미만'},
    'DART_ICR_3Q_CONSECUTIVE_DROP': {'default': 'REVIEW', 'description': '3분기 연속 ICR 하락'},
    'DART_ICR_AND_OCF_DUAL_BREAK': {'default': 'CRITICAL', 'description': 'ICR<1.0 + OCF 적자'},
    'DART_SHORT_TERM_DEBT_SURGE': {'default': 'REVIEW', 'description': '단기차입금 50%+ 증가'},
    # ── CB/BW Term ──
    'DART_CB_NO_FLOOR_MONTHLY_RESET': {'default': 'CRITICAL', 'description': 'Floor 없음 + 월단위 Refixing'},
    'DART_CB_NO_DOWNSIDE_PROTECTION': {'default': 'CRITICAL', 'description': '조기상환권 없음 + 무담보'},
    'DART_CB_REPEAT_24M': {'default': 'REVIEW', 'description': '24개월 내 3회+ 반복발행'},
    'DART_CB_HIGH_RISK_COMBO': {'default': 'CRITICAL', 'description': 'No Floor + No Put + 반복발행'},
    'DART_USE_OF_PROCEEDS_CHANGED': {'default': 'CRITICAL', 'description': '자금용도 변경'},
    'DART_CONVERSION_PRICE_ADJUSTED': {'default': 'REVIEW', 'description': '전환가액 하향'},
    # ── 법원 State Machine ──
    'COURT_REHAB_STAGE_FILED': {'default': 'CRITICAL'},
    'COURT_REHAB_STAGE_OPENING': {'default': 'CRITICAL'},
    'COURT_REHAB_STAGE_PLAN_FILED': {'default': 'REVIEW'},
    'COURT_REHAB_STAGE_CONFIRMED': {'default': 'WATCH'},
    'COURT_EXECUTION_IMMINENT': {'default': 'CRITICAL'},
    # ── NTS ──
    'NTS_BUSINESS_CLOSED': {'default': 'FATAL'},
    'NTS_BUSINESS_SUSPENDED': {'default': 'CRITICAL'},
    # ── OnBid ──
    'ONBID_RELISTED_MULTIPLE': {'default': 'REVIEW'},
    'ONBID_APPRAISAL_DROP_STEEP': {'default': 'CRITICAL'},
    'ONBID_DEBT_PORTFOLIO_LISTED': {'default': 'CRITICAL'},
    # ── Registry ──
    'REGISTRY_REPEATED_ATTACHMENT': {'default': 'REVIEW'},
    'REGISTRY_MORTGAGE_ENFORCEMENT': {'default': 'CRITICAL'},
    'REGISTRY_PROVISIONAL_SEIZURE': {'default': 'REVIEW'},
}


def get_severity(signal_type: str, deal_type: str = None) -> str:
    """딜타입을 고려한 severity 반환."""
    config = SIGNAL_TAXONOMY_V2.get(signal_type, {})
    if deal_type and 'by_deal_type' in config:
        return config['by_deal_type'].get(deal_type, config.get('default', 'INFO'))
    return config.get('default', 'INFO')

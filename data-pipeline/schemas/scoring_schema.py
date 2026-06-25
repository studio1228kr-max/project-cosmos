"""스코어링 모델 메타 (5개 모델 + urgency/evidence)."""

MODEL_NAMES = [
    'credit_deterioration',   # Oaktree
    'refinancing_pressure',   # Apollo
    'collateral_coverage',    # Lone Star
    'enforcement_pathway',    # Elliott
    'sector_cycle',           # MBK
]

SCORE_COLUMNS = {
    'credit_deterioration': 'score_credit_deterioration',
    'refinancing_pressure': 'score_refinancing_pressure',
    'collateral_coverage':  'score_collateral_coverage',
    'enforcement_pathway':  'score_enforcement_pathway',
    'sector_cycle':         'score_sector_cycle',
}

URGENCY_LEVELS = ['CRITICAL_72H', 'WATCH_2W', 'MONITOR']
EVIDENCE_QUALITY = ['PUBLIC', 'OFFICIAL', 'VENDOR', 'MANUAL', 'UNVERIFIED']
SCORING_VERSION = 'v0_rule'

"""Altman Z-score + 이자보상배율(ICR) 엔진."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional


def _dec(value, places: int) -> Optional[Decimal]:
    """float/int → 지정 scale Decimal (Mythos scale guard 통과용). None 보존."""
    if value is None:
        return None
    return Decimal(str(round(float(value), places)))


@dataclass
class FinancialFeatures:
    entity_id: str
    entity_name: str
    period_end: str
    # Balance sheet
    current_assets: float = 0
    total_assets: float = 0
    retained_earnings: float = 0
    ebit: float = 0
    equity: float = 0
    total_debt: float = 0
    sales: float = 0
    # Income / Cash flow
    interest_expense: float = 0
    operating_cf: float = 0
    short_term_debt: float = 0


class FinancialEngine:

    def calculate_altman_z(self, f: FinancialFeatures) -> dict:
        """Altman Z-score (한국 비상장 SME 수정 버전).
        Z = 0.717·X1 + 0.847·X2 + 3.107·X3 + 0.420·X4 + 0.998·X5
        """
        if f.total_assets == 0:
            return {'z_score': None, 'z_zone': 'UNKNOWN', 'components': {}}

        working_capital = f.current_assets - (f.total_debt - f.short_term_debt)
        x1 = working_capital / f.total_assets
        x2 = f.retained_earnings / f.total_assets
        x3 = f.ebit / f.total_assets
        x4 = f.equity / max(f.total_debt, 1)
        x5 = f.sales / f.total_assets

        z = 0.717 * x1 + 0.847 * x2 + 3.107 * x3 + 0.420 * x4 + 0.998 * x5

        if z < 1.23:
            zone = 'DISTRESS'
        elif z < 2.90:
            zone = 'GREY'
        else:
            zone = 'SAFE'

        return {
            'z_score': round(z, 4),
            'z_zone': zone,
            'components': {'x1': x1, 'x2': x2, 'x3': x3, 'x4': x4, 'x5': x5},
        }

    def calculate_icr(self, f: FinancialFeatures) -> dict:
        """이자보상배율 (EBIT / 이자비용)."""
        if f.interest_expense == 0:
            return {'icr': None, 'status': 'UNKNOWN'}
        icr = f.ebit / f.interest_expense
        if icr < 1.0:
            status = 'CRITICAL'
        elif icr < 2.0:
            status = 'WARNING'
        elif icr < 3.0:
            status = 'WATCH'
        else:
            status = 'NORMAL'
        return {'icr': round(icr, 4), 'status': status}

    def build_ratio_features(self, f: FinancialFeatures) -> dict:
        """FinancialFeatures → entity_financial_features ratio 스키마 dict (Mythos features).

        Altman X1~X5 비율(4 scale) + z_score(4) + icr(4) + 원시금액(2 scale).
        total_assets=0이면 ratio들이 None → Mythos REQUIRED 검증에서 거부(정상).
        """
        z = self.calculate_altman_z(f)
        icr = self.calculate_icr(f)
        comp = z.get("components") or {}
        return {
            "working_capital_ratio":   _dec(comp.get("x1"), 4),
            "retained_earnings_ratio": _dec(comp.get("x2"), 4),
            "ebit_ratio":              _dec(comp.get("x3"), 4),
            "equity_to_debt_ratio":    _dec(comp.get("x4"), 4),
            "sales_ratio":             _dec(comp.get("x5"), 4),
            "z_score":                 _dec(z.get("z_score"), 4),
            "ebit":                    _dec(f.ebit, 2),
            "interest_expense":        _dec(f.interest_expense, 2),
            "icr":                     _dec(icr.get("icr"), 4),
            "ocf":                     _dec(f.operating_cf, 2),
            "short_term_debt":         _dec(f.short_term_debt, 2),
        }

    def detect_signals(self, current: FinancialFeatures, history: List[FinancialFeatures]) -> List[dict]:
        """재무 지표 → 신호 자동 감지."""
        signals = []
        z = self.calculate_altman_z(current)
        icr = self.calculate_icr(current)

        if z['z_zone'] == 'DISTRESS':
            signals.append({'signal_type': 'DART_Z_SCORE_DISTRESS_ZONE', 'severity': 'CRITICAL',
                            'reason_code': 'z_score_distress_zone', 'points': 25, 'detail': f"Z-score: {z['z_score']}"})
        elif z['z_zone'] == 'GREY':
            signals.append({'signal_type': 'DART_Z_SCORE_GREY_ZONE_ENTRY', 'severity': 'REVIEW',
                            'reason_code': 'z_score_grey_zone', 'points': 12, 'detail': f"Z-score: {z['z_score']}"})

        if icr['icr'] is not None and icr['icr'] < 1.0:
            signals.append({'signal_type': 'DART_ICR_BELOW_ONE', 'severity': 'CRITICAL',
                            'reason_code': 'icr_below_one', 'points': 30, 'detail': f"ICR: {icr['icr']}"})

        if len(history) >= 3:
            trend = [self.calculate_icr(h)['icr'] for h in history[-3:]]
            if all(trend[i] is not None and trend[i + 1] is not None and trend[i] > trend[i + 1]
                   for i in range(len(trend) - 1)):
                signals.append({'signal_type': 'DART_ICR_3Q_CONSECUTIVE_DROP', 'severity': 'REVIEW',
                                'reason_code': 'icr_3q_consecutive_drop', 'points': 20, 'detail': f"ICR trend: {trend}"})

        if icr['icr'] is not None and icr['icr'] < 1.0 and current.operating_cf < 0:
            signals.append({'signal_type': 'DART_ICR_AND_OCF_DUAL_BREAK', 'severity': 'CRITICAL',
                            'reason_code': 'icr_ocf_dual_break', 'points': 35,
                            'detail': f"ICR: {icr['icr']}, OCF: {current.operating_cf}"})

        if len(history) >= 1 and history[-1].short_term_debt > 0:
            growth = (current.short_term_debt - history[-1].short_term_debt) / history[-1].short_term_debt
            if growth > 0.5:
                signals.append({'signal_type': 'DART_SHORT_TERM_DEBT_SURGE', 'severity': 'REVIEW',
                                'reason_code': 'short_term_debt_surge', 'points': 15, 'detail': f"YoY 증가: {growth * 100:.1f}%"})

        return signals

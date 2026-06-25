"""signal_engine v0 — 5개 모델 shell (rule-based) + aggregate."""
from __future__ import annotations

from typing import List


class SignalEngine:

    async def score_credit_deterioration(self, signal: dict) -> dict:
        """신용악화 (Oaktree)."""
        score, reasons = 0, []
        st = signal.get('signal_type')
        if st == 'DART_AUDIT_OPINION_CHANGE':
            score += 30; reasons.append({'code': 'audit_opinion_change', 'points': 30})
        if st == 'DART_GOING_CONCERN':
            score += 35; reasons.append({'code': 'going_concern_flag', 'points': 35})
        if st == 'DART_LARGE_LOSS':
            score += 20; reasons.append({'code': 'large_loss_reported', 'points': 20})
        return {'score': min(score, 100), 'reasons': reasons, 'model': 'credit_deterioration', 'version': 'v0_rule'}

    async def score_refinancing_pressure(self, signal: dict) -> dict:
        """리파이낸싱 압력 (Apollo)."""
        score, reasons = 0, []
        if signal.get('signal_type') == 'DART_DEBT_ISSUANCE':
            score += 25; reasons.append({'code': 'new_debt_issuance', 'points': 25})
        return {'score': min(score, 100), 'reasons': reasons, 'model': 'refinancing_pressure', 'version': 'v0_rule'}

    async def score_collateral_coverage(self, signal: dict) -> dict:
        """담보 커버리지 (Lone Star) — MOLIT 연결 전 placeholder."""
        return {'score': 0, 'reasons': [], 'model': 'collateral_coverage', 'version': 'v0_placeholder'}

    async def score_enforcement_pathway(self, signal: dict) -> dict:
        """법적 집행 (Elliott)."""
        score, reasons = 0, []
        if signal.get('signal_type') in ('COURT_REHABILITATION', 'COURT_AUCTION_START'):
            score += 40; reasons.append({'code': 'legal_enforcement_active', 'points': 40})
        return {'score': min(score, 100), 'reasons': reasons, 'model': 'enforcement_pathway', 'version': 'v0_rule'}

    async def score_sector_cycle(self, signal: dict) -> dict:
        """섹터 사이클 (MBK) — 섹터 테이블 연결 전 placeholder."""
        return {'score': 0, 'reasons': [], 'model': 'sector_cycle', 'version': 'v0_placeholder'}

    async def score_all(self, signal: dict) -> List[dict]:
        return [
            await self.score_credit_deterioration(signal),
            await self.score_refinancing_pressure(signal),
            await self.score_collateral_coverage(signal),
            await self.score_enforcement_pathway(signal),
            await self.score_sector_cycle(signal),
        ]

    async def aggregate(self, scores: List[dict]) -> dict:
        """5개 모델 통합 점수 + 딜타입 분류 + Thesis 제안."""
        total = sum(s['score'] for s in scores)
        all_reasons = []
        for s in scores:
            all_reasons.extend(s['reasons'])

        cd = next(s for s in scores if s['model'] == 'credit_deterioration')['score']
        ep = next(s for s in scores if s['model'] == 'enforcement_pathway')['score']

        if ep >= 40:
            deal_type, urgency = 'DISTRESSED_SPECIAL', 'CRITICAL_72H'
            thesis = '법적 집행 경로 확보 — Distressed 진입 검토'
        elif cd >= 30:
            deal_type, urgency = 'DIRECT_LENDING', 'WATCH_2W'
            thesis = '신용악화 조기 진입 — Direct Lending 또는 Debt Purchase 기회'
        else:
            deal_type, urgency, thesis = None, 'MONITOR', None

        return {
            'aggregate_score': min(total, 100),
            'suggested_deal_type': deal_type,
            'urgency': urgency,
            'thesis_suggestion': thesis,
            'reason_codes': all_reasons,
        }

"""CB/BW Term Extraction — Claude API로 발행조건 파싱 + 위험도 판정.

client/모델 호출은 lazy (import-time·키부재 크래시 방지). 실제 호출 시 ANTHROPIC_API_KEY 필요.
"""
from __future__ import annotations

import json
from typing import List, Optional

EXTRACT_MODEL = "claude-sonnet-4-6"

EXTRACT_PROMPT = """아래는 한국 CB(전환사채) 또는 BW(신주인수권부사채) 발행 공시 원문입니다.
다음 항목을 JSON으로 추출하세요. 항목이 없으면 null로 표시하세요.

추출 항목:
- security_type: CB/BW/EB/RCPS 중 하나
- issue_amount: 발행금액 (숫자, 원 단위)
- maturity_date: 만기일 (YYYY-MM-DD)
- coupon_rate: 표면이자율 (숫자, 소수점)
- conversion_price: 전환가액 (숫자, 원 단위)
- refixing_present: Refixing 조항 존재 여부 (true/false)
- refixing_floor: Refixing 하한가 (숫자, 원 단위, 없으면 null)
- refixing_period: Refixing 주기 (monthly/quarterly/semi/annual, 없으면 null)
- early_redemption_right: 조기상환청구권(Put option) 존재 여부 (true/false)
- call_option: 콜옵션 존재 여부 (true/false)
- collateral_present: 담보/보증 존재 여부 (true/false)

JSON만 반환하세요. 설명 없이.

공시 원문:
{text}
"""

_client = None


def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic()
    return _client


class CBTermExtractor:

    def extract(self, raw_text: str, entity_id: str, entity_name: str, source_ref_id: str) -> dict:
        """Claude API로 CB/BW 조건 추출 + 위험도 판정."""
        client = _get_client()
        response = client.messages.create(
            model=EXTRACT_MODEL,
            max_tokens=1000,
            messages=[{'role': 'user', 'content': EXTRACT_PROMPT.format(text=(raw_text or "")[:8000])}],
        )
        try:
            terms = json.loads(response.content[0].text)
        except Exception:
            return {'error': 'parse_failed', 'entity_id': entity_id, 'source_ref_id': source_ref_id}
        return self.judge_risk(terms, entity_id, entity_name, source_ref_id)

    def judge_risk(self, terms: dict, entity_id: str, entity_name: str, source_ref_id: str) -> dict:
        """추출 조건 → 위험도/risk_codes (순수 로직, 단위 테스트 가능)."""
        risk_codes: List[str] = []
        risk_level = 'LOW'

        if terms.get('refixing_present'):
            if not terms.get('refixing_floor'):
                risk_codes.append('no_refixing_floor'); risk_level = 'CRITICAL'
            if terms.get('refixing_period') == 'monthly':
                risk_codes.append('monthly_reset'); risk_level = 'CRITICAL'

        if not terms.get('early_redemption_right'):
            risk_codes.append('no_put_option')
            if risk_level != 'CRITICAL':
                risk_level = 'HIGH'

        if not terms.get('collateral_present'):
            risk_codes.append('no_collateral')
            if risk_level == 'LOW':
                risk_level = 'MEDIUM'

        if 'no_refixing_floor' in risk_codes and 'no_put_option' in risk_codes:
            risk_codes.append('high_risk_combo'); risk_level = 'CRITICAL'

        return {
            **terms,
            'entity_id': entity_id, 'entity_name': entity_name, 'source_ref_id': source_ref_id,
            'risk_level': risk_level, 'risk_codes': risk_codes,
        }

    def to_signals(self, extraction: dict) -> List[dict]:
        """추출 결과 → 신호 변환."""
        signals = []
        codes = extraction.get('risk_codes', [])

        if 'high_risk_combo' in codes:
            signals.append({'signal_type': 'DART_CB_HIGH_RISK_COMBO', 'severity': 'CRITICAL',
                            'reason_code': 'cb_high_risk_combo', 'points': 35})
        elif 'no_refixing_floor' in codes and 'monthly_reset' in codes:
            signals.append({'signal_type': 'DART_CB_NO_FLOOR_MONTHLY_RESET', 'severity': 'CRITICAL',
                            'reason_code': 'cb_no_floor_monthly_reset', 'points': 35})
        if 'no_put_option' in codes and 'no_collateral' in codes:
            signals.append({'signal_type': 'DART_CB_NO_DOWNSIDE_PROTECTION', 'severity': 'CRITICAL',
                            'reason_code': 'cb_no_downside_protection', 'points': 30})

        return signals

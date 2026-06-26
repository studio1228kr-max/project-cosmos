"""DART 공시 → NormalizedSignal 정규화 + signal_type 분류."""
from __future__ import annotations

from typing import Optional

from schemas.signal_schema import severity_for
from schemas.source_event_schema import NormalizedSignal, RawEvent

# 노이즈 공시 (이 키워드가 있으면 신호 아님 — 키워드 매칭 전에 먼저 차단)
EXCLUDE_KEYWORDS = [
    "기업설명회", "주주총회", "주주명부", "사외이사", "지속가능", "기타시장안내",
    "수익증권", "재간접", "집합투자", "특정증권등소유상황", "대량보유",
]

# 공시명 키워드 → signal_type (우선순위 순, 위에서부터 첫 매칭)
REPORT_TO_SIGNAL = [
    # 부실/디폴트 (최우선)
    ("감사보고서", "DART_AUDIT_OPINION_CHANGE"),
    ("감사의견", "DART_AUDIT_OPINION_CHANGE"),
    ("의견거절", "DART_AUDIT_OPINION_CHANGE"),
    ("계속기업", "DART_GOING_CONCERN"),
    ("자본잠식", "DART_GOING_CONCERN"),
    ("부도", "DART_DEFAULT_EVENT"),
    ("당좌거래정지", "DART_DEFAULT_EVENT"),
    ("기한이익상실", "DART_DEFAULT_EVENT"),
    ("회생절차", "DART_COURT_REHABILITATION"),
    ("파산", "DART_COURT_BANKRUPTCY"),
    ("횡령", "DART_FRAUD_EMBEZZLEMENT"),
    ("배임", "DART_FRAUD_EMBEZZLEMENT"),
    # 우발채무/유동성
    ("채무보증", "DART_DEBT_GUARANTEE"),
    ("채무인수", "DART_DEBT_GUARANTEE"),
    ("자금차입", "DART_LIQUIDITY_BORROWING"),
    ("금전대여", "DART_LIQUIDITY_BORROWING"),
    ("유상증자", "DART_EQUITY_RAISE"),
    ("사채", "DART_DEBT_ISSUANCE"),
    ("기업어음", "DART_DEBT_ISSUANCE"),
    ("CP", "DART_DEBT_ISSUANCE"),
    # 사업/지배구조
    ("단일판매", "DART_LARGE_CONTRACT"),
    ("공급계약", "DART_LARGE_CONTRACT"),
    ("최대주주변경", "DART_OWNERSHIP_CHANGE"),
    ("최대주주등소유주식변동", "DART_OWNERSHIP_CHANGE"),
    ("경영권", "DART_OWNERSHIP_CHANGE"),
    ("타법인주식", "DART_EQUITY_ACQUISITION"),
    ("주식양수도", "DART_EQUITY_ACQUISITION"),
    ("중대재해", "DART_SERIOUS_ACCIDENT"),
    ("소송", "DART_LAWSUIT_FILED"),
    ("제소", "DART_LAWSUIT_FILED"),
    ("손실", "DART_LARGE_LOSS"),
    ("손익구조", "DART_LARGE_LOSS"),
    ("정정", "DART_AMENDMENT"),
]


def classify_signal_type(report_nm: str) -> Optional[str]:
    nm = report_nm or ""
    # 노이즈 선차단 → 그 다음 키워드 매칭
    if any(x in nm for x in EXCLUDE_KEYWORDS):
        return None
    for kw, st in REPORT_TO_SIGNAL:
        if kw in nm:
            return st
    return None


def normalize_dart(event: RawEvent) -> Optional[NormalizedSignal]:
    signal_type = classify_signal_type(event.raw_content or event.source_ref_id or "")
    if not signal_type:
        return None
    return NormalizedSignal(
        source=event.source,
        entity_name=event.entity_name,
        entity_id=event.entity_id,
        signal_type=signal_type,
        signal_subtype=None,
        normalized_summary=(event.raw_content or "")[:300],
        severity=severity_for(signal_type),
        confidence=0.7,
        evidence_quality="PUBLIC",
        observed_at=event.observed_at,
    )

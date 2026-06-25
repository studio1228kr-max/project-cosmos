"""DART 공시 → NormalizedSignal 정규화 + signal_type 분류."""
from __future__ import annotations

from typing import Optional

from schemas.signal_schema import severity_for
from schemas.source_event_schema import NormalizedSignal, RawEvent

# 공시명 키워드 → signal_type
REPORT_TO_SIGNAL = [
    ("감사의견", "DART_AUDIT_OPINION_CHANGE"),
    ("의견거절", "DART_AUDIT_OPINION_CHANGE"),
    ("계속기업", "DART_GOING_CONCERN"),
    ("자본잠식", "DART_GOING_CONCERN"),
    ("손실", "DART_LARGE_LOSS"),
    ("매출", "DART_REVENUE_DECLINE"),
    ("사채", "DART_DEBT_ISSUANCE"),
    ("CP", "DART_DEBT_ISSUANCE"),
    ("기업어음", "DART_DEBT_ISSUANCE"),
    ("정정", "DART_AMENDMENT"),
]


def classify_signal_type(report_nm: str) -> Optional[str]:
    for kw, st in REPORT_TO_SIGNAL:
        if kw in (report_nm or ""):
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

"""Intake guardrail — scan 결과를 받아 채택/거부 판정.

원본 dart_scanner(별도 guardrail 코드)가 레포에 없어, 스펙 §5의 contract
(hits에 intake_status, result에 intake_summary, 거부 사유 guardrail_rejections 저장)을
충족하는 신규 모듈로 작성. RawEvent 단위로 평가.
"""
from __future__ import annotations

import db

# 거부 키워드 (명백 노이즈)
NOISE_KEYWORDS = ["기재정정", "단순참고", "정정신고(첨부정정)"]


def evaluate(event) -> dict:
    """RawEvent → {'intake_status': 'ACCEPT'|'REJECT', 'reason': str|None}."""
    if not event.entity_name or not event.entity_name.strip():
        return {"intake_status": "REJECT", "reason": "entity_name 없음"}
    content = (event.raw_content or "") + " " + (event.source_ref_id or "")
    for kw in NOISE_KEYWORDS:
        if kw in content:
            return {"intake_status": "REJECT", "reason": f"노이즈 키워드: {kw}"}
    return {"intake_status": "ACCEPT", "reason": None}


def record_rejection(dedupe_key: str, entity_name: str, reason: str, scanner: str) -> None:
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO guardrail_rejections (dedupe_key, entity_name, reason, scanner) VALUES (%s,%s,%s,%s)",
        (dedupe_key, entity_name, reason, scanner),
    )
    conn.commit()
    cur.close()
    conn.close()

"""Morning Brief — 매일 새벽 4시(KST) 자동 실행.

오늘의 CRITICAL/WATCH/MONITOR 상위 신호를 Signal Room 카드로 집계하고,
Claude API로 운용역용 모닝 브리핑 텍스트를 생성해 COSMOS /api/brief/today 로 전달한다.

스케줄러 연결은 main._brief_loop (worker 백그라운드). 1회 수동 실행은 `python main.py brief`.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

import httpx

import db

KST = timezone(timedelta(hours=9))
COSMOS_INTERNAL_URL = os.getenv("COSMOS_INTERNAL_URL", "")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")
# 코드베이스 LLM 컨벤션(claude-sonnet-4-6)을 따른다. opus 전환은 BRIEF_MODEL 환경변수로.
BRIEF_MODEL = os.getenv("BRIEF_MODEL", "claude-sonnet-4-6")

# (urgency, 카드 라벨, 카드 상한)
_URGENCY_TIERS = (
    ("CRITICAL_72H", "CRITICAL", 5),
    ("WATCH_2W", "WATCH", 10),
    ("MONITOR", "MONITOR", 5),
)

_BRIEF_PROMPT = """당신은 사모 크레딧 운용사 COSMOS의 리스크 애널리스트입니다.
아래는 오늘 자동 수집·채점된 신호 카드입니다. 운용역이 출근 직후 2분 안에 읽을 수 있는
'모닝 브리핑'을 한국어로 작성하세요.

[작성 규칙]
- 맨 위 1~2문장으로 오늘의 핵심 요약(가장 시급한 건 중심).
- 이어서 CRITICAL(72시간) → WATCH(2주) → MONITOR 순으로 정리.
- 각 신호는 "기업명 — 제안딜유형 (스코어): 한 줄 코멘트" 형식.
- 근거가 약하면 단정하지 말 것. 카드에 없는 사실을 지어내지 말 것.
- 전체 400~900자. 인사말·맺음말 없이 바로 본문만.

[오늘 통계]
{stats}

[신호 카드(JSON)]
{cards}
"""

_client = None


def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic()
    return _client


def _signals_by_urgency(urgency: str, limit: int) -> list[dict]:
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, entity_name, entity_id, aggregate_score, suggested_deal_type,
               urgency, thesis_suggestion, reason_codes
        FROM scored_signals WHERE urgency = %s
        ORDER BY aggregate_score DESC LIMIT %s
        """,
        (urgency, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def _count_new_signals(hours: int) -> int:
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) c FROM scored_signals WHERE scored_at >= NOW() - (%s || ' hours')::interval",
        (hours,),
    )
    n = cur.fetchone()["c"]
    cur.close()
    conn.close()
    return n


def _to_card(row: dict, tier: str) -> dict:
    """scored_signals 행 → Signal Room 카드."""
    return {
        "tier": tier,
        "signal_id": row["id"],
        "entity_name": row["entity_name"],
        "entity_id": row["entity_id"],
        "aggregate_score": row["aggregate_score"],
        "suggested_deal_type": row["suggested_deal_type"],
        "urgency": row["urgency"],
        "thesis": row["thesis_suggestion"],
        "reason_codes": row.get("reason_codes") or [],
    }


def _fallback_text(cards: list[dict]) -> str:
    """Claude 호출 실패/무가용 시 템플릿 브리핑(파이프라인은 멈추지 않는다)."""
    if not cards:
        return "오늘 새로 채점된 주요 신호가 없습니다."
    lines = ["[자동 생성 — 요약 모델 미가용]"]
    for c in cards:
        deal = c["suggested_deal_type"] or "미분류"
        lines.append(f"· [{c['tier']}] {c['entity_name']} — {deal} ({c['aggregate_score']})")
    return "\n".join(lines)


def _generate_brief_text(cards: list[dict], stats: dict) -> str:
    """Claude API로 모닝 브리핑 텍스트 생성. 실패 시 템플릿 폴백."""
    if not cards:
        return "오늘 새로 채점된 주요 신호가 없습니다."
    if not os.getenv("ANTHROPIC_API_KEY"):
        return _fallback_text(cards)
    try:
        client = _get_client()
        prompt = _BRIEF_PROMPT.format(
            stats=json.dumps(stats, ensure_ascii=False),
            cards=json.dumps(cards, ensure_ascii=False, default=str),
        )
        resp = client.messages.create(
            model=BRIEF_MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (resp.content[0].text or "").strip()
        return text or _fallback_text(cards)
    except Exception as e:
        print(json.dumps({"brief_llm_error": str(e)}, ensure_ascii=False))
        return _fallback_text(cards)


def _save_brief(brief: dict) -> None:
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO morning_brief_runs (run_date, top_signals, stats, brief_text) VALUES (%s,%s,%s,%s)",
        (
            brief["date"],
            json.dumps(brief["cards"], ensure_ascii=False, default=str),
            json.dumps(brief["stats"], ensure_ascii=False),
            brief["brief_text"],
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


async def _push_to_cosmos(brief: dict) -> None:
    if not COSMOS_INTERNAL_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                f"{COSMOS_INTERNAL_URL}/api/brief/today",
                json=brief,
                headers={"X-Internal-Key": INTERNAL_API_KEY},
            )
    except Exception as e:
        print(json.dumps({"brief_push_error": str(e)}, ensure_ascii=False))


async def generate_morning_brief() -> dict:
    db.ensure_schema()

    cards: list[dict] = []
    counts: dict[str, int] = {}
    for urgency, label, limit in _URGENCY_TIERS:
        rows = await asyncio.to_thread(_signals_by_urgency, urgency, limit)
        counts[label.lower() + "_count"] = len(rows)
        cards.extend(_to_card(r, label) for r in rows)

    new_24h = await asyncio.to_thread(_count_new_signals, 24)
    stats = {**counts, "new_signals_24h": new_24h, "total_cards": len(cards)}

    brief_text = await asyncio.to_thread(_generate_brief_text, cards, stats)

    brief = {
        "date": datetime.now(KST).date().isoformat(),
        "model": BRIEF_MODEL,
        "brief_text": brief_text,
        "cards": cards,
        "stats": stats,
        **counts,
    }

    await asyncio.to_thread(_save_brief, brief)
    await _push_to_cosmos(brief)
    return brief

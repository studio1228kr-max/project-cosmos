"""Morning Brief — 상위 신호 랭킹 집계 (Railway cron: KST 05:50)."""
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


def _signals_by_urgency(urgency: str, limit: int):
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, entity_name, entity_id, aggregate_score, suggested_deal_type,
               urgency, thesis_suggestion
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


def _save_brief(brief: dict) -> None:
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO morning_brief_runs (run_date, top_signals, stats) VALUES (%s,%s,%s)",
        (brief["date"], json.dumps(brief["top_signals"], ensure_ascii=False, default=str),
         json.dumps(brief["stats"], ensure_ascii=False)),
    )
    conn.commit()
    cur.close()
    conn.close()


async def generate_morning_brief() -> dict:
    db.ensure_schema()
    top_critical = await asyncio.to_thread(_signals_by_urgency, "CRITICAL_72H", 5)
    top_watch = await asyncio.to_thread(_signals_by_urgency, "WATCH_2W", 10)
    new_24h = await asyncio.to_thread(_count_new_signals, 24)

    brief = {
        "date": datetime.now(KST).date().isoformat(),
        "critical_count": len(top_critical),
        "watch_count": len(top_watch),
        "top_signals": top_critical + top_watch,
        "stats": {"new_signals_24h": new_24h},
    }
    await asyncio.to_thread(_save_brief, brief)

    if COSMOS_INTERNAL_URL:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{COSMOS_INTERNAL_URL}/api/signals/brief",
                    json=brief, headers={"X-Internal-Key": INTERNAL_API_KEY},
                )
        except Exception:
            pass
    return brief

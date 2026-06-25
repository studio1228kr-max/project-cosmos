"""data-pipeline 오케스트레이터.

modes:
  worker  : scan 1회 → Redis consume 루프 (scored → COSMOS push)  [default]
  scan    : DART scan 1회
  consume : Redis consume 루프만
  brief   : Morning Brief 1회
  initdb  : schema.sql 적용
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

import httpx

import db
from engines.signal_engine import SignalEngine
from scanners.dart_scanner import DartScanner
from streams.redis_streams import consume_signals

COSMOS_INTERNAL_URL = os.getenv("COSMOS_INTERNAL_URL", "")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

engine = SignalEngine()


async def push_to_cosmos(scored_signal: dict) -> None:
    if not COSMOS_INTERNAL_URL:
        return
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            f"{COSMOS_INTERNAL_URL}/api/signals/ingest",
            json=scored_signal,
            headers={"X-Internal-Key": INTERNAL_API_KEY},
        )


async def score_handler(signal_data: dict) -> None:
    """Redis normalized 신호 1건 → 5개 모델 스코어 → DB 저장 → COSMOS push."""
    scores_list = await engine.score_all(signal_data)
    agg = await engine.aggregate(scores_list)
    scores = {s['model']: s['score'] for s in scores_list}

    normalized_id = signal_data.get('normalized_id')
    sid = await asyncio.to_thread(
        db.save_scored, normalized_id,
        signal_data.get('entity_name'), signal_data.get('entity_id'), scores, agg,
    )
    await push_to_cosmos({
        "id": sid,
        "entity_name": signal_data.get('entity_name'),
        "entity_id": signal_data.get('entity_id'),
        "signal_type": signal_data.get('signal_type'),
        "aggregate_score": agg['aggregate_score'],
        "suggested_deal_type": agg['suggested_deal_type'],
        "urgency": agg['urgency'],
        "thesis_suggestion": agg['thesis_suggestion'],
        "reason_codes": agg['reason_codes'],
    })


async def run_scan() -> dict:
    db.ensure_schema()
    result = await DartScanner().run()
    summary = {k: v for k, v in result.items() if k != 'hits'}
    print(json.dumps(summary, ensure_ascii=False))
    return result


async def run_consume() -> None:
    await consume_signals(score_handler)


async def run_worker() -> None:
    db.ensure_schema()
    await run_scan()
    await run_consume()


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "worker"
    if mode == "initdb":
        db.ensure_schema()
        print("schema applied")
    elif mode == "scan":
        asyncio.run(run_scan())
    elif mode == "consume":
        asyncio.run(run_consume())
    elif mode == "brief":
        from brief.morning_brief import generate_morning_brief
        print(json.dumps(asyncio.run(generate_morning_brief()), ensure_ascii=False, default=str))
    else:
        asyncio.run(run_worker())


if __name__ == "__main__":
    main()

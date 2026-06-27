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
from datetime import datetime, timedelta, timezone

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
    if sid is None:
        return  # 이미 채점됨(멱등) → 재push 생략
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
    # #6: ECOS 매크로 지표 수집 (best-effort, sector_cycle 입력). upsert라 일 1회 무해.
    try:
        from scanners.ecos_scanner import EcosScanner
        result["ecos"] = await EcosScanner().scan()
    except Exception as e:
        print(json.dumps({"ecos_error": str(e)}, ensure_ascii=False))
    # #8: MOLIT 담보 실거래 → LTV (담보주소 있는 딜)
    try:
        from scanners.molit_scanner import MolitScanner
        result["molit"] = await MolitScanner().scan_all_deals()
    except Exception as e:
        print(json.dumps({"molit_error": str(e)}, ensure_ascii=False))
    summary = {k: v for k, v in result.items() if k != 'hits'}
    print(json.dumps(summary, ensure_ascii=False))
    return result


async def run_consume() -> None:
    await consume_signals(score_handler)


# 정기수집: KST 지정 시각 (스펙 §5: 05:50, 17:50). Railway cron을 쓰면 false로 끄기.
KST = timezone(timedelta(hours=9))
SCAN_TIMES_KST = os.getenv("SCAN_TIMES_KST", "05:50,17:50")
SCAN_SCHEDULE_ENABLED = os.getenv("SCAN_SCHEDULE_ENABLED", "true").lower() != "false"


def _seconds_until_next_scan() -> float:
    now = datetime.now(KST)
    cands = []
    for t in SCAN_TIMES_KST.split(","):
        t = t.strip()
        if not t:
            continue
        hh, mm = t.split(":")
        c = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if c <= now:
            c += timedelta(days=1)
        cands.append(c)
    if not cands:
        return 6 * 3600
    return max(1.0, (min(cands) - now).total_seconds())


async def _scan_loop() -> None:
    """부팅 시 1회 → 이후 SCAN_TIMES_KST 지정 시각마다."""
    await run_scan()
    while True:
        await asyncio.sleep(_seconds_until_next_scan())
        try:
            await run_scan()
        except Exception as e:
            print(json.dumps({"scan_error": str(e)}, ensure_ascii=False))


async def run_worker() -> None:
    db.ensure_schema()
    # consume 상시 + (옵션) 지정 시각 scan. Railway cron 사용 시 SCAN_SCHEDULE_ENABLED=false
    if SCAN_SCHEDULE_ENABLED:
        await asyncio.gather(run_consume(), _scan_loop())
    else:
        await run_consume()


def _serve() -> None:
    """HERMES API(uvicorn) 구동 — api:app startup이 워커를 백그라운드로 띄움.
    Railway 시작명령이 'python main.py worker'로 고정돼 있어도 HTTP 서버가 뜨도록."""
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api:app", host="::", port=port)


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
    elif mode == "worker_only":
        asyncio.run(run_worker())
    else:
        # 기본/worker: HERMES API 서버 구동(+startup 백그라운드 워커)
        _serve()


if __name__ == "__main__":
    main()

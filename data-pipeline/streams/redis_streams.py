"""Redis Streams 파이프라인 — publish/consume + dead-letter."""
from __future__ import annotations

import asyncio
import json
import os

import redis.asyncio as aioredis

STREAMS = {
    'raw':        'signals.raw',
    'normalized': 'signals.normalized',
    'scored':     'signals.scored',
}
CONSUMER_GROUP = 'signal_engine_group'
DEAD_LETTER = 'signals.dead_letter'
MAX_RETRY = 3

_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(os.environ["REDIS_URL"])
    return _redis


async def publish_signal(signal) -> str:
    r = await get_redis()
    msg_id = await r.xadd(
        STREAMS['normalized'],
        {
            'data': json.dumps(signal.__dict__, default=str, ensure_ascii=False),
            'idempotency_key': f"{signal.source}:{signal.raw_event_id}",
        },
    )
    return msg_id


async def consume_signals(handler_fn, batch_size: int = 10):
    r = await get_redis()
    try:
        # id='0': 그룹 생성 전 publish된 메시지도 처음부터 소비 (scan→consume 순서 안전)
        await r.xgroup_create(STREAMS['normalized'], CONSUMER_GROUP, id='0', mkstream=True)
    except Exception:
        pass  # 이미 존재
    # 기존에 '$'로 만들어졌던 그룹도 처음부터 재전달 (소비는 멱등이라 안전)
    try:
        await r.xgroup_setid(STREAMS['normalized'], CONSUMER_GROUP, id='0')
    except Exception:
        pass

    while True:
        try:
            messages = await r.xreadgroup(
                CONSUMER_GROUP, 'worker-1',
                {STREAMS['normalized']: '>'},
                count=batch_size, block=5000,
            )
        except Exception:
            await asyncio.sleep(2)
            continue
        for _stream, msgs in (messages or []):
            for msg_id, data in msgs:
                try:
                    signal_data = json.loads(data[b'data'])
                    await handler_fn(signal_data)
                    await r.xack(STREAMS['normalized'], CONSUMER_GROUP, msg_id)
                except Exception as e:
                    retry_count = int(data.get(b'retry_count', 0))
                    if retry_count >= MAX_RETRY:
                        await r.xadd(DEAD_LETTER, {'data': data[b'data'], 'error': str(e)})
                        await r.xack(STREAMS['normalized'], CONSUMER_GROUP, msg_id)
                    else:
                        await r.xadd(
                            STREAMS['normalized'],
                            {'data': data[b'data'], 'retry_count': retry_count + 1},
                        )

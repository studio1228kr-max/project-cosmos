"""HERMES API (Sprint #9) — facts endpoint + 백그라운드 워커.

data-pipeline는 본래 워커(scan+redis consume)였다. COSMOS가 DART를 직접 호출하던 것을
HERMES 경유로 바꾸기 위해 FastAPI 서버를 추가하고, 기존 워커를 startup 백그라운드 태스크로 구동.

  POST /facts/{corp_code}  (X-Internal-Key 인증)  → corp facts(DART 빌드 + DB 캐시)
  GET  /health
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException

import db
import facts_builder

app = FastAPI(title="HERMES data-pipeline API")

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")
RUN_WORKER = os.getenv("RUN_WORKER", "true").lower() != "false"


@app.on_event("startup")
async def _startup():
    if RUN_WORKER:
        # 기존 워커(scan 루프 + redis consume)를 백그라운드로 구동
        async def _worker():
            try:
                from main import run_worker
                await run_worker()
            except Exception as e:
                print(f"[HERMES] worker stopped: {e}")
        asyncio.create_task(_worker())


@app.get("/health")
def health():
    return {"status": "ok", "service": "hermes-data-pipeline"}


@app.post("/facts/{corp_code}")
async def get_facts(corp_code: str, x_internal_key: str = Header(None)):
    """COSMOS sdd_auto가 호출하는 facts API (3계층: COSMOS→HERMES→DART)."""
    if not INTERNAL_API_KEY or x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    # 재무 캐시 존재 여부(cached 플래그용)
    fin_cached = await asyncio.to_thread(_has_financial_cache, corp_code)

    # facts 빌드 (HERMES가 DART 호출) — sdd_auto가 기대하는 flat facts dict
    facts = await asyncio.to_thread(facts_builder.build_facts, corp_code)
    cb_terms = await asyncio.to_thread(db.get_cb_terms, corp_code)
    facts["cb_terms"] = cb_terms
    facts["cached"] = fin_cached
    facts["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return facts


def _has_financial_cache(corp_code: str) -> bool:
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM entity_financial_features WHERE entity_id=%s LIMIT 1", (corp_code,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row is not None

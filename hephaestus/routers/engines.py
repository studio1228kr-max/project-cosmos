"""
routers/engines.py
──────────────────
엔진 실행 API.

GET  /engines              — 등록 엔진 목록
POST /engines/{name}/run   — 엔진 실행
GET  /engines/run-log      — 실행 로그 조회
"""

from __future__ import annotations

from collections import deque

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.config import settings
from core.exceptions import EngineExecutionError, EngineNotFoundError
from core.logging_config import get_logger
from engines.registry import get_engine, list_engines
from schemas.base import EngineRunLog

logger = get_logger("router.engines")
router = APIRouter(prefix="/engines", tags=["engines"])

# 인메모리 런로그 (circular buffer)
_run_log: deque[EngineRunLog] = deque(maxlen=settings.RUN_LOG_MAX_IN_MEMORY)


# ─────────────────────────────────────────────────────────────
# 엔진 목록
# ─────────────────────────────────────────────────────────────

@router.get("", summary="등록된 엔진 목록")
async def get_engines():
    engines = list_engines()
    return {"engines": engines, "count": len(engines)}


# ─────────────────────────────────────────────────────────────
# 엔진 실행
# ─────────────────────────────────────────────────────────────

@router.post("/{engine_name}/run", summary="엔진 실행")
async def run_engine(engine_name: str, body: dict) -> dict:
    """
    범용 엔진 실행.
    body는 엔진별 Input 스키마에 맞는 JSON.

    응답:
      output   — 엔진 출력
      run_log  — 이번 실행 런로그
    """
    try:
        engine = get_engine(engine_name)
    except EngineNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.to_response())

    try:
        inp = engine.input_model.model_validate(body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"입력 검증 실패: {e}")

    try:
        output, log = engine.run(inp)
    except EngineExecutionError as e:
        raise HTTPException(status_code=500, detail=e.to_response())

    _run_log.append(log)

    return {
        "output": output.model_dump(),
        "run_log": log.model_dump(),
    }


# ─────────────────────────────────────────────────────────────
# 런로그 조회
# ─────────────────────────────────────────────────────────────

@router.get("/run-log", summary="엔진 실행 로그 조회")
async def get_run_log(
    engine_name: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    status: str | None = Query(default=None),
):
    logs = list(reversed(list(_run_log)))

    if engine_name:
        logs = [l for l in logs if l.engine_name == engine_name]

    if status:
        logs = [l for l in logs if l.status.value == status.upper()]

    logs = logs[:limit]

    return {
        "total": len(logs),
        "filters": {"engine_name": engine_name, "status": status},
        "logs": [l.model_dump() for l in logs],
    }

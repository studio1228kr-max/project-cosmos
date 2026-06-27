"""
routers/health.py
──────────────────
Railway 헬스체크 + 서비스 상태 엔드포인트.

GET /health  — Railway 헬스체크. 엔진 레지스트리 상태 포함.
GET /ready   — Readiness probe. 엔진 0개면 503.
GET /version — 서비스 버전 정보.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from core.config import settings
from engines.registry import list_engines

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    timestamp: datetime
    engines: list[dict]
    engine_count: int


@router.get("/health", response_model=HealthResponse)
async def health():
    engines = list_engines()
    return HealthResponse(
        status="ok",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        engines=engines,
        engine_count=len(engines),
    )


@router.get("/ready")
async def ready():
    engines = list_engines()
    if not engines:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="엔진 레지스트리 비어있음")
    return {"ready": True, "engine_count": len(engines)}


@router.get("/version")
async def version():
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
    }

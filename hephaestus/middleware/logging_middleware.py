"""
middleware/logging_middleware.py
─────────────────────────────────
모든 HTTP 요청/응답 구조화 로깅.

- request_id 자동 생성 및 contextvars 바인딩
- /health, /ready 는 로그 스팸 방지로 드롭
- 4xx/5xx 는 warning 레벨
- 응답시간 ms 단위 기록
"""

from __future__ import annotations

import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger("hephaestus.http")

_SKIP_PATHS = frozenset({"/health", "/ready"})


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        response: Response | None = None

        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            status_code = response.status_code if response else 500
            path = request.url.path

            # 건너뛸 경로는 '로깅만' 스킵 — finally 안에서 return 하면
            # try의 return response가 덮여 None이 반환되므로 절대 금지.
            if path not in _SKIP_PATHS:
                log_fn = (
                    logger.warning if status_code >= 400 else logger.info
                )
                log_fn(
                    "http_request",
                    method=request.method,
                    path=path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                )

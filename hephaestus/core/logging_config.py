"""
core/logging_config.py
───────────────────────
structlog 기반 구조화 로깅.

환경별 전략:
  development  → 컬러 콘솔 (가독성 우선)
  staging      → JSON (Railway 로그 수집 테스트)
  production   → JSON + 민감 필드 자동 마스킹

보안 규칙:
  - API 키, 토큰, 패스워드 필드 자동 마스킹
  - 스택트레이스는 로그에만, HTTP 응답에는 절대 불포함
  - request_id로 추적, IP는 해시 처리
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

from core.config import settings

# ── 마스킹 대상 키 (룰테이블 — 추가시 여기에만) ──────────────
_SENSITIVE_KEYS = frozenset(
    {
        "password", "passwd", "secret", "token", "api_key",
        "apikey", "authorization", "access_token", "refresh_token",
        "private_key", "client_secret", "x_api_key",
    }
)
_MASK = "***REDACTED***"


def _mask_sensitive(logger: WrappedLogger, method: str, event_dict: EventDict) -> EventDict:
    """로그 이벤트에서 민감 키 자동 마스킹."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = _MASK
    return event_dict


def _hash_ip(logger: WrappedLogger, method: str, event_dict: EventDict) -> EventDict:
    """IP 주소를 SHA256 앞 12자리로 대체 (역추적 불가, 상관관계 분석은 가능)."""
    if "client_ip" in event_dict and event_dict["client_ip"]:
        ip = str(event_dict["client_ip"])
        event_dict["client_ip"] = hashlib.sha256(ip.encode()).hexdigest()[:12]
    return event_dict


def _drop_health_check(logger: WrappedLogger, method: str, event_dict: EventDict) -> EventDict:
    """/health, /ready 요청은 로그 스팸 방지를 위해 INFO 이하 드롭."""
    path = event_dict.get("path", "")
    if path in ("/health", "/ready") and method in ("info", "debug"):
        raise structlog.DropEvent()
    return event_dict


def setup_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        # NOTE: structlog.stdlib.add_logger_name 은 stdlib 로거의 .name 을 읽는데
        # 아래 logger_factory 가 PrintLoggerFactory(=PrintLogger, .name 없음)라
        # 호출 시 AttributeError 로 모든 로깅 요청이 500 으로 터진다. 그래서 제외.
        # 로거 이름을 남기려면 logger_factory 를 structlog.stdlib.LoggerFactory() 로 교체할 것.
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _mask_sensitive,
        _hash_ip,
        _drop_health_check,
    ]

    if settings.ENVIRONMENT == "development":
        structlog.configure(
            processors=shared_processors
            + [structlog.dev.ConsoleRenderer(colors=True)],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # staging / production → JSON
        structlog.configure(
            processors=shared_processors
            + [
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )

    logging.basicConfig(format="%(message)s", level=log_level)


def get_logger(name: str = "hephaestus") -> structlog.BoundLogger:
    return structlog.get_logger(name)

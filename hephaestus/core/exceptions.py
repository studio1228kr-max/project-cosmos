"""
core/exceptions.py
──────────────────
HEPHAESTUS 예외 계층.

설계 원칙:
  - 외부에 내부 구현 절대 노출 금지 (스택트레이스, 파일경로, DB쿼리 등)
  - error_code는 클라이언트가 파싱 가능한 고정 문자열
  - detail은 내부 로그 전용 — HTTP 응답에는 production 환경에서 제거
  - 모든 예외는 HephaestusError 하위 — 핸들러 단일화
"""

from __future__ import annotations

from typing import Any, Optional

from core.config import settings


class HephaestusError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, detail: Optional[Any] = None):
        self.message = message
        self.detail = detail if settings.ENVIRONMENT != "production" else None
        super().__init__(message)

    def to_response(self) -> dict:
        resp = {"error": self.error_code, "message": self.message}
        if self.detail is not None:
            resp["detail"] = self.detail
        return resp


class EngineNotFoundError(HephaestusError):
    status_code = 404
    error_code = "ENGINE_NOT_FOUND"


class EngineValidationError(HephaestusError):
    status_code = 422
    error_code = "ENGINE_VALIDATION_ERROR"


class AsOfRangeError(HephaestusError):
    status_code = 200
    error_code = "AS_OF_OUT_OF_RANGE_COERCED"


class ConfidenceDegradationError(HephaestusError):
    status_code = 422
    error_code = "CONFIDENCE_DEGRADATION_FORCED_HOLD"


class UnauthorizedError(HephaestusError):
    status_code = 401
    error_code = "UNAUTHORIZED"

    def __init__(self):
        super().__init__("인증 실패")


class ForbiddenError(HephaestusError):
    status_code = 403
    error_code = "FORBIDDEN"

    def __init__(self):
        super().__init__("접근 권한 없음")


class RateLimitError(HephaestusError):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"


class EngineExecutionError(HephaestusError):
    status_code = 500
    error_code = "ENGINE_EXECUTION_ERROR"


class NumericalInstabilityError(HephaestusError):
    status_code = 500
    error_code = "NUMERICAL_INSTABILITY"


class EngineRegistryError(HephaestusError):
    status_code = 500
    error_code = "ENGINE_REGISTRY_ERROR"


class UpstreamServiceError(HephaestusError):
    status_code = 502
    error_code = "UPSTREAM_SERVICE_ERROR"

    def __init__(self, service: str, detail: Optional[Any] = None):
        super().__init__("내부 서비스 오류", detail=f"upstream={service}: {detail}")

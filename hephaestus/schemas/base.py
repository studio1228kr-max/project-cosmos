"""
schemas/base.py
───────────────
HEPHAESTUS 전 엔진 공통 스키마.

COSMOS Canon 적용:
  C-01  IRR·스코어는 항상 Downside 먼저
  C-04  미검증 입력 → UNVERIFIED 태깅 → 전체 신뢰도 하락
  C-07  P0 미지 → HOLD 강제
  C-11  deterioration → 4개 상태 전이
  C-12  게이트 로직은 룰테이블 하드코딩. AI 프롬프트 불가.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class ConfidenceLevel(str, Enum):
    HIGH       = "HIGH"
    MEDIUM     = "MEDIUM"
    LOW        = "LOW"
    UNVERIFIED = "UNVERIFIED"


class WarningCode(str, Enum):
    # 입력
    UNVERIFIED_INPUT            = "UNVERIFIED_INPUT"
    MISSING_OPTIONAL_FIELD      = "MISSING_OPTIONAL_FIELD"
    AS_OF_OUT_OF_RANGE_COERCED  = "AS_OF_OUT_OF_RANGE_COERCED"
    # 신뢰도
    LOW_CONFIDENCE_SOURCE       = "LOW_CONFIDENCE_SOURCE"
    CONFIDENCE_DOWNGRADED       = "CONFIDENCE_DOWNGRADED"
    # 게이트
    P0_UNKNOWN_FORCED_HOLD      = "P0_UNKNOWN_FORCED_HOLD"
    DOWNSIDE_CASE_FORCED        = "DOWNSIDE_CASE_FORCED"
    # 엔진
    ENGINE_FALLBACK_USED        = "ENGINE_FALLBACK_USED"
    NUMERICAL_INSTABILITY       = "NUMERICAL_INSTABILITY"
    # 행동리스크
    BEHAVIORAL_SCORE_CAPPED     = "BEHAVIORAL_SCORE_CAPPED"
    HYSTERESIS_APPLIED          = "HYSTERESIS_APPLIED"
    ZERO_CONFIDENCE_SUPPRESSED  = "ZERO_CONFIDENCE_SUPPRESSED"


class WarningSeverity(str, Enum):
    INFO     = "INFO"
    CAUTION  = "CAUTION"
    CRITICAL = "CRITICAL"


class EngineGate(str, Enum):
    """
    C-07 / C-11 게이트 상태.
    룰테이블 기반. AI 프롬프트로 변경 불가 (C-12).
    """
    PASS          = "PASS"
    HOLD          = "HOLD"
    MONITOR       = "MONITOR"
    RE_UNDERWRITE = "RE_UNDERWRITE"
    ENFORCE       = "ENFORCE"
    REALIZE       = "REALIZE"


class RunStatus(str, Enum):
    SUCCESS  = "SUCCESS"
    FAILED   = "FAILED"
    FALLBACK = "FALLBACK"


# ─────────────────────────────────────────────────────────────
# Warning
# ─────────────────────────────────────────────────────────────

class WarningFlag(BaseModel):
    code: WarningCode
    severity: WarningSeverity
    message: str
    field: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Base Input / Output
# ─────────────────────────────────────────────────────────────

class EngineInput(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    deal_id: Optional[str] = None
    as_of: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    confidence_override: Optional[ConfidenceLevel] = None

    @field_validator("as_of", mode="before")
    @classmethod
    def ensure_timezone_aware(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class EngineOutput(BaseModel):
    request_id: str
    engine_name: str
    engine_version: str
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    as_of: datetime
    duration_ms: float = 0.0
    gate: EngineGate = EngineGate.PASS
    confidence: ConfidenceLevel
    warnings: list[WarningFlag] = []
    metadata: dict[str, Any] = {}

    @property
    def has_critical_warning(self) -> bool:
        return any(w.severity == WarningSeverity.CRITICAL for w in self.warnings)


# ─────────────────────────────────────────────────────────────
# Engine Run Log
# ─────────────────────────────────────────────────────────────

class EngineRunLog(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    engine_name: str
    engine_version: str
    request_id: str
    deal_id: Optional[str] = None
    input_hash: str
    computed_at: datetime
    duration_ms: float
    confidence: ConfidenceLevel
    gate: EngineGate
    warning_count: int
    has_critical_warning: bool
    status: RunStatus
    error: Optional[str] = None

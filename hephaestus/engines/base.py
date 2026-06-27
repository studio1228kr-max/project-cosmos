"""
engines/base.py
───────────────
모든 HEPHAESTUS 엔진의 추상 기반 클래스.

엔진 구현 규칙:
  1. name, version 반드시 정의
  2. _execute() 구현 (비즈니스 로직)
  3. 게이트 로직은 룰테이블 하드코딩 (AI 프롬프트 절대 불가)
  4. 미검증 입력 → _flag_unverified() 호출
  5. as_of 미래값 → _coerce_as_of() 자동 처리
  6. IRR·스코어 출력 → downside 먼저 (C-01)
"""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from core.config import settings
from core.exceptions import EngineExecutionError
from core.logging_config import get_logger
from schemas.base import (
    ConfidenceLevel,
    EngineGate,
    EngineInput,
    EngineOutput,
    EngineRunLog,
    RunStatus,
    WarningCode,
    WarningFlag,
    WarningSeverity,
)

logger = get_logger("engine.base")


class BaseEngine(ABC):
    name: str
    version: str

    # ─────────────────────────────────────────────────────────
    # Public
    # ─────────────────────────────────────────────────────────

    def run(self, inp: EngineInput) -> tuple[EngineOutput, EngineRunLog]:
        start = time.perf_counter()
        warnings: list[WarningFlag] = []
        status = RunStatus.SUCCESS
        error_msg: str | None = None
        output: EngineOutput | None = None

        # as_of 검증
        inp, as_of_warn = self._coerce_as_of(inp)
        if as_of_warn:
            warnings.append(as_of_warn)

        # confidence_override 경고
        if (
            inp.confidence_override == ConfidenceLevel.UNVERIFIED
            and settings.AUTO_DOWNGRADE_UNVERIFIED
        ):
            warnings.append(
                WarningFlag(
                    code=WarningCode.CONFIDENCE_DOWNGRADED,
                    severity=WarningSeverity.CAUTION,
                    message="confidence_override=UNVERIFIED: 전체 출력 신뢰도 하락",
                )
            )

        try:
            output = self._execute(inp)
            output.warnings = warnings + output.warnings
            output.duration_ms = (time.perf_counter() - start) * 1000

            if inp.confidence_override == ConfidenceLevel.UNVERIFIED:
                output.confidence = ConfidenceLevel.UNVERIFIED

            logger.info(
                "engine_run_complete",
                engine=self.name,
                version=self.version,
                request_id=inp.request_id,
                duration_ms=round(output.duration_ms, 2),
                gate=output.gate.value,
                confidence=output.confidence.value,
                warning_count=len(output.warnings),
            )

        except Exception as exc:
            status = RunStatus.FAILED
            error_msg = str(exc)
            logger.error(
                "engine_run_failed",
                engine=self.name,
                request_id=inp.request_id,
                error=error_msg,
            )
            raise EngineExecutionError(
                f"[{self.name}] 엔진 실행 실패: {error_msg}",
                detail=error_msg,
            ) from exc

        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            run_log = EngineRunLog(
                engine_name=self.name,
                engine_version=self.version,
                request_id=inp.request_id,
                deal_id=inp.deal_id,
                input_hash=self._hash_input(inp),
                computed_at=datetime.now(timezone.utc),
                duration_ms=round(duration_ms, 2),
                confidence=output.confidence if output else ConfidenceLevel.UNVERIFIED,
                gate=output.gate if output else EngineGate.HOLD,
                warning_count=len(output.warnings) if output else len(warnings),
                has_critical_warning=output.has_critical_warning if output else False,
                status=status,
                error=error_msg,
            )

        return output, run_log

    # ─────────────────────────────────────────────────────────
    # Abstract
    # ─────────────────────────────────────────────────────────

    @abstractmethod
    def _execute(self, inp: EngineInput) -> EngineOutput:
        ...

    # ─────────────────────────────────────────────────────────
    # 유틸리티
    # ─────────────────────────────────────────────────────────

    def _coerce_as_of(
        self, inp: EngineInput
    ) -> tuple[EngineInput, WarningFlag | None]:
        now = datetime.now(timezone.utc)
        delta = (inp.as_of - now).total_seconds()

        if delta > settings.AS_OF_FUTURE_TOLERANCE_SEC:
            original = inp.as_of.isoformat()
            inp = inp.model_copy(update={"as_of": now})
            return inp, WarningFlag(
                code=WarningCode.AS_OF_OUT_OF_RANGE_COERCED,
                severity=WarningSeverity.CAUTION,
                message=(
                    f"as_of={original} 허용범위 초과 → "
                    f"현재시각({now.isoformat()})으로 coerce"
                ),
                field="as_of",
            )

        return inp, None

    def _flag_unverified(self, field: str, message: str = "") -> WarningFlag:
        return WarningFlag(
            code=WarningCode.UNVERIFIED_INPUT,
            severity=WarningSeverity.CAUTION,
            message=message or f"'{field}' 미검증 — 출력 신뢰도 하락",
            field=field,
        )

    def _flag_p0_hold(self, field: str, reason: str) -> WarningFlag:
        return WarningFlag(
            code=WarningCode.P0_UNKNOWN_FORCED_HOLD,
            severity=WarningSeverity.CRITICAL,
            message=f"[P0 HOLD] {field}: {reason}",
            field=field,
        )

    def _resolve_confidence(
        self, levels: list[ConfidenceLevel]
    ) -> ConfidenceLevel:
        order = [
            ConfidenceLevel.UNVERIFIED,
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH,
        ]
        for level in order:
            if level in levels:
                return level
        return ConfidenceLevel.HIGH

    def _make_base_output(self, inp: EngineInput, **kwargs) -> dict:
        return {
            "request_id": inp.request_id,
            "engine_name": self.name,
            "engine_version": self.version,
            "as_of": inp.as_of,
            "warnings": [],
            **kwargs,
        }

    @staticmethod
    def _hash_input(inp: EngineInput) -> str:
        raw = inp.model_dump_json(exclude={"request_id"})
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

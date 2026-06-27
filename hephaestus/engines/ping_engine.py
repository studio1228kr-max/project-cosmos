"""
engines/ping_engine.py
──────────────────────
골격 검증 + 배포 smoke test 전용 더미 엔진.
실제 계산 없음. 엔진 인터페이스 정상 동작 확인용.
"""

from __future__ import annotations

from schemas.base import (
    ConfidenceLevel,
    EngineGate,
    EngineInput,
    EngineOutput,
)
from engines.base import BaseEngine


class PingOutput(EngineOutput):
    pong: str = "pong"


class PingEngine(BaseEngine):
    name = "ping"
    version = "1.0"

    def _execute(self, inp: EngineInput) -> PingOutput:
        return PingOutput(
            **self._make_base_output(inp),
            gate=EngineGate.PASS,
            confidence=ConfidenceLevel.HIGH,
            pong="pong",
        )

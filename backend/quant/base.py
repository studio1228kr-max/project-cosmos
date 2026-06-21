"""
COSMOS Quant Layer — Engine Base Class

GPT한테 새 엔진(merton_kmv.py, cecl_engine.py 등)을 짜게 시킬 때마다
아래 지시문을 같이 줄 것:

"QuantEngine을 상속받는 클래스를 만들고, compute(inputs: dict) -> EngineResult
 메서드만 구현해라. EngineResult, ConfidenceInfo, Provenance, ProvenanceInput은
 quant/schemas.py에서 import해라. confidence와 provenance를 반드시 채워라."

이렇게 하면 어떤 엔진이든 quant/api.py의 라우터에 그냥 꽂힌다.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from quant.schemas import EngineResult


class QuantEngine(ABC):
    """모든 금융공학 엔진의 베이스 클래스."""

    engine_name: str = "base"
    model_version: str = "v0.0"

    @abstractmethod
    def compute(self, deal_master_id: int, inputs: dict) -> EngineResult:
        """
        inputs: 엔진별로 필요한 입력 딕셔너리.
        반드시 EngineResult(confidence, provenance 포함)를 반환해야 한다.
        절대 raw float/dict만 반환하지 않는다 — House Canon 위반.
        """
        raise NotImplementedError

    def validate_inputs(self, inputs: dict, required_keys: list[str]) -> list[str]:
        """공통 입력 검증 헬퍼. 누락된 키 리스트를 반환 (없으면 빈 리스트)."""
        return [k for k in required_keys if k not in inputs or inputs[k] is None]

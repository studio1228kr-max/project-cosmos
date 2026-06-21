"""
[템플릿 예시 — GPT에게 이 패턴을 그대로 따르라고 지시할 것]

실제 merton_kmv.py를 GPT한테 시킬 때 프롬프트:

"quant/engines/merton_kmv.py를 작성해라. quant/base.py의 QuantEngine을
상속받고, compute() 메서드 안에서 Distance-to-Default와 PD를 계산해라.
inputs 딕셔너리는 {'avm_value': float, 'avm_sigma': float, 'debt_balance': float,
'horizon_years': float}를 받는다. 반드시 EngineResult를 반환하고,
confidence와 provenance(ProvenanceInput 리스트)를 채워라.
아래 템플릿 구조를 그대로 따라라:"
"""
from __future__ import annotations
from datetime import datetime
from quant.base import QuantEngine
from quant.schemas import (
    EngineResult, ConfidenceInfo, ConfidenceTier,
    Provenance, ProvenanceInput, SourceType,
)


class TemplateExampleEngine(QuantEngine):
    engine_name = "template_example"
    model_version = "v0.1"

    def compute(self, deal_master_id: int, inputs: dict) -> EngineResult:
        # 1) 입력 검증
        missing = self.validate_inputs(inputs, ["avm_value", "debt_balance"])
        warnings = []
        if missing:
            warnings.append(f"누락된 입력: {missing}")

        # 2) 실제 계산 로직 (GPT가 여기에 Merton/CECL/Cox 수식 채움)
        avm_value = inputs.get("avm_value", 0)
        debt_balance = inputs.get("debt_balance", 0)
        dummy_metric = avm_value - debt_balance  # ← 실제론 PD/DD 계산식

        # 3) provenance 기록 (입력값 출처 — 이게 핵심)
        provenance_inputs = [
            ProvenanceInput(
                metric_name="avm_value",
                value=avm_value,
                source_type=SourceType.MANUAL,
                source_detail="avm_engine output",
            ),
            ProvenanceInput(
                metric_name="debt_balance",
                value=debt_balance,
                source_type=SourceType.DERIVED,
                source_detail="reverse_debt_engine output",
            ),
        ]

        # 4) confidence 산출 (입력 신뢰도 기반으로 계산)
        confidence = ConfidenceInfo(
            tier=ConfidenceTier.MEDIUM,
            score=0.7,
            reasoning="템플릿 예시 — 실제 엔진은 입력 confidence 가중평균으로 산출",
        )

        return EngineResult(
            deal_master_id=deal_master_id,
            engine_name=self.engine_name,
            metrics={"dummy_metric": dummy_metric},
            confidence=confidence,
            provenance=Provenance(
                model_version=self.model_version,
                engine_name=self.engine_name,
                inputs=provenance_inputs,
                notes="템플릿 예시 — 실제 수식으로 교체 필요",
            ),
            warnings=warnings,
        )

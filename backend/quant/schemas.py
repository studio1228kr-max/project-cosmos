"""
COSMOS Quant Layer — Common Schemas
모든 금융공학 엔진(Merton, CECL, Cox, Copula, Behavioral 등)은
이 파일에 정의된 계약(EngineResult)을 반환해야 한다.

설계 원칙:
- 숫자만 던지지 않는다. confidence와 provenance를 항상 같이 던진다.
- "이 숫자 어디서 나왔어요?"에 즉답 가능해야 한다 (House Canon: falsifiability).
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ConfidenceTier(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SourceType(str, Enum):
    AUTO = "auto"        # 인프라계 자동 수집
    MANUAL = "manual"    # 수동 입력 (출처 기록됨)
    ASSUMPTION = "assumption"  # 가정치 (실측 데이터 없음, 명시적으로 낮은 신뢰도)
    DERIVED = "derived"  # 다른 엔진의 출력값을 입력으로 재사용


class ProvenanceInput(BaseModel):
    """입력값 하나의 출처 기록 — 이게 쌓여서 audit_trail이 된다."""
    metric_name: str
    value: Any
    source_type: SourceType
    source_detail: str          # 예: "ECOS_2026-06-21" 또는 "MOLIT_12comps"
    as_of_date: Optional[datetime] = None
    confidence_contribution: Optional[float] = Field(
        default=None, description="이 입력값이 최종 confidence에 기여한 정도 (0~1)"
    )


class ConfidenceInfo(BaseModel):
    tier: ConfidenceTier
    score: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None   # "Comps 3건 미달로 fallback 적용" 등


class Provenance(BaseModel):
    model_version: str
    engine_name: str
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    inputs: list[ProvenanceInput] = Field(default_factory=list)
    notes: Optional[str] = None       # "공시가격 대비 15% 할인 적용" 같은 수식 기록


class EngineResult(BaseModel):
    """
    모든 quant 엔진이 반환해야 하는 표준 결과 객체.
    Core(운용계)는 metrics만 보는 게 아니라 confidence/provenance까지
    deal_evidence.output_value / audit_trail 컬럼에 통째로 저장한다.
    """
    deal_master_id: int
    engine_name: str
    metrics: dict[str, float]              # {"pd": 0.083, "lgd": 0.27, ...}
    confidence: ConfidenceInfo
    provenance: Provenance
    warnings: list[str] = Field(default_factory=list)   # 비치명적 이슈 (fallback 사용 등)

    class Config:
        use_enum_values = True

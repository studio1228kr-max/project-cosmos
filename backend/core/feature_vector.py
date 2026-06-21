from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class FeatureVector:
    """
    EngineResult의 특정 metric 하나를 표준화해서 담는 최소 단위.

    지금은 dict wrapper 수준으로 시작 — 나중에 GPT가 만들 정교한
    quant_vectors/ 레이어로 교체 가능하지만, 지금은 failure_engine.py에
    엔진 결과를 꽂는 게 우선이라 최소 구현으로 간다.
    """
    name: str
    value: Any
    source_type: str          # "auto" | "manual" | "assumption" | "derived"
    source_detail: str
    confidence_score: float
    as_of_date: datetime


def extract(engine_result: Dict[str, Any], metric_name: str) -> FeatureVector:
    """
    quant_client.evaluate_deal()이 반환한 EngineResult(dict)에서
    특정 metric 하나를 뽑아 FeatureVector로 변환.
    """
    value = engine_result.get("metrics", {}).get(metric_name)
    confidence_score = engine_result.get("confidence", {}).get("score", 0.0)
    engine_name = engine_result.get("engine_name", "unknown_engine")

    return FeatureVector(
        name=metric_name,
        value=value,
        source_type="derived",
        source_detail=f"{engine_name}.{metric_name}",
        confidence_score=confidence_score,
        as_of_date=datetime.now(timezone.utc),
    )


def extract_merton_features(merton_result: Dict[str, Any]) -> Dict[str, FeatureVector]:
    """merton_kmv EngineResult에서 게이트에 필요한 핵심 2개만 뽑음."""
    return {
        "pd_structural_raw": extract(merton_result, "pd_structural_raw"),
        "distance_to_default_effective": extract(merton_result, "distance_to_default_effective"),
    }


def extract_cecl_features(cecl_result: Dict[str, Any]) -> Dict[str, FeatureVector]:
    """cecl_engine EngineResult에서 게이트에 필요한 핵심 3개만 뽑음."""
    return {
        "expected_loss": extract(cecl_result, "expected_loss"),
        "unexpected_loss": extract(cecl_result, "unexpected_loss"),
        "ifrs9_stage_effective": extract(cecl_result, "ifrs9_stage_effective"),
    }

"""
COSMOS Quant Layer — API Router

Core(운용계)는 이 엔드포인트만 호출한다.
지금은 같은 프로세스 안(모놀리식)에 마운트하고,
나중에 별도 Railway 서비스로 분리할 때 이 라우터를 그대로 옮기면 된다
(엔진 코드/스키마는 전혀 안 건드림 — 이게 "물리분리는 나중에" 설계 의도).
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from quant.registry import get_engine, list_engines
from quant.schemas import EngineResult

router = APIRouter(prefix="/quant", tags=["quant"])


class EvaluateRequest(BaseModel):
    deal_master_id: int
    inputs: dict


@router.get("/engines")
def get_available_engines() -> dict:
    """등록된 엔진 목록 — 디버깅/확인용."""
    return {"engines": list_engines()}


@router.post("/evaluate_deal/{engine_name}", response_model=EngineResult)
def evaluate_deal(engine_name: str, req: EvaluateRequest) -> EngineResult:
    """
    예: POST /quant/evaluate_deal/merton_kmv
        body: {"deal_master_id": 6, "inputs": {"avm_value": ..., "avm_sigma": ..., "debt_balance": ...}}
    """
    try:
        engine = get_engine(engine_name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        result = engine.compute(deal_master_id=req.deal_master_id, inputs=req.inputs)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"엔진 '{engine_name}' 계산 실패: {e}",
        )
    return result

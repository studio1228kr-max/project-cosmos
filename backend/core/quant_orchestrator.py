"""
COSMOS Core — Quant Orchestrator

딜의 dd_stage(PRE/SOFT/FULL)에 따라 어떤 quant 엔진을 호출할지 결정한다.
House Rule: Pre 단계에 Full-DD급 계산(t-copula 포트폴리오 등)을 강제하지 않는다
(failure_engine.py에서 이미 적용한 stage-aware 원칙을 quant 호출에도 동일 적용).

이건 스켈레톤이다 — 실제 inputs 조립(avm_engine 결과, reverse_debt_engine 결과를
어디서 가져와서 quant_client.evaluate_deal()에 넣을지)은 각 엔진 완성 후 채운다.
"""
from __future__ import annotations
from core.quant_client import evaluate_deal, QuantClientError

# dd_stage별로 호출할 엔진 목록 (필요해지는 순서대로 채워나감)
STAGE_ENGINE_MAP: dict[str, list[str]] = {
    "PRE": [
        "merton_kmv",
        "cecl_engine",
    ],
    "SOFT": [
        "merton_kmv",
        "cecl_engine",
        # "cox_hazard_engine",   # TODO: Cox Hazard 완성되면 등록 (lifetime PD flat approximation 해소)
    ],
    "FULL": [
        "merton_kmv",
        "cecl_engine",          # cecl_engine 내부에서 dd_stage=FULL이면 pd_accounting=1.0 강제
        # "cox_hazard_engine",
    ],
}

# 포트폴리오 단위 엔진(t-copula 등)은 딜 개수 임계치 넘기 전까지 호출 안 함
PORTFOLIO_ENGINE_MIN_DEALS = 5


def get_engines_for_stage(dd_stage: str) -> list[str]:
    return STAGE_ENGINE_MAP.get(dd_stage, [])


def run_quant_pipeline(deal_master_id: int, dd_stage: str, inputs_by_engine: dict[str, dict]) -> list[dict]:
    """
    inputs_by_engine: {"merton_kmv": {...}, "cecl_engine": {...}, ...}
    각 엔진별로 필요한 입력을 호출하는 쪽(failure_engine.py 등)에서 미리 조립해서 넘긴다.

    반환: 성공한 EngineResult 리스트. 실패한 엔진은 warnings로 기록하고 계속 진행
    (한 엔진 실패가 전체 게이트 판정을 막으면 안 됨).
    """
    engines = get_engines_for_stage(dd_stage)
    results = []

    for engine_name in engines:
        inputs = inputs_by_engine.get(engine_name)
        if inputs is None:
            continue  # 입력 없으면 스킵, failure_engine 쪽에서 missing 처리

        try:
            result = evaluate_deal(engine_name, deal_master_id, inputs)
            results.append(result)
        except QuantClientError as e:
            results.append({
                "engine_name": engine_name,
                "error": str(e),
                "metrics": {},
            })

    return results


def should_run_portfolio_engines(total_active_deals: int) -> bool:
    """t-copula 등 포트폴리오 엔진은 딜 수가 충분히 쌓여야 의미가 생긴다."""
    return total_active_deals >= PORTFOLIO_ENGINE_MIN_DEALS

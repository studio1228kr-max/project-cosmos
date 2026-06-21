"""
COSMOS Core — Quant Input Assembler

deal_master / deal_financials row(dict)를 받아서
merton_kmv, cecl_engine이 필요로 하는 inputs dict로 변환한다.

House 기본값(avm_sigma, lgd 등)은 전용 컬럼이 아직 없어서
명시적으로 house_assumption으로 표시한다 — 나중에 avm_engine,
recovery_strategy_engine_kr이 완성되면 이 House 기본값을 대체한다.
"""
from __future__ import annotations
from datetime import date
from typing import Any, Dict, Optional

# ── House 기본값 (전용 엔진 없을 때만 사용) ──────────────────
HOUSE_DEFAULT_AVM_SIGMA = 0.18
HOUSE_DEFAULT_LGD = 0.35
HOUSE_DEFAULT_LIQUIDITY_HAIRCUT = 0.10
HOUSE_DEFAULT_ENFORCEMENT_COST_RATIO = 0.05


def assemble_merton_inputs(
    deal_master: Dict[str, Any],
    deal_financials: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    필수 데이터(담보가치, 부채잔액, 만기일) 없으면 None 반환
    — failure_engine 쪽에서 None이면 quant 스킵하고 DEFERRED 처리.
    """
    avm_value = deal_financials.get("collateral_value_base")
    current_debt_balance = deal_financials.get("senior_debt") or deal_financials.get("loan_amount")
    maturity_date = deal_master.get("maturity_date")

    if avm_value is None or current_debt_balance is None or maturity_date is None:
        return None

    if isinstance(maturity_date, str):
        maturity_date = date.fromisoformat(maturity_date)

    days_to_maturity = (maturity_date - date.today()).days
    if days_to_maturity <= 0:
        days_to_maturity = 1  # 이미 만기 도달 — 최소 horizon으로 강제 (절대부도 트리거 유도)

    valuation_date = deal_financials.get("updated_at")
    valuation_date_str = (
        valuation_date.date().isoformat() if hasattr(valuation_date, "date")
        else str(valuation_date) if valuation_date else date.today().isoformat()
    )

    return {
        "avm_value": float(avm_value),
        "avm_sigma": HOUSE_DEFAULT_AVM_SIGMA,
        "current_debt_balance": float(current_debt_balance),
        "default_threshold": float(current_debt_balance),
        "days_to_maturity": days_to_maturity,
        "asset_class": deal_master.get("asset_class", "CRE"),
        "collateral_type": deal_master.get("asset_type") or "OFFICE",
        "valuation_date": valuation_date_str,
        "debt_as_of_date": valuation_date_str,
        "sigma_method": "house_assumption",
        "liquidity_haircut": HOUSE_DEFAULT_LIQUIDITY_HAIRCUT,
        "enforcement_cost_ratio": HOUSE_DEFAULT_ENFORCEMENT_COST_RATIO,
    }


def assemble_cecl_inputs(
    deal_master: Dict[str, Any],
    deal_financials: Dict[str, Any],
    merton_result: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    merton_kmv 결과(pd_structural_raw, current_ltv_effective)를 체이닝해서
    cecl_engine 입력을 만든다. merton 실패했으면 None.
    """
    if merton_result is None or "metrics" not in merton_result:
        return None

    merton_metrics = merton_result["metrics"]
    pd_value = merton_metrics.get("pd_structural_raw")
    effective_ltv = merton_metrics.get("current_ltv_effective")

    current_balance = deal_financials.get("senior_debt") or deal_financials.get("loan_amount")
    maturity_date = deal_master.get("maturity_date")

    if pd_value is None or current_balance is None or maturity_date is None:
        return None

    if isinstance(maturity_date, str):
        maturity_date = date.fromisoformat(maturity_date)

    days_to_maturity = (maturity_date - date.today()).days
    remaining_term_years = max(days_to_maturity, 1) / 365.0

    return {
        "pd": pd_value,
        "lgd": HOUSE_DEFAULT_LGD,
        "lgd_volatility_method": "MISSING",  # recovery_strategy_engine_kr 완성되면 대체
        "dd_stage": deal_master.get("dd_stage", "PRE"),
        "remaining_term_years": remaining_term_years,
        "current_balance": float(current_balance),
        "ead_basis": "DRAWN_ONLY",
        "effective_ltv": effective_ltv,
    }

"""COSMOS Narrative Gate — Thesis vs SDD 증빙 정합 판정.

각 딜타입별 thesis_type을 정의하고, thesis_type별로 '핵심 지지 증빙(key_items)'과
'반박 증빙(contradicting, 주로 RULE 레드플래그)'을 매핑한다. SDD 체크리스트의
item_status(CONFIRMED/PENDING/NOT_AVAILABLE)를 읽어 게이트를 판정한다:

  BROKEN    : 반박 증빙이 CONFIRMED (thesis가 깨짐)
  CONFIRMED : 핵심 지지 증빙 CONFIRMED 수 >= confirmed_threshold
  WEAK      : 그 외 (지지 부족, 반박 없음)
"""
from __future__ import annotations

from typing import Dict, List

# 딜타입 → thesis_type → 매핑 (item_code는 SDD 시드 기준)
THESIS_EVIDENCE_MAP: Dict[str, Dict[str, dict]] = {
    "DIRECT_LENDING": {
        "GOING_CONCERN": {
            "label": "계속기업·상환능력",
            "key_items": ["DL_A01", "DL_A07", "DL_B04", "DL_C02", "DL_C03"],
            "confirmed_threshold": 3,
            "contradicting": ["DL_D01", "DL_D02"],  # 법인 Dissolved / 사업자 Closed
        },
        "CASHFLOW_REPAYMENT": {
            "label": "현금흐름 기반 상환",
            "key_items": ["DL_B04", "DL_C01", "DL_C02", "DL_C03", "DL_A07"],
            "confirmed_threshold": 3,
            "contradicting": ["DL_D04"],  # 자금목적 설명 불가
        },
        "BUSINESS_VIABILITY": {
            "label": "사업성·시장지위",
            "key_items": ["DL_C02", "DL_C03", "DL_C04", "DL_C05", "DL_A04"],
            "confirmed_threshold": 3,
            "contradicting": ["DL_D02"],
        },
    },
    "DEBT_PURCHASE": {
        "CLAIM_VALIDITY": {
            "label": "채권 유효성",
            "key_items": ["DP_B01", "DP_B02", "DP_B03", "DP_E01", "DP_E03"],
            "confirmed_threshold": 3,
            "contradicting": ["DP_G01", "DP_G02"],  # 채권원인 불명 / 매도자-채권자 연결불가
        },
        "COLLATERAL_RECOVERY": {
            "label": "담보 기반 회수",
            "key_items": ["DP_C01", "DP_C02", "DP_C03", "DP_F01", "DP_F02"],
            "confirmed_threshold": 3,
            "contradicting": ["DP_G02"],
        },
    },
    "STRUCTURED_TRANCHE": {
        "WATERFALL_PRIORITY": {
            "label": "워터폴·트랜치 순위",
            "key_items": ["ST_B01", "ST_B02", "ST_B03", "ST_B04"],
            "confirmed_threshold": 3,
            "contradicting": ["ST_D01", "ST_D02", "ST_D05"],
        },
        "CASHFLOW_SOURCE": {
            "label": "현금흐름 원천",
            "key_items": ["ST_A03", "ST_B07", "ST_C04"],
            "confirmed_threshold": 2,
            "contradicting": ["ST_D03"],
        },
    },
    "DISTRESSED_SPECIAL": {
        "ENFORCEMENT_PATH": {
            "label": "집행·회수경로",
            "key_items": ["DS_C01", "DS_C02", "DS_B05", "DS_C04"],
            "confirmed_threshold": 2,
            "contradicting": ["DS_D04", "DS_D05"],  # 회수경로 전무 / 권리-경로 연결불가
        },
        "CLAIM_EXISTENCE": {
            "label": "채권 존재·확정",
            "key_items": ["DS_A03", "DS_A08", "DS_B05"],
            "confirmed_threshold": 2,
            "contradicting": ["DS_D01", "DS_D02", "DS_D03"],
        },
    },
    "EQUITY_LINKED_CREDIT": {
        "DOWNSIDE_PROTECTION": {
            "label": "하방 보호",
            "key_items": ["EL_B05", "EL_B07", "EL_B09", "EL_B12"],
            "confirmed_threshold": 3,
            "contradicting": ["EL_D03", "EL_D04", "EL_D05"],
        },
        "ENTERPRISE_VALUE": {
            "label": "기업가치·전환경제성",
            "key_items": ["EL_A03", "EL_C02", "EL_C03", "EL_C04"],
            "confirmed_threshold": 3,
            "contradicting": ["EL_D01", "EL_D02"],  # 법인 Dissolved / 감사 부적정
        },
    },
}


def list_thesis_types(deal_type: str) -> List[dict]:
    """딜타입의 사용 가능 thesis_type 목록 (코드 + 라벨)."""
    return [{"thesis_type": k, "label": v["label"]}
            for k, v in THESIS_EVIDENCE_MAP.get(deal_type, {}).items()]


def compute_gate(deal_type: str, thesis_type: str, sdd_items: List[dict]) -> dict:
    """SDD item_status 기반 Narrative Gate 판정.

    sdd_items: [{'item_code','item_name','item_status'}, ...]
    """
    cfg = THESIS_EVIDENCE_MAP.get(deal_type, {}).get(thesis_type)
    name = {i.get("item_code"): i.get("item_name") for i in sdd_items}
    status = {i.get("item_code"): (i.get("item_status") or "PENDING") for i in sdd_items}

    if not cfg:
        return {
            "deal_type": deal_type, "thesis_type": thesis_type,
            "gate_result": "WEAK", "supported_count": 0,
            "contradicted_items": [], "missing_evidence": [],
            "auto_reason": f"정의되지 않은 thesis_type '{thesis_type}' (딜타입 {deal_type})",
        }

    key_items = cfg["key_items"]
    threshold = cfg["confirmed_threshold"]
    contradicting = cfg.get("contradicting", [])

    supported = [c for c in key_items if status.get(c) == "CONFIRMED"]
    contradicted = [c for c in contradicting if status.get(c) == "CONFIRMED"]
    missing = [c for c in key_items if status.get(c) not in ("CONFIRMED", "NOT_AVAILABLE")]

    def detail(codes):
        return [{"item_code": c, "item_name": name.get(c, c)} for c in codes]

    if contradicted:
        gate = "BROKEN"
        reason = f"반박 증빙 확정 {len(contradicted)}건 — thesis 성립 불가: {', '.join(contradicted)}"
    elif len(supported) >= threshold:
        gate = "CONFIRMED"
        reason = f"핵심 지지 증빙 {len(supported)}/{threshold} 충족, 반박 없음"
    else:
        gate = "WEAK"
        reason = f"지지 증빙 {len(supported)}/{threshold} 미달, 미확인 {len(missing)}건 — 보강 필요"

    return {
        "deal_type": deal_type, "thesis_type": thesis_type,
        "gate_result": gate, "supported_count": len(supported),
        "threshold": threshold,
        "contradicted_items": detail(contradicted),
        "missing_evidence": detail(missing),
        "auto_reason": reason,
    }

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from evidence_engine import evaluate_evidence_engine, EvidencePackage
from refi_path_engine import evaluate_refi_path_engine, RefiPathPackage
from recovery_strategy_engine_kr import evaluate_korea_recovery_strategy_engine, KoreaRecoveryPackage


class CombinedGate(str, Enum):
    PASS = "PASS"
    WATCH = "WATCH"
    HOLD = "HOLD"
    REJECT_OR_DROP = "REJECT_OR_DROP"
    NOT_EVALUATED = "NOT_EVALUATED"


_GATE_SEVERITY = {
    "PASS": 0,
    "WATCH": 1,
    "HOLD": 2,
    "DROP": 3,
    "REJECT": 3,
}

_SEVERITY_TO_COMBINED = {
    0: CombinedGate.PASS,
    1: CombinedGate.WATCH,
    2: CombinedGate.HOLD,
    3: CombinedGate.REJECT_OR_DROP,
}

CP_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "TAX_CP": ["TAX", "PRIORITY_CLAIMS"],
    "TENANCY_CP": ["TENANT", "TENANCY", "OCCUPANCY", "EVICTION", "JEONSE"],
    "CASHFLOW_CP": ["DSRA", "DSCR", "CASH"],
    "COLLATERAL_CP": ["TITLE", "PERFECTION", "SENIOR", "LIEN", "COLLATERAL", "VIOLATION"],
    "LEGAL_CP": ["LEGAL", "COURT", "BLOCKER"],
    "STRUCTURE_CP": ["MARKET", "FUND_LIFE", "STRUCTURE", "REFI_GAP"],
    "PAYOFF_CP": ["SUPPORT", "PAYOFF", "CURE"],
    "DOC_CP": ["DOCUMENT", "SOURCE", "EXCERPT", "MISSING"],
}

_BLOCKER_KEYWORDS = ["UNVERIFIED", "TITLE", "LEGAL_BLOCKER", "DROP", "TAX", "SENIOR", "REJECT"]


@dataclass(frozen=True)
class DealDecisionPackage:
    deal_id: str
    deal_name: str

    combined_gate: CombinedGate
    final_gate: str
    final_gate_reasons: List[str]

    evidence_gate: Optional[str]
    refi_gate: Optional[str]
    recovery_gate: Optional[str]

    stages_run: List[str]
    stages_skipped: List[str]

    binding_constraints: List[str]
    flags: List[str]
    required_actions: List[str]
    required_cps: List[Dict[str, Any]]

    evidence_package: Optional[Dict[str, Any]]
    refi_path_package: Optional[Dict[str, Any]]
    recovery_package: Optional[Dict[str, Any]]

    memo_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "deal_name": self.deal_name,
            "combined_gate": self.combined_gate.value,
            "final_gate": self.final_gate,
            "final_gate_reasons": self.final_gate_reasons,
            "evidence_gate": self.evidence_gate,
            "refi_gate": self.refi_gate,
            "recovery_gate": self.recovery_gate,
            "stages_run": self.stages_run,
            "stages_skipped": self.stages_skipped,
            "binding_constraints": self.binding_constraints,
            "flags": self.flags,
            "required_actions": self.required_actions,
            "required_cps": self.required_cps,
            "evidence_package": self.evidence_package,
            "refi_path_package": self.refi_path_package,
            "recovery_package": self.recovery_package,
            "memo_summary": self.memo_summary,
        }


def evaluate_deal_pipeline(
    deal_master: Mapping[str, Any],
    evidence_items: Optional[Sequence[Mapping[str, Any]]] = None,
    required_fields: Optional[Sequence[str]] = None,
    p0_fields: Optional[Sequence[str]] = None,
    evidence_field_policies: Optional[Mapping[str, Any]] = None,
    refi_path_input: Optional[Mapping[str, Any]] = None,
    refi_scenarios: Optional[Sequence[Mapping[str, Any]]] = None,
    refi_policy: Optional[Mapping[str, Any]] = None,
    recovery_input: Optional[Mapping[str, Any]] = None,
    recovery_scenarios: Optional[Sequence[Mapping[str, Any]]] = None,
    recovery_policy: Optional[Mapping[str, Any]] = None,
) -> DealDecisionPackage:
    stages_run: List[str] = []
    stages_skipped: List[str] = []

    all_flags: List[str] = []
    all_actions: List[str] = []
    all_binding: List[str] = []

    evidence_dict: Optional[Dict[str, Any]] = None
    refi_dict: Optional[Dict[str, Any]] = None
    recovery_dict: Optional[Dict[str, Any]] = None

    evidence_gate_value: Optional[str] = None
    refi_gate_value: Optional[str] = None
    recovery_gate_value: Optional[str] = None

    if evidence_items:
        evidence_package: EvidencePackage = evaluate_evidence_engine(
            deal_master=deal_master,
            evidence_items=evidence_items,
            required_fields=required_fields,
            p0_fields=p0_fields,
            field_policies=evidence_field_policies,
        )
        evidence_dict = evidence_package.to_dict()
        evidence_gate_value = evidence_dict["gate"]
        stages_run.append("EVIDENCE")

        all_flags.extend([f"EVIDENCE:{b['code']}" for b in evidence_dict.get("blockers", [])])
        all_flags.extend([f"EVIDENCE:{w['code']}" for w in evidence_dict.get("warnings", [])])
        if evidence_dict.get("missing_required_fields"):
            all_actions.append(
                f"Evidence missing for required fields: {', '.join(evidence_dict['missing_required_fields'])}"
            )
    else:
        stages_skipped.append("EVIDENCE")

    if refi_path_input:
        refi_path_package: RefiPathPackage = evaluate_refi_path_engine(
            deal_master=deal_master,
            refi_path_input=refi_path_input,
            scenarios=refi_scenarios,
            policy=refi_policy,
            evidence_package=evidence_dict,
        )
        refi_dict = refi_path_package.to_dict()
        refi_gate_value = refi_dict["overall_gate"]
        stages_run.append("REFI_PATH")

        memo = refi_dict.get("memo_summary", {})
        if memo.get("base_binding_constraint"):
            all_binding.append(f"REFI:{memo['base_binding_constraint']}")
        for result in refi_dict.get("scenario_results", []):
            all_flags.extend([f"REFI:{f}" for f in result.get("flags", [])])
            all_actions.extend([f"REFI:{a}" for a in result.get("required_actions", [])])
    else:
        stages_skipped.append("REFI_PATH")

    if recovery_input:
        recovery_package: KoreaRecoveryPackage = evaluate_korea_recovery_strategy_engine(
            deal_master=deal_master,
            recovery_input=recovery_input,
            scenarios=recovery_scenarios,
            policy=recovery_policy,
            evidence_package=evidence_dict,
            refi_path_package=refi_dict,
        )
        recovery_dict = recovery_package.to_dict()
        recovery_gate_value = recovery_dict["overall_gate"]
        stages_run.append("RECOVERY")

        memo = recovery_dict.get("memo_summary", {})
        if memo.get("worst_binding_constraint"):
            all_binding.append(f"RECOVERY:{memo['worst_binding_constraint']}")
        for result in recovery_dict.get("strategy_results", []):
            all_flags.extend([f"RECOVERY:{f}" for f in result.get("flags", [])])
            all_actions.extend([f"RECOVERY:{a}" for a in result.get("required_actions", [])])
    else:
        stages_skipped.append("RECOVERY")

    combined_gate = compute_combined_gate(evidence_gate_value, refi_gate_value, recovery_gate_value)

    final_gate, final_gate_reasons = apply_final_gate_rules(
        evidence_gate=evidence_gate_value,
        refi_gate=refi_gate_value,
        recovery_gate=recovery_gate_value,
        flags=all_flags,
        recovery_dict=recovery_dict,
    )

    flags_unique = sorted(set(all_flags))
    actions_unique = sorted(set(all_actions))

    required_cps = extract_required_cps(flags_unique)

    memo_summary = build_combined_memo(
        deal_master=deal_master,
        combined_gate=combined_gate,
        final_gate=final_gate,
        final_gate_reasons=final_gate_reasons,
        evidence_gate_value=evidence_gate_value,
        refi_gate_value=refi_gate_value,
        recovery_gate_value=recovery_gate_value,
        evidence_dict=evidence_dict,
        refi_dict=refi_dict,
        recovery_dict=recovery_dict,
    )

    return DealDecisionPackage(
        deal_id=str(deal_master.get("deal_id", "")),
        deal_name=str(deal_master.get("deal_name", "")),
        combined_gate=combined_gate,
        final_gate=final_gate,
        final_gate_reasons=final_gate_reasons,
        evidence_gate=evidence_gate_value,
        refi_gate=refi_gate_value,
        recovery_gate=recovery_gate_value,
        stages_run=stages_run,
        stages_skipped=stages_skipped,
        binding_constraints=sorted(set(all_binding)),
        flags=flags_unique,
        required_actions=actions_unique,
        required_cps=required_cps,
        evidence_package=evidence_dict,
        refi_path_package=refi_dict,
        recovery_package=recovery_dict,
        memo_summary=memo_summary,
    )


def compute_combined_gate(
    evidence_gate_value: Optional[str],
    refi_gate_value: Optional[str],
    recovery_gate_value: Optional[str],
) -> CombinedGate:
    gates = [g for g in [evidence_gate_value, refi_gate_value, recovery_gate_value] if g]

    if not gates:
        return CombinedGate.NOT_EVALUATED

    worst_severity = max(_GATE_SEVERITY.get(g, 2) for g in gates)
    return _SEVERITY_TO_COMBINED[worst_severity]


def apply_final_gate_rules(
    evidence_gate: Optional[str],
    refi_gate: Optional[str],
    recovery_gate: Optional[str],
    flags: Sequence[str],
    recovery_dict: Optional[Dict[str, Any]],
) -> Tuple[str, List[str]]:
    """하우스 룰 truth table — IRR이 좋아도 이 룰을 못 뚫는다."""
    reasons: List[str] = []

    if evidence_gate == "REJECT":
        reasons.append("Evidence gate REJECT — 핵심 숫자 신뢰 불가")
        return "REJECT_OR_DROP", reasons

    if evidence_gate == "HOLD":
        reasons.append("Evidence gate HOLD (P0 필드 미검증) → Final HOLD")
        return "HOLD", reasons

    if any("UNVERIFIED_PRIORITY_CLAIMS" in f for f in flags):
        reasons.append("미검증 법정 우선채권 존재 (세금/임금/임차보증금) → Final HOLD")
        return "HOLD", reasons

    if any("TITLE_OR_PERFECTION_ISSUE" in f for f in flags):
        reasons.append("담보 등기/perfection 미확인 → Final HOLD")
        return "HOLD", reasons

    if any("SENIOR_OR_PARI_PASSU_CLAIMS_PRESENT" in f for f in flags):
        reasons.append("선순위/동순위 채권 존재 — 검증 전까지 Final HOLD")
        return "HOLD", reasons

    if recovery_dict is not None:
        worst_lgd = recovery_dict.get("worst_pv_lgd")
        if worst_lgd is not None and worst_lgd > 0.25:
            reasons.append(f"Tail PV LGD {worst_lgd:.1%} > 25% 하우스 한도 → DROP/재구조화 필요")
            return "REJECT_OR_DROP", reasons

    if refi_gate == "DROP" and recovery_gate == "DROP":
        reasons.append("Refi DROP + Recovery DROP → Final DROP")
        return "REJECT_OR_DROP", reasons

    if refi_gate == "DROP":
        reasons.append("Refi DROP (리파이 경로 막힘) → 재구조화 조건부 HOLD")
        return "HOLD", reasons

    gates = [g for g in [evidence_gate, refi_gate, recovery_gate] if g]
    if not gates:
        return "NOT_EVALUATED", reasons

    worst = max(_GATE_SEVERITY.get(g, 2) for g in gates)

    if worst == 0:
        reasons.append("Evidence/Refi/Recovery 전부 PASS, P0 블로커 없음 — WATCH로 사람 검토 필요 (자동 ADVANCE 없음)")
        return "WATCH", reasons

    reasons.append(f"개별 게이트 중 최악 심각도 기준 ({worst})")
    return _SEVERITY_TO_COMBINED[worst].value, reasons


def categorize_flag(flag: str) -> str:
    upper = flag.upper()
    for category, keywords in CP_CATEGORY_KEYWORDS.items():
        if any(k in upper for k in keywords):
            return category
    return "DOC_CP"


def extract_required_cps(flags: Sequence[str]) -> List[Dict[str, Any]]:
    cps: List[Dict[str, Any]] = []
    seen = set()

    for flag in flags:
        if flag in seen:
            continue
        seen.add(flag)

        category = categorize_flag(flag)
        severity = "BLOCKER" if any(k in flag.upper() for k in _BLOCKER_KEYWORDS) else "WARNING"

        cps.append({
            "cp_id": f"CP-{len(cps) + 1:03d}",
            "category": category,
            "description": flag,
            "severity": severity,
            "status": "OPEN",
            "owner": None,
            "due_date": None,
        })

    return cps


def build_combined_memo(
    deal_master: Mapping[str, Any],
    combined_gate: CombinedGate,
    final_gate: str,
    final_gate_reasons: Sequence[str],
    evidence_gate_value: Optional[str],
    refi_gate_value: Optional[str],
    recovery_gate_value: Optional[str],
    evidence_dict: Optional[Dict[str, Any]],
    refi_dict: Optional[Dict[str, Any]],
    recovery_dict: Optional[Dict[str, Any]],
) -> str:
    deal_name = deal_master.get("deal_name", "Unnamed deal")
    lines = [f"Deal pipeline result for {deal_name}: FINAL GATE = {final_gate}."]
    lines.append(f"Reason: {'; '.join(final_gate_reasons)}.")
    lines.append(f"(Reference combined_gate by severity: {combined_gate.value})")

    if evidence_dict:
        lines.append(
            f"Evidence gate: {evidence_gate_value} (overall score {evidence_dict.get('overall_score')}, "
            f"grade {evidence_dict.get('model_grade')})."
        )

    if refi_dict:
        memo = refi_dict.get("memo_summary", {})
        lines.append(f"Refi gate: {refi_gate_value}. {memo.get('memo_language', '')}")

    if recovery_dict:
        memo = recovery_dict.get("memo_summary", {})
        lines.append(f"Recovery gate: {recovery_gate_value}. {memo.get('memo_language', '')}")

    return " ".join(lines)

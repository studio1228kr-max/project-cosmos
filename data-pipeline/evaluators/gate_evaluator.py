"""
data-pipeline/evaluators/gate_evaluator.py

GATE EVALUATOR v2.0.0 — 객체 레이어(shared.ontology) 기반 재작성.

policy_rule(gate.{deal_type}).rule_body.evaluation[] 을 priority 순서로 순회하며
첫 매칭 조건의 then(GO/HOLD/KILL)을 반환한다. raw SQL 미사용.

현재 지원 조건 (단순 비교):
  - deal.properties.{dscr|ltv|irr_downside} <op> <number>   (op: < > <= >= == !=)
  - collateral.<field> <op> <number>   (deal.collaterals[0] 의 직접 컬럼; JSONB 아님)
스킵(차후 8~12 단계에서 처리):
  - "... < threshold(...)" 형태(임계값 참조)는 일단 건너뛴다.
그 외 인식 불가 조건 / 값 누락 → fail-closed: HOLD.
"""
from __future__ import annotations

import re

from shared.ontology import Deal, PolicyRule


# deal.properties.<field> <op> <number>  (지원 필드 3개 한정)
_SIMPLE_RE = re.compile(
    r"^deal\.properties\.(?P<field>dscr|ltv|irr_downside)\s*"
    r"(?P<op>==|!=|<=|>=|<|>)\s*"
    r"(?P<num>-?\d+(?:\.\d+)?)$"
)

# collateral.<field> <op> <number>  (Collateral 객체의 직접 컬럼 — 필드명 제한 없음)
_COLLATERAL_RE = re.compile(
    r"^collateral\.(?P<field>[a-zA-Z_][a-zA-Z0-9_]*)\s*"
    r"(?P<op>==|!=|<=|>=|<|>)\s*"
    r"(?P<num>-?\d+(?:\.\d+)?)$"
)

_OPS = {
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


class GateEvaluator:
    name = "gate_evaluator"
    version = "2.0.0"

    def evaluate(self, deal_id: int) -> dict:
        """
        return: {
            'gate_status': 'GO'|'HOLD'|'KILL',
            'reason': str,
            'matched_rule': str | None   # 어느 priority 에서 멈췄는지
        }
        """
        # 1. 딜 조회
        deal = Deal.get(deal_id)
        if deal is None:
            return self._result("HOLD", f"deal not found (id={deal_id})", None)

        with deal:
            deal_type = deal.raw.deal_type

            # 2. deal_type 의 활성 게이트 룰
            rule = PolicyRule.get_active(f"gate.{deal_type}")
            if rule is None:
                return self._result(
                    "HOLD", f"no gate rule for deal_type {deal_type!r}", None
                )

            with rule:
                evaluation = (rule.rule_body or {}).get("evaluation") or []
                ordered = sorted(evaluation, key=lambda r: r.get("priority", 1_000_000))

                skipped = 0
                for entry in ordered:
                    priority = entry.get("priority")
                    matched = f"priority {priority}"

                    # else 캐치올 → GO (또는 룰이 지정한 then)
                    if entry.get("else") is True:
                        action = entry.get("then", "GO")
                        return self._result(
                            action, f"all conditions passed → {action}", matched
                        )

                    cond = entry.get("if")
                    action = entry.get("then", "HOLD")
                    cond_str = cond.strip() if isinstance(cond, str) else None

                    # threshold(...) 형태 → 스킵 (차후 단계에서 처리)
                    if cond_str is not None and "threshold(" in cond_str:
                        skipped += 1
                        continue

                    # ── deal.properties.<field> 단순비교 (JSONB → .props) ──
                    m = _SIMPLE_RE.match(cond_str) if cond_str else None
                    if m is not None:
                        field = m.group("field")
                        op = m.group("op")
                        threshold = float(m.group("num"))
                        raw_value = deal.props[field].value
                        value = self._to_float(raw_value)
                        if value is None:
                            return self._result(
                                "HOLD",
                                f"deal.properties.{field} is missing/non-numeric "
                                f"({raw_value!r}) → defaulting to HOLD",
                                matched,
                            )
                        if _OPS[op](value, threshold):
                            return self._result(
                                action,
                                f"{field}={value} {op} {threshold} → {action}",
                                matched,
                            )
                        continue  # 불충족 → 다음 priority

                    # ── collateral.<field> 단순비교 (직접 컬럼) ──
                    mc = _COLLATERAL_RE.match(cond_str) if cond_str else None
                    if mc is not None:
                        collaterals = deal.collaterals
                        if not collaterals:
                            return self._result(
                                "HOLD", "no collateral records for deal", matched
                            )
                        # TODO: 복수 담보 합산 로직은 추후 — 지금은 단일 담보(첫 번째)만 가정
                        col = collaterals[0]
                        field = mc.group("field")
                        op = mc.group("op")
                        threshold = float(mc.group("num"))
                        # JSONB 아니라 직접 컬럼이므로 .props 안 거치고 객체 속성 직접 접근
                        raw_value = getattr(col.raw, field, None)
                        value = self._to_float(raw_value)
                        if value is None:
                            return self._result(
                                "HOLD",
                                f"collateral.{field} is missing/non-numeric "
                                f"({raw_value!r}) → defaulting to HOLD",
                                matched,
                            )
                        if _OPS[op](value, threshold):
                            return self._result(
                                action,
                                f"collateral.{field}={value} {op} {threshold} → {action}",
                                matched,
                            )
                        continue  # 불충족 → 다음 priority

                    # 3. 인식 불가 → fail-closed HOLD
                    return self._result(
                        "HOLD",
                        f"unrecognized condition, defaulting to HOLD: {cond!r}",
                        matched,
                    )

                # 4. 매칭/else 없이 끝 → GO
                tail = f" ({skipped} threshold condition(s) deferred)" if skipped else ""
                return self._result("GO", f"all conditions passed → GO{tail}", None)

    # ── helpers ───────────────────────────────────────────────
    @staticmethod
    def _to_float(value):
        if value is None or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _result(gate_status: str, reason: str, matched_rule):
        return {
            "gate_status": gate_status,
            "reason": reason,
            "matched_rule": matched_rule,
        }

"""
data-pipeline/evaluators/gate_evaluator.py

GATE EVALUATOR v2.0.0 — 객체 레이어(shared.ontology) 기반 재작성.

policy_rule(gate.{deal_type}).rule_body.evaluation[] 을 priority 순서로 순회하며
첫 매칭 조건의 then(GO/HOLD/KILL)을 반환한다. raw SQL 미사용.

P0 confidence_min 게이트 (게이트 evaluation 전에 먼저 수행):
  policy_rule(p0.{deal_type}).p0_inputs[] 의 각 입력이 요구하는 confidence_min 을
  실제 데이터의 gate_eligibility 등급과 비교해, 요구치 미달이면 즉시 HOLD.
  (p0 룰이 없으면 이 단계는 스킵)

  두 어휘 체계와 매핑 근거:
    confidence       : UNVERIFIED < LOW < MEDIUM < HIGH < VERIFIED   (데이터 신뢰도)
    gate_eligibility : UNCERTAIN  < COMPUTED_ELIGIBLE < VERIFIED      (게이트 사용성)

    UNVERIFIED / LOW → UNCERTAIN          신뢰도 부족 → 게이트 근거로 못 씀
    MEDIUM / HIGH    → COMPUTED_ELIGIBLE  계산·모델값으로 게이트 가능(사람검증은 아님).
                                          그래서 HIGH 라도 VERIFIED 가 아니라 COMPUTED_ELIGIBLE.
    VERIFIED         → VERIFIED           사람/원문 검증 완료 — 최고 등급

현재 지원 조건 (단순 비교):
  - deal.properties.{dscr|ltv|irr_downside} <op> <number>   (op: < > <= >= == !=)
  - collateral.<field> <op> <number>   (deal.collaterals[0] 의 직접 컬럼; JSONB 아님)
  - valuation.<method>.primary_case <op> <number | deal.properties.<field>>
        (deal.valuations 중 valuation_method==<method>; confidence=UNVERIFIED 면 게이트 불가.
         primary_case 는 cases[](JSONB 리스트) 안의 케이스 '이름' 포인터 →
         name==primary_case 인 item 의 value 를 비교값으로 사용)
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

# valuation.<method>.primary_case <op> <rhs>  (rhs 는 아래에서 숫자/deal.properties 로 해소)
_VALUATION_RE = re.compile(
    r"^valuation\.(?P<method>[a-zA-Z_][a-zA-Z0-9_]*)\.primary_case\s*"
    r"(?P<op>==|!=|<=|>=|<|>)\s*"
    r"(?P<rhs>.+)$"
)

# RHS 피연산자: 숫자 리터럴 또는 deal.properties.<field>
_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_DEAL_PROP_RE = re.compile(r"^deal\.properties\.(?P<field>[a-zA-Z_][a-zA-Z0-9_]*)$")

_OPS = {
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}

# confidence(데이터 신뢰도) → gate_eligibility(게이트 사용 등급) 매핑.
# 매핑 근거는 모듈 docstring 참조 (HIGH 가 COMPUTED_ELIGIBLE 인 이유 등).
CONFIDENCE_MIN_TO_GATE_ELIGIBILITY = {
    "UNVERIFIED": "UNCERTAIN",
    "LOW": "UNCERTAIN",
    "MEDIUM": "COMPUTED_ELIGIBLE",
    "HIGH": "COMPUTED_ELIGIBLE",
    "VERIFIED": "VERIFIED",
}

# gate_eligibility 등급 순서 (높을수록 강함).
GATE_ELIGIBILITY_ORDER = {
    "UNCERTAIN": 0,
    "COMPUTED_ELIGIBLE": 1,
    "VERIFIED": 2,
}

# P0 경로용: valuation.<method>.primary_case (연산자 없는 경로 형태)
_P0_VALUATION_RE = re.compile(
    r"^valuation\.(?P<method>[a-zA-Z_][a-zA-Z0-9_]*)\.primary_case$"
)

# 미구현/비대상 P0 경로 스킵 표식 (None 과 구분하기 위한 sentinel)
_SKIP = object()


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

            # 1.5 P0 입력 confidence_min 게이트 (게이트 evaluation 전에 먼저 수행)
            p0_block = self._check_p0(deal, deal_type)
            if p0_block is not None:
                return p0_block

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

                    # ── valuation.<method>.primary_case 비교 ──
                    mv = _VALUATION_RE.match(cond_str) if cond_str else None
                    if mv is not None:
                        method = mv.group("method")
                        op = mv.group("op")

                        # 1~3. method 와 일치하는 valuation 찾기 (없으면 fail-closed)
                        found = None
                        for v in deal.valuations:
                            if v.raw.valuation_method == method:
                                found = v
                                break
                        if found is None:
                            return self._result(
                                "HOLD",
                                f"no valuation found for method {method!r}",
                                matched,
                            )

                        # 5. confidence=UNVERIFIED 면 게이트 불가 (008 adopted_or_external_only 최소버전)
                        if found.raw.confidence == "UNVERIFIED":
                            return self._result(
                                "HOLD",
                                "valuation confidence is UNVERIFIED, cannot gate on it",
                                matched,
                            )

                        # 4. primary_case 는 cases[](JSONB 리스트) 안의 케이스 '이름' 포인터.
                        #    name==primary_case 인 item 을 찾아 그 value 를 비교값으로 쓴다.
                        primary = found.raw.primary_case
                        cases = found.raw.cases
                        case_item = None
                        if isinstance(cases, list):
                            for item in cases:
                                if isinstance(item, dict) and item.get("name") == primary:
                                    case_item = item
                                    break
                        if case_item is None:
                            return self._result(
                                "HOLD",
                                f"primary_case '{primary}' not found in cases for {method}",
                                matched,
                            )

                        # 5. 찾은 케이스의 value → float 캐스팅 (실패 시 fail-closed)
                        case_value = case_item.get("value")
                        left = self._to_float(case_value)
                        if left is None:
                            return self._result(
                                "HOLD",
                                f"valuation.{method} case '{primary}' value is non-numeric "
                                f"({case_value!r}) → defaulting to HOLD",
                                matched,
                            )

                        # RHS 해소: 숫자 또는 deal.properties.<field>
                        right, err = self._resolve_rhs(mv.group("rhs"), deal)
                        if right is None:
                            return self._result(
                                "HOLD", f"{err} → defaulting to HOLD", matched
                            )

                        if _OPS[op](left, right):
                            return self._result(
                                action,
                                f"valuation.{method}.primary_case={left} {op} {right} → {action}",
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

    # ── P0 confidence_min 게이트 ───────────────────────────────
    def _check_p0(self, deal, deal_type):
        """
        p0.{deal_type}.p0_inputs[] 의 confidence_min 을 실제 gate_eligibility 와 비교.
        요구치 미달이면 HOLD 결과 dict 반환, 통과/대상없음이면 None.
        """
        p0_rule = PolicyRule.get_active(f"p0.{deal_type}")
        if p0_rule is None:
            return None  # p0 룰 없으면 이 단계 스킵하고 기존대로 진행

        with p0_rule:
            p0_inputs = (p0_rule.rule_body or {}).get("p0_inputs") or []
            for item in p0_inputs:
                path = item.get("path")
                confidence_min = item.get("confidence_min")

                # 요구 등급: confidence_min → gate_eligibility
                required = CONFIDENCE_MIN_TO_GATE_ELIGIBILITY.get(confidence_min)
                if required is None:
                    return self._result(
                        "HOLD",
                        f"P0 path {path!r} has unknown confidence_min {confidence_min!r}",
                        None,
                    )
                required_rank = GATE_ELIGIBILITY_ORDER[required]

                actual = self._p0_actual_eligibility(path, deal)
                if actual is _SKIP:
                    continue  # 미구현/비대상 경로 → 스킵

                # None/미인식 등급은 -1 → fail-closed
                actual_rank = GATE_ELIGIBILITY_ORDER.get(actual, -1)
                if actual_rank < required_rank:
                    return self._result(
                        "HOLD",
                        f"P0 path '{path}' gate_eligibility below required "
                        f"(need >= {required}, got {actual})",
                        None,
                    )
        return None

    def _p0_actual_eligibility(self, path, deal):
        """P0 path 의 실제 gate_eligibility 등급. 미대상 경로는 _SKIP 반환."""
        if not isinstance(path, str):
            return _SKIP

        # deal.properties.<field> → PropertyAccessor.gate_eligibility 그대로 사용
        mp = _DEAL_PROP_RE.match(path)
        if mp is not None:
            return deal.props[mp.group("field")].gate_eligibility

        # collateral.<field> → 스킵 (TODO: collateral 레벨 confidence 는 추후)
        if path.startswith("collateral."):
            return _SKIP

        # valuation.<method>.primary_case → valuation.confidence 컬럼을 매핑 변환
        mv = _P0_VALUATION_RE.match(path)
        if mv is not None:
            method = mv.group("method")
            for v in deal.valuations:
                if v.raw.valuation_method == method:
                    return CONFIDENCE_MIN_TO_GATE_ELIGIBILITY.get(v.raw.confidence)
            return None  # 해당 method valuation 없음 → None → fail-closed

        # 기타 경로(borrower.* 등) → 스킵 (TODO)
        return _SKIP

    # ── helpers ───────────────────────────────────────────────
    def _resolve_rhs(self, rhs, deal):
        """
        비교 RHS 피연산자 → float.
        지원: 숫자 리터럴, deal.properties.<field>.
        실패 시 (None, reason) 반환.
        """
        rhs = rhs.strip()
        if _NUMBER_RE.match(rhs):
            return float(rhs), None
        mp = _DEAL_PROP_RE.match(rhs)
        if mp is not None:
            field = mp.group("field")
            v = self._to_float(deal.props[field].value)
            if v is None:
                return None, f"RHS deal.properties.{field} is missing/non-numeric"
            return v, None
        return None, f"unrecognized RHS operand {rhs!r}"

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

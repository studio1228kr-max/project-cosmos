"""
data-pipeline/evaluators/narrative_gate_evaluator.py

NARRATIVE GATE EVALUATOR v1.0.0 — 객체 레이어(shared.ontology) 기반.
GateEvaluator(gate_evaluator.py) 패턴을 따른다.

정성적 완결성(Evidence) + 외부 부정 신호(Signal)를 종합해
narrative_gate 를 CONFIRMED / WEAK / BROKEN 으로 판정한다.

  Evidence (deal_evidence_checklist, deal_master_id 기준):
    - MANDATORY(gate_blocking=true) 가 status='MISSING' → BROKEN
    - CONDITIONAL(gate_blocking=false) 가 MISSING       → WEAK
  Signal (scored_signals, borrower.dart_corp_code = entity_id):
    - urgency == 'CRITICAL_72H'    → BROKEN
    - aggregate_score >= 20        → BROKEN
    - urgency == 'WATCH_2W' / score 10~19 → WEAK

최종값: BROKEN > WEAK > CONFIRMED 중 가장 나쁜 것.

NOTE: deal_evidence_checklist / scored_signals 는 아직 온톨로지 객체가 아니라
      이 부분만 예외적으로 기존 data-pipeline 의 `from db import get_conn` 를 쓴다.
      TODO: Phase 6 에서 온톨로지 객체로 전환 예정.
"""
from __future__ import annotations

from shared.ontology import Deal, Borrower


# narrative_gate 심각도 순위 (높을수록 나쁨)
_RANK = {"CONFIRMED": 0, "WEAK": 1, "BROKEN": 2}


class NarrativeGateEvaluator:
    name = "narrative_gate_evaluator"
    version = "1.0.0"

    def evaluate(self, deal_id: int) -> dict:
        """
        return: {
            'narrative_gate': 'CONFIRMED'|'WEAK'|'BROKEN',
            'reason': str
        }
        """
        # 1. 딜 조회
        deal = Deal.get(deal_id)
        if deal is None:
            return self._result("BROKEN", f"deal not found (id={deal_id})")

        with deal:
            verdict = "CONFIRMED"   # worst-so-far
            reasons: list[str] = []

            # 2. legacy deal_master 링크 확인
            legacy_id = deal.raw.legacy_deal_master_id
            if legacy_id is None:
                verdict = self._worse(verdict, "WEAK")
                reasons.append("no legacy deal_master link, evidence unverifiable")
                # evidence 체크 스킵 → signal 체크만 진행
            else:
                # 3. Evidence 체크
                ev = self._check_evidence(legacy_id)
                if ev is not None:
                    level, reason = ev
                    verdict = self._worse(verdict, level)
                    reasons.append(reason)

            # 4. Signal 체크
            borrower = deal.borrower
            corp_code = borrower.raw.dart_corp_code if borrower is not None else None
            if corp_code:
                sig = self._check_signals(corp_code)
                if sig is not None:
                    level, reason = sig
                    verdict = self._worse(verdict, level)
                    reasons.append(reason)
            # corp_code 없으면 signal 체크 스킵 (evidence 결과만 사용)

            # 5~6. 최종 결정
            if not reasons:
                return self._result("CONFIRMED", "no evidence gaps or adverse signals")
            return self._result(verdict, "; ".join(reasons))

    # ── Evidence (raw SQL — TODO: Phase 6 온톨로지 전환) ──────────
    def _check_evidence(self, legacy_deal_master_id):
        """
        deal_evidence_checklist(status='MISSING') 조회.
        반환: ('BROKEN'|'WEAK', reason) 또는 None(누락 없음).

        TODO: Phase 6 에서 온톨로지 객체로 전환 예정.
              현재는 온톨로지 객체가 없어 raw SQL(db.get_conn) 사용.
        """
        from db import get_conn

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """SELECT evidence_item_code, gate_blocking
               FROM deal_evidence_checklist
               WHERE deal_master_id = %s AND status = 'MISSING'""",
            (legacy_deal_master_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        mandatory = [r["evidence_item_code"] for r in rows if r["gate_blocking"]]
        conditional = [r["evidence_item_code"] for r in rows if not r["gate_blocking"]]

        if mandatory:
            return ("BROKEN", f"mandatory evidence missing: {', '.join(mandatory)}")
        if conditional:
            return ("WEAK", f"conditional evidence missing: {', '.join(conditional)}")
        return None

    # ── Signal (raw SQL — TODO: Phase 6 온톨로지 전환) ───────────
    def _check_signals(self, corp_code):
        """
        scored_signals(entity_id=corp_code) 최신 5건 조회.
        반환: ('BROKEN'|'WEAK', reason) 또는 None(영향 없음).

        TODO: Phase 6 에서 온톨로지 객체로 전환 예정.
              현재는 온톨로지 객체가 없어 raw SQL(db.get_conn) 사용.
        """
        from db import get_conn

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """SELECT entity_name, aggregate_score, urgency
               FROM scored_signals
               WHERE entity_id = %s
               ORDER BY scored_at DESC
               LIMIT 5""",
            (corp_code,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return None

        # BROKEN: CRITICAL_72H 신호
        for r in rows:
            if r["urgency"] == "CRITICAL_72H":
                return ("BROKEN", f"critical signal detected: {r['entity_name']}")
        # BROKEN: aggregate_score >= 20
        for r in rows:
            score = r["aggregate_score"]
            if score is not None and score >= 20:
                return (
                    "BROKEN",
                    f"high aggregate_score signal ({score}) for {r['entity_name']}",
                )
        # WEAK: WATCH_2W 또는 점수 10~19
        for r in rows:
            score = r["aggregate_score"]
            if r["urgency"] == "WATCH_2W" or (score is not None and 10 <= score <= 19):
                return ("WEAK", f"watch-level signal for {r['entity_name']}")
        return None

    # ── helpers ───────────────────────────────────────────────
    @staticmethod
    def _worse(a, b):
        """두 narrative_gate 중 더 나쁜(높은 rank) 것."""
        return a if _RANK[a] >= _RANK[b] else b

    @staticmethod
    def _result(narrative_gate: str, reason: str) -> dict:
        return {"narrative_gate": narrative_gate, "reason": reason}

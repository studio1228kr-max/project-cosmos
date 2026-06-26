"""COSMOS IC Memo — Claude 기반 내부 IC 메모 초안 생성 (섹션 6).

7개 input을 DB에서 구조화 → Claude(claude-sonnet-4-6)로 S1~S8 초안 생성.
S9 숫자(딜 구조)·S10 판단 의견은 Claude 생성 금지(공란/레이블만), S11 Audit Trail은
코드에서 결정론적으로 생성. 잠금 해제 조건 5가지를 평가해 미충족 시 생성 차단.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

PROMPT_VERSION = "ic-memo-v1.0"
MODEL = "claude-sonnet-4-6"
STALE_DAYS = 183  # 6개월
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# 딜타입별 S9 딜 구조 term 레이블 (숫자 공란 — 민우 입력 필수)
S9_TERMS = {
    "DIRECT_LENDING": ["원금(Principal)", "금리(Coupon)", "만기(Maturity)", "상환구조", "담보(LTV)", "코버넌트", "수수료"],
    "DEBT_PURCHASE": ["매입가", "액면가(Par)", "할인율", "예상 회수기간", "담보", "보증/연대"],
    "STRUCTURED_TRANCHE": ["트랜치 규모", "우선순위(Seniority)", "금리", "워터폴 비율", "신용보강(Credit Enhancement)"],
    "DISTRESSED_SPECIAL": ["매입가", "회수목표(Recovery)", "집행비용", "예상 기간", "권리 우선순위"],
    "EQUITY_LINKED_CREDIT": ["원금", "쿠폰", "전환가(Strike)", "전환비율", "만기", "하방보호(Floor)"],
}

S9_LABEL = "자동 생성 불가 — 민우 입력 필요"


# ── 7개 input 구조화 ──
def build_inputs(cur, deal_id: int) -> dict:
    cur.execute("SELECT * FROM deal_master WHERE id=%s", (deal_id,))
    deal = cur.fetchone()
    if not deal:
        raise ValueError("deal not found")
    deal = dict(deal)

    cur.execute("SELECT * FROM deal_checklist_item WHERE deal_id=%s AND dd_tier='SDD' ORDER BY display_order, id", (deal_id,))
    sdd = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT * FROM narrative_gate_results WHERE deal_id=%s ORDER BY created_at DESC LIMIT 1", (deal_id,))
    ng = cur.fetchone()
    ng = dict(ng) if ng else None

    cur.execute("SELECT result, drop_reasons, checked_at FROM deal_kill_check_log WHERE deal_id=%s ORDER BY checked_at DESC LIMIT 1", (deal_id,))
    kc = cur.fetchone()

    # 신호: deal에 연결된 signal_room + 동일 entity 신호
    cur.execute("""SELECT entity_name, signal_type, aggregate_score, suggested_deal_type, urgency,
                          thesis_suggestion, reason_summary, created_at
                   FROM signal_room WHERE deal_id=%s OR entity_name=%s
                   ORDER BY aggregate_score DESC NULLS LAST, created_at DESC LIMIT 5""",
                (deal_id, deal.get("borrower") or deal.get("deal_name")))
    signals = [dict(r) for r in cur.fetchall()]

    def _src(it):
        return "AUTO" if it["item_type"] in ("AUTO", "RULE") else "MANUAL"

    sdd_snapshot = [{
        "item_code": it["item_code"], "item_name": it["item_name"],
        "value": it.get("value_text"), "source": _src(it),
        "item_status": it.get("item_status") or "PENDING",
        "data_source": it.get("data_source"),
        "data_as_of": it["data_as_of"].isoformat() if it.get("data_as_of") else None,
    } for it in sdd]

    # information_age: 가장 오래된 / 최신 신호 생성 시점
    sig_dates = [s["created_at"] for s in signals if s.get("created_at")]
    info_age = {
        "oldest_signal": min(sig_dates).isoformat() if sig_dates else None,
        "newest_signal": max(sig_dates).isoformat() if sig_dates else None,
    }

    return {
        "deal_intake": {
            "deal_code": deal.get("deal_code"), "borrower": deal.get("borrower") or deal.get("deal_name"),
            "deal_type": deal.get("deal_type"), "thesis": deal.get("thesis"),
            "thesis_type": deal.get("thesis_type"), "exposure_amount": deal.get("exposure_amount"),
            "target_irr": deal.get("target_irr"), "sector": deal.get("sector"),
        },
        "kill_check_result": {
            "status": deal.get("kill_check_status"),
            "drop_reasons": (kc["drop_reasons"] if kc else None) or [],
            "checked_at": kc["checked_at"].isoformat() if kc and kc.get("checked_at") else None,
        },
        "sdd_snapshot": sdd_snapshot,
        "narrative_gate": ({
            "gate_result": ng["gate_result"], "thesis_type": ng["thesis_type"],
            "supported_count": ng["supported_count"],
            "contradicted_items": ng.get("contradicted_items") or [],
            "missing_evidence": ng.get("missing_evidence") or [],
            "auto_reason": ng.get("auto_reason"),
        } if ng else None),
        "signal_summary": [{
            "entity": s.get("entity_name"), "type": s.get("signal_type"),
            "score": s.get("aggregate_score"), "thesis": s.get("thesis_suggestion"),
            "reason": s.get("reason_summary"),
            "created_at": s["created_at"].isoformat() if s.get("created_at") else None,
        } for s in signals],
        "catalyst": {
            "counterparty_motive": deal.get("counterparty_motive"),
            "info_edge": deal.get("info_edge"),
            "thesis": deal.get("thesis"),
        },
        "information_age": info_age,
    }


# ── 잠금 해제 조건 5가지 ──
def check_unlock(cur, deal_id: int) -> dict:
    # mandatory = SDD AUTO/RULE 항목 (자동 백본)
    cur.execute("""SELECT item_type, item_status, data_as_of, data_source FROM deal_checklist_item
                   WHERE deal_id=%s AND dd_tier='SDD'""", (deal_id,))
    items = [dict(r) for r in cur.fetchall()]
    # mandatory = SDD AUTO/RULE 백본 중 인프라 커넥터(NTS/COURT/ONBID, Phase 2 미연결) 제외.
    # 인프라성 NOT_AVAILABLE은 조건 ④(총 NA<3)에서 별도로 잡힘.
    INFRA = {"NTS", "COURT", "ONBID"}
    mandatory = [i for i in items if i["item_type"] in ("AUTO", "RULE") and (i.get("data_source") not in INFRA)]
    mand_na = [i for i in mandatory if (i.get("item_status") == "NOT_AVAILABLE")]
    na_total = len([i for i in items if i.get("item_status") == "NOT_AVAILABLE"])

    cur.execute("SELECT kill_check_status FROM deal_master WHERE id=%s", (deal_id,))
    kc = cur.fetchone()
    kc_status = kc["kill_check_status"] if kc else None

    cur.execute("SELECT gate_result FROM narrative_gate_results WHERE deal_id=%s ORDER BY created_at DESC LIMIT 1", (deal_id,))
    ng = cur.fetchone()
    gate = ng["gate_result"] if ng else None

    # 가장 오래된 AUTO 데이터 경과일
    cur.execute("""SELECT MIN(data_as_of) AS oldest FROM deal_checklist_item
                   WHERE deal_id=%s AND dd_tier='SDD' AND data_source IS NOT NULL AND data_as_of IS NOT NULL""", (deal_id,))
    oldest_row = cur.fetchone()
    oldest = oldest_row["oldest"] if oldest_row else None
    stale = bool(oldest and (datetime.now(timezone.utc) - oldest) > timedelta(days=STALE_DAYS))

    conds = [
        {"key": "MANDATORY_COMPLETE", "label": "MANDATORY 항목 NOT_AVAILABLE 없음",
         "passed": len(mand_na) == 0, "detail": f"미확인 mandatory {len(mand_na)}건"},
        {"key": "KILL_CHECK_PASS", "label": "Kill Check = PASS",
         "passed": kc_status == "PASS", "detail": f"현재 {kc_status or '미실행'}"},
        {"key": "GATE_NOT_BROKEN", "label": "Narrative Gate ≠ BROKEN",
         "passed": gate is not None and gate != "BROKEN", "detail": f"현재 {gate or '미평가'}"},
        {"key": "NA_UNDER_3", "label": "NOT_AVAILABLE < 3건",
         "passed": na_total < 3, "detail": f"총 {na_total}건"},
        {"key": "AUTO_FRESH", "label": "최신 AUTO 데이터 6개월 이내",
         "passed": (oldest is not None and not stale),
         "detail": (f"가장 오래된 {oldest.date().isoformat()}" if oldest else "AUTO 데이터 없음")},
    ]
    unlocked = all(c["passed"] for c in conds)
    return {"unlocked": unlocked, "conditions": conds,
            "gate_result": gate, "na_total": na_total,
            "sdd_completion": {
                "total": len(items), "mandatory": len(mandatory),
                "mandatory_na": len(mand_na), "na_total": na_total,
                "oldest_auto": oldest.isoformat() if oldest else None,
            }}


# ── Claude 호출 (S1~S8) ──
SYSTEM_PROMPT = (
    "당신은 COSMOS 사모 크레딧 펀드의 IC(투자심의위원회) 메모 초안 작성자입니다. "
    "제공된 구조화 input만 근거로 사실 기반으로 작성하세요. 추정 숫자를 지어내지 말고, "
    "데이터가 없으면 '데이터 없음'으로 표기하세요. downside-first(하방 우선) 관점을 유지하세요. "
    "반드시 JSON 객체 하나만 반환하며, 키는 S1~S8입니다. 각 값은 한국어 마크다운 문자열입니다. "
    "각 섹션은 핵심 위주로 간결하게(섹션당 최대 ~200단어) 작성하세요.\n"
    "S1 Executive Summary: 딜타입·thesis·권고 한 장 요약\n"
    "S2 Thesis & Catalyst: primary thesis / thesis_type / 왜 지금인가(catalyst)\n"
    "S3 Borrower 개요: 법인 기본정보(AUTO) + 사업 설명(데이터 있으면)\n"
    "S4 SDD 요약: MANDATORY 항목별 value + 출처(AUTO/MANUAL) + NOT_AVAILABLE 항목 명시\n"
    "S5 재무 분석: ICR/OCF/Z-score 등 AUTO 재무지표 해석(있는 값만)\n"
    "S6 신호 & 시퀀스: Top5 신호 + 출처 + 생성일, 정보 반감기 워닝\n"
    "S7 Narrative Gate: CONFIRMED/WEAK/BROKEN 결과 + 지지/반박/미확인\n"
    "S8 위험 및 경감 방안: contradicted_items 기반 downside-first 위험과 경감책\n"
    "절대 S9(딜 구조 숫자)·S10(판단 의견)은 생성하지 마세요."
)


def _call_claude(inputs: dict) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY 미설정")
    body = {
        "model": MODEL, "max_tokens": 8000, "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content":
            "다음 IC_MEMO_INPUT으로 S1~S8 초안을 JSON으로 작성하세요.\n\n"
            + json.dumps(inputs, ensure_ascii=False, default=str)}],
    }
    r = requests.post(ANTHROPIC_URL, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json=body, timeout=90)
    r.raise_for_status()
    data = r.json()
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
    # ```json 펜스 제거
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip().strip("`").strip()
    # 첫 { ~ 마지막 } 구간 파싱
    s, e = text.find("{"), text.rfind("}")
    if s >= 0 and e > s:
        text = text[s:e + 1]
    return json.loads(text)


def _build_s11(inputs: dict, unlock: dict) -> str:
    auto_srcs = sorted({s["data_source"] for s in inputs["sdd_snapshot"]
                        if s.get("source") == "AUTO" and s.get("data_source")})
    ng = inputs.get("narrative_gate") or {}
    comp = unlock["sdd_completion"]
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "## S11. Audit Trail",
        f"- 생성 시각: {now}",
        f"- AUTO 출처: {', '.join(auto_srcs) or '없음'}",
        f"- Gate 판정: {ng.get('gate_result') or '미평가'} — {ng.get('auto_reason') or 'n/a'}",
        f"- SDD 스냅샷: 총 {comp['total']}항목 / mandatory {comp['mandatory']} / NOT_AVAILABLE {comp['na_total']}",
        f"- 가장 오래된 AUTO 데이터: {comp.get('oldest_auto') or 'n/a'}",
        f"- Kill Check: {inputs['kill_check_result'].get('status') or '미실행'}",
        f"- prompt_version: {PROMPT_VERSION} (model: {MODEL})",
    ]
    return "\n".join(lines)


def generate(cur, deal_id: int, force: bool = False) -> dict:
    """잠금 조건 평가 → 통과 시 Claude로 S1~S8 생성 + S9/S11 코드 생성 → ic_memos 저장."""
    unlock = check_unlock(cur, deal_id)
    if not unlock["unlocked"] and not force:
        return {"locked": True, "unlock": unlock}

    inputs = build_inputs(cur, deal_id)
    sections = _call_claude(inputs)  # S1~S8
    sections["S11"] = _build_s11(inputs, unlock)

    deal_type = inputs["deal_intake"]["deal_type"]
    s9_terms = [{"label": t, "value": "", "note": S9_LABEL} for t in S9_TERMS.get(deal_type, [])]

    cur.execute("""INSERT INTO ic_memos
        (deal_id, sections, inputs, unlock_status, s9_terms, gate_result, sdd_completion, prompt_version, model)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id, generated_at""",
        (deal_id, json.dumps(sections, ensure_ascii=False, default=str),
         json.dumps(inputs, ensure_ascii=False, default=str),
         json.dumps(unlock, ensure_ascii=False, default=str),
         json.dumps(s9_terms, ensure_ascii=False),
         unlock.get("gate_result"),
         json.dumps(unlock["sdd_completion"], ensure_ascii=False, default=str),
         PROMPT_VERSION, MODEL))
    row = cur.fetchone()
    return {"locked": False, "memo_id": row["id"],
            "generated_at": row["generated_at"].isoformat(),
            "sections": sections, "s9_terms": s9_terms, "s10": None,
            "unlock": unlock, "prompt_version": PROMPT_VERSION, "model": MODEL,
            "gate_result": unlock.get("gate_result")}

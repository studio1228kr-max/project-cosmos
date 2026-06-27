"""COSMOS SDD AUTO — DART 기반 SDD AUTO/RULE 항목 자동 채움.

corp_code로 DART 회사기본정보 + 재무제표(fnlttSinglAcntAll) + 공시(list)를 받아
파생 facts를 만들고, 딜의 SDD 체크리스트 AUTO/RULE 항목을 item_name 키워드로 매칭해
value_text + data_as_of + data_source + ttl_days + item_status를 채운다.

품질: data_as_of 6개월 이상 → STALE, NOT_AVAILABLE >=3 → MANY_NA.
인프라계(NTS/COURT/OnBid)는 미연결 → NOT_AVAILABLE (Phase 2).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

# Sprint #9: DART 직접 호출 제거 → HERMES facts endpoint 경유 (3계층 분리 복원).
#   COSMOS → HERMES(data-pipeline) → DART
HERMES_URL = os.getenv("COSMOS_INTERNAL_URL", "http://data-pipeline.railway.internal:8000")
INTERNAL_KEY = os.getenv("INTERNAL_API_KEY", "")
TIMEOUT = 30
STALE_DAYS = 183  # 6개월


# ── HERMES facts endpoint 경유 (DART 직접 호출 제거) ──
def fetch_facts(corp_code: str) -> dict:
    """HERMES facts API 호출 → corp facts dict. 실패 시 graceful 빈 facts(→ NOT_AVAILABLE)."""
    try:
        r = requests.post(
            f"{HERMES_URL}/facts/{corp_code}",
            headers={"X-Internal-Key": INTERNAL_KEY},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"HERMES facts fetch failed {corp_code}: {e}")
        return {"corp_code": corp_code, "fin_as_of": None, "disc_as_of": None}


# ── item_name 키워드 → fact 매핑 ──
# (keywords, fact_key, source, ttl_days, category)  category: support|redflag|infra
# 순서 중요: 더 특정한/레드플래그/인프라 키워드를 먼저. "법인등기"는 출처표기로 여러 항목에
# 붙으므로 corp_exists 키워드에서 제외("법인 존속"만 사용).
KEYWORD_MAP = [
    (["Dissolved", "Liquidation", "폐업"], "rf_dissolved", "DART", 90, "redflag"),
    (["대표자 변경"], "rf_ceo_change", "DART", 90, "redflag"),
    (["사업자", "Closed", "Suspended"], "nts_status", "NTS", 30, "infra"),
    (["회생", "파산"], "court_status", "COURT", 30, "infra"),
    (["공매", "OnBid"], "onbid", "ONBID", 30, "infra"),
    (["법인 존속"], "corp_exists", "DART", 90, "support"),
    (["대표자"], "ceo", "DART", 90, "support"),
    (["업종", "사업목적"], "industry", "DART", 180, "support"),
    (["설립", "업력"], "est_year", "DART", 365, "support"),
    (["DART 공시"], "dart_filed", "DART", 30, "support"),
    (["감사의견", "감사보고서"], "audit_opinion", "DART", 365, "support"),
    (["매출"], "revenue", "DART", 365, "support"),
    (["영업이익", "EBITDA"], "ebit", "DART", 365, "support"),
]


def _match(item_name: str):
    nm = item_name or ""
    for kws, fact, source, ttl, cat in KEYWORD_MAP:
        if any(k in nm for k in kws):
            return fact, source, ttl, cat
    return None


def _resolve(facts: dict, fact: str, cat: str):
    """반환: (value_text, item_status, as_of) | None(=NOT_AVAILABLE)."""
    fin_as_of, disc_as_of = facts.get("fin_as_of"), facts.get("disc_as_of")
    if cat == "infra":
        return None  # 인프라계 미연결
    if cat == "redflag":
        if fact == "rf_dissolved":
            # 법인 미존속(company.json 무응답) → 레드플래그 확정, 아니면 미트리거(PENDING 유지)
            if facts.get("corp_exists") is False:
                return ("법인 미존속 정황", "CONFIRMED", disc_as_of)
            return ("해당없음", "PENDING", disc_as_of)
        if fact == "rf_ceo_change":
            # '설명 회피'는 자동 판정 불가 → 정보만 채우고 PENDING(휴먼 판단). 게이트 미트리거.
            n = facts.get("ceo_changes", 0)
            if n > 0:
                return (f"최근 2년 대표이사 변경/선임 공시 {n}건 — 사유 검토 필요", "PENDING", disc_as_of)
            return ("최근 2년 대표이사 변경 공시 없음", "PENDING", disc_as_of)
        return None
    # support
    if fact == "corp_exists":
        return ("법인 존속 확인", "CONFIRMED", disc_as_of) if facts.get("corp_exists") else None
    if fact == "ceo":
        return (facts["ceo"], "CONFIRMED", disc_as_of) if facts.get("ceo") else None
    if fact == "industry":
        return (f"업종코드 {facts['industry']}", "CONFIRMED", disc_as_of) if facts.get("industry") else None
    if fact == "est_year":
        return (f"{facts['est_year']}년 설립", "CONFIRMED", disc_as_of) if facts.get("est_year") else None
    if fact == "dart_filed":
        return ("DART 공시 있음", "CONFIRMED", disc_as_of) if facts.get("dart_filed") else None
    if fact == "audit_opinion":
        return (f"감사의견 {facts['audit_opinion']}", "CONFIRMED", facts.get("fin_as_of") or disc_as_of) if facts.get("audit_opinion") else None
    if fact == "revenue":
        r = facts.get("revenue")
        if r:
            extra = f" / Z={facts['zscore']}({facts['z_zone']})" if facts.get("zscore") is not None else ""
            extra += f" / ICR={facts['icr']}" if facts.get("icr") is not None else ""
            return (f"매출 {r:,.0f}원{extra}", "CONFIRMED", fin_as_of)
        return None
    if fact == "ebit":
        e = facts.get("ebit")
        if e is not None:
            ocf = "" if facts.get("ocf_positive") is None else f" / OCF {'+' if facts['ocf_positive'] else '-'}"
            dr = f" / 부채비율 {facts['debt_ratio']}%" if facts.get("debt_ratio") is not None else ""
            return (f"영업이익 {e:,.0f}원{ocf}{dr}", "CONFIRMED", fin_as_of)
        return None
    return None


def populate(cur, deal_id: int, corp_code: str) -> dict:
    """SDD AUTO/RULE 항목 자동 채움 + 메타데이터 저장. cur는 호출자 트랜잭션."""
    facts = fetch_facts(corp_code)
    cur.execute("SELECT id, item_code, item_name, item_type FROM deal_checklist_item WHERE deal_id=%s AND dd_tier='SDD'", (deal_id,))
    items = [dict(r) for r in cur.fetchall()]
    filled, not_available = [], []

    for it in items:
        if it["item_type"] not in ("AUTO", "RULE"):
            continue
        m = _match(it["item_name"])
        if not m:
            continue
        fact, source, ttl, cat = m
        res = _resolve(facts, fact, cat)
        if res is None:
            cur.execute(
                "UPDATE deal_checklist_item SET item_status='NOT_AVAILABLE', data_source=%s, data_as_of=NOW(), ttl_days=%s, updated_at=NOW() WHERE id=%s",
                (source, ttl, it["id"]))
            not_available.append(it["item_code"])
        else:
            value_text, status, as_of = res
            cur.execute(
                "UPDATE deal_checklist_item SET value_text=%s, item_status=%s, data_source=%s, data_as_of=%s, ttl_days=%s, updated_at=NOW() WHERE id=%s",
                (value_text, status, source, as_of, ttl, it["id"]))
            # CONFIRMED만 '채움'으로 집계. PENDING(레드플래그 정보성)은 게이트 미트리거 — 별도 집계 안함.
            if status == "CONFIRMED":
                filled.append({"item_code": it["item_code"], "value": value_text, "status": status, "source": source})

    # 품질 플래그
    cur.execute("SELECT count(*) c FROM deal_checklist_item WHERE deal_id=%s AND dd_tier='SDD' AND item_status='NOT_AVAILABLE'", (deal_id,))
    na_count = cur.fetchone()["c"]
    cur.execute("""SELECT count(*) c FROM deal_checklist_item WHERE deal_id=%s AND dd_tier='SDD'
                   AND data_as_of IS NOT NULL AND data_as_of < NOW() - (%s || ' days')::interval""", (deal_id, STALE_DAYS))
    stale_count = cur.fetchone()["c"]
    quality_flags = []
    if stale_count > 0:
        quality_flags.append("STALE_DATA")
    if na_count >= 3:
        quality_flags.append("MANY_NA")

    return {
        "corp_code": corp_code,
        "filled": filled, "filled_count": len(filled),
        "not_available": not_available, "na_count": na_count,
        "stale_count": stale_count, "quality_flags": quality_flags,
        "facts": facts,
    }

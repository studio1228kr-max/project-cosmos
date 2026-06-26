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

DART_BASE = "https://opendart.fss.or.kr/api"
TIMEOUT = 15
STALE_DAYS = 183  # 6개월

# ── 재무 계정 매핑 (fnlttSinglAcntAll, account_id + 한글 startswith) ──
ACCOUNT_ID = {
    "ifrs-full_CurrentAssets": "current_assets", "ifrs-full_Assets": "total_assets",
    "ifrs-full_RetainedEarnings": "retained_earnings", "ifrs-full_Equity": "equity",
    "ifrs-full_Liabilities": "total_debt", "ifrs-full_ShorttermBorrowings": "short_term_debt",
    "ifrs-full_Revenue": "revenue", "ifrs-full_OperatingIncome": "ebit",
    "dart_OperatingIncomeLoss": "ebit", "ifrs-full_FinanceCosts": "interest_expense",
    "ifrs-full_CashFlowsFromUsedInOperatingActivities": "operating_cf",
}
KOREAN = [("유동자산", "current_assets"), ("자산총계", "total_assets"), ("이익잉여금", "retained_earnings"),
          ("결손금", "retained_earnings"), ("자본총계", "equity"), ("부채총계", "total_debt"),
          ("단기차입금", "short_term_debt"), ("매출액", "revenue"), ("영업수익", "revenue"),
          ("영업이익", "ebit"), ("이자비용", "interest_expense"), ("영업활동", "operating_cf")]


def _key():
    return os.getenv("DART_API_KEY", "")


def _num(s) -> float:
    s = str(s or "").replace(",", "").strip()
    if not s or s == "-":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _get(path: str, params: dict) -> dict:
    try:
        r = requests.get(f"{DART_BASE}/{path}", params={**params, "crtfc_key": _key()}, timeout=TIMEOUT)
        return r.json()
    except Exception:
        return {}


# ── DART fetch ──
def fetch_company(corp_code: str) -> dict:
    d = _get("company.json", {"corp_code": corp_code})
    if d.get("status") != "000":
        return {"exists": False}
    est = (d.get("est_dt") or "")[:4]
    return {"exists": True, "ceo": d.get("ceo_nm"), "industry": d.get("induty_code"),
            "est_year": est or None, "corp_name": d.get("corp_name")}


def _parse_financial_rows(rows: list) -> dict:
    out: dict = {}
    for it in rows:
        sj = str(it.get("sj_div") or "").upper()
        if sj == "SCE":   # 자본변동표 제외 (자본총계 중복 오매칭 방지)
            continue
        f = ACCOUNT_ID.get(it.get("account_id", ""))
        if not f:
            nm = (it.get("account_nm") or "").strip()
            for kw, fn in KOREAN:
                if nm.startswith(kw):
                    f = fn
                    break
        if f and f not in out:
            amt = it.get("thstrm_add_amount") if f in ("revenue", "ebit", "interest_expense", "operating_cf") else None
            out[f] = _num(amt if amt not in (None, "") else it.get("thstrm_amount"))
    return out


def fetch_financials(corp_code: str, year: str) -> dict:
    for fs in ("CFS", "OFS"):
        d = _get("fnlttSinglAcntAll.json", {"corp_code": corp_code, "bsns_year": year,
                                            "reprt_code": "11011", "fs_div": fs})
        if d.get("status") == "000" and d.get("list"):
            return _parse_financial_rows(d["list"])
    return {}


def fetch_disclosures(corp_code: str) -> dict:
    """최근 2년 공시 분류."""
    end = datetime.now(timezone.utc)
    bgn = end - timedelta(days=730)
    facts = {"dart_filed": False, "audit_opinion": None, "cb_bw": False,
             "ceo_changes": 0, "litigation": False, "amendment": False}
    page = 1
    while page <= 5:
        d = _get("list.json", {"corp_code": corp_code, "bgn_de": bgn.strftime("%Y%m%d"),
                               "end_de": end.strftime("%Y%m%d"), "page_no": page, "page_count": 100})
        if d.get("status") != "000":
            break
        items = d.get("list", [])
        if items:
            facts["dart_filed"] = True
        for it in items:
            nm = it.get("report_nm", "") or ""
            if "감사보고서" in nm or "감사의견" in nm:
                for op in ("의견거절", "부적정", "한정"):
                    if op in nm:
                        facts["audit_opinion"] = op
                if facts["audit_opinion"] is None:
                    facts["audit_opinion"] = "적정"
            if "전환사채" in nm or "신주인수권부사채" in nm or "교환사채" in nm:
                facts["cb_bw"] = True
            if "대표이사" in nm and ("변경" in nm or "선임" in nm):
                facts["ceo_changes"] += 1
            if "소송" in nm or "제소" in nm:
                facts["litigation"] = True
            if "정정" in nm:
                facts["amendment"] = True
        if len(items) < 100:
            break
        page += 1
    return facts


# ── facts 빌드 ──
def build_facts(corp_code: str) -> dict:
    year = str(datetime.now(timezone.utc).year - 1)
    comp = fetch_company(corp_code)
    fin = fetch_financials(corp_code, year)
    disc = fetch_disclosures(corp_code)

    # Altman Z (한국 SME) + ICR + 부채비율 + OCF
    z = z_zone = icr = debt_ratio = None
    ocf_positive = None
    ta = fin.get("total_assets", 0)
    if ta:
        wc = fin.get("current_assets", 0) - (fin.get("total_debt", 0) - fin.get("short_term_debt", 0))
        zscore = (0.717 * (wc / ta) + 0.847 * (fin.get("retained_earnings", 0) / ta)
                  + 3.107 * (fin.get("ebit", 0) / ta) + 0.420 * (fin.get("equity", 0) / max(fin.get("total_debt", 0), 1))
                  + 0.998 * (fin.get("revenue", 0) / ta))
        z = round(zscore, 2)
        z_zone = "DISTRESS" if z < 1.23 else "GREY" if z < 2.90 else "SAFE"
    ie = fin.get("interest_expense", 0)
    if ie:
        icr = round(fin.get("ebit", 0) / ie, 2)
    eq = fin.get("equity", 0)
    if eq:
        debt_ratio = round(fin.get("total_debt", 0) / eq * 100, 1)
    if "operating_cf" in fin:
        ocf_positive = fin.get("operating_cf", 0) > 0

    fin_as_of = f"{year}-12-31T00:00:00+00:00" if fin else None
    disc_as_of = datetime.now(timezone.utc).isoformat()
    return {
        "corp_code": corp_code, "fin_as_of": fin_as_of, "disc_as_of": disc_as_of,
        "corp_exists": comp.get("exists"), "ceo": comp.get("ceo"), "industry": comp.get("industry"),
        "est_year": comp.get("est_year"),
        "revenue": fin.get("revenue", 0) if fin else None, "ebit": fin.get("ebit") if fin else None,
        "icr": icr, "zscore": z, "z_zone": z_zone, "debt_ratio": debt_ratio, "ocf_positive": ocf_positive,
        **disc,
    }


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
    facts = build_facts(corp_code)
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

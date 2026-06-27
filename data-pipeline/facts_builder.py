"""HERMES facts builder (Sprint #9) — DART 기반 corp facts 생성.

COSMOS sdd_auto가 직접 DART를 호출하던 로직을 HERMES로 이전(3계층 분리 복원).
corp_code → 회사기본정보 + 재무(fnlttSinglAcntAll) + 공시(list) → 파생 facts dict.
cb_terms는 cb_term_extractions(이미 수집됨)에서 보강.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

import requests

DART_BASE = "https://opendart.fss.or.kr/api"
TIMEOUT = 15

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
        if str(it.get("sj_div") or "").upper() == "SCE":
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


def build_facts(corp_code: str) -> dict:
    """corp_code → COSMOS sdd_auto가 기대하는 facts dict (DART 빌드)."""
    year = str(datetime.now(timezone.utc).year - 1)
    comp = fetch_company(corp_code)
    fin = fetch_financials(corp_code, year)
    disc = fetch_disclosures(corp_code)

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
        "corp_exists": comp.get("exists"), "corp_name": comp.get("corp_name"),
        "ceo": comp.get("ceo"), "industry": comp.get("industry"), "est_year": comp.get("est_year"),
        "revenue": fin.get("revenue", 0) if fin else None, "ebit": fin.get("ebit") if fin else None,
        "icr": icr, "zscore": z, "z_zone": z_zone, "debt_ratio": debt_ratio, "ocf_positive": ocf_positive,
        **disc,
    }

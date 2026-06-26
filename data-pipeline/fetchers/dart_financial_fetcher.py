"""DART 재무제표 fetcher.

스펙의 fnlttSinglAcnt(주요계정)는 이자비용/현금흐름이 없어 ICR 계산 불가 →
TARGET_ACCOUNTS(IFRS 전체코드)에 맞는 fnlttSinglAcntAll(전체계정)을 사용.
corp_code는 공시 item에 이미 있으므로(scan→entity_id) 그것을 직접 쓰는 게 정확.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import List, Optional

import httpx

DART_API_KEY = os.getenv("DART_API_KEY", "")
DART_FINANCIAL_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
DART_CORP_URL = "https://opendart.fss.or.kr/api/company.json"

REPORT_CODES = {"annual": "11011", "q3": "11014", "half": "11012", "q1": "11013"}

# IFRS account_id → 필드
TARGET_ACCOUNTS = {
    "ifrs-full_CurrentAssets": "current_assets",
    "ifrs-full_Assets": "total_assets",
    "ifrs-full_RetainedEarnings": "retained_earnings",
    "ifrs-full_Equity": "equity",
    "ifrs-full_Liabilities": "total_debt",
    "ifrs-full_CurrentLiabilities": "current_liabilities",
    "ifrs-full_ShorttermBorrowings": "short_term_debt",
    "ifrs-full_Revenue": "sales",
    "ifrs-full_OperatingIncome": "ebit",
    "dart_OperatingIncomeLoss": "ebit",
    "ifrs-full_FinanceCosts": "interest_expense",
    "ifrs-full_CashFlowsFromUsedInOperatingActivities": "operating_cf",
}

# account_nm(한글) 부분일치 fallback — 표준 account_id 없는 SME 대응
KOREAN_FALLBACK = [
    ("유동자산", "current_assets"),
    ("자산총계", "total_assets"),
    ("이익잉여금", "retained_earnings"),
    ("결손금", "retained_earnings"),
    ("자본총계", "equity"),
    ("부채총계", "total_debt"),
    ("유동부채", "current_liabilities"),
    ("단기차입금", "short_term_debt"),
    ("매출액", "sales"),
    ("영업수익", "sales"),
    ("영업이익", "ebit"),
    ("이자비용", "interest_expense"),
    ("영업활동", "operating_cf"),
]


def _num(s) -> float:
    """부호 보존 숫자 파싱 (음수 보존 — 결손금/손실/적자 신호 핵심)."""
    s = str(s or "").replace(",", "").strip()
    if not s or s == "-":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


class DartFinancialFetcher:

    async def get_corp_code(self, entity_name: str) -> Optional[str]:
        """(fallback) company.json은 이름검색을 지원하지 않아 보통 None.
        실제로는 공시 item의 corp_code(entity_id)를 사용한다."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get(DART_CORP_URL, params={"crtfc_key": DART_API_KEY, "corp_name": entity_name})
                data = res.json()
                if data.get("status") == "000" and data.get("list"):
                    return data["list"][0].get("corp_code")
        except Exception:
            pass
        return None

    async def fetch_financial(self, corp_code: str, year: str, report_type: str = "annual") -> dict:
        """전체계정 재무제표 → 필드 dict (CFS 우선, 없으면 OFS)."""
        for fs_div in ("CFS", "OFS"):
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    res = await client.get(DART_FINANCIAL_URL, params={
                        "crtfc_key": DART_API_KEY, "corp_code": corp_code,
                        "bsns_year": year, "reprt_code": REPORT_CODES[report_type], "fs_div": fs_div,
                    })
                    data = res.json()
            except Exception:
                continue
            if data.get("status") == "000" and data.get("list"):
                return self._parse_accounts(data["list"])
        return {}

    def _parse_accounts(self, rows: List[dict]) -> dict:
        result: dict = {}
        for item in rows:
            field_name = TARGET_ACCOUNTS.get(item.get("account_id", ""))
            if not field_name:
                nm = (item.get("account_nm", "") or "").strip()
                for kw, fn in KOREAN_FALLBACK:
                    # startswith: "자본및부채총계"가 "부채총계"에 오인매칭되는 것 방지,
                    # "영업이익(손실)"·"이익잉여금(결손금)" 같은 접미사는 허용
                    if nm.startswith(kw):
                        field_name = fn
                        break
            if field_name and field_name not in result:
                result[field_name] = _num(item.get("thstrm_amount", "0"))
        return result

    async def fetch_multi_period(self, corp_code: str, periods: int = 4) -> List[dict]:
        """최근 N기 재무 (연간·분기, rate-limit sleep)."""
        results: List[dict] = []
        cy = datetime.now().year
        for year in range(cy - 1, cy - 3, -1):
            for rtype in ("annual", "q3", "half", "q1"):
                data = await self.fetch_financial(corp_code, str(year), rtype)
                if data:
                    data["period_year"] = year
                    data["report_type"] = rtype
                    results.append(data)
                    if len(results) >= periods:
                        return results
                await asyncio.sleep(0.3)
        return results

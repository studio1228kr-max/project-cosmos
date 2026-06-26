"""DART 재무제표 fetcher.

fnlttSinglAcntAll(전체계정)을 CFS/OFS 각각 호출 → ChatGPT 파서
(parse_opendart_financial_accounts_with_fallback) → to_financial_features 로
FinancialFeatures 생성. corp_code는 공시 item의 corp_code(entity_id)를 직접 사용.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import List, Optional

import httpx

from engines.financial_engine import FinancialFeatures
from parsers.dart_financial_parser import (
    parse_opendart_financial_accounts,
    to_financial_features,
)

DART_API_KEY = os.getenv("DART_API_KEY", "")
# 주요계정(fnlttSinglAcnt): 행마다 fs_div(CFS/OFS) 포함 → ChatGPT 파서 native.
# (전체계정 All은 행에 fs_div가 없고 SCE 자본총계 중복으로 오매칭 → 사용 안 함)
DART_FINANCIAL_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
DART_CORP_URL = "https://opendart.fss.or.kr/api/company.json"

REPORT_CODES = {"annual": "11011", "q3": "11014", "half": "11012", "q1": "11013"}


class DartFinancialFetcher:

    async def get_corp_code(self, entity_name: str) -> Optional[str]:
        """(fallback) company.json은 이름검색 미지원이라 보통 None — 실제로는 공시 corp_code 사용."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get(DART_CORP_URL, params={"crtfc_key": DART_API_KEY, "corp_name": entity_name})
                data = res.json()
                if data.get("status") == "000" and data.get("list"):
                    return data["list"][0].get("corp_code")
        except Exception:
            pass
        return None

    async def _fetch_raw(self, corp_code: str, year: str, report_type: str) -> Optional[dict]:
        """주요계정: fs_div 파라미터 없음 → 한 응답에 CFS/OFS 행이 fs_div로 구분돼 옴."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                res = await client.get(DART_FINANCIAL_URL, params={
                    "crtfc_key": DART_API_KEY, "corp_code": corp_code,
                    "bsns_year": year, "reprt_code": REPORT_CODES[report_type],
                })
                return res.json()
        except Exception:
            return None

    async def fetch_features(self, corp_code: str, year: str, report_type: str,
                             entity_id: str, entity_name: str) -> Optional[FinancialFeatures]:
        """fetch → ChatGPT 파서(parse_opendart_financial_accounts) → FinancialFeatures."""
        resp = await self._fetch_raw(corp_code, year, report_type)
        parsed = parse_opendart_financial_accounts(
            resp or {}, strict_fs_consistency=False,  # CFS 누락계정 OFS 보완 허용
        )
        return to_financial_features(parsed, entity_id, entity_name, f"{year}-12-31")

    async def fetch_multi_period(self, corp_code: str, entity_id: str, entity_name: str,
                                 periods: int = 4) -> List[FinancialFeatures]:
        """최근 N기 FinancialFeatures (스코어용 detect_signals 입력, rate-limit sleep)."""
        out: List[FinancialFeatures] = []
        cy = datetime.now().year
        for year in range(cy - 1, cy - 3, -1):
            for rtype in ("annual", "q3", "half", "q1"):
                feat = await self.fetch_features(corp_code, str(year), rtype, entity_id, entity_name)
                if feat and (feat.total_assets or feat.sales or feat.equity):
                    out.append(feat)
                    if len(out) >= periods:
                        return out
                await asyncio.sleep(0.3)
        return out

    # ── Mythos: 1회계연도 4보고서(annual/q3/half/q1) 묶음 ──
    _RTYPE = [("annual", "11011", "12-31", 12), ("q3", "11014", "09-30", 9),
              ("half", "11012", "06-30", 6), ("q1", "11013", "03-31", 3)]

    async def fetch_mythos_rows(self, corp_code: str, entity_name: str, max_years: int = 3) -> List[dict]:
        """Mythos 저장용 — 4보고서가 모두 존재하는 가장 최근 회계연도 1개를 반환.

        period_end = 회계연도 앵커({year}-12-31), statement_end = 보고서별 실제 결산일.
        features = financial_engine.build_ratio_features (X1~X5 ratio dict).
        max_years: 거슬러 탐색할 회계연도 수 (대량 루프는 1로 DART 호출 제한).
        """
        from engines.financial_engine import FinancialEngine
        fe = FinancialEngine()
        cy = datetime.now().year
        for year in range(cy - 1, cy - 1 - max_years, -1):
            rows: List[dict] = []
            for rtype, reprt, mmdd, months in self._RTYPE:
                feat = await self.fetch_features(corp_code, str(year), rtype, corp_code, entity_name)
                await asyncio.sleep(0.3)
                if not feat or not (feat.total_assets or feat.sales or feat.equity):
                    rows = []
                    break
                rows.append({
                    "reprt_code": reprt, "report_type": rtype,
                    "period_end": f"{year}-12-31",        # 회계연도 앵커
                    "statement_end": f"{year}-{mmdd}",     # 보고서 실제 결산일
                    "period_months": months, "is_accumulated": True,
                    "features": fe.build_ratio_features(feat),
                })
            if len(rows) == 4:
                return rows
        return []

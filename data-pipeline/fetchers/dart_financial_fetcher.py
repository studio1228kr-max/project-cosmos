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
        """최근 N기 FinancialFeatures (rate-limit sleep)."""
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

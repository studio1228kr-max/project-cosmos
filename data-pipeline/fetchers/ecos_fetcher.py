"""ECOS(한국은행 경제통계시스템) API fetcher.

StatisticSearch API: 통계표코드/주기/기간/항목코드 → 시계열.
URL: {BASE}/StatisticSearch/{KEY}/json/kr/{start}/{end}/{stat}/{period}/{s_date}/{e_date}/{item}
"""
from __future__ import annotations

import os
from typing import List, Optional

import httpx

BASE_URL = os.getenv("ECOS_ENDPOINT", "https://ecos.bok.or.kr/api")
TIMEOUT = 20


def _key() -> str:
    return os.getenv("ECOS_API_KEY", "")


async def fetch_stat(stat_code: str, item_code: str, start_date: str, end_date: str,
                     period: str = "M", count: int = 100) -> List[dict]:
    """StatisticSearch 호출 → [{time, value, item_name}, ...].

    period: M(월)/D(일)/Q(분기)/A(연). start/end_date 포맷은 period에 맞춤
            (M=YYYYMM, D=YYYYMMDD).
    """
    key = _key()
    if not key:
        return []
    url = (f"{BASE_URL}/StatisticSearch/{key}/json/kr/1/{count}/"
           f"{stat_code}/{period}/{start_date}/{end_date}/{item_code}").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(url)
            data = r.json()
    except Exception:
        return []
    rows = (data.get("StatisticSearch") or {}).get("row")
    if not rows:
        return []
    out: List[dict] = []
    for row in rows:
        v = row.get("DATA_VALUE")
        if v in (None, ""):
            continue
        try:
            val = float(str(v).replace(",", ""))
        except ValueError:
            continue
        out.append({"time": row.get("TIME"), "value": val,
                    "item_name": row.get("ITEM_NAME1")})
    return out


def time_to_date(time_str: str) -> Optional[str]:
    """ECOS TIME(YYYYMM / YYYYMMDD) → ISO date(YYYY-MM-01 / YYYY-MM-DD)."""
    t = str(time_str or "")
    if len(t) == 6:
        return f"{t[:4]}-{t[4:6]}-01"
    if len(t) == 8:
        return f"{t[:4]}-{t[4:6]}-{t[6:8]}"
    return None

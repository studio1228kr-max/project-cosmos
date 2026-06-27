"""MOLIT 아파트 매매 실거래가 fetcher.

법정동코드(LAWD_CD) + 계약년월(DEAL_YMD)으로 실거래 조회 → XML 파싱 → list[dict].
주의: data.go.kr 게이트웨이는 http + 오퍼레이션 경로 + User-Agent 필요.
      dealAmount 단위는 만원(쉼표 포함) → ×10000 = 원.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import List, Optional

import httpx

TIMEOUT = 20
_UA = {"User-Agent": "Mozilla/5.0"}

# 주소 → 법정동 코드 5자리 (주요 지역, 확장 가능)
LAWD_MAP = {
    "강남구": "11680", "서초구": "11650", "송파구": "11710", "강동구": "11740",
    "마포구": "11440", "성동구": "11200", "용산구": "11170", "광진구": "11215",
    "영등포구": "11560", "여의도": "11560", "양천구": "11470", "강서구": "11500",
    "종로구": "11110", "중구": "11140", "성북구": "11290", "노원구": "11350",
    # 경기
    "분당구": "41135", "수지구": "41465", "기흥구": "41463", "일산동구": "41285",
    "일산서구": "41287", "과천": "41290", "광교": "41135",
}


def _endpoint() -> str:
    base = os.getenv("MOLIT_APT_ENDPOINT", "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev")
    base = base.replace("https://", "http://").rstrip("/")
    return base + "/getRTMSDataSvcAptTradeDev"


def _key() -> str:
    return os.getenv("DATA_GO_KR_API_KEY", "")


def address_to_lawd_cd(address: str) -> Optional[str]:
    """주소 문자열에서 법정동 코드 5자리 추출 (LAWD_MAP). 없으면 None."""
    if not address:
        return None
    for name, code in LAWD_MAP.items():
        if name in address:
            return code
    return None


def _num(s) -> int:
    s = str(s or "").replace(",", "").strip()
    try:
        return int(float(s))
    except ValueError:
        return 0


def fetch_apt_trades(lawd_cd: str, deal_ym: str) -> List[dict]:
    """단일 법정동 + 단일 년월 거래 전체 조회 → [{...}, ...]. 거래금액은 원 단위."""
    if not _key():
        return []
    params = {
        "serviceKey": _key(), "LAWD_CD": lawd_cd, "DEAL_YMD": deal_ym,
        "numOfRows": 1000, "pageNo": 1,
    }
    try:
        with httpx.Client(timeout=TIMEOUT, headers=_UA) as client:
            r = client.get(_endpoint(), params=params)
        root = ET.fromstring(r.text)
    except Exception:
        return []
    code = root.findtext(".//resultCode")
    if code not in (None, "000", "00"):
        return []
    out: List[dict] = []
    for it in root.findall(".//item"):
        def g(tag):
            return (it.findtext(tag) or "").strip()
        amt_manwon = _num(g("dealAmount"))
        if amt_manwon <= 0:
            continue
        try:
            month = int(g("dealMonth") or 0)
        except ValueError:
            month = 0
        out.append({
            "apt_name": g("aptNm"),
            "exclusive_area": float(g("excluUseAr") or 0) or None,
            "floor": _num(g("floor")) or None,
            "trade_price_krw": amt_manwon * 10000,   # 만원 → 원
            "trade_ym": f"{g('dealYear')}{month:02d}" if month else "",
            "trade_day": g("dealDay"),
            "build_year": _num(g("buildYear")) or None,
            "lawd_cd": g("sggCd") or lawd_cd,
            "umd_nm": g("umdNm"),
        })
    return out

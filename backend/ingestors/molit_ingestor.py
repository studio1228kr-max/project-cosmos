"""
MOLIT 인제스터 — 국토교통부 상업업무용 부동산 매매 실거래가 수집.
대상: 서울 + 경기(판교/분당/수원 라인) 상업·업무용 부동산
저장: molit_trade_raw → molit_trade_normalized
"""
from __future__ import annotations

import json
import logging
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras
import requests

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")
DATA_GO_KR_KEY = os.getenv("DATA_GO_KR_KEY", "")
MOLIT_URL = "http://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"
REQUEST_TIMEOUT = 30

# 서울 + 경기 판교/분당/수원 라인 법정동 코드
TARGET_LAWD = {
    # 서울
    "11110": "종로구", "11140": "중구", "11170": "용산구",
    "11200": "성동구", "11215": "광진구", "11230": "동대문구",
    "11260": "중랑구", "11290": "성북구", "11305": "강북구",
    "11320": "도봉구", "11350": "노원구", "11380": "은평구",
    "11410": "서대문구", "11440": "마포구", "11470": "양천구",
    "11500": "강서구", "11530": "구로구", "11545": "금천구",
    "11560": "영등포구", "11590": "동작구", "11620": "관악구",
    "11650": "서초구", "11680": "강남구", "11710": "송파구",
    "11740": "강동구",
    # 경기 판교/분당/수원 라인
    "41135": "성남시 수정구", "41137": "성남시 중원구", "41131": "성남시 분당구",
    "41117": "수원시 장안구", "41113": "수원시 권선구", "41115": "수원시 팔달구", "41119": "수원시 영통구",
    "41281": "용인시 처인구", "41283": "용인시 기흥구", "41285": "용인시 수지구",
}


@dataclass
class MolitTrade:
    lawd_cd: str
    deal_year: int
    deal_month: int
    deal_day: int
    deal_amount: int       # 만원
    building_use: str
    building_type: str
    build_year: Optional[int]
    floor: Optional[str]
    area: Optional[float]  # 전용면적 m²
    buyer_gbn: Optional[str]
    dealing_gbn: Optional[str]
    raw_xml: str


def get_conn():
    url = os.environ["DATABASE_URL"]
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)


def ensure_tables(conn) -> None:
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS molit_trade_raw (
        id              SERIAL PRIMARY KEY,
        lawd_cd         TEXT NOT NULL,
        deal_ym         TEXT NOT NULL,
        deal_date       DATE,
        deal_amount_man INTEGER,
        building_use    TEXT,
        building_type   TEXT,
        build_year      INTEGER,
        floor           TEXT,
        area_sqm        NUMERIC(10,2),
        buyer_gbn       TEXT,
        dealing_gbn     TEXT,
        raw_xml         TEXT,
        ingested_at     TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(lawd_cd, deal_date, deal_amount_man, area_sqm)
    );
    CREATE INDEX IF NOT EXISTS idx_molit_lawd ON molit_trade_raw(lawd_cd);
    CREATE INDEX IF NOT EXISTS idx_molit_deal_ym ON molit_trade_raw(deal_ym);

    CREATE TABLE IF NOT EXISTS molit_trade_normalized (
        id              SERIAL PRIMARY KEY,
        raw_id          INTEGER REFERENCES molit_trade_raw(id),
        lawd_cd         TEXT NOT NULL,
        sgg_nm          TEXT,
        deal_ym         TEXT NOT NULL,
        deal_date       DATE,
        deal_amount_man INTEGER,
        deal_amount_eok NUMERIC(10,2),
        building_use    TEXT,
        area_sqm        NUMERIC(10,2),
        price_per_sqm   NUMERIC(12,2),
        buyer_type      TEXT,
        normalized_at   TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_molit_norm_lawd ON molit_trade_normalized(lawd_cd);
    CREATE INDEX IF NOT EXISTS idx_molit_norm_ym ON molit_trade_normalized(deal_ym);
    """)
    conn.commit()
    cur.close()
    logger.info("molit 테이블 확인 완료")


def fetch_trades(lawd_cd: str, deal_ym: str, page: int = 1, num_rows: int = 100) -> List[MolitTrade]:
    params = {
        "serviceKey": DATA_GO_KR_KEY,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ym,
        "numOfRows": num_rows,
        "pageNo": page,
    }
    resp = requests.get(MOLIT_URL, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    result_code = root.findtext(".//resultCode", "")
    if result_code != "000":
        logger.warning("MOLIT API 오류: %s %s", lawd_cd, deal_ym)
        return []

    trades = []
    for item in root.findall(".//item"):
        def t(tag): return (item.findtext(tag) or "").strip()
        try:
            amount_str = t("dealAmount").replace(",", "")
            amount = int(amount_str) if amount_str else 0
            trades.append(MolitTrade(
                lawd_cd=lawd_cd,
                deal_year=int(t("dealYear") or 0),
                deal_month=int(t("dealMonth") or 0),
                deal_day=int(t("dealDay") or 0),
                deal_amount=amount,
                building_use=t("buildingUse"),
                building_type=t("buildingType"),
                build_year=int(t("buildYear")) if t("buildYear") else None,
                floor=t("floor") or None,
                area=float(t("buildingAr")) if t("buildingAr") else None,
                buyer_gbn=t("buyerGbn") or None,
                dealing_gbn=t("dealingGbn") or None,
                raw_xml=ET.tostring(item, encoding="unicode"),
            ))
        except Exception as e:
            logger.warning("파싱 오류: %s", e)
    return trades


def upsert_raw(conn, trade: MolitTrade, deal_ym: str) -> Optional[int]:
    cur = conn.cursor()
    deal_date = None
    if trade.deal_year and trade.deal_month and trade.deal_day:
        try:
            deal_date = date(trade.deal_year, trade.deal_month, trade.deal_day).isoformat()
        except Exception:
            pass
    cur.execute("""
        INSERT INTO molit_trade_raw
            (lawd_cd, deal_ym, deal_date, deal_amount_man, building_use,
             building_type, build_year, floor, area_sqm, buyer_gbn, dealing_gbn, raw_xml)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (lawd_cd, deal_date, deal_amount_man, area_sqm) DO NOTHING
        RETURNING id
    """, (
        trade.lawd_cd, deal_ym, deal_date, trade.deal_amount,
        trade.building_use, trade.building_type, trade.build_year,
        trade.floor, trade.area, trade.buyer_gbn, trade.dealing_gbn, trade.raw_xml,
    ))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    return row["id"] if row else None


def normalize_raw(conn, raw_id: int, trade: MolitTrade, deal_ym: str, sgg_nm: str) -> None:
    deal_date = None
    if trade.deal_year and trade.deal_month and trade.deal_day:
        try:
            deal_date = date(trade.deal_year, trade.deal_month, trade.deal_day).isoformat()
        except Exception:
            pass
    deal_amount_eok = round(trade.deal_amount / 10000, 2) if trade.deal_amount else None
    price_per_sqm = round(trade.deal_amount * 10000 / trade.area, 0) if trade.deal_amount and trade.area else None
    buyer_type = "법인" if trade.buyer_gbn and "법인" in trade.buyer_gbn else "개인"
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO molit_trade_normalized
            (raw_id, lawd_cd, sgg_nm, deal_ym, deal_date, deal_amount_man,
             deal_amount_eok, building_use, area_sqm, price_per_sqm, buyer_type)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """, (raw_id, trade.lawd_cd, sgg_nm, deal_ym, deal_date, trade.deal_amount,
          deal_amount_eok, trade.building_use, trade.area, price_per_sqm, buyer_type))
    conn.commit()
    cur.close()


def run_ingestion(months_back: int = 3) -> Dict[str, Any]:
    if not DATA_GO_KR_KEY:
        raise ValueError("DATA_GO_KR_KEY 없음")

    conn = get_conn()
    ensure_tables(conn)

    today = date.today()
    deal_yms = []
    for i in range(months_back):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        deal_yms.append(f"{y}{m:02d}")

    stats = {"lawd_count": 0, "fetched": 0, "inserted": 0, "errors": 0}

    for lawd_cd, sgg_nm in TARGET_LAWD.items():
        for deal_ym in deal_yms:
            try:
                page = 1
                while True:
                    trades = fetch_trades(lawd_cd, deal_ym, page)
                    if not trades:
                        break
                    stats["fetched"] += len(trades)
                    for trade in trades:
                        raw_id = upsert_raw(conn, trade, deal_ym)
                        if raw_id:
                            normalize_raw(conn, raw_id, trade, deal_ym, sgg_nm)
                            stats["inserted"] += 1
                    if len(trades) < 100:
                        break
                    page += 1
            except Exception as e:
                logger.warning("오류 lawd=%s ym=%s: %s", lawd_cd, deal_ym, e)
                stats["errors"] += 1
        stats["lawd_count"] += 1

    conn.close()
    logger.info("MOLIT 수집 완료: %s", stats)
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run_ingestion(months_back=3)
    print(json.dumps(result, ensure_ascii=False, indent=2))

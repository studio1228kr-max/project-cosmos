"""
DART 인제스터 — OpenDART API에서 차주 공시 이벤트를 수집해 DB에 저장.
수집 대상: 회생절차, 기한이익상실, 감사보고서 의견거절/한정, 자본잠식
저장 테이블: dart_disclosure_events
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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
SOURCE = "DART"
KST = ZoneInfo("Asia/Seoul")
DART_API_BASE = "https://opendart.fss.or.kr/api"
DART_API_KEY = os.getenv("DART_API_KEY", "")
REQUEST_TIMEOUT = 30

# 수집할 공시 키워드 → 이벤트 타입 매핑
DISCLOSURE_FILTER: Dict[str, str] = {
    "회생절차": "REHAB_FILING",
    "기한이익상실": "COVENANT_BREACH",
    "자본잠식": "CAPITAL_IMPAIRMENT",
    "감사의견": "AUDIT_OPINION_ISSUE",
    "불성실공시": "NONCOMPLIANT_DISCLOSURE",
    "영업정지": "BUSINESS_SUSPENSION",
    "상장폐지": "DELISTING",
}

# 감사보고서 의견 부적정/한정/의견거절
AUDIT_NEGATIVE_OPINIONS = {"한정", "부적정", "의견거절"}


@dataclass
class DartEvent:
    corp_code: str
    corp_name: str
    rcept_no: str          # 접수번호 (unique)
    report_nm: str         # 공시명
    rcept_dt: str          # 접수일자 YYYYMMDD
    event_type: str        # REHAB_FILING | COVENANT_BREACH | ...
    raw_json: dict


def get_conn():
    url = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def ensure_table(conn) -> None:
    """dart_disclosure_events 테이블 없으면 생성."""
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dart_disclosure_events (
        id              SERIAL PRIMARY KEY,
        corp_code       TEXT NOT NULL,
        corp_name       TEXT,
        rcept_no        TEXT NOT NULL UNIQUE,
        report_nm       TEXT,
        rcept_dt        DATE,
        event_type      TEXT NOT NULL,
        raw_json        JSONB,
        deal_master_id  INTEGER REFERENCES deal_master(id),
        ingested_at     TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_dart_corp_code ON dart_disclosure_events(corp_code);
    CREATE INDEX IF NOT EXISTS idx_dart_event_type ON dart_disclosure_events(event_type);
    CREATE INDEX IF NOT EXISTS idx_dart_deal ON dart_disclosure_events(deal_master_id);
    """)
    conn.commit()
    cur.close()
    logger.info("dart_disclosure_events 테이블 확인 완료")


def search_disclosures(
    bgn_de: str,
    end_de: str,
    pblntf_ty: str = None,   # A=정기공시, B=주요사항보고, C=발행공시
    page_no: int = 1,
    page_count: int = 100,
) -> List[dict]:
    """OpenDART 공시검색 API 호출."""
    url = f"{DART_API_BASE}/list.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "bgn_de": bgn_de,
        "end_de": end_de,
        **({"pblntf_ty": pblntf_ty} if pblntf_ty else {}),
        "page_no": page_no,
        "page_count": page_count,
        "sort": "date",
        "sort_mth": "desc",
    }
    resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "000":
        logger.warning("DART API 오류: %s %s", data.get("status"), data.get("message"))
        return []
    return data.get("list", [])


def classify_event(report_nm: str) -> Optional[str]:
    """공시명 → 이벤트 타입 분류."""
    for keyword, event_type in DISCLOSURE_FILTER.items():
        if keyword in report_nm:
            return event_type
    return None


def map_to_deal(conn, corp_name: str) -> Optional[int]:
    """차주명으로 deal_master 매핑 시도."""
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM deal_master
        WHERE borrower_name ILIKE %s OR deal_name ILIKE %s
        LIMIT 1
    """, (f"%{corp_name}%", f"%{corp_name}%"))
    row = cur.fetchone()
    cur.close()
    return row["id"] if row else None


def upsert_event(conn, event: DartEvent, deal_id: Optional[int]) -> bool:
    """이미 있으면 skip, 없으면 insert. True=신규."""
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO dart_disclosure_events
        (corp_code, corp_name, rcept_no, report_nm, rcept_dt,
         event_type, raw_json, deal_master_id)
    VALUES (%s, %s, %s, %s, TO_DATE(%s, 'YYYYMMDD'), %s, %s, %s)
    ON CONFLICT (rcept_no) DO NOTHING
    RETURNING id
    """, (
        event.corp_code, event.corp_name, event.rcept_no, event.report_nm,
        event.rcept_dt, event.event_type,
        json.dumps(event.raw_json, ensure_ascii=False), deal_id,
    ))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    return row is not None


def run_ingestion(lookback_days: int = 90) -> Dict[str, int]:
    """메인 수집 함수."""
    if not DART_API_KEY:
        raise ValueError("DART_API_KEY 환경변수 없음")

    conn = get_conn()
    ensure_table(conn)

    end_de = date.today().strftime("%Y%m%d")
    bgn_de = (date.today() - timedelta(days=lookback_days)).strftime("%Y%m%d")

    logger.info("DART 수집 시작: %s ~ %s", bgn_de, end_de)

    stats = {"fetched": 0, "classified": 0, "inserted": 0, "mapped_to_deal": 0}

    # 주요사항보고(B) — 회생, 기한이익상실이 주로 여기 있음
    for pblntf_ty in [None, "B"]:
        page_no = 1
        while True:
            items = search_disclosures(bgn_de, end_de, pblntf_ty, page_no)
            if not items:
                break

            stats["fetched"] += len(items)

            for item in items:
                report_nm = item.get("report_nm", "")
                event_type = classify_event(report_nm)
                if not event_type:
                    continue

                stats["classified"] += 1
                corp_name = item.get("corp_name", "")
                deal_id = map_to_deal(conn, corp_name)
                if deal_id:
                    stats["mapped_to_deal"] += 1

                event = DartEvent(
                    corp_code=item.get("corp_code", ""),
                    corp_name=corp_name,
                    rcept_no=item.get("rcept_no", ""),
                    report_nm=report_nm,
                    rcept_dt=item.get("rcept_dt", ""),
                    event_type=event_type,
                    raw_json=item,
                )
                if upsert_event(conn, event, deal_id):
                    stats["inserted"] += 1

            if len(items) < 100:
                break
            page_no += 1

    logger.info("DART 수집 완료: %s", stats)
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run_ingestion(lookback_days=90)
    print(json.dumps(result, ensure_ascii=False, indent=2))

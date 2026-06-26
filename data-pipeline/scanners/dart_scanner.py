"""DART Scanner — backend/ingestors/dart_ingestor.py 의 수집 로직 이전 + BaseScanner 상속.

G1 스코어링: 원본 dart_scanner(G1 버그 코드)가 레포에 없어 스펙 §5의 올바른 로직을
신규 구현(= 결과적으로 버그 수정). 2개 키워드가 잘못 P2로 분류되던 문제를 보정한
calculate_g1_score 사용.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx

import db
from engines.financial_engine import FinancialEngine
from extractors.cb_term_extractor import CBTermExtractor
from fetchers.dart_financial_fetcher import DartFinancialFetcher
from normalizers.dart_normalizer import normalize_dart
from resolvers.entity_resolver import EntityResolver
from scanners.base_scanner import BaseScanner, NormalizedSignal, RawEvent

CB_KEYWORDS = ["전환사채", "신주인수권부사채", "교환사채", "전환우선주"]

# 모듈 싱글톤 — 한 워커 프로세스 내 entity_id 안정성 확보 (재시작 시 리셋: persist는 다음 단계)
_entity_resolver = EntityResolver()

DART_API_BASE = "https://opendart.fss.or.kr/api"
REQUEST_TIMEOUT = 30

# G1 키워드 (확장)
G1_KEYWORDS_EXTENDED = [
    "사모사채", "사모대출", "메자닌", "CB", "BW",
    "선순위대출", "후순위대출", "시니어론", "코메자닌",
    "임대형리츠", "공모리츠", "위탁관리리츠",
    "캡레이트", "cap rate", "수익률",
    # 부실/이벤트 키워드
    "회생절차", "기한이익상실", "자본잠식", "감사의견", "상장폐지",
]


def calculate_g1_score(g1_count: int, base_score: int) -> int:
    """G1 키워드 수에 따른 부스트. (구버전 25점 과다부여 → P2 오분류 버그 보정)"""
    boost = 0
    if g1_count >= 3:
        boost = 35   # +20 +15
    elif g1_count >= 2:
        boost = 20   # +20
    return base_score + boost


def g1_count_in(text: str) -> int:
    t = text or ""
    return sum(1 for kw in G1_KEYWORDS_EXTENDED if kw in t)


def priority_bucket(total_score: int) -> str:
    """P0(최우선) / P1 / P2. 임계값은 보정 기준."""
    if total_score >= 50:
        return "P0"
    if total_score >= 30:
        return "P1"
    return "P2"


class DartScanner(BaseScanner):
    VERSION = "v0.1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DART_API_KEY", "")
        self.financial_fetcher = DartFinancialFetcher()
        self.financial_engine = FinancialEngine()
        self.cb_extractor = CBTermExtractor()
        # 재무 fetch 비활성 옵션 (DART API 부하/디버그용)
        self.financial_enabled = os.getenv("FINANCIAL_FETCH_ENABLED", "true").lower() != "false"
        # 대량 재무 fetch 루프 시 회계연도 탐색 폭 (DART 호출 제한)
        self.bulk_fetch_max_years = int(os.getenv("BULK_FETCH_MAX_YEARS", "1"))

    async def run(self, **kwargs) -> dict:
        """BaseScanner.run() → 그 뒤 normalize 무관 전체 corp_code 재무 fetch 루프(Sprint #3)."""
        result = await super().run(**kwargs)
        corp_map = result.pop("corp_map", {}) or {}
        if self.financial_enabled and corp_map:
            try:
                result["financial_fetch"] = await self.run_financial_fetch_loop(corp_map)
            except Exception as e:
                print(f"financial fetch loop error: {e}")
                result["financial_fetch"] = {"error": str(e)}
        return result

    async def run_financial_fetch_loop(self, corp_map: dict) -> dict:
        """스캔된 전체 corp_code 재무 fetch → Mythos 저장 + financial_fetch_log.

        normalize/signal 루프와 완전 격리(try/except). 오늘 이미 fetch한 corp는 SKIP.
        """
        already = await asyncio.to_thread(db.get_today_fetched_corps)
        stats = {"total": len(corp_map), "SUCCESS": 0, "EMPTY": 0, "FAILED": 0, "SKIP": 0, "saved_periods": 0}
        for corp_code, entity_name in corp_map.items():
            if corp_code in already:
                stats["SKIP"] += 1
                continue
            try:
                rows = await self.financial_fetcher.fetch_mythos_rows(
                    corp_code, entity_name or "", max_years=self.bulk_fetch_max_years)
                if not rows:
                    await asyncio.to_thread(db.save_fetch_log, corp_code, "EMPTY", 0, None)
                    stats["EMPTY"] += 1
                    continue
                await asyncio.to_thread(db.save_financial_rows, corp_code, rows)
                await asyncio.to_thread(db.save_fetch_log, corp_code, "SUCCESS", len(rows), None)
                stats["SUCCESS"] += 1
                stats["saved_periods"] += len(rows)
            except Exception as e:
                # 실패 격리 — 다음 corp_code 계속 (즉시 재시도 금지)
                try:
                    await asyncio.to_thread(db.save_fetch_log, corp_code, "FAILED", 0, str(e))
                except Exception:
                    pass
                stats["FAILED"] += 1
            await asyncio.sleep(0.5)   # DART rate-limit
        print(json.dumps({"financial_fetch": stats}, ensure_ascii=False))
        return stats

    async def scan(self, bgn_de: str = None, end_de: str = None, page_count: int = 100, **kwargs) -> List[RawEvent]:
        if not self.api_key:
            raise ValueError("DART_API_KEY 없음")
        params = {
            "crtfc_key": self.api_key,
            "bgn_de": bgn_de or end_de or datetime.now(timezone.utc).strftime("%Y%m%d"),
            "end_de": end_de or datetime.now(timezone.utc).strftime("%Y%m%d"),
            "page_no": 1, "page_count": page_count, "sort": "date", "sort_mth": "desc",
        }
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(f"{DART_API_BASE}/list.json", params=params)
            resp.raise_for_status()
            data = resp.json()
        if data.get("status") != "000":
            return []

        events: List[RawEvent] = []
        for item in data.get("list", []):
            report_nm = item.get("report_nm", "")
            rcept_no = item.get("rcept_no", "")
            corp_name = item.get("corp_name", "")
            observed = None
            rcept_dt = item.get("rcept_dt", "")
            if rcept_dt and len(rcept_dt) == 8:
                observed = datetime.strptime(rcept_dt, "%Y%m%d").replace(tzinfo=timezone.utc)
            events.append(RawEvent(
                source="DART",
                source_ref_id=rcept_no,
                source_url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                observed_at=observed,
                entity_name=corp_name,
                entity_id=item.get("corp_code"),
                entity_type="CORP",
                raw_content=report_nm,
                dedupe_key=hashlib.sha1(f"DART:{rcept_no}".encode()).hexdigest(),
                scanner_version=self.VERSION,
                raw_json=item,   # Raw Data Lake (v2.9)
            ))
        return events

    async def normalize(self, raw_event: RawEvent) -> Optional[NormalizedSignal]:
        signal = normalize_dart(raw_event)
        if signal is None:
            return None
        # G1 부스트를 subtype 으로 태깅 (스코어링 단계 입력)
        g1c = g1_count_in(raw_event.raw_content)
        if g1c >= 2:
            base = 10
            total = calculate_g1_score(g1c, base)
            signal.signal_subtype = f"G1x{g1c}:{priority_bucket(total)}"

        # Entity Resolution → entity_event_timeline 적재
        try:
            res = _entity_resolver.resolve({
                "source": "DART",
                "corp_code": raw_event.entity_id,
                "corp_name": raw_event.entity_name,
                "as_of_date": raw_event.observed_at,
            })
            eid = res.get("entity_id") or raw_event.entity_id or "UNKNOWN"
            await asyncio.to_thread(db.save_entity_event, eid, raw_event, signal)
        except Exception as e:
            print(f"entity resolve error {raw_event.entity_name}: {e}")

        # v2.9 ingestion: 분류된 신호에만 재무/CB 데이터 fetch (호출량 제한)
        if self.financial_enabled:
            signal.financial_signals = await self._fetch_and_score_financial(raw_event)
            if self._is_cb_disclosure(raw_event):
                signal.cb_signals = await self._extract_cb_terms(raw_event)
        return signal

    async def _fetch_and_score_financial(self, raw_event: RawEvent) -> List[dict]:
        """corp_code(=entity_id) 재무제표 fetch → Z-score/ICR 신호 (스코어 전용).

        Mythos 저장은 Sprint #3에서 run_financial_fetch_loop(전체 corp_code)로 분리됨.
        여기선 normalize 통과 신호의 스코어링을 위한 raw FinancialFeatures만 사용한다.
        """
        corp_code = raw_event.entity_id or await self.financial_fetcher.get_corp_code(raw_event.entity_name)
        if not corp_code:
            return []
        try:
            features = await self.financial_fetcher.fetch_multi_period(
                corp_code, raw_event.entity_id or corp_code, raw_event.entity_name, periods=4)
            if not features:
                return []
            return self.financial_engine.detect_signals(features[0], features[1:])
        except Exception as e:
            print(f"financial fetch error {raw_event.entity_name}: {e}")
            return []

    def _is_cb_disclosure(self, raw_event: RawEvent) -> bool:
        text = raw_event.raw_content or ""
        return any(kw in text for kw in CB_KEYWORDS)

    async def _extract_cb_terms(self, raw_event: RawEvent) -> List[dict]:
        """CB 공시 원문 fetch → Claude 추출 → 위험 신호."""
        try:
            raw_text = await self._fetch_disclosure_text(raw_event.source_ref_id)
            if not raw_text:
                return []
            ext = await asyncio.to_thread(
                self.cb_extractor.extract, raw_text,
                raw_event.entity_id or "", raw_event.entity_name, raw_event.source_ref_id,
            )
            if ext.get("error"):
                return []
            await asyncio.to_thread(db.save_cb_extraction, {**ext, "raw_text": raw_text})
            return self.cb_extractor.to_signals(ext)
        except Exception as e:
            print(f"cb extraction error {raw_event.entity_name}: {e}")
            return []

    async def _fetch_disclosure_text(self, rcept_no: str) -> str:
        """DART 정식 문서 API(document.xml) — ZIP→XML 본문 추출.

        (구버전: dart.fss.or.kr 뷰어 HTML 스크래핑은 JS 프레임 껍데기라 본문 0자 →
         CB 추출 0건의 직접 원인이었음. document.xml은 실제 공시 원문 XML을 반환.)
        """
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                res = await client.get(f"{DART_API_BASE}/document.xml",
                                       params={"crtfc_key": self.api_key, "rcept_no": rcept_no})
            if res.status_code != 200 or res.content[:2] != b"PK":  # ZIP 매직 아님(=에러 XML)
                return ""
            import io
            import zipfile
            import re
            z = zipfile.ZipFile(io.BytesIO(res.content))
            raw = z.read(z.namelist()[0])
            doc = None
            for enc in ("utf-8", "euc-kr", "cp949"):
                try:
                    doc = raw.decode(enc)
                    break
                except Exception:
                    continue
            if not doc:
                return ""
            text = re.sub(r"<[^>]+>", " ", doc)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:12000]
        except Exception:
            return ""

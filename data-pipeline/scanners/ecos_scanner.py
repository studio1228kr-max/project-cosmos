"""ECOS Scanner (Sprint #6) — 한국은행 매크로 지표 수집 → macro_indicators.

수집:
  BASE_RATE      722Y001/0101000 (월)  한국은행 기준금리
  CORP_BOND_AA3  817Y002/010300000 (일) 회사채(3년, AA-)
  TREASURY_3Y    817Y002/010200000 (일) 국고채(3년)
  CREDIT_SPREAD  = CORP_BOND_AA3 - TREASURY_3Y (bp)  시장 신용위험 온도계

sector_cycle 엔진이 BASE_RATE / CREDIT_SPREAD 최신값을 읽어 스코어에 반영.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import db
from fetchers.ecos_fetcher import fetch_stat, time_to_date


class EcosScanner:
    source_name = "ECOS"
    refresh_cycle = "monthly"
    signal_tier = "A"

    async def scan(self) -> dict:
        now = datetime.now()
        rows = []   # (code, name, value, period_date, source)
        stats = {"BASE_RATE": 0, "CORP_BOND_AA3": 0, "TREASURY_3Y": 0, "CREDIT_SPREAD": 0}

        # 1) 기준금리 (월, 최근 ~13개월)
        ym_end = now.strftime("%Y%m")
        ym_start = (now.replace(day=1) - timedelta(days=400)).strftime("%Y%m")
        base = await fetch_stat("722Y001", "0101000", ym_start, ym_end, "M")
        for r in base:
            d = time_to_date(r["time"])
            if d:
                rows.append(("BASE_RATE", "한국은행 기준금리", r["value"], d, "ECOS"))
                stats["BASE_RATE"] += 1

        # 2) 회사채 AA- 3년 / 국고채 3년 (일, 최근 ~45일) → 스프레드(bp)
        d_end = now.strftime("%Y%m%d")
        d_start = (now - timedelta(days=45)).strftime("%Y%m%d")
        corp = await fetch_stat("817Y002", "010300000", d_start, d_end, "D")
        tre = await fetch_stat("817Y002", "010200000", d_start, d_end, "D")
        tre_by_date = {time_to_date(r["time"]): r["value"] for r in tre}
        for r in corp:
            d = time_to_date(r["time"])
            if not d:
                continue
            rows.append(("CORP_BOND_AA3", "회사채(3년,AA-)", r["value"], d, "ECOS"))
            stats["CORP_BOND_AA3"] += 1
            tv = tre_by_date.get(d)
            if tv is not None:
                rows.append(("TREASURY_3Y", "국고채(3년)", tv, d, "ECOS"))
                stats["TREASURY_3Y"] += 1
                spread_bp = round((r["value"] - tv) * 100, 1)  # %p → bp
                rows.append(("CREDIT_SPREAD", "회사채AA- 스프레드(bp)", spread_bp, d, "ECOS"))
                stats["CREDIT_SPREAD"] += 1

        # 3) 기업경기실사지수 BSI (월) — 512Y015: 업종(C0000제조/Y9900비제조/99988전산업) × 업황실적BSI(AA)
        #    (KOSIS BSI 표 DT_512Y007의 업종 objL1이 포털 잠금이라, 동일 한국은행 BSI를 ECOS에서 수집)
        for code, item, name in [
            ("BSI_MANUFACTURING", "C0000/AA", "제조업 업황실적BSI"),
            ("BSI_NONMANUFACTURING", "Y9900/AA", "비제조업 업황실적BSI"),
            ("BSI_ALL", "99988/AA", "전산업 업황실적BSI"),
        ]:
            bsi = await fetch_stat("512Y015", item, ym_start, ym_end, "M")
            for r in bsi:
                d = time_to_date(r["time"])
                if d:
                    rows.append((code, name, r["value"], d, "ECOS-BSI"))
                    stats[code] = stats.get(code, 0) + 1

        saved = await asyncio.to_thread(db.save_macro_indicators_bulk, rows)
        return {"scanner": "ECOS", "saved": stats, "rows": saved}

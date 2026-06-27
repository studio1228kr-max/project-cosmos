"""MOLIT Scanner (Sprint #8) — 담보 아파트 실거래가 → LTV → collateral_coverage.

scan_deal: 딜 담보 주소 → 법정동코드 → 최근 6개월 실거래 fetch → 동일 아파트
           비교거래 중위값 = gross_value → net_ltv = target_debt/gross_value 저장.
scan_all_deals: deal_master에서 담보주소(asset_address) 있는 딜 전체 처리.
"""
from __future__ import annotations

import asyncio
import statistics
from datetime import datetime, timedelta

import db
from fetchers.molit_fetcher import fetch_apt_trades, address_to_lawd_cd


def _recent_yms(n: int = 6):
    """현재월 기준 최근 n개월 YYYYMM 리스트."""
    now = datetime.now()
    out = []
    y, m = now.year, now.month
    for _ in range(n):
        out.append(f"{y}{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return out


def _confidence(n: int) -> str:
    if n >= 5:
        return "HIGH"
    if n >= 2:
        return "MEDIUM"
    return "LOW"


class MolitScanner:
    source_name = "MOLIT"
    refresh_cycle = "monthly"
    signal_tier = "S"

    async def scan_deal(self, deal_id: str, address: str, target_debt: int,
                        apt_hint: str = None) -> dict:
        """담보 주소 실거래 → LTV 계산 + 저장."""
        lawd_cd = address_to_lawd_cd(address)
        if not lawd_cd:
            return {"deal_id": deal_id, "skipped": "no_lawd_cd", "address": address}

        # 최근 6개월 실거래 수집
        all_trades = []
        for ym in _recent_yms(6):
            trades = await asyncio.to_thread(fetch_apt_trades, lawd_cd, ym)
            for t in trades:
                t["deal_id"] = deal_id
                t["address_raw"] = address
            all_trades.extend(trades)
            await asyncio.sleep(0.2)

        # 가격이력 저장
        rows = [(t["deal_id"], t["address_raw"], t["lawd_cd"], t["apt_name"],
                 t["exclusive_area"], t["floor"], t["trade_price_krw"],
                 t["trade_ym"], t["trade_day"], t["build_year"]) for t in all_trades]
        await asyncio.to_thread(db.save_collateral_prices_bulk, rows)

        # 비교거래 필터: apt_hint(아파트명) 있으면 동일 아파트, 없으면 동(umd) 단위 전체
        comps = all_trades
        if apt_hint:
            comps = [t for t in all_trades if apt_hint in (t["apt_name"] or "")] or all_trades

        prices = [t["trade_price_krw"] for t in comps if t["trade_price_krw"] > 0]
        n = len(prices)
        if n == 0:
            await asyncio.to_thread(db.save_ltv_snapshot, deal_id, None, target_debt,
                                    None, None, 0, "MOLIT_ESTIMATED", "LOW", "비교거래 없음")
            return {"deal_id": deal_id, "comparable_count": 0, "confidence": "LOW", "net_ltv": None}

        gross_value = int(statistics.median(prices))
        net_ltv = round(target_debt / gross_value, 4) if gross_value else None
        coverage = round(gross_value / target_debt, 4) if target_debt else None
        conf = _confidence(n)
        await asyncio.to_thread(
            db.save_ltv_snapshot, deal_id, gross_value, target_debt, net_ltv, coverage,
            n, "MOLIT_ACTUAL", conf, f"lawd={lawd_cd} 비교 {n}건 중위값")
        return {"deal_id": deal_id, "gross_value": gross_value, "target_debt": target_debt,
                "net_ltv": net_ltv, "coverage_ratio": coverage,
                "comparable_count": n, "confidence": conf}

    async def scan_all_deals(self) -> dict:
        """deal_master에서 담보주소 있는 딜 전체 → scan_deal."""
        rows = await asyncio.to_thread(self._deals_with_collateral)
        results = []
        for deal_code, address, target_debt in rows:
            try:
                results.append(await self.scan_deal(deal_code, address, int(target_debt or 0)))
            except Exception as e:
                results.append({"deal_id": deal_code, "error": str(e)[:120]})
        return {"scanner": "MOLIT", "deals": len(rows), "results": results}

    @staticmethod
    def _deals_with_collateral():
        conn = db.get_conn()
        cur = conn.cursor()
        # asset_address(담보주소) + exposure_amount(목표대출, 원) 있는 딜
        cur.execute("""SELECT deal_code, asset_address, exposure_amount FROM deal_master
                       WHERE asset_address IS NOT NULL AND asset_address <> ''
                         AND exposure_amount IS NOT NULL AND exposure_amount > 0""")
        rows = [(r["deal_code"], r["asset_address"], r["exposure_amount"]) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return rows

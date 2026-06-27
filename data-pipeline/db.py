"""data-pipeline DB 헬퍼 (동기 psycopg2). base_scanner 에서 asyncio.to_thread 로 호출."""
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)


# ── Mythos 재무 피처 파이프라인 (append-only versions + current projection) ──
_pool = None
_pipeline = None


def get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        # 기본 tuple cursor (Mythos는 row[0] 인덱스 접근)
        _pool = ThreadedConnectionPool(1, 5, dsn=os.environ["DATABASE_URL"])
    return _pool


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from mythos_financial_feature_pipeline import MythosFinancialFeaturePipeline
        _pipeline = MythosFinancialFeaturePipeline(get_pool())
    return _pipeline


def save_financial_rows(entity_id: str, mythos_rows: list) -> None:
    """Mythos 저장 — 1회계연도 4보고서 dict 리스트 → versions append + current upsert."""
    from mythos_financial_feature_pipeline import canonicalize_rows
    rows = canonicalize_rows(entity_id=entity_id, fetched_rows=mythos_rows,
                             require_single_period_end=True)
    get_pipeline().save_rows(rows=rows, expected_report_types={"annual", "q3", "half", "q1"})


# ── Sprint #3: 재무 fetch 로그 (normalize 무관 전체 corp_code 루프) ──
def save_fetch_log(corp_code: str, status: str, periods_saved: int = 0, error_msg=None) -> None:
    """financial_fetch_log 기록. status: SUCCESS / FAILED / EMPTY / SKIP."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO financial_fetch_log (corp_code, fetch_status, periods_saved, error_msg)
           VALUES (%s,%s,%s,%s)""",
        (corp_code, status, periods_saved, (error_msg or None) and str(error_msg)[:1000]),
    )
    conn.commit()
    cur.close()
    conn.close()


def save_macro_indicator(code: str, name: str, value: float, period_date: str, source: str = "ECOS") -> None:
    """macro_indicators upsert (indicator_code, period_date)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO macro_indicators (indicator_code, indicator_name, value, period_date, source)
           VALUES (%s,%s,%s,%s,%s)
           ON CONFLICT (indicator_code, period_date)
           DO UPDATE SET value=EXCLUDED.value, indicator_name=EXCLUDED.indicator_name, fetched_at=NOW()""",
        (code, name, value, period_date, source),
    )
    conn.commit()
    cur.close()
    conn.close()


def save_macro_indicators_bulk(rows: list) -> int:
    """macro_indicators 일괄 upsert. rows=[(code,name,value,period_date,source),...]. 1커넥션."""
    if not rows:
        return 0
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany(
        """INSERT INTO macro_indicators (indicator_code, indicator_name, value, period_date, source)
           VALUES (%s,%s,%s,%s,%s)
           ON CONFLICT (indicator_code, period_date)
           DO UPDATE SET value=EXCLUDED.value, indicator_name=EXCLUDED.indicator_name, fetched_at=NOW()""",
        rows,
    )
    conn.commit()
    cur.close()
    conn.close()
    return len(rows)


def save_collateral_prices_bulk(rows: list) -> int:
    """collateral_price_history 일괄 upsert. rows=[(deal_id,address_raw,lawd_cd,apt_name,
    exclusive_area,floor,trade_price_krw,trade_ym,trade_day,build_year),...]."""
    if not rows:
        return 0
    # 배치 내 충돌키(lawd,apt,area,floor,ym,day=idx 2,3,4,5,7,8) 중복 제거 (마지막 유지)
    dedup = {}
    for r in rows:
        dedup[(r[2], r[3], r[4], r[5], r[7], r[8])] = r
    rows = list(dedup.values())
    conn = get_conn()
    cur = conn.cursor()
    # execute_values: 행별 round-trip 대신 1배치 INSERT (강남 등 대량 거래 대응)
    psycopg2.extras.execute_values(
        cur,
        """INSERT INTO collateral_price_history
           (deal_id,address_raw,lawd_cd,apt_name,exclusive_area,floor,
            trade_price_krw,trade_ym,trade_day,build_year)
           VALUES %s
           ON CONFLICT (lawd_cd, apt_name, exclusive_area, floor, trade_ym, trade_day)
           DO UPDATE SET trade_price_krw=EXCLUDED.trade_price_krw,
             deal_id=COALESCE(EXCLUDED.deal_id, collateral_price_history.deal_id), fetched_at=NOW()""",
        rows, page_size=500,
    )
    conn.commit()
    cur.close()
    conn.close()
    return len(rows)


def save_ltv_snapshot(deal_id, gross_value, target_debt, net_ltv, coverage_ratio,
                      comparable_count, price_source, confidence, notes) -> None:
    """collateral_ltv_snapshot upsert (deal_id, calc_date=오늘)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO collateral_ltv_snapshot
           (deal_id,gross_value,target_debt,net_ltv,coverage_ratio,comparable_count,price_source,confidence,notes)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (deal_id, calc_date) DO UPDATE SET
             gross_value=EXCLUDED.gross_value, target_debt=EXCLUDED.target_debt,
             net_ltv=EXCLUDED.net_ltv, coverage_ratio=EXCLUDED.coverage_ratio,
             comparable_count=EXCLUDED.comparable_count, price_source=EXCLUDED.price_source,
             confidence=EXCLUDED.confidence, notes=EXCLUDED.notes, fetched_at=NOW()""",
        (deal_id, gross_value, target_debt, net_ltv, coverage_ratio,
         comparable_count, price_source, confidence, notes),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_latest_ltv(deal_id: str):
    """딜의 최신 LTV 스냅샷 (net_ltv) — collateral_coverage용. 없으면 None."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT net_ltv, confidence FROM collateral_ltv_snapshot WHERE deal_id=%s ORDER BY calc_date DESC LIMIT 1",
        (deal_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return (float(row["net_ltv"]) if row and row["net_ltv"] is not None else None,
            row["confidence"] if row else None)


def get_latest_macro(code: str):
    """지표의 최신 값 (없으면 None)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT value FROM macro_indicators WHERE indicator_code=%s ORDER BY period_date DESC LIMIT 1",
        (code,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return float(row["value"]) if row else None


def get_today_fetched_corps() -> set:
    """오늘(batch_date=CURRENT_DATE) 이미 fetch 시도한 corp_code 집합 (중복 방지)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT corp_code FROM financial_fetch_log WHERE batch_date = CURRENT_DATE")
    out = {r["corp_code"] for r in cur.fetchall()}
    cur.close()
    conn.close()
    return out


def ensure_schema():
    """schema.sql 적용 (재실행 안전)."""
    sql = (Path(__file__).resolve().parent / "schema.sql").read_text(encoding="utf-8")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()


def save_raw_event(event) -> int:
    """raw_source_events upsert. 기존이면 기존 id 반환."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO raw_source_events
            (source, source_ref_id, source_url, observed_at, entity_name, entity_id,
             entity_type, raw_content, dedupe_key, scanner_version,
             raw_json, parser_version, parse_success)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (dedupe_key) DO NOTHING
        RETURNING id
        """,
        (event.source, event.source_ref_id, event.source_url, event.observed_at,
         event.entity_name, event.entity_id, event.entity_type, event.raw_content,
         event.dedupe_key, event.scanner_version,
         json.dumps(event.raw_json, ensure_ascii=False) if event.raw_json else None,
         event.scanner_version, True),
    )
    row = cur.fetchone()
    if row is None:
        cur.execute("SELECT id FROM raw_source_events WHERE dedupe_key = %s", (event.dedupe_key,))
        row = cur.fetchone()
    conn.commit()
    rid = row["id"]
    cur.close()
    conn.close()
    return rid


def save_normalized(signal) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO normalized_signals
            (raw_event_id, source, entity_name, entity_id, signal_type, signal_subtype,
             normalized_summary, severity, confidence, evidence_quality, observed_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (signal.raw_event_id, signal.source, signal.entity_name, signal.entity_id,
         signal.signal_type, signal.signal_subtype, signal.normalized_summary,
         signal.severity, signal.confidence, signal.evidence_quality, signal.observed_at),
    )
    nid = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return nid


def save_scored(normalized_signal_id, entity_name, entity_id, scores: dict, agg: dict) -> int:
    """scored_signals + signal_model_results 저장."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO scored_signals
            (normalized_signal_id, entity_name, entity_id,
             score_credit_deterioration, score_refinancing_pressure, score_collateral_coverage,
             score_enforcement_pathway, score_sector_cycle, aggregate_score,
             suggested_deal_type, urgency, reason_codes, thesis_suggestion, scoring_version)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (normalized_signal_id) DO NOTHING
        RETURNING id
        """,
        (normalized_signal_id, entity_name, entity_id,
         scores.get('credit_deterioration', 0), scores.get('refinancing_pressure', 0),
         scores.get('collateral_coverage', 0), scores.get('enforcement_pathway', 0),
         scores.get('sector_cycle', 0), agg['aggregate_score'],
         agg['suggested_deal_type'], agg['urgency'],
         json.dumps(agg['reason_codes'], ensure_ascii=False), agg['thesis_suggestion'],
         agg.get('scoring_version', 'v0_rule')),
    )
    row = cur.fetchone()   # ON CONFLICT DO NOTHING → 이미 채점됨이면 None
    conn.commit()
    cur.close()
    conn.close()
    return row["id"] if row else None


def save_entity_event(entity_id: str, raw_event, signal) -> None:
    """entity_event_timeline 적재 (Entity Resolution → 시퀀스 추적)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO entity_event_timeline
            (entity_id, entity_name, source, signal_type, severity, confidence,
             event_time, observed_at, source_ref_id, normalized_summary, raw_event_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (entity_id, raw_event.entity_name, raw_event.source, signal.signal_type,
         signal.severity, signal.confidence, signal.observed_at, signal.observed_at,
         raw_event.source_ref_id, signal.normalized_summary, signal.raw_event_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def save_cb_extraction(ext: dict) -> None:
    codes = ext.get("risk_codes", [])
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO cb_term_extractions
            (entity_id, entity_name, source_ref_id, security_type, issue_amount,
             maturity_date, coupon_rate, conversion_price, refixing_present, refixing_floor,
             refixing_period, refixing_no_floor, refixing_monthly_reset,
             early_redemption_right, call_option, collateral_present,
             risk_level, risk_codes, raw_text)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (ext.get("entity_id"), ext.get("entity_name"), ext.get("source_ref_id"),
         ext.get("security_type"), ext.get("issue_amount"), ext.get("maturity_date"),
         ext.get("coupon_rate"), ext.get("conversion_price"),
         bool(ext.get("refixing_present")), ext.get("refixing_floor"),
         ext.get("refixing_period"), "no_refixing_floor" in codes, "monthly_reset" in codes,
         bool(ext.get("early_redemption_right")), bool(ext.get("call_option")),
         bool(ext.get("collateral_present")), ext.get("risk_level"),
         json.dumps(codes, ensure_ascii=False), (ext.get("raw_text") or "")[:5000]),
    )
    conn.commit()
    cur.close()
    conn.close()

"""data-pipeline DB 헬퍼 (동기 psycopg2). base_scanner 에서 asyncio.to_thread 로 호출."""
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg2
import psycopg2.extras


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)


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


def save_financial_features(features, corp_code: str, z: dict, icr: dict) -> None:
    """entity_financial_features upsert (entity_id, period_end).

    테이블은 Altman X1~X5 비율(working_capital_ratio 등)을 저장하므로
    z['components']를 매핑한다. 원시 금액 컬럼은 ebit/interest_expense/ocf/short_term_debt만.
    """
    comp = z.get("components") or {}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO entity_financial_features
            (entity_id, entity_name, dart_corp_code, period_end,
             working_capital_ratio, retained_earnings_ratio, ebit_ratio,
             equity_to_debt_ratio, sales_ratio,
             z_score, z_zone, ebit, interest_expense, icr, ocf, short_term_debt)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (entity_id, period_end) DO UPDATE
          SET working_capital_ratio   = EXCLUDED.working_capital_ratio,
              retained_earnings_ratio  = EXCLUDED.retained_earnings_ratio,
              ebit_ratio               = EXCLUDED.ebit_ratio,
              equity_to_debt_ratio     = EXCLUDED.equity_to_debt_ratio,
              sales_ratio              = EXCLUDED.sales_ratio,
              z_score                  = EXCLUDED.z_score,
              z_zone                   = EXCLUDED.z_zone,
              ebit                     = EXCLUDED.ebit,
              interest_expense         = EXCLUDED.interest_expense,
              icr                      = EXCLUDED.icr,
              ocf                      = EXCLUDED.ocf,
              short_term_debt          = EXCLUDED.short_term_debt,
              calculated_at            = NOW()
        """,
        (features.entity_id, features.entity_name, corp_code, features.period_end,
         comp.get("x1"), comp.get("x2"), comp.get("x3"), comp.get("x4"), comp.get("x5"),
         z.get("z_score"), z.get("z_zone"),
         features.ebit, features.interest_expense, icr.get("icr"),
         features.operating_cf, features.short_term_debt),
    )
    conn.commit()
    cur.close()
    conn.close()


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

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

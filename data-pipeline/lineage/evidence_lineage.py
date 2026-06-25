"""Evidence lineage — raw → normalized → scored 연결 추적.

Phase 2에서 audit trail 강화. v0은 정규화 신호의 출처 raw_event 체인 조회만 제공.
"""
from __future__ import annotations

import db


def trace(scored_signal_id: int) -> dict:
    """scored_signal → normalized → raw 체인 반환 (IC 설명용)."""
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ss.id AS scored_id, ss.aggregate_score, ss.reason_codes,
               ns.id AS normalized_id, ns.signal_type, ns.severity,
               rse.id AS raw_id, rse.source, rse.source_url, rse.observed_at
        FROM scored_signals ss
        JOIN normalized_signals ns ON ns.id = ss.normalized_signal_id
        JOIN raw_source_events rse ON rse.id = ns.raw_event_id
        WHERE ss.id = %s
        """,
        (scored_signal_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else {}

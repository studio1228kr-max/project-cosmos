"""
COSMOS Core — Evidence Writer

계산계에서 받은 EngineResult(metrics + confidence + provenance)를
deal_evidence 테이블의 output_value / audit_trail / confidence_level 컬럼에 저장.

이게 핵심 이유: "이 숫자 어디서 나왔어요?"에 즉답하려면
metrics만 저장하면 안 되고 provenance 전체를 audit_trail에 박아야 한다.
"""
from __future__ import annotations
import json
import psycopg2
import psycopg2.extras


def write_engine_result(conn, deal_master_id: int, engine_result: dict) -> int:
    """
    engine_result: quant_client.evaluate_deal()이 반환한 dict (EngineResult 형태)

    deal_evidence에 새 row를 upsert.
    evidence_type은 engine_name으로 매핑 (예: 'MERTON_KMV_PD', 'CECL_EL').
    """
    engine_name = engine_result["engine_name"]
    metrics = engine_result["metrics"]
    confidence = engine_result["confidence"]
    provenance = engine_result["provenance"]

    evidence_type = f"QUANT_{engine_name.upper()}"
    confidence_level = confidence["tier"]  # HIGH/MEDIUM/LOW

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO deal_evidence (
                deal_master_id, evidence_type, status, verification_status,
                confidence_level, output_value, audit_trail, as_of_date
            )
            VALUES (%s, %s, 'verified', 'VERIFIED', %s, %s, %s, NOW())
            RETURNING id
            """,
            (
                deal_master_id,
                evidence_type,
                confidence_level,
                json.dumps(metrics),
                json.dumps(provenance),
            ),
        )
        row = cur.fetchone()
        conn.commit()
        return row["id"]


def log_for_calibration(conn, deal_master_id: int, engine_result: dict, model_version: str) -> None:
    """
    deal_outcome_log에 예측치를 기록 — 실측치는 나중에 딜 종료시 별도로 채움.
    이게 니치 캘리브레이션 모트의 데이터 적재 지점.
    """
    metrics = engine_result["metrics"]

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO deal_outcome_log (
                deal_master_id, predicted_pd, predicted_lgd,
                predicted_ead, predicted_el, predicted_at, model_version
            )
            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
            """,
            (
                deal_master_id,
                metrics.get("pd"),
                metrics.get("lgd"),
                metrics.get("ead"),
                metrics.get("expected_loss"),
                model_version,
            ),
        )
        conn.commit()

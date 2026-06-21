from __future__ import annotations

import calendar
import json
import logging
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

logger = logging.getLogger(__name__)
SOURCE = "ECOS"
PIPELINE_STAGE = "NORMALIZE"
KST = ZoneInfo("Asia/Seoul")

def _env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}

ECOS_LLM_INSIGHTS_ENABLED = _env_bool("ECOS_LLM_INSIGHTS_ENABLED", False)
ECOS_LLM_INSIGHT_MAX_PER_RUN = int(os.getenv("ECOS_LLM_INSIGHT_MAX_PER_RUN", "30"))
ECOS_LLM_TIMEOUT_SECONDS = int(os.getenv("ECOS_LLM_TIMEOUT_SECONDS", "20"))
ECOS_NORMALIZE_STALE_MINUTES = int(os.getenv("ECOS_NORMALIZE_STALE_MINUTES", "30"))
ECOS_INSIGHT_MAX_CHARS = int(os.getenv("ECOS_INSIGHT_MAX_CHARS", "2000"))

@dataclass(frozen=True)
class MacroMetricSpec:
    stat_code: str
    metric_name: str
    frequency: str
    unit_hint: Optional[str] = None

@dataclass
class PreparedNormalizedRow:
    raw_id: int
    source: str
    stat_code: str
    metric_name: str
    period_raw: str
    as_of_date: date
    value: float
    delta_mom: Optional[float]
    unit: Optional[str]
    data_frequency: str
    confidence_score: float
    last_seen_at: datetime
    nlp_insight: Optional[str] = None

@dataclass
class RawTerminalSkip:
    raw_id: int
    message: str

@dataclass
class RawRetryFailure:
    raw_id: int
    message: str

METRIC_BY_STAT_CODE: Dict[str, MacroMetricSpec] = {
    "722Y001": MacroMetricSpec("722Y001", "base_rate", "M", "%"),
    "921Y001": MacroMetricSpec("921Y001", "cofix", "M", "%"),
    "901Y062": MacroMetricSpec("901Y062", "national_housing_sale_price_index", "M", "index"),
}

def _now_kst() -> datetime:
    return datetime.now(KST)

def _get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required.")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return database_url

def get_engine() -> Engine:
    return create_engine(_get_database_url(), pool_pre_ping=True, future=True)

def _parse_json_payload(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        return json.loads(payload)
    raise ValueError(f"Unsupported raw_payload type: {type(payload)}")

def _parse_monthly_as_of_date(period: str) -> date:
    if not period:
        raise ValueError("Empty ECOS period.")
    digits = re.sub(r"\D", "", str(period))
    if len(digits) < 6:
        raise ValueError(f"Invalid monthly ECOS period: {period}")
    year = int(digits[:4])
    month = int(digits[4:6])
    if month < 1 or month > 12:
        raise ValueError(f"Invalid month: {period}")
    return date(year, month, calendar.monthrange(year, month)[1])

def _parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text_value = str(value).strip()
    if text_value in {"", "-", "NA", "N/A", "null", "None"}:
        return None
    return float(text_value.replace(",", ""))

def _extract_unit(row: Dict[str, Any], spec: MacroMetricSpec) -> Optional[str]:
    return row.get("UNIT_NAME") or row.get("UNIT") or row.get("unit") or spec.unit_hint

def _claim_pending_raw_rows(engine: Engine, *, run_id: str, limit: int) -> List[Dict[str, Any]]:
    sql = text("""
        WITH candidates AS (
            SELECT id FROM raw_macro_data
            WHERE source = :source
              AND is_normalized = FALSE
              AND (
                normalization_status IN ('PENDING', 'FAILED_RETRY')
                OR normalization_status IS NULL
                OR (normalization_status = 'PROCESSING' AND normalization_started_at < NOW() - (:stale_minutes * INTERVAL '1 minute'))
              )
            ORDER BY fetched_at ASC, id ASC
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
        )
        UPDATE raw_macro_data r
        SET normalization_status = 'PROCESSING', normalization_run_id = :run_id, normalization_started_at = :started_at, normalize_error = NULL
        FROM candidates c WHERE r.id = c.id
        RETURNING r.id, r.source, r.stat_code, r.data_frequency, r.period, r.raw_payload, r.fetched_at
    """)
    with engine.begin() as conn:
        rows = conn.execute(sql, {"source": SOURCE, "run_id": run_id, "started_at": _now_kst(), "limit": limit, "stale_minutes": ECOS_NORMALIZE_STALE_MINUTES}).mappings().all()
    return [dict(row) for row in rows]

def _load_existing_history(engine, *, keys, max_date_by_key):
    history: Dict[Tuple[str, str], Dict[date, float]] = {key: {} for key in keys}
    sql = text("""
        SELECT stat_code, metric_name, as_of_date, value FROM normalized_macro_series
        WHERE source = :source AND stat_code = :stat_code AND metric_name = :metric_name AND as_of_date <= :max_date
        ORDER BY as_of_date ASC
    """)
    with engine.begin() as conn:
        for stat_code, metric_name in keys:
            rows = conn.execute(sql, {"source": SOURCE, "stat_code": stat_code, "metric_name": metric_name, "max_date": max_date_by_key[(stat_code, metric_name)]}).mappings().all()
            for row in rows:
                history[(stat_code, metric_name)][row["as_of_date"]] = float(row["value"])
    return history

def _previous_value_from_history(history, *, as_of_date):
    previous_dates = [d for d in history.keys() if d < as_of_date]
    if not previous_dates:
        return None
    return history[max(previous_dates)]

def _prepare_rows_without_llm(engine, *, raw_rows, run_at):
    parsed_candidates: List[PreparedNormalizedRow] = []
    terminal_skips: List[RawTerminalSkip] = []
    retry_failures: List[RawRetryFailure] = []
    for raw in raw_rows:
        raw_id = int(raw["id"])
        stat_code = str(raw["stat_code"])
        spec = METRIC_BY_STAT_CODE.get(stat_code)
        if not spec:
            terminal_skips.append(RawTerminalSkip(raw_id=raw_id, message=f"UNSUPPORTED_STAT_CODE: {stat_code}"))
            continue
        try:
            payload = _parse_json_payload(raw["raw_payload"])
            period_raw = str(payload.get("TIME") or raw.get("period") or "")
            as_of_date = _parse_monthly_as_of_date(period_raw)
            value = _parse_float(payload.get("DATA_VALUE"))
            if value is None:
                terminal_skips.append(RawTerminalSkip(raw_id=raw_id, message=f"SKIPPED_NULL_VALUE: raw_id={raw_id} stat_code={stat_code}"))
                continue
            parsed_candidates.append(PreparedNormalizedRow(
                raw_id=raw_id, source=SOURCE, stat_code=stat_code, metric_name=spec.metric_name,
                period_raw=period_raw, as_of_date=as_of_date, value=value, delta_mom=None,
                unit=_extract_unit(payload, spec), data_frequency=raw.get("data_frequency") or spec.frequency,
                confidence_score=0.90, last_seen_at=run_at,
            ))
        except Exception as exc:
            retry_failures.append(RawRetryFailure(raw_id=raw_id, message=f"raw_id={raw_id} stat_code={stat_code}: {exc}"))
    if not parsed_candidates:
        return [], terminal_skips, retry_failures
    parsed_candidates.sort(key=lambda r: (r.stat_code, r.metric_name, r.as_of_date, r.raw_id))
    keys = sorted({(r.stat_code, r.metric_name) for r in parsed_candidates})
    max_date_by_key = {key: max(r.as_of_date for r in parsed_candidates if (r.stat_code, r.metric_name) == key) for key in keys}
    history_by_key = _load_existing_history(engine, keys=keys, max_date_by_key=max_date_by_key)
    for row in parsed_candidates:
        key = (row.stat_code, row.metric_name)
        history = history_by_key.setdefault(key, {})
        prev = _previous_value_from_history(history, as_of_date=row.as_of_date)
        row.delta_mom = None if prev is None else row.value - prev
        history[row.as_of_date] = row.value
    return parsed_candidates, terminal_skips, retry_failures

def _generate_nlp_insight(row: PreparedNormalizedRow) -> Optional[str]:
    if not ECOS_LLM_INSIGHTS_ENABLED:
        return None
    return None

def _attach_llm_insights_outside_transaction(rows: List[PreparedNormalizedRow]) -> int:
    attempted = 0
    for row in rows:
        if attempted >= ECOS_LLM_INSIGHT_MAX_PER_RUN:
            break
        attempted += 1
        row.nlp_insight = _generate_nlp_insight(row)
    return attempted

def _bulk_upsert_normalized_rows(conn: Connection, rows: List[PreparedNormalizedRow]) -> int:
    if not rows:
        return 0
    sql = text("""
        INSERT INTO normalized_macro_series (source, stat_code, metric_name, period_raw, as_of_date, value, delta_mom, nlp_insight, unit, data_frequency, confidence_score, last_seen_at, updated_at)
        VALUES (:source, :stat_code, :metric_name, :period_raw, :as_of_date, :value, :delta_mom, :nlp_insight, :unit, :data_frequency, :confidence_score, :last_seen_at, :updated_at)
        ON CONFLICT (source, metric_name, as_of_date) DO UPDATE SET
            stat_code=EXCLUDED.stat_code, period_raw=EXCLUDED.period_raw, value=EXCLUDED.value,
            delta_mom=EXCLUDED.delta_mom, nlp_insight=EXCLUDED.nlp_insight, unit=EXCLUDED.unit,
            data_frequency=EXCLUDED.data_frequency, confidence_score=EXCLUDED.confidence_score,
            last_seen_at=EXCLUDED.last_seen_at, updated_at=EXCLUDED.updated_at
    """)
    now = _now_kst()
    result = conn.execute(sql, [{"source": r.source, "stat_code": r.stat_code, "metric_name": r.metric_name, "period_raw": r.period_raw, "as_of_date": r.as_of_date, "value": r.value, "delta_mom": r.delta_mom, "nlp_insight": r.nlp_insight, "unit": r.unit, "data_frequency": r.data_frequency, "confidence_score": r.confidence_score, "last_seen_at": r.last_seen_at, "updated_at": now} for r in rows])
    return max(int(result.rowcount or 0), 0)

def _bulk_mark_success(conn, rows):
    if not rows:
        return
    now = _now_kst()
    conn.execute(text("UPDATE raw_macro_data SET is_normalized=TRUE, normalized_at=:t, normalize_error=NULL, normalization_status='SUCCESS', normalization_run_id=NULL, normalization_started_at=NULL WHERE id=:raw_id"), [{"raw_id": r.raw_id, "t": now} for r in rows])

def _bulk_mark_terminal_skips(conn, rows):
    if not rows:
        return
    now = _now_kst()
    conn.execute(text("UPDATE raw_macro_data SET is_normalized=TRUE, normalized_at=:t, normalize_error=:message, normalization_status='SKIPPED', normalization_run_id=NULL, normalization_started_at=NULL WHERE id=:raw_id"), [{"raw_id": r.raw_id, "t": now, "message": r.message[:5000]} for r in rows])

def _bulk_mark_retry_failures(conn, rows):
    if not rows:
        return
    conn.execute(text("UPDATE raw_macro_data SET is_normalized=FALSE, normalized_at=NULL, normalize_error=:message, normalization_status='FAILED_RETRY', normalization_run_id=NULL, normalization_started_at=NULL WHERE id=:raw_id"), [{"raw_id": r.raw_id, "message": r.message[:5000]} for r in rows])

def _record_normalize_run(engine, *, run_at, status, records_fetched, records_inserted, records_processed, records_failed, error_message):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO ingestion_runs (source, pipeline_stage, run_at, status, records_fetched, records_inserted, records_processed, records_failed, error_message) VALUES (:source, :pipeline_stage, :run_at, :status, :records_fetched, :records_inserted, :records_processed, :records_failed, :error_message)"),
            {"source": SOURCE, "pipeline_stage": PIPELINE_STAGE, "run_at": run_at, "status": status, "records_fetched": records_fetched, "records_inserted": records_inserted, "records_processed": records_processed, "records_failed": records_failed, "error_message": error_message})

def normalize(*, limit: int = 5000) -> Dict[str, Any]:
    run_at = _now_kst()
    run_id = str(uuid.uuid4())
    engine = get_engine()
    raw_rows_loaded = records_processed = records_inserted_or_updated = records_failed = records_skipped = llm_insights_attempted = 0
    errors: List[str] = []
    try:
        raw_rows = _claim_pending_raw_rows(engine, run_id=run_id, limit=limit)
        raw_rows_loaded = len(raw_rows)
        prepared_rows, terminal_skips, retry_failures = _prepare_rows_without_llm(engine, raw_rows=raw_rows, run_at=run_at)
        records_processed = raw_rows_loaded
        records_skipped = len(terminal_skips)
        records_failed = len(retry_failures)
        if retry_failures:
            errors.extend(r.message for r in retry_failures)
        llm_insights_attempted = _attach_llm_insights_outside_transaction(prepared_rows)
        with engine.begin() as conn:
            records_inserted_or_updated = _bulk_upsert_normalized_rows(conn, prepared_rows)
            _bulk_mark_success(conn, prepared_rows)
            _bulk_mark_terminal_skips(conn, terminal_skips)
            _bulk_mark_retry_failures(conn, retry_failures)
        status = "FAILED" if errors and records_inserted_or_updated == 0 and records_skipped == 0 else ("PARTIAL_FAILURE" if errors else "SUCCESS")
        error_message = " | ".join(errors) if errors else None
        _record_normalize_run(engine, run_at=run_at, status=status, records_fetched=raw_rows_loaded, records_inserted=records_inserted_or_updated, records_processed=records_processed, records_failed=records_failed, error_message=error_message)
        return {"source": SOURCE, "pipeline_stage": PIPELINE_STAGE, "run_id": run_id, "status": status, "raw_rows_loaded": raw_rows_loaded, "records_processed": records_processed, "records_inserted_or_updated": records_inserted_or_updated, "records_skipped": records_skipped, "records_failed": records_failed, "llm_insights_attempted": llm_insights_attempted, "error_message": error_message}
    except Exception as exc:
        logger.exception("ECOS normalization failed.")
        try:
            _record_normalize_run(engine, run_at=run_at, status="FAILED", records_fetched=raw_rows_loaded, records_inserted=records_inserted_or_updated, records_processed=records_processed, records_failed=records_failed+1, error_message=str(exc))
        except Exception:
            pass
        return {"source": SOURCE, "pipeline_stage": PIPELINE_STAGE, "run_id": run_id, "status": "FAILED", "raw_rows_loaded": raw_rows_loaded, "records_processed": records_processed, "records_inserted_or_updated": records_inserted_or_updated, "records_skipped": records_skipped, "records_failed": records_failed+1, "llm_insights_attempted": llm_insights_attempted, "error_message": str(exc)}

if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    print(json.dumps(normalize(), ensure_ascii=False, indent=2, default=str))

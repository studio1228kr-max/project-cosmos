from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

logger = logging.getLogger(__name__)
SOURCE = "ECOS"
PIPELINE_STAGE = "INGEST"
KST = ZoneInfo("Asia/Seoul")
ECOS_API_BASE_URL = os.getenv("ECOS_API_BASE_URL", "https://ecos.bok.or.kr/api")
DEFAULT_LOOKBACK_MONTHS = int(os.getenv("ECOS_LOOKBACK_MONTHS", "36"))
ECOS_PAGE_SIZE = int(os.getenv("ECOS_PAGE_SIZE", "1000"))
ECOS_MAX_PAGES = int(os.getenv("ECOS_MAX_PAGES", "50"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("ECOS_REQUEST_TIMEOUT_SECONDS", "30"))

def _env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}

def _split_item_codes(env_name: str) -> Tuple[str, ...]:
    raw_value = os.getenv(env_name, "").strip()
    if not raw_value:
        return ()
    return tuple(item.strip() for item in raw_value.split(",") if item.strip())

@dataclass(frozen=True)
class EcosTarget:
    stat_code: str
    metric_name: str
    frequency: str
    unit_hint: Optional[str]
    item_codes: Tuple[str, ...]
    requires_item_codes: bool
    item_codes_env_name: str
    allow_empty: bool = False

GLOBAL_REQUIRE_ITEM_CODES = _env_bool("ECOS_REQUIRE_ITEM_CODES", True)

ECOS_TARGETS: List[EcosTarget] = [
    EcosTarget(
        stat_code="722Y001",
        metric_name="base_rate",
        frequency="M",
        unit_hint="%",
        item_codes=_split_item_codes("ECOS_BASE_RATE_ITEM_CODES"),
        requires_item_codes=_env_bool("ECOS_REQUIRE_BASE_RATE_ITEM_CODES", GLOBAL_REQUIRE_ITEM_CODES),
        item_codes_env_name="ECOS_BASE_RATE_ITEM_CODES",
    ),
    EcosTarget(
        stat_code="921Y001",
        metric_name="cofix",
        frequency="M",
        unit_hint="%",
        item_codes=_split_item_codes("ECOS_COFIX_ITEM_CODES"),
        requires_item_codes=_env_bool("ECOS_REQUIRE_COFIX_ITEM_CODES", GLOBAL_REQUIRE_ITEM_CODES),
        item_codes_env_name="ECOS_COFIX_ITEM_CODES",
    ),
    EcosTarget(
        stat_code="901Y062",
        metric_name="national_housing_sale_price_index",
        frequency="M",
        unit_hint="index",
        item_codes=_split_item_codes("ECOS_HOUSING_INDEX_ITEM_CODES"),
        requires_item_codes=_env_bool("ECOS_REQUIRE_HOUSING_INDEX_ITEM_CODES", GLOBAL_REQUIRE_ITEM_CODES),
        item_codes_env_name="ECOS_HOUSING_INDEX_ITEM_CODES",
    ),
]

class EcosApiError(RuntimeError):
    pass

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

def _subtract_months(base: date, months: int) -> date:
    year = base.year
    month = base.month - months
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)

def _default_period_range() -> tuple[str, str]:
    today = datetime.now(KST).date()
    start = _subtract_months(today, DEFAULT_LOOKBACK_MONTHS)
    return start.strftime("%Y%m"), today.strftime("%Y%m")

def _stable_payload_hash(*, source, stat_code, frequency, period, raw_payload) -> str:
    body = {"source": source, "stat_code": stat_code, "frequency": frequency, "period": period, "raw_payload": raw_payload}
    encoded = json.dumps(body, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

def _quote_path_part(value: Any) -> str:
    return quote(str(value), safe="")

def _build_ecos_url(*, api_key, stat_code, frequency, start_period, end_period, start_index, end_index, item_codes) -> str:
    base = ECOS_API_BASE_URL.rstrip("/")
    parts = ["StatisticSearch", api_key, "json", "kr", str(start_index), str(end_index), stat_code, frequency, start_period, end_period]
    parts.extend(item_codes)
    return base + "/" + "/".join(_quote_path_part(p) for p in parts)

def _validate_target_contract(target: EcosTarget) -> None:
    if target.requires_item_codes and not target.item_codes:
        raise RuntimeError(f"ECOS item_codes not configured. stat_code={target.stat_code}, env={target.item_codes_env_name}. Set ECOS_REQUIRE_ITEM_CODES=false to skip.")

def _get_body_level_error(payload: Dict[str, Any]) -> Optional[str]:
    result = payload.get("RESULT")
    if not isinstance(result, dict):
        return None
    code = result.get("CODE")
    message = result.get("MESSAGE")
    if code and code != "INFO-000":
        return f"{code} / {message}"
    return None

def _extract_statistic_search(payload: Dict[str, Any]) -> Dict[str, Any]:
    ss = payload.get("StatisticSearch")
    if not ss:
        return {}
    if isinstance(ss, list):
        return ss[0] if ss and isinstance(ss[0], dict) else {}
    return ss if isinstance(ss, dict) else {}

def _extract_rows_and_total(payload: Dict[str, Any]) -> tuple[List[Dict[str, Any]], int]:
    err = _get_body_level_error(payload)
    if err:
        raise EcosApiError(f"ECOS body-level error: {err}")
    ss = _extract_statistic_search(payload)
    if not ss:
        return [], 0
    try:
        total = int(ss.get("list_total_count", 0) or 0)
    except (TypeError, ValueError):
        total = 0
    rows = ss.get("row", [])
    if isinstance(rows, dict):
        return [rows], total
    if isinstance(rows, list):
        return rows, total
    return [], total

def _fetch_page(target, *, api_key, start_period, end_period, start_index, end_index):
    url = _build_ecos_url(api_key=api_key, stat_code=target.stat_code, frequency=target.frequency, start_period=start_period, end_period=end_period, start_index=start_index, end_index=end_index, item_codes=target.item_codes)
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise EcosApiError(f"ECOS non-JSON: {exc}") from exc
    return _extract_rows_and_total(payload)

def _fetch_target_all_pages(target, *, start_period, end_period):
    _validate_target_contract(target)
    api_key = os.getenv("ECOS_API_KEY")
    if not api_key:
        raise RuntimeError("ECOS_API_KEY required.")
    all_rows: List[Dict[str, Any]] = []
    start_index = 1
    total_count = None
    page_count = 0
    while True:
        page_count += 1
        if page_count > ECOS_MAX_PAGES:
            raise RuntimeError(f"ECOS pagination exceeded {ECOS_MAX_PAGES} pages.")
        end_index = start_index + ECOS_PAGE_SIZE - 1
        rows, page_total = _fetch_page(target, api_key=api_key, start_period=start_period, end_period=end_period, start_index=start_index, end_index=end_index)
        if total_count is None:
            total_count = page_total
        all_rows.extend(rows)
        if not rows:
            break
        if total_count and len(all_rows) >= total_count:
            break
        if len(rows) < ECOS_PAGE_SIZE:
            break
        start_index += ECOS_PAGE_SIZE
    if not all_rows and not target.allow_empty and _env_bool("ECOS_FAIL_ON_EMPTY_RESPONSE", True):
        raise RuntimeError(f"ECOS empty rows. stat_code={target.stat_code}, period={start_period}-{end_period}. Check item_codes.")
    return all_rows

def _insert_raw_rows(engine, *, target, rows, fetched_at) -> int:
    if not rows:
        return 0
    sql = text("""
        INSERT INTO raw_macro_data (source, stat_code, data_frequency, period, raw_payload, payload_hash, fetched_at, is_normalized, normalization_status)
        VALUES (:source, :stat_code, :data_frequency, :period, CAST(:raw_payload AS JSONB), :payload_hash, :fetched_at, FALSE, 'PENDING')
        ON CONFLICT (payload_hash) DO NOTHING
    """)
    params = []
    for row in rows:
        period = str(row.get("TIME") or row.get("period") or "")
        params.append({
            "source": SOURCE, "stat_code": target.stat_code, "data_frequency": target.frequency,
            "period": period, "raw_payload": json.dumps(row, ensure_ascii=False, default=str),
            "payload_hash": _stable_payload_hash(source=SOURCE, stat_code=target.stat_code, frequency=target.frequency, period=period, raw_payload=row),
            "fetched_at": fetched_at,
        })
    with engine.begin() as conn:
        result = conn.execute(sql, params)
    return max(int(result.rowcount or 0), 0)

def _record_ingestion_run(engine, *, run_at, status, records_fetched, records_inserted, records_processed, records_failed, error_message):
    sql = text("""
        INSERT INTO ingestion_runs (source, pipeline_stage, run_at, status, records_fetched, records_inserted, records_processed, records_failed, error_message)
        VALUES (:source, :pipeline_stage, :run_at, :status, :records_fetched, :records_inserted, :records_processed, :records_failed, :error_message)
    """)
    with engine.begin() as conn:
        conn.execute(sql, {"source": SOURCE, "pipeline_stage": PIPELINE_STAGE, "run_at": run_at, "status": status, "records_fetched": records_fetched, "records_inserted": records_inserted, "records_processed": records_processed, "records_failed": records_failed, "error_message": error_message})

def ingest(*, start_period=None, end_period=None) -> Dict[str, Any]:
    run_at = _now_kst()
    engine = get_engine()
    if not start_period or not end_period:
        start_period, end_period = _default_period_range()
    total_fetched = total_inserted = total_failed = 0
    errors: List[str] = []
    for target in ECOS_TARGETS:
        try:
            rows = _fetch_target_all_pages(target, start_period=start_period, end_period=end_period)
            total_fetched += len(rows)
            total_inserted += _insert_raw_rows(engine, target=target, rows=rows, fetched_at=run_at)
        except EcosApiError as exc:
            total_failed += 1
            errors.append(f"API_ERROR {target.stat_code}: {exc}")
        except Exception as exc:
            total_failed += 1
            errors.append(f"{target.stat_code}: {exc}")
    status = "FAILED" if errors and total_fetched == 0 else ("PARTIAL_FAILURE" if errors else "SUCCESS")
    error_message = " | ".join(errors) if errors else None
    try:
        _record_ingestion_run(engine, run_at=run_at, status=status, records_fetched=total_fetched, records_inserted=total_inserted, records_processed=total_fetched, records_failed=total_failed, error_message=error_message)
    except Exception:
        logger.exception("Failed to record ingestion run.")
    return {"source": SOURCE, "pipeline_stage": PIPELINE_STAGE, "status": status, "records_fetched": total_fetched, "records_inserted": total_inserted, "records_processed": total_fetched, "records_failed": total_failed, "error_message": error_message, "start_period": start_period, "end_period": end_period}

if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    print(json.dumps(ingest(), ensure_ascii=False, indent=2, default=str))

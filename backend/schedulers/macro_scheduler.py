from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from ingestors.ecos_ingestor import ingest
from ingestors.ecos_normalizer import normalize

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")

def _stable_lock_key(name: str) -> int:
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return value & 0x7FFFFFFFFFFFFFFF

ADVISORY_LOCK_KEY = _stable_lock_key("cosmos.macro_pipeline.ecos.v1")

def _get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required.")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return database_url

def _get_engine() -> Engine:
    return create_engine(_get_database_url(), pool_pre_ping=True, future=True)

def _try_advisory_lock(conn: Connection) -> bool:
    sql = text("SELECT pg_try_advisory_lock(:lock_key) AS acquired")
    row = conn.execute(sql, {"lock_key": ADVISORY_LOCK_KEY}).mappings().first()
    return bool(row and row["acquired"])

def _release_advisory_lock(conn: Connection) -> None:
    conn.execute(text("SELECT pg_advisory_unlock(:lock_key)"), {"lock_key": ADVISORY_LOCK_KEY})

def run_macro_pipeline() -> Dict[str, Any]:
    engine = _get_engine()
    result: Dict[str, Any] = {"lock_key": ADVISORY_LOCK_KEY, "lock_acquired": False, "ingest": None, "normalize": None, "status": None}
    with engine.connect() as lock_conn:
        try:
            lock_acquired = _try_advisory_lock(lock_conn)
            result["lock_acquired"] = lock_acquired
            if not lock_acquired:
                logger.warning("Macro pipeline skipped: advisory lock already held.")
                result["status"] = "SKIPPED_LOCK_HELD"
                return result
            try:
                ingest_result = ingest()
                result["ingest"] = ingest_result
                logger.info("ECOS ingest completed: %s", ingest_result)
            except Exception as exc:
                logger.exception("ECOS ingest step failed.")
                result["ingest"] = {"source": "ECOS", "pipeline_stage": "INGEST", "status": "FAILED", "error_message": str(exc)}
            try:
                normalize_result = normalize()
                result["normalize"] = normalize_result
                logger.info("ECOS normalize completed: %s", normalize_result)
            except Exception as exc:
                logger.exception("ECOS normalize step failed.")
                result["normalize"] = {"source": "ECOS", "pipeline_stage": "NORMALIZE", "status": "FAILED", "error_message": str(exc)}
            ingest_status = (result["ingest"] or {}).get("status")
            normalize_status = (result["normalize"] or {}).get("status")
            if ingest_status == "FAILED" and normalize_status == "FAILED":
                result["status"] = "FAILED"
            elif ingest_status in {"FAILED", "PARTIAL_FAILURE"} or normalize_status in {"FAILED", "PARTIAL_FAILURE"}:
                result["status"] = "PARTIAL_FAILURE"
            else:
                result["status"] = "SUCCESS"
            return result
        finally:
            if result.get("lock_acquired"):
                try:
                    _release_advisory_lock(lock_conn)
                except Exception:
                    logger.exception("Failed to release advisory lock.")

def start_scheduler() -> None:
    scheduler = BlockingScheduler(timezone=KST)
    scheduler.add_job(run_macro_pipeline, CronTrigger(hour=6, minute=0, timezone=KST), id="ecos_macro_daily_0600_kst", name="ECOS macro ingest and normalize", max_instances=1, coalesce=True, misfire_grace_time=3600, replace_existing=True)

    # DART 공시 수집 — 매일 07:00 KST
    try:
        from ingestors.dart_ingestor import run_ingestion as dart_run
        scheduler.add_job(lambda: dart_run(lookback_days=2), CronTrigger(hour=7, minute=0, timezone=KST), id="dart_daily_0700_kst", name="DART disclosure ingest", max_instances=1, coalesce=True, misfire_grace_time=3600, replace_existing=True)
        logger.info("DART scheduler added. Job: daily 07:00 Asia/Seoul.")
    except Exception as e:
        logger.warning("DART scheduler 등록 실패: %s", e)

    # MOLIT 실거래가 — 매월 1일 08:00 KST
    try:
        from ingestors.molit_ingestor import run_ingestion as molit_run
        scheduler.add_job(lambda: molit_run(months_back=2), CronTrigger(day=1, hour=8, minute=0, timezone=KST), id="molit_monthly_0800_kst", name="MOLIT trade ingest", max_instances=1, coalesce=True, misfire_grace_time=86400, replace_existing=True)
        logger.info("MOLIT scheduler added. Job: monthly day-1 08:00 Asia/Seoul.")
    except Exception as e:
        logger.warning("MOLIT scheduler 등록 실패: %s", e)

    logger.info("Macro scheduler started. Job: daily 06:00 Asia/Seoul.")
    scheduler.start()

def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-once", action="store_true", help="Run ingest -> normalize once, then exit.")
    args = parser.parse_args()
    if args.run_once:
        result = run_macro_pipeline()
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return
    start_scheduler()

if __name__ == "__main__":
    main()

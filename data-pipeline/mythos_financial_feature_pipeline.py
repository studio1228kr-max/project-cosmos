"""MythosFinancialFeaturePipeline — append-only versions + current projection.

ChatGPT 원본 구조 그대로. 단 COSMOS 충돌 반영:
- ALLOWED_FEATURE_COLUMNS = entity_financial_features 의 Altman X1~X5 ratio 스키마
- entity_id = corp_code 라서 TEXT (원본 BIGINT → str)
- z_zone 은 z_score 파생 generated 컬럼 (파이프라인이 직접 쓰지 않음)
"""
import hashlib
import io
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Iterable, Optional
from uuid import UUID, uuid4

from psycopg2 import sql, extensions
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLogger(__name__)

VALID_REPORT_TYPES = frozenset({"annual", "q3", "half", "q1"})

DART_REPRT_CODE_TO_REPORT_TYPE = {
    "11011": "annual", "11014": "q3", "11012": "half", "11013": "q1",
}
REPORT_TYPE_TO_PERIOD_MONTHS = {"annual": 12, "q3": 9, "half": 6, "q1": 3}
REPORT_TYPE_ORDER = {"annual": 1, "q3": 2, "half": 3, "q1": 4}

# 충돌1: 실제 entity_financial_features 의 ratio 기반 피처 컬럼
ALLOWED_FEATURE_COLUMNS = (
    "working_capital_ratio",
    "retained_earnings_ratio",
    "ebit_ratio",
    "equity_to_debt_ratio",
    "sales_ratio",
    "z_score",
    "ebit",
    "interest_expense",
    "icr",
    "ocf",
    "short_term_debt",
)
ALLOWED_FEATURE_COLUMN_SET = frozenset(ALLOWED_FEATURE_COLUMNS)

# 재무 데이터가 실재하면 Altman 5비율 + z_score 는 계산 가능(0 포함). 나머지는 옵션.
REQUIRED_FEATURE_COLUMNS = frozenset({
    "working_capital_ratio", "retained_earnings_ratio", "ebit_ratio",
    "equity_to_debt_ratio", "sales_ratio", "z_score",
})

NUMERIC_SCALE_LIMITS = {
    "working_capital_ratio": 4, "retained_earnings_ratio": 4, "ebit_ratio": 4,
    "equity_to_debt_ratio": 4, "sales_ratio": 4, "z_score": 4, "icr": 4,
    "ebit": 2, "interest_expense": 2, "ocf": 2, "short_term_debt": 2,
}


class MythosFinancialFeatureError(RuntimeError):
    pass


class MythosValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CanonicalFeatureRow:
    entity_id: str
    period_end: date
    report_type: str
    reprt_code: Optional[str]
    statement_end: Optional[date]
    period_months: int
    is_accumulated: bool
    fetched_at: datetime
    batch_id: UUID
    source_hash: str
    feature_quality: dict
    features: dict


def _parse_date(value: Any, *, field_name: str) -> date:
    if value is None:
        raise MythosValidationError(f"{field_name} is required")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        raw = value.strip()[:10]
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise MythosValidationError(f"Invalid {field_name}: {value!r}") from exc
    raise MythosValidationError(f"Invalid {field_name} type: {type(value).__name__}")


def _parse_optional_date(value: Any, *, field_name: str) -> Optional[date]:
    if value in (None, ""):
        return None
    return _parse_date(value, field_name=field_name)


def _normalize_report_type(row: dict) -> str:
    report_type = row.get("report_type")
    if report_type:
        report_type = str(report_type).strip().lower()
        if report_type in VALID_REPORT_TYPES:
            return report_type
        raise MythosValidationError(f"Invalid report_type={report_type!r}")
    reprt_code = row.get("reprt_code")
    if reprt_code:
        mapped = DART_REPRT_CODE_TO_REPORT_TYPE.get(str(reprt_code).strip())
        if mapped:
            return mapped
    raise MythosValidationError("Missing valid report_type or DART reprt_code")


def _normalize_reprt_code(row: dict) -> Optional[str]:
    reprt_code = row.get("reprt_code")
    if reprt_code in (None, ""):
        return None
    return str(reprt_code).strip()


def _normalize_decimal(value: Any, *, column: str, allow_float: bool) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        dec = value
    elif isinstance(value, int):
        dec = Decimal(value)
    elif isinstance(value, str):
        raw = value.strip().replace(",", "")
        if raw == "":
            return None
        try:
            dec = Decimal(raw)
        except InvalidOperation as exc:
            raise MythosValidationError(f"Invalid decimal string. column={column}, value={value!r}") from exc
    elif isinstance(value, float):
        if not allow_float:
            raise MythosValidationError(f"Float rejected for numeric field. column={column}, value={value!r}")
        dec = Decimal(str(value))
    else:
        raise MythosValidationError(f"Unsupported numeric type. column={column}, type={type(value).__name__}")

    allowed_scale = NUMERIC_SCALE_LIMITS.get(column)
    if allowed_scale is not None:
        exponent = dec.as_tuple().exponent
        actual_scale = abs(exponent) if isinstance(exponent, int) and exponent < 0 else 0
        if actual_scale > allowed_scale:
            raise MythosValidationError(
                f"Decimal scale exceeds limit. column={column}, value={str(dec)}, "
                f"actual_scale={actual_scale}, allowed_scale={allowed_scale}")
    return dec


def _json_dumps_canonical(obj: Any) -> str:
    def default(value: Any) -> str:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        return str(value)
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=default)


def _compute_source_hash(*, entity_id, period_end, report_type, reprt_code,
                         statement_end, period_months, is_accumulated, features) -> str:
    payload = {
        "entity_id": entity_id, "period_end": period_end, "report_type": report_type,
        "reprt_code": reprt_code, "statement_end": statement_end,
        "period_months": period_months, "is_accumulated": is_accumulated, "features": features,
    }
    return hashlib.sha256(_json_dumps_canonical(payload).encode("utf-8")).hexdigest()


def _filter_and_validate_features(features, *, report_type, strict_unknown_columns, allow_float):
    if not isinstance(features, dict) or not features:
        raise MythosValidationError(f"features must be non-empty dict. report_type={report_type}")
    incoming = set(features.keys())
    unknown = sorted(incoming - ALLOWED_FEATURE_COLUMN_SET)
    if unknown and strict_unknown_columns:
        raise MythosValidationError(f"Unknown feature columns. report_type={report_type}, unknown={unknown}")

    safe = {}
    for col in ALLOWED_FEATURE_COLUMNS:
        safe[col] = _normalize_decimal(features.get(col), column=col, allow_float=allow_float)

    missing_required = sorted(c for c in REQUIRED_FEATURE_COLUMNS if safe.get(c) is None)
    if missing_required:
        raise MythosValidationError(f"Missing required features. report_type={report_type}, missing={missing_required}")

    missing_optional = sorted(
        c for c in ALLOWED_FEATURE_COLUMNS if c not in REQUIRED_FEATURE_COLUMNS and safe.get(c) is None)
    quality = {
        "unknown_keys": unknown, "missing_required": missing_required,
        "missing_optional": missing_optional, "schema_version": "entity_financial_features.v2",
    }
    return safe, quality


def canonicalize_rows(*, entity_id: str, fetched_rows: Iterable[dict],
                      batch_id: Optional[UUID] = None, fetched_at: Optional[datetime] = None,
                      strict_unknown_columns: bool = False, allow_float: bool = False,
                      require_single_period_end: bool = True) -> list:
    batch_id = batch_id or uuid4()
    fetched_at = fetched_at or datetime.now(timezone.utc)
    output, seen_keys = [], set()

    for raw in fetched_rows:
        report_type = _normalize_report_type(raw)
        reprt_code = _normalize_reprt_code(raw)
        period_end = _parse_date(raw.get("period_end"), field_name="period_end")
        statement_end = _parse_optional_date(raw.get("statement_end"), field_name="statement_end")
        period_months = int(raw.get("period_months") or REPORT_TYPE_TO_PERIOD_MONTHS[report_type])
        expected_months = REPORT_TYPE_TO_PERIOD_MONTHS[report_type]
        if period_months != expected_months:
            raise MythosValidationError(
                f"period_months mismatch. report_type={report_type}, actual={period_months}, expected={expected_months}")
        is_accumulated = bool(raw.get("is_accumulated", True))
        features, quality = _filter_and_validate_features(
            raw.get("features"), report_type=report_type,
            strict_unknown_columns=strict_unknown_columns, allow_float=allow_float)
        source_hash = _compute_source_hash(
            entity_id=entity_id, period_end=period_end, report_type=report_type,
            reprt_code=reprt_code, statement_end=statement_end,
            period_months=period_months, is_accumulated=is_accumulated, features=features)

        natural_key = (entity_id, period_end, report_type)
        if natural_key in seen_keys:
            raise MythosValidationError(f"Duplicate report_type in same batch: {natural_key}")
        seen_keys.add(natural_key)

        output.append(CanonicalFeatureRow(
            entity_id=entity_id, period_end=period_end, report_type=report_type,
            reprt_code=reprt_code, statement_end=statement_end, period_months=period_months,
            is_accumulated=is_accumulated, fetched_at=fetched_at, batch_id=batch_id,
            source_hash=source_hash, feature_quality=quality, features=features))

    if not output:
        raise MythosValidationError("No rows to save")

    period_ends = {r.period_end for r in output}
    if require_single_period_end and len(period_ends) != 1:
        raise MythosValidationError(
            f"Batch must share one fiscal period_end anchor. found={sorted(str(x) for x in period_ends)}")

    return sorted(output, key=lambda r: (r.entity_id, r.period_end, REPORT_TYPE_ORDER[r.report_type]))


_TEXT_NULL = "\\N"


def _text_escape(s: str) -> str:
    """COPY TEXT 포맷 이스케이프 (backslash/탭/개행만). JSON의 따옴표는 그대로 둔다."""
    return (s.replace("\\", "\\\\").replace("\t", "\\t")
             .replace("\n", "\\n").replace("\r", "\\r"))


def _copy_value(value: Any) -> str:
    """COPY TEXT 포맷 1필드. None → \\N(이스케이프 제외), 그 외 직렬화 후 이스케이프."""
    if value is None:
        return _TEXT_NULL
    if isinstance(value, Decimal):
        s = format(value, "f")
    elif isinstance(value, (date, datetime)):
        s = value.isoformat()
    elif isinstance(value, UUID):
        s = str(value)
    elif isinstance(value, bool):
        s = "true" if value else "false"
    elif isinstance(value, dict):
        s = _json_dumps_canonical(value)
    else:
        s = str(value)
    return _text_escape(s)


class MythosFinancialFeaturePipeline:
    def __init__(self, pool: ThreadedConnectionPool, *, page_size: int = 5000,
                 statement_timeout_ms: int = 30000, lock_timeout_ms: int = 3000,
                 reset_connection_on_release: bool = True) -> None:
        self.pool = pool
        self.page_size = page_size
        self.statement_timeout_ms = statement_timeout_ms
        self.lock_timeout_ms = lock_timeout_ms
        self.reset_connection_on_release = reset_connection_on_release

    def save_from_fetch(self, *, entity_id: str, dart_code: str,
                        fetch_multi_period: Callable[[str], list],
                        expected_report_types=VALID_REPORT_TYPES,
                        strict_unknown_columns: bool = False, allow_float: bool = False) -> list:
        fetched_rows = fetch_multi_period(dart_code)
        rows = canonicalize_rows(
            entity_id=entity_id, fetched_rows=fetched_rows,
            strict_unknown_columns=strict_unknown_columns, allow_float=allow_float,
            require_single_period_end=True)
        self.save_rows(rows=rows, expected_report_types=expected_report_types)
        return rows

    def save_rows(self, *, rows: list, expected_report_types=VALID_REPORT_TYPES) -> None:
        if not rows:
            raise MythosValidationError("rows must not be empty")
        entity_ids = {r.entity_id for r in rows}
        period_ends = {r.period_end for r in rows}
        if len(entity_ids) != 1:
            raise MythosValidationError(f"save_rows expects one entity_id. found={entity_ids}")
        if len(period_ends) != 1:
            raise MythosValidationError(f"save_rows expects one period_end. found={period_ends}")

        entity_id = rows[0].entity_id
        period_end = rows[0].period_end
        batch_id = rows[0].batch_id

        conn = self.pool.getconn()
        try:
            conn.autocommit = False
            with conn.cursor() as cur:
                self._set_local_timeouts(cur)
                self._acquire_entity_period_lock(cur, entity_id, period_end)
                self._create_temp_staging(cur)
                self._copy_rows_to_staging(cur, rows)
                self._insert_versions_from_staging(cur)
                self._refresh_current_projection(cur, batch_id)
                self._verify_batch_before_commit(
                    cur, entity_id=entity_id, period_end=period_end, batch_id=batch_id,
                    expected_report_types=set(expected_report_types))
            conn.commit()
            logger.info("[OK] saved features. entity_id=%s period_end=%s batch_id=%s rows=%s",
                        entity_id, period_end, batch_id, len(rows))
        except Exception as exc:
            self._safe_rollback(conn)
            logger.exception("[FAIL] rolled back. entity_id=%s period_end=%s error=%s",
                             entity_id, period_end, exc)
            raise MythosFinancialFeatureError(
                f"Failed to save. entity_id={entity_id}, period_end={period_end}, batch_id={batch_id}") from exc
        finally:
            self._release_conn(conn)

    def _set_local_timeouts(self, cur) -> None:
        cur.execute("SET LOCAL statement_timeout = %s", (f"{self.statement_timeout_ms}ms",))
        cur.execute("SET LOCAL lock_timeout = %s", (f"{self.lock_timeout_ms}ms",))

    def _acquire_entity_period_lock(self, cur, entity_id: str, period_end: date) -> None:
        lock_key = f"eff:{entity_id}:{period_end.isoformat()}"
        cur.execute("SELECT pg_advisory_xact_lock(830221, hashtext(%s))", (lock_key,))

    def _create_temp_staging(self, cur) -> None:
        feature_defs = sql.SQL(",\n").join(
            sql.SQL("{} NUMERIC").format(sql.Identifier(c)) for c in ALLOWED_FEATURE_COLUMNS)
        query = sql.SQL("""
            CREATE TEMP TABLE tmp_eff_staging (
                entity_id TEXT NOT NULL,
                period_end DATE NOT NULL,
                report_type VARCHAR(10) NOT NULL,
                reprt_code VARCHAR(10),
                statement_end DATE,
                period_months SMALLINT,
                is_accumulated BOOLEAN NOT NULL,
                fetched_at TIMESTAMPTZ NOT NULL,
                batch_id UUID NOT NULL,
                source_hash CHAR(64) NOT NULL,
                feature_quality JSONB NOT NULL,
                {feature_defs}
            ) ON COMMIT DROP
        """).format(feature_defs=feature_defs)
        cur.execute(query)

    def _copy_rows_to_staging(self, cur, rows: list) -> None:
        columns = ("entity_id", "period_end", "report_type", "reprt_code", "statement_end",
                   "period_months", "is_accumulated", "fetched_at", "batch_id", "source_hash",
                   "feature_quality") + ALLOWED_FEATURE_COLUMNS
        buffer = io.StringIO()
        for row in rows:
            record = [row.entity_id, row.period_end, row.report_type, row.reprt_code,
                      row.statement_end, row.period_months, row.is_accumulated, row.fetched_at,
                      row.batch_id, row.source_hash, row.feature_quality]
            record.extend(row.features.get(c) for c in ALLOWED_FEATURE_COLUMNS)
            buffer.write("\t".join(_copy_value(v) for v in record))
            buffer.write("\n")
        buffer.seek(0)
        # COPY TEXT 포맷 (기본): 탭 구분, NULL=\N, backslash/탭/개행만 이스케이프 → JSON 따옴표 안전.
        copy_sql = sql.SQL("COPY tmp_eff_staging ({columns}) FROM STDIN").format(
            columns=sql.SQL(", ").join(map(sql.Identifier, columns)))
        cur.copy_expert(copy_sql.as_string(cur), buffer)

    def _insert_versions_from_staging(self, cur) -> None:
        columns = ("entity_id", "period_end", "report_type", "reprt_code", "statement_end",
                   "period_months", "is_accumulated", "fetched_at", "batch_id", "source_hash",
                   "feature_quality") + ALLOWED_FEATURE_COLUMNS
        query = sql.SQL("""
            INSERT INTO entity_financial_feature_versions ({columns})
            SELECT {columns} FROM tmp_eff_staging
            ORDER BY entity_id, period_end,
                CASE report_type WHEN 'annual' THEN 1 WHEN 'q3' THEN 2 WHEN 'half' THEN 3 WHEN 'q1' THEN 4 ELSE 99 END
            ON CONFLICT (entity_id, period_end, report_type, source_hash) DO NOTHING
        """).format(columns=sql.SQL(", ").join(map(sql.Identifier, columns)))
        cur.execute(query)

    def _refresh_current_projection(self, cur, batch_id: UUID) -> None:
        feature_columns = ALLOWED_FEATURE_COLUMNS
        insert_columns = ("entity_id", "period_end", "report_type", "reprt_code", "statement_end",
                          "period_months", "is_accumulated", "fetched_at", "batch_id", "source_hash",
                          "feature_quality", "current_version_id") + feature_columns
        select_columns = ("entity_id", "period_end", "report_type", "reprt_code", "statement_end",
                          "period_months", "is_accumulated", "fetched_at", "batch_id", "source_hash",
                          "feature_quality", "version_id") + feature_columns
        update_columns = ("reprt_code", "statement_end", "period_months", "is_accumulated",
                          "fetched_at", "batch_id", "source_hash", "feature_quality",
                          "current_version_id") + feature_columns
        update_assignments = [sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c))
                              for c in update_columns]
        update_assignments.append(sql.SQL("updated_at = NOW()"))
        diff_conditions = [
            sql.SQL("entity_financial_features.{} IS DISTINCT FROM EXCLUDED.{}").format(
                sql.Identifier(c), sql.Identifier(c)) for c in update_columns]
        query = sql.SQL("""
            WITH latest AS (
                SELECT DISTINCT ON (entity_id, period_end, report_type) {select_columns}
                FROM entity_financial_feature_versions
                WHERE batch_id = %s
                ORDER BY entity_id, period_end, report_type, fetched_at DESC, version_id DESC
            )
            INSERT INTO entity_financial_features ({insert_columns})
            SELECT {select_columns} FROM latest
            ON CONFLICT (entity_id, period_end, report_type)
            DO UPDATE SET {updates}
            WHERE {diff_condition}
        """).format(
            select_columns=sql.SQL(", ").join(map(sql.Identifier, select_columns)),
            insert_columns=sql.SQL(", ").join(map(sql.Identifier, insert_columns)),
            updates=sql.SQL(", ").join(update_assignments),
            diff_condition=sql.SQL(" OR ").join(diff_conditions))
        cur.execute(query, (str(batch_id),))

    def _verify_batch_before_commit(self, cur, *, entity_id, period_end, batch_id, expected_report_types) -> None:
        invalid = expected_report_types - VALID_REPORT_TYPES
        if invalid:
            raise MythosValidationError(f"Invalid expected_report_types={sorted(invalid)}")
        # batch_id로 필터하지 않는다: 동일 source_hash 재수집은 ON CONFLICT DO NOTHING이라
        # 이번 batch_id로는 0건 → 멱등 재실행이 실패함. (entity_id, period_end) 완전성으로 검증.
        cur.execute("""
            SELECT DISTINCT report_type FROM entity_financial_feature_versions
            WHERE entity_id = %s AND period_end = %s
        """, (entity_id, period_end))
        found = {row[0] for row in cur.fetchall()}
        missing = expected_report_types - found
        unexpected = found - VALID_REPORT_TYPES
        if missing or unexpected:
            raise MythosValidationError(
                f"Batch verification failed. entity_id={entity_id}, period_end={period_end}, "
                f"found={sorted(found)}, missing={sorted(missing)}, unexpected={sorted(unexpected)}")

    def _safe_rollback(self, conn) -> None:
        try:
            if conn and not conn.closed:
                conn.rollback()
        except Exception:
            logger.exception("[WARN] rollback failed")

    def _release_conn(self, conn) -> None:
        if conn is None:
            return
        try:
            if not conn.closed:
                if conn.status != extensions.STATUS_READY:
                    self._safe_rollback(conn)
                if self.reset_connection_on_release:
                    conn.reset()
        except Exception:
            logger.exception("[WARN] connection reset failed; closing")
            try:
                conn.close()
            except Exception:
                pass
        finally:
            self.pool.putconn(conn)


def get_financial_features_as_of(conn, *, entity_id: str, period_end: date,
                                 report_type: str, as_of: datetime) -> Optional[dict]:
    if report_type not in VALID_REPORT_TYPES:
        raise ValueError(f"Invalid report_type={report_type!r}")
    feature_select = ", ".join(ALLOWED_FEATURE_COLUMNS)
    query = f"""
        SELECT version_id, entity_id, period_end, report_type, reprt_code, statement_end,
               period_months, is_accumulated, fetched_at, batch_id, source_hash, feature_quality,
               {feature_select}
        FROM entity_financial_feature_versions
        WHERE entity_id = %s AND period_end = %s AND report_type = %s AND fetched_at <= %s
        ORDER BY fetched_at DESC, version_id DESC LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(query, (entity_id, period_end, report_type, as_of))
        row = cur.fetchone()
    if row is None:
        return None
    base_keys = ["version_id", "entity_id", "period_end", "report_type", "reprt_code",
                 "statement_end", "period_months", "is_accumulated", "fetched_at", "batch_id",
                 "source_hash", "feature_quality"]
    keys = base_keys + list(ALLOWED_FEATURE_COLUMNS)
    return dict(zip(keys, row))


def verify_current_four_rows(conn, *, entity_id: str, period_end: date) -> list:
    query = """
        SELECT entity_id, period_end, report_type, statement_end, period_months,
               fetched_at, source_hash, current_version_id
        FROM entity_financial_features
        WHERE entity_id = %s AND period_end = %s
        ORDER BY CASE report_type WHEN 'annual' THEN 1 WHEN 'q3' THEN 2 WHEN 'half' THEN 3 WHEN 'q1' THEN 4 ELSE 99 END
    """
    with conn.cursor() as cur:
        cur.execute(query, (entity_id, period_end))
        rows = cur.fetchall()
    found = {r[2] for r in rows}
    expected = {"annual", "q3", "half", "q1"}
    missing = expected - found
    unexpected = found - expected
    if len(rows) != 4 or missing or unexpected:
        raise AssertionError(
            f"Expected current 4 report rows. entity_id={entity_id}, period_end={period_end}, "
            f"row_count={len(rows)}, found={sorted(found)}, missing={sorted(missing)}, unexpected={sorted(unexpected)}")
    return rows

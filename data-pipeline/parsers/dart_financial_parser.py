from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)


# ============================================================
# 1. Account mapping
# ============================================================

ACCOUNT_SUFFIXES: Dict[str, str] = {
    "current_assets": "CurrentAssets",
    "assets": "Assets",
    "retained_earnings": "RetainedEarnings",
    "equity": "Equity",
    "liabilities": "Liabilities",
    "revenue": "Revenue",
    "operating_income": "OperatingIncome",
    "finance_costs": "FinanceCosts",
    "cash_flows_from_operations": "CashFlowsFromOperations",
}


ACCOUNT_ID_MAP: Dict[str, List[str]] = {
    field: [
        f"ifrs-full_{suffix}",
        f"dart_{suffix}",
    ]
    for field, suffix in ACCOUNT_SUFFIXES.items()
}


ACCOUNT_NAME_EXACT_ALIASES: Dict[str, List[str]] = {
    "current_assets": [
        "유동자산",
        "currentassets",
    ],
    "assets": [
        "자산총계",
        "총자산",
        "자산합계",
        "totalassets",
        "assets",
    ],
    "retained_earnings": [
        "이익잉여금",
        "결손금",
        "retainedearnings",
        "retainedearningsaccumulateddeficit",
    ],
    "equity": [
        "자본총계",
        "총자본",
        "자본합계",
        "totalequity",
        "equity",
    ],
    "liabilities": [
        "부채총계",
        "총부채",
        "부채합계",
        "totalliabilities",
        "liabilities",
    ],
    "revenue": [
        "매출액",
        "영업수익",
        "수익",
        "revenue",
        "sales",
    ],
    "operating_income": [
        "영업이익",
        "영업손실",
        "operatingincome",
        "operatingloss",
    ],
    "finance_costs": [
        "금융비용",
        "이자비용",
        "financecosts",
        "interestexpense",
    ],
    "cash_flows_from_operations": [
        "영업활동현금흐름",
        "영업활동으로인한현금흐름",
        "영업활동순현금흐름",
        "netcashflowsfromoperatingactivities",
        "cashflowsfromoperations",
    ],
}


ACCOUNT_NAME_CONTAINS_ALIASES: Dict[str, List[str]] = {
    "current_assets": [
        "유동자산",
        "currentassets",
    ],
    "assets": [
        "자산총계",
        "총자산",
        "자산합계",
        "totalassets",
    ],
    "retained_earnings": [
        "이익잉여금",
        "결손금",
        "retainedearnings",
    ],
    "equity": [
        "자본총계",
        "총자본",
        "자본합계",
        "totalequity",
    ],
    "liabilities": [
        "부채총계",
        "총부채",
        "부채합계",
        "totalliabilities",
    ],
    "revenue": [
        "매출액",
        "영업수익",
        "revenue",
    ],
    "operating_income": [
        "영업이익",
        "영업손실",
        "operatingincome",
        "operatingloss",
    ],
    "finance_costs": [
        "금융비용",
        "이자비용",
        "financecosts",
        "interestexpense",
    ],
    "cash_flows_from_operations": [
        "영업활동현금흐름",
        "영업활동으로인한현금흐름",
        "영업활동순현금흐름",
        "netcashflowsfromoperatingactivities",
        "cashflowsfromoperations",
    ],
}


FLOW_FIELDS = {
    "revenue",
    "operating_income",
    "finance_costs",
    "cash_flows_from_operations",
}


# ============================================================
# 2. Status classification
# ============================================================

DART_STATUS_CLASSIFICATION: Dict[str, Dict[str, Any]] = {
    "000": {"kind": "OK", "transient": False},
    "010": {"kind": "INVALID_API_KEY", "transient": False},
    "011": {"kind": "INVALID_PARAMETER", "transient": False},
    "012": {"kind": "NO_PERMISSION", "transient": False},
    "013": {"kind": "NO_DATA", "transient": False},
    "014": {"kind": "FILE_NOT_FOUND", "transient": False},
    "020": {"kind": "AUTH_ERROR", "transient": False},
    "021": {"kind": "DAILY_LIMIT_EXCEEDED", "transient": True},
    "800": {"kind": "RATE_LIMIT_OR_SERVICE_RESTRICTED", "transient": True},
    "900": {"kind": "SERVER_OR_UNKNOWN_ERROR", "transient": True},
}


def classify_dart_status(status: Any, message: Any = None) -> Dict[str, Any]:
    code = str(status or "").strip()

    base = DART_STATUS_CLASSIFICATION.get(
        code,
        {"kind": "UNKNOWN_STATUS", "transient": False},
    )

    return {
        "status": code,
        "message": message,
        "kind": base["kind"],
        "transient": bool(base["transient"]),
    }


# ============================================================
# 3. Unit policy
# ============================================================

SUPPORTED_UNITS = {
    "KRW",
    "KRW_THOUSAND",
    "USD",
    "USD_THOUSAND",
    "RAW",
}


UNIT_ALIASES = {
    "KRW": "KRW",
    "원": "KRW",
    "WON": "KRW",
    "KOREANWON": "KRW",

    "KRW_THOUSAND": "KRW_THOUSAND",
    "천원": "KRW_THOUSAND",
    "단위:천원": "KRW_THOUSAND",
    "THOUSANDKRW": "KRW_THOUSAND",
    "KRW000": "KRW_THOUSAND",

    "USD": "USD",
    "US$": "USD",
    "DOLLAR": "USD",
    "DOLLARS": "USD",

    "USD_THOUSAND": "USD_THOUSAND",
    "THOUSANDUSD": "USD_THOUSAND",
    "USD000": "USD_THOUSAND",

    "RAW": "RAW",
}


UNIT_KEYS = {
    "unit",
    "currency",
    "currency_unit",
    "amount_unit",
    "unit_nm",
    "unit_name",
}


def _normalize_unit(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip().upper()
    text = text.replace(" ", " ")
    text = re.sub(r"\s+", "", text)

    if not text:
        return None

    return UNIT_ALIASES.get(text)


def _collect_declared_units(
    response: Dict[str, Any],
    rows: List[Dict[str, Any]],
) -> List[str]:
    units: List[str] = []

    for key in UNIT_KEYS:
        unit = _normalize_unit(response.get(key))
        if unit:
            units.append(unit)

    for row in rows:
        for key in UNIT_KEYS:
            unit = _normalize_unit(row.get(key))
            if unit:
                units.append(unit)

    return units


def _unit_multiplier(
    input_unit: str,
    output_unit: str,
) -> Optional[Decimal]:
    """
    FX 변환은 여기서 하지 않는다.
    USD -> KRW 같은 변환은 scanner 단계가 아니라 별도 FX anchor가 필요하다.
    """
    if input_unit == output_unit:
        return Decimal("1")

    if input_unit == "KRW_THOUSAND" and output_unit == "KRW":
        return Decimal("1000")

    if input_unit == "USD_THOUSAND" and output_unit == "USD":
        return Decimal("1000")

    if input_unit == "RAW" and output_unit == "RAW":
        return Decimal("1")

    return None


def _resolve_unit_policy(
    *,
    response: Dict[str, Any],
    rows: List[Dict[str, Any]],
    input_unit: Optional[str],
    output_unit: str,
    strict_unit_consistency: bool,
    fail_on_unknown_unit: bool,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    반환:
      unit_policy, error
    """
    declared_units = _collect_declared_units(response, rows)
    declared_set = set(declared_units)

    normalized_input_unit = _normalize_unit(input_unit) if input_unit else None
    normalized_output_unit = _normalize_unit(output_unit) or output_unit

    if normalized_output_unit not in SUPPORTED_UNITS:
        return None, {
            "kind": "UNSUPPORTED_OUTPUT_UNIT",
            "message": f"unsupported output_unit={output_unit}",
            "transient": False,
        }

    if len(declared_set) > 1 and strict_unit_consistency:
        return None, {
            "kind": "MIXED_UNIT_DETECTED",
            "message": f"multiple declared units detected: {sorted(declared_set)}",
            "transient": False,
            "declared_units": sorted(declared_set),
        }

    if normalized_input_unit:
        if normalized_input_unit not in SUPPORTED_UNITS:
            return None, {
                "kind": "UNSUPPORTED_INPUT_UNIT",
                "message": f"unsupported input_unit={input_unit}",
                "transient": False,
            }

        if declared_set and strict_unit_consistency and declared_set != {normalized_input_unit}:
            return None, {
                "kind": "UNIT_CONFLICT",
                "message": (
                    f"configured input_unit={normalized_input_unit}, "
                    f"but declared units={sorted(declared_set)}"
                ),
                "transient": False,
                "configured_unit": normalized_input_unit,
                "declared_units": sorted(declared_set),
            }

        unit_source = "configured"
        final_input_unit = normalized_input_unit
        unit_warning = None

    else:
        if len(declared_set) == 1:
            final_input_unit = next(iter(declared_set))
            unit_source = "inferred"
            unit_warning = None
        elif not declared_set:
            if fail_on_unknown_unit:
                return None, {
                    "kind": "UNKNOWN_UNIT",
                    "message": "no unit metadata found and input_unit is None",
                    "transient": False,
                }

            final_input_unit = "RAW"
            unit_source = "unknown"
            unit_warning = "unit is unknown; values are parsed as RAW without currency assumption"
        else:
            return None, {
                "kind": "MIXED_UNIT_DETECTED",
                "message": f"multiple declared units detected: {sorted(declared_set)}",
                "transient": False,
                "declared_units": sorted(declared_set),
            }

    multiplier = _unit_multiplier(final_input_unit, normalized_output_unit)

    if multiplier is None:
        return None, {
            "kind": "UNIT_CONVERSION_UNSUPPORTED",
            "message": (
                f"conversion from {final_input_unit} to {normalized_output_unit} "
                "is not supported without explicit FX or unit policy"
            ),
            "transient": False,
            "input_unit": final_input_unit,
            "output_unit": normalized_output_unit,
        }

    return {
        "input_unit": final_input_unit,
        "output_unit": normalized_output_unit,
        "unit_source": unit_source,
        "declared_units": sorted(declared_set),
        "multiplier": multiplier,
        "unit_warning": unit_warning,
    }, None


# ============================================================
# 4. Text / numeric parsing
# ============================================================

_NUM_RE = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$"
)


_VALID_COMMA_RE = re.compile(
    r"^[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:[eE][+-]?\d+)?$"
)


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.replace(" ", " ")
    text = re.sub(r"\s+", "", text)

    text = text.replace("Ⅰ", "i")
    text = text.replace("Ⅱ", "ii")
    text = text.replace("Ⅲ", "iii")
    text = text.replace("Ⅳ", "iv")

    text = text.replace("(", "").replace(")", "")
    text = text.replace("（", "").replace("）", "")

    return text


def _parse_amount(
    value: Any,
    *,
    multiplier: Decimal,
    field: str,
    amount_key: str,
) -> Tuple[Optional[int], Dict[str, Any]]:
    """
    Institutional-grade numeric parser.

    원칙:
    - float 입력 차단
    - Decimal 직접 파싱
    - 과학적 표기법 지원
    - 비정상 콤마는 정제하되 warning 남김
    - 소수점은 ROUND_HALF_UP
    """
    meta: Dict[str, Any] = {
        "raw_value": value,
        "amount_key": amount_key,
        "parse_warnings": [],
    }

    if value is None:
        return None, meta

    if isinstance(value, bool):
        meta["parse_warnings"].append("BOOL_AMOUNT_IGNORED")
        logger.warning("bool amount ignored: field=%s key=%s value=%r", field, amount_key, value)
        return None, meta

    if isinstance(value, float):
        meta["parse_warnings"].append("FLOAT_AMOUNT_BLOCKED")
        logger.error("float amount blocked to prevent precision loss: field=%s key=%s value=%r", field, amount_key, value)
        return None, meta

    if isinstance(value, int):
        d = Decimal(value)

    elif isinstance(value, Decimal):
        d = value

    else:
        raw = str(value).strip()
        raw = raw.replace(" ", " ")
        raw = re.sub(r"\s+", "", raw)

        if not raw or raw in {"-", "nan", "NaN", "N/A", "n/a"}:
            return None, meta

        negative_by_parentheses = False
        if raw.startswith("(") and raw.endswith(")"):
            negative_by_parentheses = True
            raw = raw[1:-1]

        if "," in raw and not _VALID_COMMA_RE.match(raw):
            meta["parse_warnings"].append("ABNORMAL_COMMA_CLEANED")
            logger.warning("abnormal comma cleaned: field=%s key=%s raw=%r", field, amount_key, value)

        cleaned = raw.replace(",", "")

        if not _NUM_RE.match(cleaned):
            meta["parse_warnings"].append("NON_NUMERIC_AMOUNT")
            logger.debug("non-numeric amount ignored: field=%s key=%s raw=%r", field, amount_key, value)
            return None, meta

        try:
            d = Decimal(cleaned)
        except InvalidOperation:
            meta["parse_warnings"].append("INVALID_DECIMAL")
            logger.debug("invalid Decimal amount ignored: field=%s key=%s raw=%r", field, amount_key, value)
            return None, meta

        if negative_by_parentheses:
            d = -abs(d)

    scaled = d * multiplier

    if scaled != scaled.to_integral_value():
        meta["parse_warnings"].append("FRACTIONAL_AMOUNT_ROUNDED_HALF_UP")
        logger.warning(
            "fractional amount rounded HALF_UP: field=%s key=%s raw=%r scaled=%s",
            field,
            amount_key,
            value,
            scaled,
        )

    rounded = scaled.to_integral_value(rounding=ROUND_HALF_UP)

    return int(rounded), meta


def _first_valid_amount(
    candidates: List[Tuple[str, Any]],
    *,
    field: str,
    multiplier: Decimal,
) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
    """
    0값 보존.
    amount == 0도 정상값이므로 `or` 사용 금지.
    """
    last_meta: Optional[Dict[str, Any]] = None

    for amount_key, raw_value in candidates:
        amount, meta = _parse_amount(
            raw_value,
            multiplier=multiplier,
            field=field,
            amount_key=amount_key,
        )
        last_meta = meta

        if amount is not None:
            return amount, meta

    return None, last_meta


def _get_amount(
    row: Dict[str, Any],
    field: str,
    *,
    multiplier: Decimal,
) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
    """
    BS:
      - thstrm_amount

    IS/CF:
      - thstrm_add_amount 우선
      - 없을 때만 thstrm_amount fallback

    `0`은 정상값으로 유지한다.
    """
    if field in FLOW_FIELDS:
        return _first_valid_amount(
            [
                ("thstrm_add_amount", row.get("thstrm_add_amount")),
                ("thstrm_amount", row.get("thstrm_amount")),
            ],
            field=field,
            multiplier=multiplier,
        )

    return _first_valid_amount(
        [
            ("thstrm_amount", row.get("thstrm_amount")),
        ],
        field=field,
        multiplier=multiplier,
    )


# ============================================================
# 5. Row matching
# ============================================================

def _get_clean_account_id(row: Dict[str, Any]) -> str:
    return str(row.get("account_id") or "").strip()


def _matches_account_id(row: Dict[str, Any], field: str) -> bool:
    account_id = _get_clean_account_id(row)
    return account_id in ACCOUNT_ID_MAP[field]


def _matches_account_name(row: Dict[str, Any], field: str) -> bool:
    account_nm = _normalize_text(row.get("account_nm"))

    if not account_nm:
        return False

    exact_aliases = {
        _normalize_text(alias)
        for alias in ACCOUNT_NAME_EXACT_ALIASES.get(field, [])
    }

    if account_nm in exact_aliases:
        return True

    contains_aliases = [
        _normalize_text(alias)
        for alias in ACCOUNT_NAME_CONTAINS_ALIASES.get(field, [])
    ]

    return any(alias and alias in account_nm for alias in contains_aliases)


def _row_matches(row: Dict[str, Any], field: str) -> bool:
    account_id = _get_clean_account_id(row)

    if account_id:
        return _matches_account_id(row, field)

    return _matches_account_name(row, field)


def _select_rows_by_fs_div(
    rows: List[Dict[str, Any]],
    fs_div: str,
) -> List[Dict[str, Any]]:
    target = fs_div.upper()

    return [
        row
        for row in rows
        if str(row.get("fs_div") or "").strip().upper() == target
    ]


def _fs_div_of(row: Optional[Dict[str, Any]]) -> Optional[str]:
    if not row:
        return None

    fs_div = str(row.get("fs_div") or "").strip().upper()
    return fs_div or None


def _ord_key(row: Dict[str, Any]) -> Tuple[int, str, str, str]:
    try:
        ord_value = int(str(row.get("ord")).strip())
    except (TypeError, ValueError):
        ord_value = 999999

    return (
        ord_value,
        str(row.get("sj_div") or ""),
        str(row.get("account_id") or ""),
        str(row.get("account_nm") or ""),
    )


def _build_audit_entry(
    *,
    field: str,
    row: Dict[str, Any],
    amount: int,
    amount_meta: Dict[str, Any],
    unit_policy: Dict[str, Any],
) -> Dict[str, Any]:
    """
    source_rows 원본 전체를 반환하지 않는다.
    감사·검증에 필요한 최소 필드만 반환한다.
    """
    return {
        "field": field,
        "account_id": str(row.get("account_id") or "").strip() or None,
        "account_nm": row.get("account_nm"),
        "fs_div": _fs_div_of(row),
        "sj_div": row.get("sj_div"),
        "sj_nm": row.get("sj_nm"),
        "ord": row.get("ord"),
        "amount": amount,
        "raw_value": amount_meta.get("raw_value"),
        "amount_key": amount_meta.get("amount_key"),
        "input_unit": unit_policy["input_unit"],
        "output_unit": unit_policy["output_unit"],
        "unit_source": unit_policy["unit_source"],
        "rounding": "ROUND_HALF_UP",
        "parse_warnings": amount_meta.get("parse_warnings", []),
    }


def _find_value(
    rows: List[Dict[str, Any]],
    field: str,
    *,
    multiplier: Decimal,
    unit_policy: Dict[str, Any],
) -> Tuple[Optional[int], Optional[Dict[str, Any]], Optional[str], Optional[Dict[str, Any]]]:
    matched = [
        row
        for row in rows
        if isinstance(row, dict) and _row_matches(row, field)
    ]

    if not matched:
        return None, None, None, None

    matched.sort(key=_ord_key)

    for row in matched:
        amount, amount_meta = _get_amount(
            row,
            field,
            multiplier=multiplier,
        )

        if amount is not None and amount_meta is not None:
            audit_entry = _build_audit_entry(
                field=field,
                row=row,
                amount=amount,
                amount_meta=amount_meta,
                unit_policy=unit_policy,
            )
            return amount, row, _fs_div_of(row), audit_entry

    return None, matched[0], _fs_div_of(matched[0]), None


# ============================================================
# 6. Result helpers
# ============================================================

def _empty_values() -> Dict[str, Optional[int]]:
    return {field: None for field in ACCOUNT_SUFFIXES}


def _empty_audit_trail() -> Dict[str, Optional[Dict[str, Any]]]:
    return {field: None for field in ACCOUNT_SUFFIXES}


def _empty_fs_div_per_account() -> Dict[str, Optional[str]]:
    return {field: None for field in ACCOUNT_SUFFIXES}


def _empty_result(
    *,
    error: Optional[Dict[str, Any]] = None,
    status_info: Optional[Dict[str, Any]] = None,
    unit_policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "fs_div_used": None,
        "values": _empty_values(),
        "audit_trail": _empty_audit_trail(),
        "fs_div_per_account": _empty_fs_div_per_account(),
        "missing": list(ACCOUNT_SUFFIXES.keys()),
        "unit": unit_policy["output_unit"] if unit_policy else None,
        "input_unit": unit_policy["input_unit"] if unit_policy else None,
        "unit_source": unit_policy["unit_source"] if unit_policy else None,
        "unit_warning": unit_policy.get("unit_warning") if unit_policy else None,
        "mixed_fs": False,
        "strict_fs_consistency": None,
        "strict_mode_violated": False,
        "fallback_blocked_fields": [],
        "quality_flags": [],
        "status_info": status_info,
    }

    if error:
        result["error"] = error

    return result


# ============================================================
# 7. Main parser
# ============================================================

def parse_opendart_financial_accounts(
    response: Dict[str, Any],
    *,
    strict_fs_consistency: bool = True,
    input_unit: Optional[str] = "KRW",
    output_unit: str = "KRW",
    strict_unit_consistency: bool = True,
    fail_on_unknown_unit: bool = False,
) -> Dict[str, Any]:
    """
    COSMOS financial_anchor용 OpenDART 재무계정 파서.

    기본 원칙:
    - 연결재무제표(CFS)가 있으면 CFS 우선.
    - strict_fs_consistency=True이면 CFS 누락 계정을 OFS로 보완하지 않는다.
    - strict_fs_consistency=False일 때만 OFS fallback 허용.
    - 원본 source_rows 전체를 반환하지 않고 audit_trail만 반환.
    - 단위는 명시적 정책으로 처리한다.

    Parameters
    ----------
    response:
        OpenDART fnlttSinglAcnt.json 또는 fnlttSinglAcntAll.json 응답.
    strict_fs_consistency:
        True이면 CFS/OFS 혼용 차단.
    input_unit:
        입력 금액 단위.
        기본 "KRW".
        None이면 응답/row 메타데이터에서 추론 시도.
    output_unit:
        출력 금액 단위.
        기본 "KRW".
    strict_unit_consistency:
        True이면 응답 내 단위 충돌 시 error.
    fail_on_unknown_unit:
        True이고 input_unit=None인데 단위를 추론할 수 없으면 error.

    Returns
    -------
    {
        "values": {...},
        "audit_trail": {...},
        "fs_div_per_account": {...},
        "missing": [...],
        "mixed_fs": bool,
        "strict_mode_violated": bool,
        "fallback_blocked_fields": [...],
        "quality_flags": [...],
        ...
    }
    """
    if not isinstance(response, dict):
        return _empty_result(
            error={
                "kind": "INVALID_RESPONSE_TYPE",
                "message": "response must be dict",
                "transient": False,
            },
        )

    status_info = classify_dart_status(
        response.get("status"),
        response.get("message"),
    )

    if status_info["status"] and status_info["status"] != "000":
        return _empty_result(
            error=status_info,
            status_info=status_info,
        )

    rows = response.get("list")

    if not isinstance(rows, list):
        logger.warning("response['list'] is not list; treated as empty")
        rows = []

    rows = [
        row
        for row in rows
        if isinstance(row, dict)
    ]

    unit_policy, unit_error = _resolve_unit_policy(
        response=response,
        rows=rows,
        input_unit=input_unit,
        output_unit=output_unit,
        strict_unit_consistency=strict_unit_consistency,
        fail_on_unknown_unit=fail_on_unknown_unit,
    )

    if unit_error:
        return _empty_result(
            error=unit_error,
            status_info=status_info,
        )

    assert unit_policy is not None

    multiplier: Decimal = unit_policy["multiplier"]

    cfs_rows = _select_rows_by_fs_div(rows, "CFS")
    ofs_rows = _select_rows_by_fs_div(rows, "OFS")
    other_rows = [
        row
        for row in rows
        if str(row.get("fs_div") or "").strip().upper() not in {"CFS", "OFS"}
    ]

    primary_rows = cfs_rows if cfs_rows else ofs_rows
    fallback_rows = ofs_rows if cfs_rows else []

    fs_div_used = "CFS" if cfs_rows else ("OFS" if ofs_rows else None)

    values: Dict[str, Optional[int]] = {}
    audit_trail: Dict[str, Optional[Dict[str, Any]]] = {}
    fs_div_per_account: Dict[str, Optional[str]] = {}

    fallback_blocked_fields: List[str] = []

    for field in ACCOUNT_SUFFIXES:
        amount, src, src_fs, audit = _find_value(
            primary_rows,
            field,
            multiplier=multiplier,
            unit_policy=unit_policy,
        )

        if amount is None and fallback_rows:
            fb_amount, fb_src, fb_fs, fb_audit = _find_value(
                fallback_rows,
                field,
                multiplier=multiplier,
                unit_policy=unit_policy,
            )

            if fb_amount is not None:
                if strict_fs_consistency:
                    fallback_blocked_fields.append(field)
                    logger.warning(
                        "OFS fallback blocked by strict_fs_consistency: field=%s primary=%s fallback=%s",
                        field,
                        fs_div_used,
                        fb_fs,
                    )
                else:
                    amount = fb_amount
                    src = fb_src
                    src_fs = fb_fs
                    audit = fb_audit

        values[field] = amount
        audit_trail[field] = audit
        fs_div_per_account[field] = src_fs if amount is not None else None

    used_fs_set = {
        fs
        for fs in fs_div_per_account.values()
        if fs in {"CFS", "OFS"}
    }

    mixed_fs = len(used_fs_set) > 1

    missing = [
        field
        for field, value in values.items()
        if value is None
    ]

    strict_mode_violated = bool(fallback_blocked_fields)

    quality_flags: List[str] = []

    if mixed_fs:
        quality_flags.append("MIXED_FS")
        logger.warning("financial accounts mixed CFS/OFS: %s", fs_div_per_account)

    if strict_mode_violated:
        quality_flags.append("STRICT_FS_FALLBACK_BLOCKED")

    if missing:
        quality_flags.append("MISSING_FIELDS")
        logger.info("missing financial accounts: %s", missing)

    if unit_policy.get("unit_warning"):
        quality_flags.append("UNIT_WARNING")

    if other_rows:
        quality_flags.append("UNCLASSIFIED_FS_DIV_ROWS")
        logger.debug(
            "unclassified rows ignored because fs_div is not CFS/OFS: %d",
            len(other_rows),
        )

    return {
        "fs_div_used": fs_div_used,
        "values": values,
        "audit_trail": audit_trail,
        "fs_div_per_account": fs_div_per_account,
        "missing": missing,
        "unit": unit_policy["output_unit"],
        "input_unit": unit_policy["input_unit"],
        "unit_source": unit_policy["unit_source"],
        "unit_warning": unit_policy.get("unit_warning"),
        "declared_units": unit_policy.get("declared_units", []),
        "mixed_fs": mixed_fs,
        "strict_fs_consistency": strict_fs_consistency,
        "strict_mode_violated": strict_mode_violated,
        "fallback_blocked_fields": fallback_blocked_fields,
        "quality_flags": quality_flags,
        "status_info": status_info,
    }


# ============================================================
# 8. Wrapper for separate CFS/OFS responses
# ============================================================

def parse_opendart_financial_accounts_with_fallback(
    cfs_response: Optional[Dict[str, Any]],
    ofs_response: Optional[Dict[str, Any]],
    *,
    strict_fs_consistency: bool = True,
    input_unit: Optional[str] = "KRW",
    output_unit: str = "KRW",
    strict_unit_consistency: bool = True,
    fail_on_unknown_unit: bool = False,
) -> Dict[str, Any]:
    """
    CFS/OFS를 따로 호출하는 구조용 wrapper.

    strict_fs_consistency=True이면:
    - CFS 응답이 존재하는 경우 CFS 기준으로만 파싱.
    - OFS는 fallback 후보로 존재하더라도 실제 값 보완에 쓰지 않음.
    - OFS에만 있는 계정은 fallback_blocked_fields로 기록.

    strict_fs_consistency=False이면:
    - CFS 누락 계정에 대해 OFS fallback 허용.
    - 이 경우 mixed_fs=True가 될 수 있음.
    """
    rows: List[Dict[str, Any]] = []
    partial_errors: List[Dict[str, Any]] = []

    for response in (cfs_response, ofs_response):
        if response is None:
            continue

        if not isinstance(response, dict):
            partial_errors.append({
                "kind": "INVALID_RESPONSE_TYPE",
                "message": "response must be dict",
                "transient": False,
            })
            continue

        status_info = classify_dart_status(
            response.get("status"),
            response.get("message"),
        )

        if status_info["status"] == "000":
            lst = response.get("list")

            if isinstance(lst, list):
                rows.extend(row for row in lst if isinstance(row, dict))
            else:
                partial_errors.append({
                    "kind": "INVALID_LIST_TYPE",
                    "message": "response['list'] must be list",
                    "transient": False,
                })
        else:
            partial_errors.append(status_info)

    if rows:
        merged = {
            "status": "000",
            "message": "merged",
            "list": rows,
        }

        result = parse_opendart_financial_accounts(
            merged,
            strict_fs_consistency=strict_fs_consistency,
            input_unit=input_unit,
            output_unit=output_unit,
            strict_unit_consistency=strict_unit_consistency,
            fail_on_unknown_unit=fail_on_unknown_unit,
        )

        if partial_errors:
            result["partial_errors"] = partial_errors

        return result

    if partial_errors:
        result = _empty_result(
            error=partial_errors[0],
            status_info=partial_errors[0],
        )
        result["partial_errors"] = partial_errors
        return result

    return _empty_result(
        error={
            "kind": "NO_RESPONSE",
            "message": "both cfs_response and ofs_response are empty",
            "transient": False,
        },
    )


# ============================================================
# 9. COSMOS 연동 wrapper
# ============================================================

def to_financial_features(
    parsed: dict,
    entity_id: str,
    entity_name: str,
    period_end: str,
):
    if parsed.get("error"):
        return None
    v = parsed["values"]
    from engines.financial_engine import FinancialFeatures
    return FinancialFeatures(
        entity_id=entity_id,
        entity_name=entity_name,
        period_end=period_end,
        current_assets=    v.get("current_assets") or 0,
        total_assets=      v.get("assets") or 0,
        retained_earnings= v.get("retained_earnings") or 0,
        ebit=              v.get("operating_income") or 0,
        equity=            v.get("equity") or 0,
        total_debt=        v.get("liabilities") or 0,
        sales=             v.get("revenue") or 0,
        interest_expense=  v.get("finance_costs") or 0,
        operating_cf=      v.get("cash_flows_from_operations") or 0,
        short_term_debt=   0,
    )

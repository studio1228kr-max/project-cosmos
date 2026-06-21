"""
COSMOS Lender Cashflow / IRR Engine v1.1

Scheduled lender cashflow -> IRR / MOIC / NPV / DSCR.

Scope note:
- This is a contractual schedule engine, not yet a full downside waterfall.
- Default interest, cash trap, shortfall carry, PIK, mandatory prepay,
  extension fee, recovery timing, reserve sweep, and enforcement waterfall
  should be added in the next layer.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Any

from dateutil.relativedelta import relativedelta

import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_conn():
    return psycopg2.connect(
        os.getenv("DATABASE_URL", "postgresql://localhost/cosmos"),
        cursor_factory=RealDictCursor
    )


getcontext().prec = 28

ALLOWED_FREQ_MONTHS = {1, 3, 6, 12}
ALLOWED_AMORT_TYPES = {"BULLET", "STRAIGHT"}
ALLOWED_RATE_TYPES = {"FLOATING", "FIXED"}

IRR_MAX_ITER = 200
IRR_TOL = 1e-10


class CashflowEngineError(ValueError):
    pass


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    if hasattr(row, "get"):
        return row.get(key, default)
    try:
        return row[key]
    except Exception:
        return default


def _dec(value: Any, name: str, allow_none: bool = False) -> Decimal | None:
    if value is None:
        if allow_none:
            return None
        raise CashflowEngineError(f"{name} is required")
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise CashflowEngineError(f"{name} must be numeric") from exc


def _q(value: Decimal | None, places: str = "0.0001") -> Decimal | None:
    if value is None:
        return None
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _f(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _npv(cashflows: list[float], rate: float) -> float:
    if rate <= -1:
        raise ValueError("periodic IRR rate must be greater than -100%")
    return sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cashflows))


def _dnpv(cashflows: list[float], rate: float) -> float:
    if rate <= -1:
        raise ValueError("periodic IRR rate must be greater than -100%")
    return sum(-t * cf / ((1 + rate) ** (t + 1)) for t, cf in enumerate(cashflows))


def _sign_changes(cashflows: list[float]) -> int:
    signs: list[int] = []
    for cf in cashflows:
        if abs(cf) < 1e-12:
            continue
        signs.append(1 if cf > 0 else -1)
    return sum(1 for i in range(1, len(signs)) if signs[i] != signs[i - 1])


def _find_bracket(cashflows: list[float]) -> tuple[float, float] | None:
    grid = [
        -0.999999, -0.99, -0.95, -0.90, -0.80, -0.70, -0.60, -0.50,
        -0.40, -0.30, -0.20, -0.10, -0.05, -0.01, 0.0, 0.01,
        0.02, 0.03, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30,
        0.50, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0,
    ]
    prev_r: float | None = None
    prev_v: float | None = None
    for r in grid:
        try:
            v = _npv(cashflows, r)
        except Exception:
            continue
        if abs(v) < IRR_TOL:
            return (r, r)
        if prev_v is not None and prev_v * v < 0:
            return (prev_r, r)
        prev_r, prev_v = r, v
    return None


def _irr_bisection(cashflows: list[float]) -> tuple[float | None, bool]:
    bracket = _find_bracket(cashflows)
    if bracket is None:
        return None, False
    low, high = bracket
    if low == high:
        return low, True
    f_low = _npv(cashflows, low)
    mid = None
    for _ in range(IRR_MAX_ITER):
        mid = (low + high) / 2
        f_mid = _npv(cashflows, mid)
        if abs(f_mid) < IRR_TOL or abs(high - low) < IRR_TOL:
            return mid, True
        if f_low * f_mid <= 0:
            high = mid
        else:
            low = mid
            f_low = f_mid
    return mid, False


def _irr_annual(cashflows: list[float], freq_per_year: float) -> dict[str, Any]:
    warnings: list[str] = []
    if len(cashflows) < 2:
        return {"annual_irr": None, "periodic_irr": None, "method": None,
                "warnings": ["IRR_REQUIRES_AT_LEAST_TWO_CASHFLOWS"]}
    if not any(cf < 0 for cf in cashflows) or not any(cf > 0 for cf in cashflows):
        return {"annual_irr": None, "periodic_irr": None, "method": None,
                "warnings": ["IRR_NO_SIGN_CHANGE"]}
    if _sign_changes(cashflows) > 1:
        warnings.append("IRR_MULTIPLE_SIGN_CHANGES_POSSIBLE_MULTIPLE_ROOTS")
    rate = 0.02
    newton_ok = False
    for _ in range(IRR_MAX_ITER):
        if rate <= -0.999999:
            break
        try:
            v = _npv(cashflows, rate)
            dv = _dnpv(cashflows, rate)
        except Exception:
            break
        if abs(dv) < 1e-14:
            break
        delta = v / dv
        candidate = rate - delta
        if candidate <= -0.999999:
            break
        rate = candidate
        if abs(delta) < IRR_TOL:
            try:
                newton_ok = abs(_npv(cashflows, rate)) < 1e-7
            except Exception:
                newton_ok = False
            break
    if newton_ok:
        return {"annual_irr": (1 + rate) ** freq_per_year - 1,
                "periodic_irr": rate, "method": "NEWTON", "warnings": warnings}
    warnings.append("IRR_NEWTON_FAILED_USED_BISECTION")
    periodic, converged = _irr_bisection(cashflows)
    if periodic is None:
        warnings.append("IRR_BISECTION_NO_BRACKET")
        return {"annual_irr": None, "periodic_irr": None, "method": None, "warnings": warnings}
    if not converged:
        warnings.append("IRR_BISECTION_MAX_ITER_REACHED")
    return {"annual_irr": (1 + periodic) ** freq_per_year - 1,
            "periodic_irr": periodic, "method": "BISECTION", "warnings": warnings}


def _column_exists(cur: Any, table: str, column: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s LIMIT 1",
        (table, column),
    )
    return cur.fetchone() is not None


def _fetch_assumption(cur: Any, deal_id: int, scenario_label: str) -> dict[str, Any] | None:
    cols = [
        "id", "deal_master_id", "scenario_label", "assumption_version",
        "instrument_type", "notional_eok", "rate_type", "spread_bps",
        "origination_date", "maturity_date",
        "interest_payment_frequency_months", "upfront_fee_bps",
    ]
    if _column_exists(cur, "deal_cashflow_assumptions", "fixed_rate_bps"):
        cols.append("fixed_rate_bps")
    cur.execute(
        f"SELECT {', '.join(cols)} FROM deal_cashflow_assumptions "
        "WHERE deal_master_id=%s AND scenario_label=%s ORDER BY assumption_version DESC LIMIT 1",
        (deal_id, scenario_label),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {c: _row_get(row, c) for c in cols}


def _resolve_all_in_rate(a: dict, base_rate: Decimal) -> tuple[Decimal, list[str]]:
    warnings: list[str] = []
    rate_type = str(a.get("rate_type") or "").upper().strip()
    if rate_type not in ALLOWED_RATE_TYPES:
        raise CashflowEngineError(f"rate_type must be one of {sorted(ALLOWED_RATE_TYPES)}")
    spread_bps = _dec(a.get("spread_bps"), "spread_bps", allow_none=True)
    fixed_rate_bps = _dec(a.get("fixed_rate_bps"), "fixed_rate_bps", allow_none=True)
    if rate_type == "FLOATING":
        if spread_bps is None:
            raise CashflowEngineError("FLOATING rate requires spread_bps")
        if spread_bps < 0:
            raise CashflowEngineError("spread_bps cannot be negative")
        return base_rate + spread_bps / Decimal("10000"), warnings
    if fixed_rate_bps is not None:
        if fixed_rate_bps < 0:
            raise CashflowEngineError("fixed_rate_bps cannot be negative")
        return fixed_rate_bps / Decimal("10000"), warnings
    if spread_bps is not None:
        if spread_bps < 0:
            raise CashflowEngineError("legacy fixed spread_bps cannot be negative")
        warnings.append("LEGACY_FIXED_RATE_FROM_SPREAD_BPS_USE_FIXED_RATE_BPS")
        return spread_bps / Decimal("10000"), warnings
    raise CashflowEngineError("FIXED rate requires fixed_rate_bps")


def _validate_schedule_inputs(notional, all_in_rate, origination_date, maturity_date,
                               amort_type, freq_months, upfront_fee_bps) -> None:
    if notional <= 0:
        raise CashflowEngineError("notional_eok must be greater than 0")
    if all_in_rate < 0:
        raise CashflowEngineError("all_in_rate cannot be negative")
    if not isinstance(origination_date, date) or not isinstance(maturity_date, date):
        raise CashflowEngineError("origination_date and maturity_date must be date objects")
    if maturity_date <= origination_date:
        raise CashflowEngineError("maturity_date must be later than origination_date")
    if freq_months not in ALLOWED_FREQ_MONTHS:
        raise CashflowEngineError(f"freq_months must be one of {sorted(ALLOWED_FREQ_MONTHS)}")
    if amort_type not in ALLOWED_AMORT_TYPES:
        raise CashflowEngineError(f"amort_type must be one of {sorted(ALLOWED_AMORT_TYPES)}")
    if upfront_fee_bps < 0:
        raise CashflowEngineError("upfront_fee_bps cannot be negative")
    if upfront_fee_bps >= Decimal("10000"):
        raise CashflowEngineError("upfront_fee_bps must be below 10000 bps")


def build_schedule(notional_eok, all_in_rate, origination_date, maturity_date,
                   amort_type, freq_months, upfront_fee_bps, noi_annual_eok):
    notional = _dec(notional_eok, "notional_eok")
    rate = _dec(all_in_rate, "all_in_rate")
    upfront_bps = _dec(upfront_fee_bps, "upfront_fee_bps")
    amort = str(amort_type or "BULLET").upper().strip()
    freq_months = int(freq_months)
    _validate_schedule_inputs(notional, rate, origination_date, maturity_date,
                               amort, freq_months, upfront_bps)
    noi_annual = _dec(noi_annual_eok, "noi_annual_eok", allow_none=True)
    if noi_annual is not None and noi_annual < 0:
        raise CashflowEngineError("noi_annual_eok cannot be negative")
    dates: list[date] = []
    d = origination_date
    while True:
        d = d + relativedelta(months=freq_months)
        if d >= maturity_date:
            dates.append(maturity_date)
            break
        dates.append(d)
        if len(dates) > 600:
            raise CashflowEngineError("too many periods; check maturity/frequency")
    if not dates:
        raise CashflowEngineError("schedule generated no dates")
    n = len(dates)
    balance = notional
    straight_base = notional / Decimal(n) if amort == "STRAIGHT" else Decimal("0")
    periods: list[dict] = []
    for i, pdate in enumerate(dates):
        prev = dates[i - 1] if i > 0 else origination_date
        days = Decimal((pdate - prev).days)
        if days <= 0:
            raise CashflowEngineError("cashflow period days must be positive")
        beginning = balance
        interest = beginning * rate * days / Decimal("365")
        is_last = i == n - 1
        if amort == "BULLET":
            principal = beginning if is_last else Decimal("0")
        else:
            principal = beginning if is_last else min(straight_base, beginning)
        total = interest + principal
        ending = beginning - principal
        if abs(ending) < Decimal("0.0000000001"):
            ending = Decimal("0")
        dscr = None
        if noi_annual is not None and total > 0:
            noi_period = noi_annual * days / Decimal("365")
            dscr = noi_period / total
        periods.append({
            "period_seq": i + 1,
            "period_date": pdate,
            "beginning_balance_eok": _f(_q(beginning)),
            "scheduled_interest_eok": _f(_q(interest)),
            "scheduled_principal_eok": _f(_q(principal)),
            "total_payment_eok": _f(_q(total)),
            "ending_balance_eok": _f(_q(ending)),
            "dscr_period": _f(_q(dscr)) if dscr is not None else None,
            "is_default_period": False,
            "_raw_interest_eok": interest,
            "_raw_principal_eok": principal,
            "_raw_total_payment_eok": total,
        })
        balance = ending
    if _q(balance) != Decimal("0.0000"):
        raise CashflowEngineError("schedule did not amortize to zero by maturity")
    upfront_fee = notional * upfront_bps / Decimal("10000")
    return periods, _q(upfront_fee)


def run_irr_for_deal(deal_id: int, scenario_label: str = "BASE") -> dict[str, Any]:
    conn = get_conn()
    conn.rollback()  # 이전 abort 트랜잭션 클린업
    cur = conn.cursor()

    try:
        warnings: list[str] = []

        a = _fetch_assumption(cur, deal_id, scenario_label)
        if not a:
            return {"error": "deal_cashflow_assumptions 없음", "warnings": ["NO_CASHFLOW_ASSUMPTION"]}

        try:
            cur.execute(
                "SELECT value FROM ecos_macro_normalized WHERE stat_code='CD_91' AND is_latest=TRUE LIMIT 1"
            )
            ecos = cur.fetchone()
        except Exception:
            conn.rollback()
            ecos = None
        if ecos:
            base_rate = _dec(_row_get(ecos, "value"), "CD_91") / Decimal("100")
        else:
            base_rate = Decimal("0.035")
            warnings.append("BASE_RATE_FALLBACK_USED_CD91_3_5PCT")

        if base_rate < 0:
            raise CashflowEngineError("base_rate cannot be negative")

        all_in, rate_warnings = _resolve_all_in_rate(a, base_rate)
        warnings.extend(rate_warnings)

        cur.execute(
            "SELECT noi_annual FROM deal_financials WHERE deal_master_id=%s AND is_current=TRUE LIMIT 1",
            (deal_id,),
        )
        fin = cur.fetchone()
        noi = _dec(_row_get(fin, "noi_annual"), "noi_annual", allow_none=True)
        if noi is None:
            warnings.append("NOI_MISSING_DSCR_NOT_COMPUTED")

        freq_months = int(a.get("interest_payment_frequency_months") or 3)
        freq_per_year = Decimal("12") / Decimal(freq_months)
        notional = _dec(a.get("notional_eok"), "notional_eok")
        upfront_fee_bps = _dec(a.get("upfront_fee_bps") or 0, "upfront_fee_bps")

        periods, fee = build_schedule(
            notional_eok=notional,
            all_in_rate=all_in,
            origination_date=a["origination_date"],
            maturity_date=a["maturity_date"],
            amort_type="BULLET",
            freq_months=freq_months,
            upfront_fee_bps=upfront_fee_bps,
            noi_annual_eok=noi,
        )

        cashflows_dec = [-(notional - fee)] + [p["_raw_total_payment_eok"] for p in periods]
        cashflows = [float(cf) for cf in cashflows_dec]

        irr = _irr_annual(cashflows, float(freq_per_year))
        warnings.extend(irr["warnings"])

        total_interest = sum((p["_raw_interest_eok"] for p in periods), Decimal("0"))
        total_principal = sum((p["_raw_principal_eok"] for p in periods), Decimal("0"))
        total_payment = total_interest + total_principal
        moic = total_payment / notional if notional > 0 else None

        hurdle_period = Decimal(str((1.08) ** (1 / float(freq_per_year)) - 1))
        npv = cashflows_dec[0] + sum(
            cf / ((Decimal("1") + hurdle_period) ** Decimal(i + 1))
            for i, cf in enumerate(cashflows_dec[1:])
        )

        dscr_values = [
            Decimal(str(p["dscr_period"])) for p in periods if p["dscr_period"] is not None
        ]
        dscr_avg = sum(dscr_values, Decimal("0")) / Decimal(len(dscr_values)) if dscr_values else None
        dscr_min = min(dscr_values) if dscr_values else None
        dscr_min_period = (
            next((p["period_seq"] for p in periods
                  if p["dscr_period"] is not None
                  and Decimal(str(p["dscr_period"])) == dscr_min), None)
            if dscr_min is not None else None
        )

        rd = relativedelta(a["maturity_date"], a["origination_date"])
        loan_term_months = rd.years * 12 + rd.months
        if rd.days > 0:
            warnings.append("LOAN_TERM_HAS_STUB_DAYS_NOT_INCLUDED_IN_MONTH_COUNT")

        spread_bps_used = float(a["spread_bps"]) if a.get("spread_bps") is not None else None

        cur.execute(
            """
            INSERT INTO irr_results (
                deal_master_id, scenario_label, instrument_type,
                lender_irr, lender_moic, npv_eok,
                dscr_avg, dscr_min, dscr_min_period,
                total_interest_eok, total_principal_eok,
                total_fees_eok, total_cashflow_eok,
                loan_term_months, effective_date, maturity_date,
                base_rate_used, spread_bps_used, all_in_rate,
                assumption_version
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (deal_master_id, scenario_label, assumption_version)
            DO UPDATE SET
                instrument_type=EXCLUDED.instrument_type,
                lender_irr=EXCLUDED.lender_irr, lender_moic=EXCLUDED.lender_moic,
                npv_eok=EXCLUDED.npv_eok, dscr_avg=EXCLUDED.dscr_avg,
                dscr_min=EXCLUDED.dscr_min, dscr_min_period=EXCLUDED.dscr_min_period,
                total_interest_eok=EXCLUDED.total_interest_eok,
                total_principal_eok=EXCLUDED.total_principal_eok,
                total_fees_eok=EXCLUDED.total_fees_eok,
                total_cashflow_eok=EXCLUDED.total_cashflow_eok,
                loan_term_months=EXCLUDED.loan_term_months,
                effective_date=EXCLUDED.effective_date,
                maturity_date=EXCLUDED.maturity_date,
                base_rate_used=EXCLUDED.base_rate_used,
                spread_bps_used=EXCLUDED.spread_bps_used,
                all_in_rate=EXCLUDED.all_in_rate,
                computed_at=NOW()
            RETURNING id
            """,
            (
                deal_id, scenario_label, a.get("instrument_type"),
                round(irr["annual_irr"], 6) if irr["annual_irr"] is not None else None,
                _f(_q(moic)) if moic is not None else None,
                _f(_q(npv)),
                _f(_q(dscr_avg)) if dscr_avg is not None else None,
                _f(_q(dscr_min)) if dscr_min is not None else None,
                dscr_min_period,
                _f(_q(total_interest)), _f(_q(total_principal)),
                _f(_q(fee)),
                _f(_q(total_interest + total_principal + fee)),
                loan_term_months, a["origination_date"], a["maturity_date"],
                _f(_q(base_rate, "0.000001")),
                spread_bps_used,
                _f(_q(all_in, "0.000001")),
                int(a.get("assumption_version") or 1),
            ),
        )
        irr_id = _row_get(cur.fetchone(), "id")

        cur.execute("DELETE FROM irr_cashflow_schedule WHERE irr_result_id=%s", (irr_id,))
        for p in periods:
            cur.execute(
                """
                INSERT INTO irr_cashflow_schedule (
                    irr_result_id, period_seq, period_date,
                    beginning_balance_eok, scheduled_interest_eok,
                    scheduled_principal_eok, total_payment_eok,
                    ending_balance_eok, dscr_period, is_default_period
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (irr_id, p["period_seq"], p["period_date"],
                 p["beginning_balance_eok"], p["scheduled_interest_eok"],
                 p["scheduled_principal_eok"], p["total_payment_eok"],
                 p["ending_balance_eok"], p["dscr_period"], p["is_default_period"]),
            )

        conn.commit()

        return {
            "irr_result_id": irr_id,
            "scenario_label": scenario_label,
            "engine_version": "1.1_scheduled_lender_cashflow",
            "engine_scope": "CONTRACTUAL_SCHEDULE_ONLY_NOT_DEFAULT_WATERFALL",
            "lender_irr": round(irr["annual_irr"], 6) if irr["annual_irr"] is not None else None,
            "lender_irr_pct": round(irr["annual_irr"] * 100, 3) if irr["annual_irr"] is not None else None,
            "irr_method": irr["method"],
            "lender_moic": _f(_q(moic)) if moic is not None else None,
            "npv_eok": _f(_q(npv)),
            "all_in_rate_pct": round(float(all_in) * 100, 3),
            "base_rate_pct": round(float(base_rate) * 100, 3),
            "spread_bps": spread_bps_used,
            "dscr_avg": _f(_q(dscr_avg)) if dscr_avg is not None else None,
            "dscr_min": _f(_q(dscr_min)) if dscr_min is not None else None,
            "dscr_min_period": dscr_min_period,
            "loan_term_months": loan_term_months,
            "periods_count": len(periods),
            "total_interest_eok": _f(_q(total_interest, "0.01")),
            "warnings": warnings,
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

"""
hephaestus/engines/irr_engine.py

COSMOS / HEPHAESTUS institutional IRR engine.

v5.2.0

Position:
- IRR engine is a cashflow evaluator.
- It does not calculate default, recovery, or waterfall.
- Production use should pass external investor-perspective cashflows from
  failure_engine / recovery_strategy_engine_kr / waterfall_engine.
- Generated mode is retained only as a lightweight contractual convenience path.
- No __main__ smoke test.
- No fallback schemas/classes.
- No numpy_financial.
"""

from __future__ import annotations

from decimal import Decimal, DivisionByZero, InvalidOperation, getcontext
import math
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from scipy import optimize

from schemas.base import EngineInput, EngineOutput, ConfidenceLevel, EngineGate
from engines.base import BaseEngine
from core.exceptions import NumericalInstabilityError


getcontext().prec = 50


# =============================================================================
# Constants
# =============================================================================

D_ZERO = Decimal("0")
D_ONE = Decimal("1")
D_TWELVE = Decimal("12")
D_EPS = Decimal("1e-24")

D_IRR_FLOOR_MONTHLY = Decimal("-0.999999")
D_IRR_POLICY_FLOOR_ANNUAL = Decimal("-0.9999")

NEGATIVE_BALANCE_TOLERANCE = Decimal("0.01")


Gate = Literal["PASS", "REVIEW", "RE_UNDERWRITE", "HOLD"]
Severity = Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

CashflowMode = Literal["external", "generated"]
ScenarioName = Literal["downside", "base", "upside"]
IRRMethod = Literal["IRR", "MIRR", "POLICY_FLOOR", "CAPPED", "FAILED"]

DealType = Literal[
    "direct_lending",
    "debt_purchase",
    "structured",
    "distressed",
    "equity_linked",
]

LienPosition = Literal["senior", "mezz", "sub", "equity"]
CouponType = Literal["fixed", "floating"]
RepaymentType = Literal["bullet", "amortizing", "custom"]

FeeType = Literal["origination", "monitoring", "exit", "prepayment", "other"]
FeeBase = Literal[
    "funded_amount",
    "commitment_amount",
    "beginning_balance",
    "ending_balance",
    "fixed",
]

PrepaymentPenaltyMode = Literal["none", "soft_call", "make_whole"]
MakeWholeBasis = Literal[
    "cash_pay_basis_principal",
    "accreted_principal",
    "disabled_after_pik_toggle",
]


_GATE_RANK: dict[str, int] = {
    "PASS": 0,
    "REVIEW": 1,
    "RE_UNDERWRITE": 2,
    "HOLD": 3,
}

_SEVERITY_RANK: dict[str, int] = {
    "INFO": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


# Maps engine-internal Gate -> hephaestus EngineGate (schemas.base).
# REVIEW has no exact EngineGate equivalent; MONITOR is the closest semantic.
_GATE_TO_ENGINE_GATE: dict[str, EngineGate] = {
    "PASS": EngineGate.PASS,
    "REVIEW": EngineGate.MONITOR,
    "RE_UNDERWRITE": EngineGate.RE_UNDERWRITE,
    "HOLD": EngineGate.HOLD,
}


# =============================================================================
# Rule Registry
# =============================================================================

class RuleDefinition(BaseModel):
    rule_id: str
    code: str
    severity: Severity
    default_calc_gate: Gate
    dimension: Literal[
        "NUMERICAL",
        "DATA_INTEGRITY",
        "ENGINE_SCOPE",
        "CONTRACT_TERM",
        "SCENARIO_INTEGRITY",
    ]
    message: str


RULES: dict[str, RuleDefinition] = {
    "G-01": RuleDefinition(
        rule_id="G-01",
        code="COUPON_RATE_EXTREME",
        severity="CRITICAL",
        default_calc_gate="HOLD",
        dimension="CONTRACT_TERM",
        message="coupon_rate exceeds 50%; pricing is outside engine safe range.",
    ),
    "G-03": RuleDefinition(
        rule_id="G-03",
        code="PIK_CASH_PAY_EXCEEDS_COUPON",
        severity="CRITICAL",
        default_calc_gate="HOLD",
        dimension="DATA_INTEGRITY",
        message="pik_rate + cash_pay_rate exceeds effective coupon rate.",
    ),
    "G-04": RuleDefinition(
        rule_id="G-04",
        code="FUNDED_EXCEEDS_COMMITMENT",
        severity="CRITICAL",
        default_calc_gate="HOLD",
        dimension="DATA_INTEGRITY",
        message="funded_amount exceeds commitment_amount.",
    ),
    "G-05": RuleDefinition(
        rule_id="G-05",
        code="TENOR_OUT_OF_RANGE",
        severity="CRITICAL",
        default_calc_gate="HOLD",
        dimension="DATA_INTEGRITY",
        message="tenor_months must be between 1 and 360.",
    ),
    "G-09": RuleDefinition(
        rule_id="G-09",
        code="UNVERIFIED_INPUT",
        severity="MEDIUM",
        default_calc_gate="REVIEW",
        dimension="DATA_INTEGRITY",
        message="one or more required input fields are unverified.",
    ),
    "G-10": RuleDefinition(
        rule_id="G-10",
        code="DOWNSIDE_NEGATIVE",
        severity="HIGH",
        default_calc_gate="RE_UNDERWRITE",
        dimension="CONTRACT_TERM",
        message="downside IRR is negative; economics require re-underwriting.",
    ),
    "G-11": RuleDefinition(
        rule_id="G-11",
        code="DOWNSIDE_ABOVE_BASE",
        severity="HIGH",
        default_calc_gate="REVIEW",
        dimension="NUMERICAL",
        message="downside IRR exceeds base IRR; scenario ordering may be invalid.",
    ),
    "G-12": RuleDefinition(
        rule_id="G-12",
        code="NEGATIVE_ENDING_BALANCE",
        severity="CRITICAL",
        default_calc_gate="HOLD",
        dimension="DATA_INTEGRITY",
        message="cashflow produced negative ending balance.",
    ),
    "DATA-P0-UNKNOWN": RuleDefinition(
        rule_id="DATA-P0-UNKNOWN",
        code="P0_UNKNOWN_INPUT",
        severity="CRITICAL",
        default_calc_gate="HOLD",
        dimension="DATA_INTEGRITY",
        message="P0 input is unknown; calc_gate is forced to HOLD.",
    ),
    "TERM-PREPAYMENT-CONFLICT": RuleDefinition(
        rule_id="TERM-PREPAYMENT-CONFLICT",
        code="SOFT_CALL_AND_MAKE_WHOLE_CONFLICT",
        severity="CRITICAL",
        default_calc_gate="HOLD",
        dimension="CONTRACT_TERM",
        message="soft call and make-whole cannot be applied simultaneously.",
    ),
    "TERM-OID-DISCOUNT-PAR": RuleDefinition(
        rule_id="TERM-OID-DISCOUNT-PAR",
        code="OID_TREATED_AS_DISCOUNT_TO_PAR",
        severity="INFO",
        default_calc_gate="PASS",
        dimension="CONTRACT_TERM",
        message="OID is treated as investor purchase discount to par: initial outflow is reduced, repayment remains par/accreted balance.",
    ),
    "SCOPE-GENERATED-MODE": RuleDefinition(
        rule_id="SCOPE-GENERATED-MODE",
        code="GENERATED_MODE_LIMITATION",
        severity="MEDIUM",
        default_calc_gate="REVIEW",
        dimension="ENGINE_SCOPE",
        message="generated mode is a lightweight contractual path; production should use external cashflows.",
    ),
    "SCOPE-RECOVERY-REMOVED": RuleDefinition(
        rule_id="SCOPE-RECOVERY-REMOVED",
        code="RECOVERY_WATERFALL_NOT_ALLOWED",
        severity="CRITICAL",
        default_calc_gate="HOLD",
        dimension="ENGINE_SCOPE",
        message="default/recovery/waterfall assumptions are not accepted by IRR engine; provide external scenario cashflows.",
    ),
    "EXT-NO-PAID-IN": RuleDefinition(
        rule_id="EXT-NO-PAID-IN",
        code="EXTERNAL_SCENARIO_NO_PAID_IN",
        severity="CRITICAL",
        default_calc_gate="HOLD",
        dimension="SCENARIO_INTEGRITY",
        message="external scenario has no investor paid-in cashflow.",
    ),
    "EXT-FIRST-CF-INFLOW": RuleDefinition(
        rule_id="EXT-FIRST-CF-INFLOW",
        code="EXTERNAL_FIRST_CASHFLOW_IS_INFLOW",
        severity="CRITICAL",
        default_calc_gate="HOLD",
        dimension="SCENARIO_INTEGRITY",
        message="external scenario begins with an investor inflow; investor-perspective cashflow may be reversed.",
    ),
    "EXT-MISSING-MONTH0": RuleDefinition(
        rule_id="EXT-MISSING-MONTH0",
        code="EXTERNAL_SCENARIO_MISSING_MONTH0",
        severity="MEDIUM",
        default_calc_gate="REVIEW",
        dimension="SCENARIO_INTEGRITY",
        message="external scenario has no month 0 cashflow; timing convention must be reviewed.",
    ),
    "EXT-IDENTICAL-SCENARIOS": RuleDefinition(
        rule_id="EXT-IDENTICAL-SCENARIOS",
        code="EXTERNAL_SCENARIOS_IDENTICAL",
        severity="MEDIUM",
        default_calc_gate="REVIEW",
        dimension="SCENARIO_INTEGRITY",
        message="two or more external scenarios have identical cashflow vectors.",
    ),
    "PIK-SCHEDULE-INFERRED": RuleDefinition(
        rule_id="PIK-SCHEDULE-INFERRED",
        code="PIK_SCHEDULE_INFERRED_FROM_BALANCE",
        severity="LOW",
        default_calc_gate="PASS",
        dimension="SCENARIO_INTEGRITY",
        message="PIK schedule was inferred from balance movement because explicit pik_schedule/pik_balance was not provided.",
    ),
    "PIK-SCHEDULE-UNSPECIFIED": RuleDefinition(
        rule_id="PIK-SCHEDULE-UNSPECIFIED",
        code="PIK_SCHEDULE_MAY_BE_UNDER_SPECIFIED",
        severity="MEDIUM",
        default_calc_gate="REVIEW",
        dimension="SCENARIO_INTEGRITY",
        message="cashflow balances suggest non-cash accretion, but PIK schedule was not explicitly provided.",
    ),
    "NUM-MULTIPLE-ROOTS": RuleDefinition(
        rule_id="NUM-MULTIPLE-ROOTS",
        code="MULTIPLE_IRR_ROOTS",
        severity="HIGH",
        default_calc_gate="REVIEW",
        dimension="NUMERICAL",
        message="cashflows have multiple sign changes; conventional IRR is ambiguous and MIRR was used.",
    ),
    "NUM-TOTAL-LOSS": RuleDefinition(
        rule_id="NUM-TOTAL-LOSS",
        code="NO_POSITIVE_FUTURE_DISTRIBUTION",
        severity="CRITICAL",
        default_calc_gate="HOLD",
        dimension="NUMERICAL",
        message="no positive future distribution exists; IRR floored by policy.",
    ),
    "NUM-BRENTQ-FALLBACK": RuleDefinition(
        rule_id="NUM-BRENTQ-FALLBACK",
        code="BRENTQ_FALLBACK_USED",
        severity="MEDIUM",
        default_calc_gate="REVIEW",
        dimension="NUMERICAL",
        message="scipy brentq failed or was unsuitable; fallback solver was used.",
    ),
    "NUM-DECIMAL-FALLBACK": RuleDefinition(
        rule_id="NUM-DECIMAL-FALLBACK",
        code="DECIMAL_BISECTION_FALLBACK_USED",
        severity="LOW",
        default_calc_gate="PASS",
        dimension="NUMERICAL",
        message="Decimal bisection fallback solved the IRR.",
    ),
    "NUM-NEWTON-FALLBACK": RuleDefinition(
        rule_id="NUM-NEWTON-FALLBACK",
        code="NEWTON_FALLBACK_USED",
        severity="MEDIUM",
        default_calc_gate="REVIEW",
        dimension="NUMERICAL",
        message="scipy newton fallback solved the IRR.",
    ),
    "NUM-CAPPED": RuleDefinition(
        rule_id="NUM-CAPPED",
        code="IRR_CAP_REACHED",
        severity="HIGH",
        default_calc_gate="REVIEW",
        dimension="NUMERICAL",
        message="IRR exceeded policy cap and was capped.",
    ),
    "NUM-CONVERGENCE-FAILURE": RuleDefinition(
        rule_id="NUM-CONVERGENCE-FAILURE",
        code="NUMERICAL_INSTABILITY",
        severity="CRITICAL",
        default_calc_gate="HOLD",
        dimension="NUMERICAL",
        message="IRR solver failed to converge or produced invalid output.",
    ),
}


# =============================================================================
# Pydantic Models
# =============================================================================

class WarningFlag(BaseModel):
    rule_id: str
    code: str
    severity: Severity
    message: str
    dimension: Literal[
        "NUMERICAL",
        "DATA_INTEGRITY",
        "ENGINE_SCOPE",
        "CONTRACT_TERM",
        "SCENARIO_INTEGRITY",
    ]
    scenario: Optional[ScenarioName] = None
    field: Optional[str] = None
    calc_gate: Gate


class CashflowPeriod(BaseModel):
    """
    Investor-perspective cashflow.

    net_cashflow < 0 : paid-in / funding outflow
    net_cashflow > 0 : distribution / repayment / fee inflow
    """

    month: int = Field(ge=0)
    beginning_balance: float = 0.0
    cash_interest: float = 0.0
    pik_interest: float = 0.0
    principal_repayment: float = 0.0
    fees: float = 0.0
    net_cashflow: float
    ending_balance: float = 0.0
    pik_balance: Optional[float] = None
    event: Optional[str] = None
    source_engine: Optional[str] = None
    source_event_id: Optional[str] = None

    @field_validator(
        "beginning_balance",
        "cash_interest",
        "pik_interest",
        "principal_repayment",
        "fees",
        "net_cashflow",
        "ending_balance",
        "pik_balance",
        mode="before",
    )
    @classmethod
    def _finite_float(cls, value: Any) -> Optional[float]:
        if value is None:
            return None
        f = float(value)
        if not math.isfinite(f):
            raise ValueError("cashflow field must be finite")
        return f


class ScenarioCashflows(BaseModel):
    scenario: ScenarioName
    periods: list[CashflowPeriod]

    pik_schedule: Optional[list[float]] = None

    source_engine: Optional[str] = None
    source_version: Optional[str] = None
    scenario_id: Optional[str] = None

    @model_validator(mode="after")
    def _validate_periods(self) -> "ScenarioCashflows":
        if not self.periods:
            raise ValueError("scenario cashflows cannot be empty")
        months = [p.month for p in self.periods]
        if any(m < 0 for m in months):
            raise ValueError("cashflow month cannot be negative")
        if self.pik_schedule is not None:
            for x in self.pik_schedule:
                if not math.isfinite(float(x)):
                    raise ValueError("pik_schedule values must be finite")
                if float(x) < -1e-9:
                    raise ValueError("pik_schedule cannot contain negative values")
        return self


class ScenarioCashflowSet(BaseModel):
    downside: ScenarioCashflows
    base: ScenarioCashflows
    upside: ScenarioCashflows

    @model_validator(mode="after")
    def _validate_names(self) -> "ScenarioCashflowSet":
        if self.downside.scenario != "downside":
            raise ValueError("downside.scenario must be 'downside'")
        if self.base.scenario != "base":
            raise ValueError("base.scenario must be 'base'")
        if self.upside.scenario != "upside":
            raise ValueError("upside.scenario must be 'upside'")
        return self


class RateResetPoint(BaseModel):
    month: int = Field(ge=1)
    base_rate: float

    @field_validator("base_rate")
    @classmethod
    def _validate_base_rate(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("base_rate must be finite")
        if value < -0.10 or value > 1.00:
            raise ValueError("base_rate out of safe range")
        return value


class FeeEvent(BaseModel):
    month: int = Field(ge=0)
    fee_type: FeeType = "other"
    base: FeeBase = "fixed"
    rate: float = 0.0
    amount: float = 0.0
    description: Optional[str] = None

    @model_validator(mode="after")
    def _validate_fee(self) -> "FeeEvent":
        if self.rate < 0 or self.amount < 0:
            raise ValueError("fee rate/amount cannot be negative")
        if self.base == "fixed" and self.amount <= 0:
            raise ValueError("fixed fee event requires amount > 0")
        return self


class IRRScenarioMeta(BaseModel):
    scenario: ScenarioName
    annual_irr: float
    conventional_irr: Optional[float] = None
    mirr: Optional[float] = None
    monthly_rate: Optional[float] = None
    method: IRRMethod
    problem_flag: Optional[str] = None
    capped: bool = False
    sign_changes: int = 0
    solver: Optional[str] = None
    iterations: Optional[int] = None


class IRRInput(EngineInput):
    model_config = ConfigDict(extra="forbid")

    deal_id: str
    deal_type: DealType
    lien_position: LienPosition = "senior"

    cashflow_mode: CashflowMode = "external"
    external_scenarios: Optional[ScenarioCashflowSet] = None

    commitment_amount: float = 0.0
    funded_amount: float = 0.0
    oid_discount_rate: float = 0.0

    coupon_rate: float = 0.0
    coupon_type: CouponType = "fixed"
    base_rate: float = 0.0
    spread: float = 0.0
    base_rate_schedule: Optional[list[RateResetPoint]] = None
    rate_reset_frequency_months: int = 3

    pik_rate: float = 0.0
    cash_pay_rate: float = 0.0
    pik_toggle: bool = False
    pik_toggle_schedule: Optional[list[bool]] = None

    tenor_months: int = 1
    repayment_type: RepaymentType = "bullet"
    amortization_schedule: Optional[list[float]] = None

    origination_fee_rate: float = 0.0
    monitoring_fee_rate: float = 0.0
    fixed_monitoring_fee_per_month: float = 0.0
    minimum_monitoring_fee_per_month: float = 0.0
    exit_fee_rate: float = 0.0
    fee_events: list[FeeEvent] = Field(default_factory=list)

    prepayment_month: Optional[int] = None
    prepayment_penalty_schedule: Optional[list[tuple[int, float]]] = None
    prepayment_penalty_mode: PrepaymentPenaltyMode = "none"
    make_whole_enabled: bool = False
    make_whole_until_month: Optional[int] = None
    make_whole_discount_rate: float = 0.0
    make_whole_basis: MakeWholeBasis = "cash_pay_basis_principal"

    irr_annual_cap: float = 5.0
    prefer_decimal_solver: bool = True
    mirr_finance_rate: float = 0.0
    mirr_reinvestment_rate: float = 0.0

    benchmark_rate: Optional[float] = None
    benchmark_label: Optional[str] = None

    ltv_verified: bool = False
    financials_verified: bool = False
    collateral_verified: bool = False
    p0_unknown_fields: list[str] = Field(default_factory=list)

    upstream_waterfall_summary: Optional[dict[str, Any]] = None
    upstream_scenario_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_input(self) -> "IRRInput":
        if self.cashflow_mode == "external":
            if self.external_scenarios is None:
                raise ValueError("external_scenarios is required when cashflow_mode='external'")
            self._validate_common_policy_fields()
            return self

        self._validate_common_policy_fields()

        if self.commitment_amount <= 0:
            raise ValueError("commitment_amount must be positive in generated mode")
        if self.funded_amount <= 0:
            raise ValueError("funded_amount must be positive in generated mode")
        if self.funded_amount > self.commitment_amount:
            raise ValueError(RULES["G-04"].message)
        if self.tenor_months < 1 or self.tenor_months > 360:
            raise ValueError(RULES["G-05"].message)
        if self.rate_reset_frequency_months < 1 or self.rate_reset_frequency_months > 120:
            raise ValueError("rate_reset_frequency_months must be between 1 and 120")
        if self.oid_discount_rate < 0 or self.oid_discount_rate > 1:
            raise ValueError("oid_discount_rate must be between 0 and 1")
        if self.origination_fee_rate < 0:
            raise ValueError("origination_fee_rate cannot be negative")
        if self.monitoring_fee_rate < 0:
            raise ValueError("monitoring_fee_rate cannot be negative")
        if self.exit_fee_rate < 0:
            raise ValueError("exit_fee_rate cannot be negative")
        if self.coupon_rate < 0:
            raise ValueError("coupon_rate cannot be negative")
        if self.coupon_rate > 0.50:
            raise ValueError(RULES["G-01"].message)

        effective_coupon = self._effective_coupon_for_validation()
        if self.pik_rate + self.cash_pay_rate > effective_coupon + 0.001:
            raise ValueError(RULES["G-03"].message)

        if self.pik_toggle:
            if self.pik_toggle_schedule is None:
                raise ValueError("pik_toggle=True requires pik_toggle_schedule")
            if len(self.pik_toggle_schedule) < self.tenor_months:
                raise ValueError("pik_toggle_schedule length must be at least tenor_months")

        if self.repayment_type == "custom":
            if not self.amortization_schedule:
                raise ValueError("custom repayment_type requires amortization_schedule")
            if len(self.amortization_schedule) < self.tenor_months:
                raise ValueError("amortization_schedule length must be at least tenor_months")
            if any(x < 0 for x in self.amortization_schedule):
                raise ValueError("amortization_schedule cannot contain negative values")

        if self.prepayment_month is not None:
            if self.prepayment_month < 1 or self.prepayment_month > self.tenor_months:
                raise ValueError("prepayment_month must be within tenor_months")

        has_soft_call = bool(self.prepayment_penalty_schedule)
        has_make_whole = bool(self.make_whole_enabled)

        if has_soft_call and has_make_whole:
            raise ValueError(RULES["TERM-PREPAYMENT-CONFLICT"].message)

        if self.prepayment_penalty_mode == "soft_call" and not has_soft_call:
            raise ValueError("prepayment_penalty_mode='soft_call' requires prepayment_penalty_schedule")
        if self.prepayment_penalty_mode == "make_whole" and not has_make_whole:
            raise ValueError("prepayment_penalty_mode='make_whole' requires make_whole_enabled=True")
        if self.prepayment_penalty_mode == "none" and (has_soft_call or has_make_whole):
            raise ValueError("prepayment_penalty_mode must explicitly select soft_call or make_whole")

        if self.make_whole_enabled:
            if self.make_whole_until_month is None:
                raise ValueError("make_whole_until_month is required when make_whole_enabled=True")
            if self.make_whole_until_month < 1 or self.make_whole_until_month > self.tenor_months:
                raise ValueError("make_whole_until_month must be within tenor_months")
            if self.make_whole_discount_rate < -0.10 or self.make_whole_discount_rate > 1.00:
                raise ValueError("make_whole_discount_rate out of safe range")

        return self

    def _validate_common_policy_fields(self) -> None:
        if self.irr_annual_cap <= 0:
            raise ValueError("irr_annual_cap must be positive")
        if self.irr_annual_cap > 20:
            raise ValueError("irr_annual_cap too high for policy-safe IRR solver")
        if self.benchmark_rate is not None:
            if not math.isfinite(float(self.benchmark_rate)):
                raise ValueError("benchmark_rate must be finite")
            if self.benchmark_rate < -0.10 or self.benchmark_rate > 1.00:
                raise ValueError("benchmark_rate out of safe range")

    def _effective_coupon_for_validation(self) -> float:
        if self.coupon_type == "floating":
            return self.base_rate + self.spread
        return self.coupon_rate


class IRROutput(EngineOutput):
    # Downside FIRST — house rule.
    irr_downside: float
    irr_base: float
    irr_upside: float

    moic_downside: float
    moic_base: float
    moic_upside: float

    dpi_downside: float
    dpi_base: float
    dpi_upside: float

    residual_nav_downside: float
    residual_nav_base: float
    residual_nav_upside: float

    cashflow_downside: list[CashflowPeriod]
    cashflow_base: list[CashflowPeriod]
    cashflow_upside: list[CashflowPeriod]

    pik_accrual_schedule_downside: list[float]
    pik_accrual_schedule_base: list[float]
    pik_accrual_schedule_upside: list[float]

    # Legacy alias only. Base scenario PIK schedule.
    pik_accrual_schedule: list[float]

    irr_method_downside: IRRMethod
    irr_method_base: IRRMethod
    irr_method_upside: IRRMethod

    conventional_irr_downside: Optional[float]
    conventional_irr_base: Optional[float]
    conventional_irr_upside: Optional[float]

    mirr_downside: Optional[float]
    mirr_base: Optional[float]
    mirr_upside: Optional[float]

    irr_problem_downside: Optional[str]
    irr_problem_base: Optional[str]
    irr_problem_upside: Optional[str]

    irr_capped_downside: bool
    irr_capped_base: bool
    irr_capped_upside: bool

    irr_meta: list[IRRScenarioMeta]

    spread_to_benchmark: Optional[float]
    benchmark_label: Optional[str]
    yield_to_worst: float
    yield_to_maturity: float

    calc_gate: Gate
    technical_confidence: float

    # Engine-native rich warnings. The inherited `warnings` field (schemas.base
    # WarningFlag) stays base-typed; IRR-specific warnings live here.
    irr_warnings: list[WarningFlag] = Field(default_factory=list)

    upstream_waterfall_summary: Optional[dict[str, Any]] = None
    upstream_scenario_metadata: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Helpers
# =============================================================================

class _IRRComputationProblem(Exception):
    pass


def _D(value: Any) -> Decimal:
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    if d.is_nan() or d in (Decimal("Infinity"), Decimal("-Infinity")):
        raise NumericalInstabilityError(f"non-finite Decimal value: {value}")
    return d


def _annual_to_monthly(rate: Decimal) -> Decimal:
    if rate <= Decimal("-1"):
        raise InvalidOperation("annual rate must be greater than -100%")
    result = Decimal(str(math.pow(float(D_ONE + rate), 1.0 / 12.0) - 1.0))
    if result.is_nan() or result in (Decimal("Infinity"), Decimal("-Infinity")):
        raise NumericalInstabilityError("annual_to_monthly produced non-finite value")
    return result


def _monthly_to_annual(rate: Decimal) -> Decimal:
    if rate <= Decimal("-1"):
        return D_IRR_POLICY_FLOOR_ANNUAL
    result = (D_ONE + rate) ** 12 - D_ONE
    if result.is_nan() or result in (Decimal("Infinity"), Decimal("-Infinity")):
        raise NumericalInstabilityError("monthly_to_annual produced non-finite value")
    return result


def _rule_warning(
    rule_id: str,
    *,
    scenario: Optional[ScenarioName] = None,
    field: Optional[str] = None,
    message_suffix: Optional[str] = None,
) -> WarningFlag:
    rule = RULES[rule_id]
    message = rule.message
    if message_suffix:
        message = f"{message} {message_suffix}"
    return WarningFlag(
        rule_id=rule.rule_id,
        code=rule.code,
        severity=rule.severity,
        message=message,
        dimension=rule.dimension,
        scenario=scenario,
        field=field,
        calc_gate=rule.default_calc_gate,
    )


def _dedupe_warnings(warnings: list[WarningFlag]) -> list[WarningFlag]:
    seen: set[tuple[str, Optional[str], Optional[str], str]] = set()
    out: list[WarningFlag] = []
    for w in warnings:
        key = (w.rule_id, w.scenario, w.field, w.message)
        if key in seen:
            continue
        seen.add(key)
        out.append(w)
    return out


def _max_gate(gates: list[Gate]) -> Gate:
    if not gates:
        return "PASS"
    return max(gates, key=lambda g: _GATE_RANK[g])


def _calc_gate_from_warnings(warnings: list[WarningFlag]) -> Gate:
    return _max_gate([w.calc_gate for w in warnings])


def _technical_confidence(warnings: list[WarningFlag]) -> float:
    confidence = Decimal("1.00")
    for w in warnings:
        if w.dimension != "NUMERICAL":
            continue
        if w.severity == "LOW":
            confidence -= Decimal("0.03")
        elif w.severity == "MEDIUM":
            confidence -= Decimal("0.07")
        elif w.severity == "HIGH":
            confidence -= Decimal("0.12")
        elif w.severity == "CRITICAL":
            confidence -= Decimal("0.25")
    return float(min(max(confidence, D_ZERO), D_ONE))


def _confidence_band(score: float) -> ConfidenceLevel:
    """Map technical_confidence (0..1 float) -> hephaestus ConfidenceLevel enum."""
    if score >= 0.85:
        return ConfidenceLevel.HIGH
    if score >= 0.60:
        return ConfidenceLevel.MEDIUM
    if score >= 0.30:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.UNVERIFIED


def _aggregate_periods(periods: list[CashflowPeriod]) -> list[CashflowPeriod]:
    by_month: dict[int, dict[str, Any]] = {}
    for _, p in sorted(enumerate(periods), key=lambda item: (item[1].month, item[0])):
        row = by_month.setdefault(
            p.month,
            {
                "month": p.month,
                "beginning_balance": p.beginning_balance,
                "cash_interest": 0.0,
                "pik_interest": 0.0,
                "principal_repayment": 0.0,
                "fees": 0.0,
                "net_cashflow": 0.0,
                "ending_balance": p.ending_balance,
                "pik_balance": p.pik_balance,
                "event": None,
                "source_engine": p.source_engine,
                "source_event_id": p.source_event_id,
            },
        )
        row["cash_interest"] += p.cash_interest
        row["pik_interest"] += p.pik_interest
        row["principal_repayment"] += p.principal_repayment
        row["fees"] += p.fees
        row["net_cashflow"] += p.net_cashflow
        row["beginning_balance"] = p.beginning_balance
        row["ending_balance"] = p.ending_balance
        row["pik_balance"] = p.pik_balance
        row["source_engine"] = p.source_engine or row["source_engine"]
        row["source_event_id"] = p.source_event_id or row["source_event_id"]
        if p.event:
            row["event"] = p.event if row["event"] is None else f"{row['event']}+{p.event}"
    return [CashflowPeriod(**by_month[m]) for m in sorted(by_month)]


def _cashflow_vector(periods: list[CashflowPeriod]) -> list[tuple[int, Decimal]]:
    aggregated = _aggregate_periods(periods)
    return [
        (p.month, _D(p.net_cashflow))
        for p in aggregated
        if abs(p.net_cashflow) > 1e-9
    ]


def _vector_signature(periods: list[CashflowPeriod]) -> tuple[tuple[int, str], ...]:
    return tuple((m, str(cf.quantize(Decimal("0.0001")))) for m, cf in _cashflow_vector(periods))


def _sign_changes(cashflows: list[tuple[int, Decimal]]) -> int:
    signs: list[int] = []
    for _, cf in cashflows:
        if abs(cf) <= D_EPS:
            continue
        signs.append(1 if cf > 0 else -1)
    return sum(1 for i in range(1, len(signs)) if signs[i] != signs[i - 1])


def _npv_decimal(cashflows: list[tuple[int, Decimal]], monthly_rate: Decimal) -> Decimal:
    if monthly_rate <= Decimal("-1"):
        raise InvalidOperation("monthly_rate must be > -100%")
    base = D_ONE + monthly_rate
    total = D_ZERO
    for month, cf in cashflows:
        if month == 0:
            total += cf
        else:
            total += cf / (base ** month)
    if total.is_nan() or total in (Decimal("Infinity"), Decimal("-Infinity")):
        raise NumericalInstabilityError("NPV produced non-finite value")
    return total


def _safe_solver_float(value: Decimal) -> float:
    if value.is_nan():
        raise ValueError("NPV returned NaN")
    if value == Decimal("Infinity"):
        return 1e308
    if value == Decimal("-Infinity"):
        return -1e308
    f = float(value)
    if math.isnan(f):
        raise ValueError("NPV returned NaN")
    if math.isinf(f):
        return 1e308 if value > 0 else -1e308
    return f


def _decimal_bisection(
    cashflows: list[tuple[int, Decimal]],
    low: Decimal,
    high: Decimal,
    *,
    max_iter: int = 100,
    tolerance: Decimal = Decimal("1e-24"),
) -> tuple[Decimal, int]:
    f_low = _npv_decimal(cashflows, low)
    f_high = _npv_decimal(cashflows, high)
    if f_low == 0:
        return low, 0
    if f_high == 0:
        return high, 0
    if (f_low > 0 and f_high > 0) or (f_low < 0 and f_high < 0):
        raise _IRRComputationProblem("decimal bisection requires valid bracket")
    lo, hi = low, high
    flo = f_low
    for i in range(1, max_iter + 1):
        mid = (lo + hi) / Decimal("2")
        fmid = _npv_decimal(cashflows, mid)
        if abs(fmid) <= tolerance or abs(hi - lo) <= tolerance:
            return mid, i
        if (flo < 0 and fmid > 0) or (flo > 0 and fmid < 0):
            hi = mid
        else:
            lo = mid
            flo = fmid
    return (lo + hi) / Decimal("2"), max_iter


def _coarse_grid(lower: Decimal, upper: Decimal, points: int) -> list[Decimal]:
    if points < 2:
        return [lower, upper]
    step = (upper - lower) / Decimal(points - 1)
    return [lower + step * Decimal(i) for i in range(points)]


def _find_bracket(
    cashflows: list[tuple[int, Decimal]],
    annual_cap: Decimal,
) -> tuple[Optional[tuple[Decimal, Decimal]], Optional[str]]:
    lower = D_IRR_FLOOR_MONTHLY
    upper = _annual_to_monthly(annual_cap)
    grid = _coarse_grid(lower, upper, 400)
    prev_r: Optional[Decimal] = None
    prev_f: Optional[Decimal] = None
    for r in grid:
        try:
            f = _npv_decimal(cashflows, r)
        except (InvalidOperation, DivisionByZero, OverflowError, NumericalInstabilityError):
            continue
        if f == 0:
            return (r, r), None
        if prev_r is not None and prev_f is not None:
            if (prev_f < 0 and f > 0) or (prev_f > 0 and f < 0):
                return (prev_r, r), None
        prev_r = r
        prev_f = f
    try:
        f_at_cap = _npv_decimal(cashflows, upper)
        if f_at_cap > 0:
            return None, "CAP_REACHED"
    except Exception:
        pass
    return None, "NO_BRACKET"


def _mirr_annual(
    cashflows: list[tuple[int, Decimal]],
    *,
    finance_rate_annual: Decimal,
    reinvestment_rate_annual: Decimal,
) -> Decimal:
    if not cashflows:
        return D_IRR_POLICY_FLOOR_ANNUAL
    terminal_month = max(month for month, _ in cashflows)
    if terminal_month <= 0:
        return D_IRR_POLICY_FLOOR_ANNUAL
    finance_m = _annual_to_monthly(finance_rate_annual)
    reinvest_m = _annual_to_monthly(reinvestment_rate_annual)
    pv_neg = D_ZERO
    fv_pos = D_ZERO
    for month, cf in cashflows:
        if cf < 0:
            pv_neg += cf / ((D_ONE + finance_m) ** month)
        elif cf > 0:
            fv_pos += cf * ((D_ONE + reinvest_m) ** (terminal_month - month))
    if pv_neg >= 0 or fv_pos <= 0:
        return D_IRR_POLICY_FLOOR_ANNUAL
    ratio = fv_pos / (-pv_neg)
    if ratio <= 0:
        return D_IRR_POLICY_FLOOR_ANNUAL
    annual = Decimal(str(math.pow(float(ratio), 12.0 / float(terminal_month)) - 1.0))
    if annual.is_nan() or annual in (Decimal("Infinity"), Decimal("-Infinity")):
        return D_IRR_POLICY_FLOOR_ANNUAL
    return annual


def _solve_irr(
    cashflows: list[tuple[int, Decimal]],
    *,
    annual_cap: Decimal,
    warnings: list[WarningFlag],
    scenario: ScenarioName,
    prefer_decimal_solver: bool,
    finance_rate_annual: Decimal,
    reinvestment_rate_annual: Decimal,
) -> tuple[Decimal, IRRScenarioMeta]:
    future_positive = any(month > 0 and cf > 0 for month, cf in cashflows)
    if not future_positive:
        warnings.append(_rule_warning("NUM-TOTAL-LOSS", scenario=scenario))
        return D_IRR_POLICY_FLOOR_ANNUAL, IRRScenarioMeta(
            scenario=scenario,
            annual_irr=float(D_IRR_POLICY_FLOOR_ANNUAL),
            conventional_irr=None,
            mirr=None,
            monthly_rate=float(D_IRR_FLOOR_MONTHLY),
            method="POLICY_FLOOR",
            problem_flag="NO_POSITIVE_FUTURE_DISTRIBUTION",
            capped=False,
            sign_changes=_sign_changes(cashflows),
            solver="policy_floor",
        )

    sign_changes = _sign_changes(cashflows)
    if sign_changes > 1:
        warnings.append(_rule_warning("NUM-MULTIPLE-ROOTS", scenario=scenario))
        mirr = _mirr_annual(
            cashflows,
            finance_rate_annual=finance_rate_annual,
            reinvestment_rate_annual=reinvestment_rate_annual,
        )
        return mirr, IRRScenarioMeta(
            scenario=scenario,
            annual_irr=float(mirr),
            conventional_irr=None,
            mirr=float(mirr),
            monthly_rate=None,
            method="MIRR",
            problem_flag="MULTIPLE_ROOTS",
            capped=False,
            sign_changes=sign_changes,
            solver="mirr",
        )

    bracket, problem = _find_bracket(cashflows, annual_cap)

    if problem == "CAP_REACHED":
        warnings.append(_rule_warning("NUM-CAPPED", scenario=scenario))
        return annual_cap, IRRScenarioMeta(
            scenario=scenario,
            annual_irr=float(annual_cap),
            conventional_irr=None,
            mirr=None,
            monthly_rate=float(_annual_to_monthly(annual_cap)),
            method="CAPPED",
            problem_flag="CAP_REACHED",
            capped=True,
            sign_changes=sign_changes,
            solver="policy_cap",
        )

    if bracket is None:
        warnings.append(_rule_warning("NUM-CONVERGENCE-FAILURE", scenario=scenario))
        return D_IRR_POLICY_FLOOR_ANNUAL, IRRScenarioMeta(
            scenario=scenario,
            annual_irr=float(D_IRR_POLICY_FLOOR_ANNUAL),
            conventional_irr=None,
            mirr=None,
            monthly_rate=float(D_IRR_FLOOR_MONTHLY),
            method="FAILED",
            problem_flag="NO_VALID_BRACKET",
            capped=False,
            sign_changes=sign_changes,
            solver="failed",
        )

    low, high = bracket

    if low == high:
        annual = _monthly_to_annual(low)
        return annual, IRRScenarioMeta(
            scenario=scenario,
            annual_irr=float(annual),
            conventional_irr=float(annual),
            mirr=None,
            monthly_rate=float(low),
            method="IRR",
            problem_flag=None,
            capped=False,
            sign_changes=sign_changes,
            solver="exact_grid_root",
            iterations=0,
        )

    def f_float(r: float) -> float:
        return _safe_solver_float(_npv_decimal(cashflows, Decimal(str(r))))

    try:
        root = optimize.brentq(f_float, float(low), float(high), xtol=1e-14, rtol=1e-14, maxiter=200)
        monthly = Decimal(str(root))
        annual = _monthly_to_annual(monthly)
        return annual, IRRScenarioMeta(
            scenario=scenario,
            annual_irr=float(annual),
            conventional_irr=float(annual),
            mirr=None,
            monthly_rate=float(monthly),
            method="IRR",
            problem_flag=None,
            capped=False,
            sign_changes=sign_changes,
            solver="scipy.brentq",
            iterations=None,
        )
    except Exception:
        warnings.append(_rule_warning("NUM-BRENTQ-FALLBACK", scenario=scenario))

    if prefer_decimal_solver:
        try:
            monthly, iterations = _decimal_bisection(cashflows, low, high)
            annual = _monthly_to_annual(monthly)
            warnings.append(_rule_warning("NUM-DECIMAL-FALLBACK", scenario=scenario))
            return annual, IRRScenarioMeta(
                scenario=scenario,
                annual_irr=float(annual),
                conventional_irr=float(annual),
                mirr=None,
                monthly_rate=float(monthly),
                method="IRR",
                problem_flag="SCIPY_BRENTQ_FAILED_DECIMAL_SOLVED",
                capped=False,
                sign_changes=sign_changes,
                solver="decimal_bisection",
                iterations=iterations,
            )
        except Exception:
            pass

    try:
        guess = float((low + high) / Decimal("2"))
        root = optimize.newton(f_float, x0=guess, maxiter=200, tol=1e-14)
        monthly = Decimal(str(root))
        if monthly <= Decimal("-1"):
            raise _IRRComputationProblem("newton root <= -100% monthly")
        annual = _monthly_to_annual(monthly)
        warnings.append(_rule_warning("NUM-NEWTON-FALLBACK", scenario=scenario))
        return annual, IRRScenarioMeta(
            scenario=scenario,
            annual_irr=float(annual),
            conventional_irr=float(annual),
            mirr=None,
            monthly_rate=float(monthly),
            method="IRR",
            problem_flag="BRENTQ_AND_DECIMAL_FAILED_NEWTON_SOLVED",
            capped=False,
            sign_changes=sign_changes,
            solver="scipy.newton",
            iterations=None,
        )
    except Exception:
        warnings.append(_rule_warning("NUM-CONVERGENCE-FAILURE", scenario=scenario))
        return D_IRR_POLICY_FLOOR_ANNUAL, IRRScenarioMeta(
            scenario=scenario,
            annual_irr=float(D_IRR_POLICY_FLOOR_ANNUAL),
            conventional_irr=None,
            mirr=None,
            monthly_rate=float(D_IRR_FLOOR_MONTHLY),
            method="FAILED",
            problem_flag="ALL_SOLVERS_FAILED",
            capped=False,
            sign_changes=sign_changes,
            solver="failed",
        )


def _paid_in(periods: list[CashflowPeriod]) -> Decimal:
    return sum((-_D(p.net_cashflow) for p in periods if p.net_cashflow < 0), D_ZERO)


def _distributions(periods: list[CashflowPeriod]) -> Decimal:
    return sum((_D(p.net_cashflow) for p in periods if p.net_cashflow > 0), D_ZERO)


def _residual_nav(periods: list[CashflowPeriod]) -> Decimal:
    if not periods:
        return D_ZERO
    last = sorted(periods, key=lambda p: p.month)[-1]
    return max(_D(last.ending_balance), D_ZERO)


def _dpi(periods: list[CashflowPeriod]) -> Decimal:
    pi = _paid_in(periods)
    if pi <= 0:
        return D_ZERO
    return _distributions(periods) / pi


def _moic(periods: list[CashflowPeriod]) -> Decimal:
    pi = _paid_in(periods)
    if pi <= 0:
        return D_ZERO
    return (_distributions(periods) + _residual_nav(periods)) / pi


def _pik_schedule(
    scenario_cf: Optional[ScenarioCashflows],
    periods: list[CashflowPeriod],
    *,
    scenario: ScenarioName,
    warnings: list[WarningFlag],
) -> list[float]:
    if scenario_cf is not None and scenario_cf.pik_schedule is not None:
        return [float(x) for x in scenario_cf.pik_schedule]

    result: list[float] = []
    cumulative = D_ZERO
    inferred_used = False
    unspecified_risk = False

    for p in sorted(periods, key=lambda x: x.month):
        if p.month == 0:
            continue

        if p.pik_balance is not None:
            cumulative = max(_D(p.pik_balance), D_ZERO)
            result.append(float(cumulative))
            continue

        pik_interest = _D(p.pik_interest)
        if pik_interest > 0:
            cumulative += pik_interest
            result.append(float(cumulative))
            continue

        beginning = _D(p.beginning_balance)
        ending = _D(p.ending_balance)
        principal_repayment = _D(p.principal_repayment)
        event_text = (p.event or "").lower()
        is_draw_or_funding = (
            "fund" in event_text or "draw" in event_text or "additional" in event_text
        )
        inferred_pik = ending - beginning + principal_repayment

        if inferred_pik > Decimal("0.01") and not is_draw_or_funding:
            cumulative += inferred_pik
            inferred_used = True
        elif inferred_pik > Decimal("0.01") and is_draw_or_funding:
            unspecified_risk = True

        result.append(float(max(cumulative, D_ZERO)))

    if inferred_used:
        warnings.append(_rule_warning("PIK-SCHEDULE-INFERRED", scenario=scenario))
    if unspecified_risk:
        warnings.append(_rule_warning("PIK-SCHEDULE-UNSPECIFIED", scenario=scenario))

    return result


def _assert_periods_finite(periods: list[CashflowPeriod], scenario: ScenarioName) -> None:
    for p in periods:
        values = {
            "beginning_balance": p.beginning_balance,
            "cash_interest": p.cash_interest,
            "pik_interest": p.pik_interest,
            "principal_repayment": p.principal_repayment,
            "fees": p.fees,
            "net_cashflow": p.net_cashflow,
            "ending_balance": p.ending_balance,
        }
        if p.pik_balance is not None:
            values["pik_balance"] = p.pik_balance
        for key, value in values.items():
            if not math.isfinite(float(value)):
                raise NumericalInstabilityError(
                    f"non-finite cashflow value scenario={scenario} month={p.month} field={key}"
                )


def _assert_scalar_finite(name: str, value: Optional[float]) -> None:
    if value is None:
        return
    if not math.isfinite(float(value)):
        raise NumericalInstabilityError(f"non-finite output scalar: {name}={value}")


def _validate_external_scenario(
    scenario: ScenarioName,
    periods: list[CashflowPeriod],
    warnings: list[WarningFlag],
) -> None:
    if not periods:
        warnings.append(_rule_warning("EXT-NO-PAID-IN", scenario=scenario))
        return

    _assert_periods_finite(periods, scenario)

    months = {p.month for p in periods}
    if 0 not in months:
        warnings.append(_rule_warning("EXT-MISSING-MONTH0", scenario=scenario))

    paid_in = _paid_in(periods)
    if paid_in <= 0:
        warnings.append(_rule_warning("EXT-NO-PAID-IN", scenario=scenario))

    nonzero = [
        p for p in sorted(periods, key=lambda x: x.month)
        if abs(p.net_cashflow) > 1e-9
    ]
    if nonzero and nonzero[0].net_cashflow > 0:
        warnings.append(_rule_warning("EXT-FIRST-CF-INFLOW", scenario=scenario))

    for p in periods:
        if _D(p.ending_balance) < -NEGATIVE_BALANCE_TOLERANCE:
            warnings.append(
                _rule_warning(
                    "G-12",
                    scenario=scenario,
                    field="ending_balance",
                    message_suffix=(
                        f"month={p.month}, ending_balance={p.ending_balance}, "
                        f"tolerance={float(NEGATIVE_BALANCE_TOLERANCE)}"
                    ),
                )
            )


def _validate_scenario_set(
    downside: list[CashflowPeriod],
    base: list[CashflowPeriod],
    upside: list[CashflowPeriod],
    warnings: list[WarningFlag],
) -> None:
    signatures = {
        "downside": _vector_signature(downside),
        "base": _vector_signature(base),
        "upside": _vector_signature(upside),
    }
    if signatures["downside"] == signatures["base"]:
        warnings.append(_rule_warning("EXT-IDENTICAL-SCENARIOS", scenario="downside", message_suffix="downside and base are identical."))
    if signatures["base"] == signatures["upside"]:
        warnings.append(_rule_warning("EXT-IDENTICAL-SCENARIOS", scenario="base", message_suffix="base and upside are identical."))
    if signatures["downside"] == signatures["upside"]:
        warnings.append(_rule_warning("EXT-IDENTICAL-SCENARIOS", scenario="upside", message_suffix="downside and upside are identical."))


# =============================================================================
# Engine
# =============================================================================

class IRREngine(BaseEngine):
    name: str = "irr_engine"
    version: str = "5.2.0"
    input_model: type[EngineInput] = IRRInput

    def _execute(self, inp: EngineInput) -> EngineOutput:
        if not isinstance(inp, IRRInput):
            if hasattr(inp, "model_dump"):
                inp = IRRInput.model_validate(inp.model_dump())
            else:
                inp = IRRInput.model_validate(inp)

        warnings: list[WarningFlag] = []

        self._append_static_warnings(inp, warnings)

        scenario_cf_downside: Optional[ScenarioCashflows] = None
        scenario_cf_base: Optional[ScenarioCashflows] = None
        scenario_cf_upside: Optional[ScenarioCashflows] = None

        if inp.cashflow_mode == "external":
            assert inp.external_scenarios is not None

            scenario_cf_downside = inp.external_scenarios.downside
            scenario_cf_base = inp.external_scenarios.base
            scenario_cf_upside = inp.external_scenarios.upside

            downside = _aggregate_periods(scenario_cf_downside.periods)
            base = _aggregate_periods(scenario_cf_base.periods)
            upside = _aggregate_periods(scenario_cf_upside.periods)

            _validate_external_scenario("downside", downside, warnings)
            _validate_external_scenario("base", base, warnings)
            _validate_external_scenario("upside", upside, warnings)
            _validate_scenario_set(downside, base, upside, warnings)

        else:
            warnings.append(_rule_warning("SCOPE-GENERATED-MODE"))

            if inp.oid_discount_rate > 0:
                warnings.append(_rule_warning("TERM-OID-DISCOUNT-PAR", field="oid_discount_rate"))

            downside = self._build_generated_scenario(inp, "downside", warnings)
            base = self._build_generated_scenario(inp, "base", warnings)
            upside = self._build_generated_scenario(inp, "upside", warnings)

            _validate_external_scenario("downside", downside, warnings)
            _validate_external_scenario("base", base, warnings)
            _validate_external_scenario("upside", upside, warnings)
            _validate_scenario_set(downside, base, upside, warnings)

        irr_downside, meta_downside = _solve_irr(
            _cashflow_vector(downside),
            annual_cap=_D(inp.irr_annual_cap),
            warnings=warnings,
            scenario="downside",
            prefer_decimal_solver=inp.prefer_decimal_solver,
            finance_rate_annual=_D(inp.mirr_finance_rate),
            reinvestment_rate_annual=_D(inp.mirr_reinvestment_rate),
        )
        irr_base, meta_base = _solve_irr(
            _cashflow_vector(base),
            annual_cap=_D(inp.irr_annual_cap),
            warnings=warnings,
            scenario="base",
            prefer_decimal_solver=inp.prefer_decimal_solver,
            finance_rate_annual=_D(inp.mirr_finance_rate),
            reinvestment_rate_annual=_D(inp.mirr_reinvestment_rate),
        )
        irr_upside, meta_upside = _solve_irr(
            _cashflow_vector(upside),
            annual_cap=_D(inp.irr_annual_cap),
            warnings=warnings,
            scenario="upside",
            prefer_decimal_solver=inp.prefer_decimal_solver,
            finance_rate_annual=_D(inp.mirr_finance_rate),
            reinvestment_rate_annual=_D(inp.mirr_reinvestment_rate),
        )

        if irr_downside < 0:
            warnings.append(_rule_warning("G-10", scenario="downside"))
        if irr_downside > irr_base:
            warnings.append(_rule_warning("G-11", scenario="downside"))

        pik_downside = _pik_schedule(scenario_cf_downside, downside, scenario="downside", warnings=warnings)
        pik_base = _pik_schedule(scenario_cf_base, base, scenario="base", warnings=warnings)
        pik_upside = _pik_schedule(scenario_cf_upside, upside, scenario="upside", warnings=warnings)

        # Single canonical dedupe point.
        # All validation, numerical, scenario, and PIK warnings must be appended before this line.
        warnings = _dedupe_warnings(warnings)

        calc_gate = _calc_gate_from_warnings(warnings)
        technical_confidence = _technical_confidence(warnings)
        spread_to_benchmark = self._spread_to_benchmark(inp, irr_base)

        # Bridge engine-native gate/confidence to the hephaestus EngineOutput contract.
        base_gate = _GATE_TO_ENGINE_GATE[calc_gate]
        base_confidence = _confidence_band(technical_confidence)

        output = IRROutput(
            irr_downside=float(irr_downside),
            irr_base=float(irr_base),
            irr_upside=float(irr_upside),
            moic_downside=float(_moic(downside)),
            moic_base=float(_moic(base)),
            moic_upside=float(_moic(upside)),
            dpi_downside=float(_dpi(downside)),
            dpi_base=float(_dpi(base)),
            dpi_upside=float(_dpi(upside)),
            residual_nav_downside=float(_residual_nav(downside)),
            residual_nav_base=float(_residual_nav(base)),
            residual_nav_upside=float(_residual_nav(upside)),
            cashflow_downside=downside,
            cashflow_base=base,
            cashflow_upside=upside,
            pik_accrual_schedule_downside=pik_downside,
            pik_accrual_schedule_base=pik_base,
            pik_accrual_schedule_upside=pik_upside,
            pik_accrual_schedule=pik_base,
            irr_method_downside=meta_downside.method,
            irr_method_base=meta_base.method,
            irr_method_upside=meta_upside.method,
            conventional_irr_downside=meta_downside.conventional_irr,
            conventional_irr_base=meta_base.conventional_irr,
            conventional_irr_upside=meta_upside.conventional_irr,
            mirr_downside=meta_downside.mirr,
            mirr_base=meta_base.mirr,
            mirr_upside=meta_upside.mirr,
            irr_problem_downside=meta_downside.problem_flag,
            irr_problem_base=meta_base.problem_flag,
            irr_problem_upside=meta_upside.problem_flag,
            irr_capped_downside=meta_downside.capped,
            irr_capped_base=meta_base.capped,
            irr_capped_upside=meta_upside.capped,
            irr_meta=[meta_downside, meta_base, meta_upside],
            spread_to_benchmark=spread_to_benchmark,
            benchmark_label=inp.benchmark_label,
            yield_to_worst=float(min(irr_downside, irr_base, irr_upside)),
            yield_to_maturity=float(irr_base),
            calc_gate=calc_gate,
            technical_confidence=technical_confidence,
            irr_warnings=warnings,
            upstream_waterfall_summary=inp.upstream_waterfall_summary,
            upstream_scenario_metadata=inp.upstream_scenario_metadata,
            request_id=inp.request_id,
            engine_name=self.name,
            engine_version=self.version,
            as_of=inp.as_of,
            warnings=[],
            gate=base_gate,
            confidence=base_confidence,
        )

        self._assert_output_finite(output)
        return output

    def _append_static_warnings(self, inp: IRRInput, warnings: list[WarningFlag]) -> None:
        if not inp.ltv_verified:
            warnings.append(_rule_warning("G-09", field="ltv_verified"))
        if not inp.financials_verified:
            warnings.append(_rule_warning("G-09", field="financials_verified"))
        if not inp.collateral_verified:
            warnings.append(_rule_warning("G-09", field="collateral_verified"))
        for field in inp.p0_unknown_fields:
            warnings.append(_rule_warning("DATA-P0-UNKNOWN", field=field))

    def _contract_rate_for_month(self, inp: IRRInput, month: int) -> Decimal:
        if inp.coupon_type == "fixed":
            return _D(inp.coupon_rate)
        return self._base_rate_for_month(inp, month) + _D(inp.spread)

    def _base_rate_for_month(self, inp: IRRInput, month: int) -> Decimal:
        if not inp.base_rate_schedule:
            return _D(inp.base_rate)
        reset_freq = max(int(inp.rate_reset_frequency_months), 1)
        active_reset_month = 1 + ((month - 1) // reset_freq) * reset_freq
        sorted_schedule = sorted(inp.base_rate_schedule, key=lambda x: x.month)
        active = sorted_schedule[0]
        for point in sorted_schedule:
            if point.month <= active_reset_month:
                active = point
            else:
                break
        return _D(active.base_rate)

    def _coupon_split_for_month(self, inp: IRRInput, month: int) -> tuple[Decimal, Decimal]:
        """
        Returns (cash_rate, pik_rate).

        PIK toggle semantics:
          True  = borrower elected PIK  -> cash=0, pik=total coupon
          False = borrower elected cash -> cash=total coupon, pik=0
        """
        total_rate = self._contract_rate_for_month(inp, month)

        if inp.pik_toggle:
            pik_elected = bool(inp.pik_toggle_schedule[month - 1])
            if pik_elected:
                return D_ZERO, total_rate
            return total_rate, D_ZERO

        explicit_split = inp.pik_rate > 0 or inp.cash_pay_rate > 0
        if explicit_split:
            return _D(inp.cash_pay_rate), _D(inp.pik_rate)

        return total_rate, D_ZERO

    def _build_generated_scenario(
        self,
        inp: IRRInput,
        scenario: ScenarioName,
        warnings: list[WarningFlag],
    ) -> list[CashflowPeriod]:
        funded = _D(inp.funded_amount)
        commitment = _D(inp.commitment_amount)
        oid = funded * _D(inp.oid_discount_rate)
        origination_fee = funded * _D(inp.origination_fee_rate)
        net_initial_outflow = -(funded - oid - origination_fee)

        periods: list[CashflowPeriod] = [
            CashflowPeriod(
                month=0,
                beginning_balance=0.0,
                cash_interest=0.0,
                pik_interest=0.0,
                principal_repayment=0.0,
                fees=float(origination_fee + oid),
                net_cashflow=float(net_initial_outflow),
                ending_balance=float(funded),
                pik_balance=0.0,
                event="funding",
                source_engine=self.name,
            )
        ]

        balance = funded
        original_principal_remaining = funded
        cumulative_pik = D_ZERO
        pik_was_used = False
        prepay_month = inp.prepayment_month if scenario == "upside" else None

        for month in range(1, inp.tenor_months + 1):
            beginning = balance
            cash_rate, pik_rate = self._coupon_split_for_month(inp, month)
            cash_interest = beginning * cash_rate / D_TWELVE
            pik_interest = beginning * pik_rate / D_TWELVE

            if pik_interest > 0:
                pik_was_used = True

            balance += pik_interest
            cumulative_pik += pik_interest

            scheduled_principal = self._scheduled_principal(inp, month, original_principal_remaining)

            event: Optional[str] = None
            prepayment_penalty = D_ZERO
            make_whole = D_ZERO

            is_prepayment_month = prepay_month is not None and month == prepay_month
            is_maturity = month == inp.tenor_months

            if is_prepayment_month:
                principal_repayment = balance
                original_principal_repaid = original_principal_remaining
                original_principal_remaining = D_ZERO
                balance = D_ZERO
                event = "prepayment"

                if inp.prepayment_penalty_mode == "soft_call":
                    prepayment_penalty = beginning * self._soft_call_rate(inp, month)
                elif inp.prepayment_penalty_mode == "make_whole":
                    if not (inp.make_whole_basis == "disabled_after_pik_toggle" and pik_was_used):
                        make_whole_base = (
                            beginning
                            if inp.make_whole_basis == "accreted_principal"
                            else original_principal_repaid
                        )
                        make_whole = self._make_whole_amount(inp, month, make_whole_base)

            elif is_maturity:
                principal_repayment = balance
                original_principal_remaining = D_ZERO
                balance = D_ZERO
                event = "maturity"

            else:
                principal_repayment = min(scheduled_principal, balance)
                original_component = min(scheduled_principal, original_principal_remaining)
                original_principal_remaining -= original_component
                balance -= principal_repayment
                event = "scheduled_amortization" if principal_repayment > 0 else None

            exit_fee = D_ZERO
            if event in {"prepayment", "maturity"}:
                exit_fee = beginning * _D(inp.exit_fee_rate)

            monitoring_fee = self._monitoring_fee(inp, beginning)
            fee_events = self._fee_events_for_month(inp, month, beginning, balance, commitment, funded)
            fees = monitoring_fee + exit_fee + prepayment_penalty + make_whole + fee_events
            net_cashflow = cash_interest + principal_repayment + fees

            if balance < -NEGATIVE_BALANCE_TOLERANCE:
                warnings.append(
                    _rule_warning(
                        "G-12",
                        scenario=scenario,
                        field="ending_balance",
                        message_suffix=(
                            f"month={month}, ending_balance={float(balance)}, "
                            f"tolerance={float(NEGATIVE_BALANCE_TOLERANCE)}"
                        ),
                    )
                )
                balance = D_ZERO

            periods.append(
                CashflowPeriod(
                    month=month,
                    beginning_balance=float(beginning),
                    cash_interest=float(cash_interest),
                    pik_interest=float(pik_interest),
                    principal_repayment=float(principal_repayment),
                    fees=float(fees),
                    net_cashflow=float(net_cashflow),
                    ending_balance=float(balance),
                    pik_balance=float(cumulative_pik),
                    event=event,
                    source_engine=self.name,
                )
            )

            if event == "prepayment":
                break

        return _aggregate_periods(periods)

    def _scheduled_principal(
        self,
        inp: IRRInput,
        month: int,
        original_principal_remaining: Decimal,
    ) -> Decimal:
        funded = _D(inp.funded_amount)
        if inp.repayment_type == "bullet":
            return D_ZERO
        if inp.repayment_type == "amortizing":
            return min(original_principal_remaining, funded / _D(inp.tenor_months))
        if inp.repayment_type == "custom":
            raw = _D(inp.amortization_schedule[month - 1])  # type: ignore[index]
            return min(original_principal_remaining, raw)
        return D_ZERO

    def _monitoring_fee(self, inp: IRRInput, beginning_balance: Decimal) -> Decimal:
        rate_fee = beginning_balance * _D(inp.monitoring_fee_rate) / D_TWELVE
        fixed_fee = _D(inp.fixed_monitoring_fee_per_month)
        minimum_fee = _D(inp.minimum_monitoring_fee_per_month)
        return max(rate_fee + fixed_fee, minimum_fee)

    def _fee_events_for_month(
        self,
        inp: IRRInput,
        month: int,
        beginning: Decimal,
        ending: Decimal,
        commitment: Decimal,
        funded: Decimal,
    ) -> Decimal:
        total = D_ZERO
        for event in inp.fee_events:
            if event.month != month:
                continue
            amount = _D(event.amount)
            if event.base == "fixed":
                total += amount
                continue
            if event.base == "funded_amount":
                base = funded
            elif event.base == "commitment_amount":
                base = commitment
            elif event.base == "beginning_balance":
                base = beginning
            elif event.base == "ending_balance":
                base = ending
            else:
                base = D_ZERO
            total += base * _D(event.rate) + amount
        return total

    def _soft_call_rate(self, inp: IRRInput, month: int) -> Decimal:
        """
        Soft-call schedule semantics.

        Example: [(12, 0.02), (24, 0.01), (36, 0.0)]
          month <= 12  -> 2%
          month <= 24  -> 1%
          month <= 36  -> 0%
          month > 36   -> 0%

        If terminal zero is omitted: [(12, 0.02), (24, 0.01)]
          month <= 12  -> 2%
          month <= 24  -> 1%
          month > 24   -> 0%

        Critical rule: after the final threshold, soft-call penalty is zero.
        """
        if not inp.prepayment_penalty_schedule:
            return D_ZERO
        schedule = sorted(inp.prepayment_penalty_schedule, key=lambda x: x[0])
        for threshold_month, rate in schedule:
            if month <= threshold_month:
                return _D(rate)
        return D_ZERO

    def _make_whole_amount(self, inp: IRRInput, month: int, basis_principal: Decimal) -> Decimal:
        if not inp.make_whole_enabled:
            return D_ZERO
        if inp.make_whole_until_month is None:
            return D_ZERO
        if month >= inp.make_whole_until_month:
            return D_ZERO
        discount_monthly = _annual_to_monthly(_D(inp.make_whole_discount_rate))
        total = D_ZERO
        for m in range(month + 1, inp.make_whole_until_month + 1):
            cash_rate, _ = self._coupon_split_for_month(inp, m)
            expected_interest = basis_principal * cash_rate / D_TWELVE
            total += expected_interest / ((D_ONE + discount_monthly) ** (m - month))
        return total

    def _spread_to_benchmark(self, inp: IRRInput, irr_base: Decimal) -> Optional[float]:
        if inp.benchmark_rate is not None:
            return float(irr_base - _D(inp.benchmark_rate))
        if inp.cashflow_mode == "generated" and inp.coupon_type == "floating":
            return float(irr_base - _D(inp.base_rate))
        return None

    def _assert_output_finite(self, output: IRROutput) -> None:
        scalars = {
            "irr_downside": output.irr_downside,
            "irr_base": output.irr_base,
            "irr_upside": output.irr_upside,
            "moic_downside": output.moic_downside,
            "moic_base": output.moic_base,
            "moic_upside": output.moic_upside,
            "dpi_downside": output.dpi_downside,
            "dpi_base": output.dpi_base,
            "dpi_upside": output.dpi_upside,
            "residual_nav_downside": output.residual_nav_downside,
            "residual_nav_base": output.residual_nav_base,
            "residual_nav_upside": output.residual_nav_upside,
            "spread_to_benchmark": output.spread_to_benchmark,
            "yield_to_worst": output.yield_to_worst,
            "yield_to_maturity": output.yield_to_maturity,
            "technical_confidence": output.technical_confidence,
        }
        for name, value in scalars.items():
            _assert_scalar_finite(name, value)
        _assert_periods_finite(output.cashflow_downside, "downside")
        _assert_periods_finite(output.cashflow_base, "base")
        _assert_periods_finite(output.cashflow_upside, "upside")
        for label, schedule in {
            "pik_accrual_schedule_downside": output.pik_accrual_schedule_downside,
            "pik_accrual_schedule_base": output.pik_accrual_schedule_base,
            "pik_accrual_schedule_upside": output.pik_accrual_schedule_upside,
        }.items():
            for i, value in enumerate(schedule):
                _assert_scalar_finite(f"{label}[{i}]", value)

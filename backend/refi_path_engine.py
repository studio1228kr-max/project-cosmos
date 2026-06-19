from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union
import math


class RefiGate(str, Enum):
    PASS = "PASS"
    WATCH = "WATCH"
    HOLD = "HOLD"
    DROP = "DROP"


class RefiMarginGrade(str, Enum):
    FAT = "FAT"
    ADEQUATE = "ADEQUATE"
    THIN = "THIN"
    NEGATIVE = "NEGATIVE"


class RefiScenarioType(str, Enum):
    BASE = "BASE"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    TAIL = "TAIL"


class DebtServiceMethod(str, Enum):
    INTEREST_ONLY = "INTEREST_ONLY"
    AMORTIZING = "AMORTIZING"


class MarketAppetiteState(str, Enum):
    OPEN = "OPEN"
    SELECTIVE = "SELECTIVE"
    WEAK = "WEAK"
    CLOSED = "CLOSED"


class InputRelianceLevel(str, Enum):
    BASE_CASE = "BASE_CASE"
    STRESS_CASE = "STRESS_CASE"
    TAIL_ONLY = "TAIL_ONLY"
    INTERNAL_REVIEW = "INTERNAL_REVIEW"
    REJECTED = "REJECTED"


class BindingConstraint(str, Enum):
    LTV = "LTV"
    DSCR = "DSCR"
    MARKET_APPETITE = "MARKET_APPETITE"
    BORROWER_CAPACITY = "BORROWER_CAPACITY"
    FUND_LIFE = "FUND_LIFE"
    NO_REFI_WINDOW = "NO_REFI_WINDOW"
    NO_REFI_MARKET = "NO_REFI_MARKET"
    NONE = "NONE"


@dataclass(frozen=True)
class DealMaster:
    deal_id: str
    deal_name: str
    asset_class: str
    deal_type: str

    currency: str = "KRW"
    jurisdiction: Optional[str] = None
    borrower: Optional[str] = None
    sponsor: Optional[str] = None
    origination_channel: Optional[str] = None
    strategy: Optional[str] = None

    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "DealMaster":
        required = {"deal_id", "deal_name", "asset_class", "deal_type"}
        missing = required - set(raw.keys())
        if missing:
            raise ValueError(f"deal_master missing required fields: {sorted(missing)}")

        known = {
            "deal_id", "deal_name", "asset_class", "deal_type", "currency",
            "jurisdiction", "borrower", "sponsor", "origination_channel", "strategy",
        }

        return cls(
            deal_id=str(raw["deal_id"]),
            deal_name=str(raw["deal_name"]),
            asset_class=str(raw["asset_class"]),
            deal_type=str(raw["deal_type"]),
            currency=str(raw.get("currency", "KRW")),
            jurisdiction=raw.get("jurisdiction"),
            borrower=raw.get("borrower"),
            sponsor=raw.get("sponsor"),
            origination_channel=raw.get("origination_channel"),
            strategy=raw.get("strategy"),
            extra={k: v for k, v in raw.items() if k not in known},
        )


@dataclass(frozen=True)
class DebtProfile:
    starting_debt_balance: float
    maturity_month: int
    current_coupon_rate: float
    current_amortization_rate: float = 0.0
    current_debt_service_method: DebtServiceMethod = DebtServiceMethod.INTEREST_ONLY
    committed_unfunded_debt: float = 0.0

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "DebtProfile":
        return cls(
            starting_debt_balance=float(raw["starting_debt_balance"]),
            maturity_month=int(raw["maturity_month"]),
            current_coupon_rate=float(raw["current_coupon_rate"]),
            current_amortization_rate=float(raw.get("current_amortization_rate", 0.0)),
            current_debt_service_method=parse_enum(
                DebtServiceMethod,
                raw.get("current_debt_service_method"),
                DebtServiceMethod.INTEREST_ONLY,
            ),
            committed_unfunded_debt=float(raw.get("committed_unfunded_debt", 0.0)),
        )


@dataclass(frozen=True)
class CashFlowProfile:
    annual_cash_flow: float
    monthly_growth_rate: float = 0.0

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "CashFlowProfile":
        return cls(
            annual_cash_flow=float(raw["annual_cash_flow"]),
            monthly_growth_rate=float(raw.get("monthly_growth_rate", 0.0)),
        )


@dataclass(frozen=True)
class ValueProfile:
    current_value: float
    monthly_value_growth_rate: float = 0.0

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ValueProfile":
        return cls(
            current_value=float(raw["current_value"]),
            monthly_value_growth_rate=float(raw.get("monthly_value_growth_rate", 0.0)),
        )


@dataclass(frozen=True)
class RefiTermsProfile:
    refi_coupon_rate: float
    refi_ltv_cap: float
    refi_dscr_floor: float
    requested_refi_tenor_months: int = 36
    refi_debt_service_method: DebtServiceMethod = DebtServiceMethod.INTEREST_ONLY
    refi_amortization_rate: float = 0.0
    market_appetite_limit: Optional[float] = None
    borrower_debt_capacity: Optional[float] = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "RefiTermsProfile":
        return cls(
            refi_coupon_rate=float(raw["refi_coupon_rate"]),
            refi_ltv_cap=float(raw["refi_ltv_cap"]),
            refi_dscr_floor=float(raw["refi_dscr_floor"]),
            requested_refi_tenor_months=int(raw.get("requested_refi_tenor_months", 36)),
            refi_debt_service_method=parse_enum(
                DebtServiceMethod,
                raw.get("refi_debt_service_method"),
                DebtServiceMethod.INTEREST_ONLY,
            ),
            refi_amortization_rate=float(raw.get("refi_amortization_rate", 0.0)),
            market_appetite_limit=to_optional_float(raw.get("market_appetite_limit")),
            borrower_debt_capacity=to_optional_float(raw.get("borrower_debt_capacity")),
        )


@dataclass(frozen=True)
class DSRAProfile:
    dsra_balance: float = 0.0
    minimum_required_dsra_months: float = 0.0
    dsra_topup_allowed: bool = False
    dsra_release_allowed: bool = False

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "DSRAProfile":
        return cls(
            dsra_balance=float(raw.get("dsra_balance", 0.0)),
            minimum_required_dsra_months=float(raw.get("minimum_required_dsra_months", 0.0)),
            dsra_topup_allowed=bool(raw.get("dsra_topup_allowed", False)),
            dsra_release_allowed=bool(raw.get("dsra_release_allowed", False)),
        )


@dataclass(frozen=True)
class CostBasisStack:
    total_project_cost: Optional[float] = None
    funded_debt: Optional[float] = None
    unfunded_commitments: float = 0.0
    equity_contributed: Optional[float] = None
    remaining_capex: float = 0.0
    cost_overrun_reserve: float = 0.0
    expected_cost_to_complete: Optional[float] = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "CostBasisStack":
        return cls(
            total_project_cost=to_optional_float(raw.get("total_project_cost")),
            funded_debt=to_optional_float(raw.get("funded_debt")),
            unfunded_commitments=float(raw.get("unfunded_commitments", 0.0)),
            equity_contributed=to_optional_float(raw.get("equity_contributed")),
            remaining_capex=float(raw.get("remaining_capex", 0.0)),
            cost_overrun_reserve=float(raw.get("cost_overrun_reserve", 0.0)),
            expected_cost_to_complete=to_optional_float(raw.get("expected_cost_to_complete")),
        )


@dataclass(frozen=True)
class CureProfile:
    borrower_cash_paydown_capacity: float = 0.0
    sponsor_equity_cure_capacity: float = 0.0
    asset_sale_paydown_capacity: float = 0.0
    cure_committed: bool = False
    sponsor_cure_confirmed: bool = False
    monthly_cure_limit: Optional[float] = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "CureProfile":
        return cls(
            borrower_cash_paydown_capacity=float(raw.get("borrower_cash_paydown_capacity", 0.0)),
            sponsor_equity_cure_capacity=float(raw.get("sponsor_equity_cure_capacity", 0.0)),
            asset_sale_paydown_capacity=float(raw.get("asset_sale_paydown_capacity", 0.0)),
            cure_committed=bool(raw.get("cure_committed", False)),
            sponsor_cure_confirmed=bool(raw.get("sponsor_cure_confirmed", False)),
            monthly_cure_limit=to_optional_float(raw.get("monthly_cure_limit")),
        )


@dataclass(frozen=True)
class MarketConstraintProfile:
    default_market_appetite: MarketAppetiteState = MarketAppetiteState.OPEN
    monthly_market_appetite: Dict[int, MarketAppetiteState] = field(default_factory=dict)
    refi_window_start_month: int = 0
    refi_window_end_month: Optional[int] = None
    fund_remaining_life_months: Optional[int] = None
    fund_reinvestment_allowed: bool = True
    secondary_liquidity_haircut: float = 0.0

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "MarketConstraintProfile":
        monthly_raw = raw.get("monthly_market_appetite", {}) or {}
        monthly = {
            int(month): parse_enum(MarketAppetiteState, state, MarketAppetiteState.OPEN)
            for month, state in monthly_raw.items()
        }
        return cls(
            default_market_appetite=parse_enum(
                MarketAppetiteState,
                raw.get("default_market_appetite"),
                MarketAppetiteState.OPEN,
            ),
            monthly_market_appetite=monthly,
            refi_window_start_month=int(raw.get("refi_window_start_month", 0)),
            refi_window_end_month=raw.get("refi_window_end_month"),
            fund_remaining_life_months=raw.get("fund_remaining_life_months"),
            fund_reinvestment_allowed=bool(raw.get("fund_reinvestment_allowed", True)),
            secondary_liquidity_haircut=float(raw.get("secondary_liquidity_haircut", 0.0)),
        )


@dataclass(frozen=True)
class RefiPathInput:
    debt: DebtProfile
    cash_flow: CashFlowProfile
    value: ValueProfile
    refi_terms: RefiTermsProfile
    dsra: DSRAProfile = field(default_factory=DSRAProfile)
    cost_basis: CostBasisStack = field(default_factory=CostBasisStack)
    cure: CureProfile = field(default_factory=CureProfile)
    market: MarketConstraintProfile = field(default_factory=MarketConstraintProfile)
    input_reliance_level: InputRelianceLevel = InputRelianceLevel.BASE_CASE
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "RefiPathInput":
        return cls(
            debt=DebtProfile.from_mapping(raw["debt"]),
            cash_flow=CashFlowProfile.from_mapping(raw["cash_flow"]),
            value=ValueProfile.from_mapping(raw["value"]),
            refi_terms=RefiTermsProfile.from_mapping(raw["refi_terms"]),
            dsra=DSRAProfile.from_mapping(raw.get("dsra", {})),
            cost_basis=CostBasisStack.from_mapping(raw.get("cost_basis", {})),
            cure=CureProfile.from_mapping(raw.get("cure", {})),
            market=MarketConstraintProfile.from_mapping(raw.get("market", {})),
            input_reliance_level=parse_enum(
                InputRelianceLevel,
                raw.get("input_reliance_level"),
                InputRelianceLevel.BASE_CASE,
            ),
            extra=dict(raw.get("extra", {})),
        )


@dataclass(frozen=True)
class RefiPathScenario:
    name: str
    scenario_type: RefiScenarioType
    cash_flow_haircut: float = 0.0
    value_haircut: float = 0.0
    refi_rate_shock: float = 0.0
    refi_ltv_cap_haircut: float = 0.0
    refi_dscr_floor_increase: float = 0.0
    capex_overrun_pct: float = 0.0
    market_appetite_override: Optional[MarketAppetiteState] = None
    sponsor_cure_haircut: float = 0.0
    borrower_cash_haircut: float = 0.0
    asset_sale_haircut: float = 0.0
    evidence_reliance_penalty: float = 0.0
    force_no_refi_market: bool = False

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "RefiPathScenario":
        return cls(
            name=str(raw["name"]),
            scenario_type=parse_enum(
                RefiScenarioType,
                raw.get("scenario_type"),
                RefiScenarioType.BASE,
            ),
            cash_flow_haircut=float(raw.get("cash_flow_haircut", 0.0)),
            value_haircut=float(raw.get("value_haircut", 0.0)),
            refi_rate_shock=float(raw.get("refi_rate_shock", 0.0)),
            refi_ltv_cap_haircut=float(raw.get("refi_ltv_cap_haircut", 0.0)),
            refi_dscr_floor_increase=float(raw.get("refi_dscr_floor_increase", 0.0)),
            capex_overrun_pct=float(raw.get("capex_overrun_pct", 0.0)),
            market_appetite_override=parse_optional_enum(
                MarketAppetiteState,
                raw.get("market_appetite_override"),
            ),
            sponsor_cure_haircut=float(raw.get("sponsor_cure_haircut", 0.0)),
            borrower_cash_haircut=float(raw.get("borrower_cash_haircut", 0.0)),
            asset_sale_haircut=float(raw.get("asset_sale_haircut", 0.0)),
            evidence_reliance_penalty=float(raw.get("evidence_reliance_penalty", 0.0)),
            force_no_refi_market=bool(raw.get("force_no_refi_market", False)),
        )


@dataclass(frozen=True)
class RefiPathPolicy:
    watch_gap_pct: float = 0.00
    hold_gap_pct: float = 0.10
    drop_gap_pct: float = 0.20
    pass_thick_margin_pct: float = 0.15
    pass_adequate_margin_pct: float = 0.05
    min_dsra_months_for_pass: float = 6.0
    min_dsra_months_for_watch: float = 3.0
    max_ltc_for_pass: float = 0.75
    max_ltc_for_watch: float = 0.85
    max_ltc_for_hold: float = 0.90
    min_refi_window_months_for_pass: int = 6
    min_refi_window_months_for_watch: int = 3
    fund_life_must_cover_refi_tenor: bool = True
    closed_market_blocks_refi: bool = True
    sponsor_cure_requires_confirmation_for_pass: bool = True
    uncommitted_cure_blocks_pass: bool = True
    evidence_blockers_force_hold: bool = True

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "RefiPathPolicy":
        return cls(
            watch_gap_pct=float(raw.get("watch_gap_pct", 0.00)),
            hold_gap_pct=float(raw.get("hold_gap_pct", 0.10)),
            drop_gap_pct=float(raw.get("drop_gap_pct", 0.20)),
            pass_thick_margin_pct=float(raw.get("pass_thick_margin_pct", 0.15)),
            pass_adequate_margin_pct=float(raw.get("pass_adequate_margin_pct", 0.05)),
            min_dsra_months_for_pass=float(raw.get("min_dsra_months_for_pass", 6.0)),
            min_dsra_months_for_watch=float(raw.get("min_dsra_months_for_watch", 3.0)),
            max_ltc_for_pass=float(raw.get("max_ltc_for_pass", 0.75)),
            max_ltc_for_watch=float(raw.get("max_ltc_for_watch", 0.85)),
            max_ltc_for_hold=float(raw.get("max_ltc_for_hold", 0.90)),
            min_refi_window_months_for_pass=int(raw.get("min_refi_window_months_for_pass", 6)),
            min_refi_window_months_for_watch=int(raw.get("min_refi_window_months_for_watch", 3)),
            fund_life_must_cover_refi_tenor=bool(raw.get("fund_life_must_cover_refi_tenor", True)),
            closed_market_blocks_refi=bool(raw.get("closed_market_blocks_refi", True)),
            sponsor_cure_requires_confirmation_for_pass=bool(raw.get("sponsor_cure_requires_confirmation_for_pass", True)),
            uncommitted_cure_blocks_pass=bool(raw.get("uncommitted_cure_blocks_pass", True)),
            evidence_blockers_force_hold=bool(raw.get("evidence_blockers_force_hold", True)),
        )


@dataclass(frozen=True)
class MonthlyRefiPathPoint:
    month: int
    debt_balance: float
    annual_cash_flow: float
    collateral_or_enterprise_value: float
    current_monthly_debt_service: float
    current_dscr: float
    current_ltv: float
    dsra_balance: float
    dsra_months_equivalent: float
    ltc_current: Optional[float]
    ltc_at_completion: Optional[float]
    equity_cushion_at_completion: Optional[float]
    market_appetite: MarketAppetiteState
    refi_window_open: bool
    fund_life_ok: bool
    refi_coupon_rate: float
    refi_ltv_cap: float
    refi_dscr_floor: float
    refi_capacity_by_ltv: float
    refi_capacity_by_dscr: float
    refi_capacity_by_market: float
    refi_capacity_by_borrower_capacity: Optional[float]
    refi_capacity_by_fund_life: float
    gross_refi_capacity: float
    binding_constraint: BindingConstraint
    available_cure_capacity: float
    refi_gap_before_cure: float
    refi_gap_after_cure: float
    refi_gap_pct_after_cure: float
    refi_capacity_margin_pct: float
    refi_margin_grade: RefiMarginGrade
    refi_feasible: bool
    flags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["market_appetite"] = self.market_appetite.value
        data["binding_constraint"] = self.binding_constraint.value
        data["refi_margin_grade"] = self.refi_margin_grade.value
        return data


@dataclass(frozen=True)
class RefiPathScenarioResult:
    scenario_name: str
    scenario_type: RefiScenarioType
    gate: RefiGate
    refi_margin_grade: RefiMarginGrade
    path: List[MonthlyRefiPathPoint]
    maturity_month: int
    maturity_refi_gap: float
    maturity_refi_gap_pct: float
    worst_refi_gap: float
    worst_refi_gap_pct: float
    worst_refi_gap_month: int
    earliest_dscr_breach_month: Optional[int]
    dsra_depletion_month: Optional[int]
    earliest_refi_feasible_month: Optional[int]
    latest_safe_refi_month: Optional[int]
    first_breach_driver: Optional[str]
    binding_constraint_at_maturity: BindingConstraint
    hard_equity_shortfall: float
    flags: List[str]
    required_actions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "scenario_type": self.scenario_type.value,
            "gate": self.gate.value,
            "refi_margin_grade": self.refi_margin_grade.value,
            "path": [x.to_dict() for x in self.path],
            "maturity_month": self.maturity_month,
            "maturity_refi_gap": self.maturity_refi_gap,
            "maturity_refi_gap_pct": self.maturity_refi_gap_pct,
            "worst_refi_gap": self.worst_refi_gap,
            "worst_refi_gap_pct": self.worst_refi_gap_pct,
            "worst_refi_gap_month": self.worst_refi_gap_month,
            "earliest_dscr_breach_month": self.earliest_dscr_breach_month,
            "dsra_depletion_month": self.dsra_depletion_month,
            "earliest_refi_feasible_month": self.earliest_refi_feasible_month,
            "latest_safe_refi_month": self.latest_safe_refi_month,
            "first_breach_driver": self.first_breach_driver,
            "binding_constraint_at_maturity": self.binding_constraint_at_maturity.value,
            "hard_equity_shortfall": self.hard_equity_shortfall,
            "flags": self.flags,
            "required_actions": self.required_actions,
        }


@dataclass(frozen=True)
class RefiPathPackage:
    deal_master: DealMaster
    overall_gate: RefiGate
    scenario_results: List[RefiPathScenarioResult]
    base_result: Optional[RefiPathScenarioResult]
    moderate_result: Optional[RefiPathScenarioResult]
    severe_result: Optional[RefiPathScenarioResult]
    tail_result: Optional[RefiPathScenarioResult]
    evidence_reliance_level: InputRelianceLevel
    evidence_blockers: List[str]
    evidence_warnings: List[str]
    memo_summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_master": asdict(self.deal_master),
            "overall_gate": self.overall_gate.value,
            "scenario_results": [x.to_dict() for x in self.scenario_results],
            "base_result": self.base_result.to_dict() if self.base_result else None,
            "moderate_result": self.moderate_result.to_dict() if self.moderate_result else None,
            "severe_result": self.severe_result.to_dict() if self.severe_result else None,
            "tail_result": self.tail_result.to_dict() if self.tail_result else None,
            "evidence_reliance_level": self.evidence_reliance_level.value,
            "evidence_blockers": self.evidence_blockers,
            "evidence_warnings": self.evidence_warnings,
            "memo_summary": self.memo_summary,
        }


def evaluate_refi_path_engine(
    deal_master: Union[DealMaster, Mapping[str, Any]],
    refi_path_input: Union[RefiPathInput, Mapping[str, Any]],
    scenarios: Optional[Sequence[Union[RefiPathScenario, Mapping[str, Any]]]] = None,
    policy: Optional[Union[RefiPathPolicy, Mapping[str, Any]]] = None,
    evidence_package: Optional[Mapping[str, Any]] = None,
) -> RefiPathPackage:
    dm = normalize_deal_master(deal_master)
    base_input = normalize_refi_path_input(refi_path_input)
    refi_policy = normalize_policy(policy)

    evidence_blockers, evidence_warnings, reliance_level = analyze_evidence_package(evidence_package)
    base_input = set_input_reliance_level(base_input, reliance_level)

    scenario_list = normalize_scenarios(scenarios)
    if not scenario_list:
        scenario_list = default_refi_path_scenarios(
            reliance_level=reliance_level,
            evidence_package=evidence_package,
        )

    results = [
        run_refi_path_scenario(
            refi_input=base_input,
            scenario=scenario,
            policy=refi_policy,
            evidence_blockers=evidence_blockers,
        )
        for scenario in scenario_list
    ]

    overall_gate = aggregate_overall_gate(results, evidence_blockers, refi_policy)

    base_result = first_result(results, RefiScenarioType.BASE)
    moderate_result = first_result(results, RefiScenarioType.MODERATE)
    severe_result = first_result(results, RefiScenarioType.SEVERE)
    tail_result = first_result(results, RefiScenarioType.TAIL)

    return RefiPathPackage(
        deal_master=dm,
        overall_gate=overall_gate,
        scenario_results=results,
        base_result=base_result,
        moderate_result=moderate_result,
        severe_result=severe_result,
        tail_result=tail_result,
        evidence_reliance_level=reliance_level,
        evidence_blockers=sorted(set(evidence_blockers)),
        evidence_warnings=sorted(set(evidence_warnings)),
        memo_summary=build_memo_summary(results, overall_gate),
    )


def run_refi_path_scenario(
    refi_input: RefiPathInput,
    scenario: RefiPathScenario,
    policy: RefiPathPolicy,
    evidence_blockers: Sequence[str],
) -> RefiPathScenarioResult:
    path: List[MonthlyRefiPathPoint] = []
    maturity = refi_input.debt.maturity_month

    debt_balance = refi_input.debt.starting_debt_balance
    dsra_balance = refi_input.dsra.dsra_balance

    earliest_dscr_breach_month: Optional[int] = None
    dsra_depletion_month: Optional[int] = None

    for month in range(0, maturity + 1):
        point = calculate_monthly_refi_point(
            refi_input=refi_input,
            scenario=scenario,
            policy=policy,
            month=month,
            debt_balance=debt_balance,
            dsra_balance=dsra_balance,
        )
        path.append(point)

        if point.current_dscr < 1.0 and earliest_dscr_breach_month is None:
            earliest_dscr_breach_month = month

        if point.dsra_balance <= 0 and dsra_balance > 0 and dsra_depletion_month is None:
            dsra_depletion_month = month

        monthly_interest = debt_balance * refi_input.debt.current_coupon_rate / 12.0
        monthly_principal = calculate_monthly_principal(
            debt_balance=debt_balance,
            amortization_rate=refi_input.debt.current_amortization_rate,
            method=refi_input.debt.current_debt_service_method,
        )
        monthly_debt_service = monthly_interest + monthly_principal
        monthly_cash_flow = point.annual_cash_flow / 12.0
        cash_shortfall = max(0.0, monthly_debt_service - monthly_cash_flow)

        dsra_balance = max(0.0, dsra_balance - cash_shortfall)
        debt_balance = max(0.0, debt_balance - monthly_principal)

    maturity_point = path[-1]
    worst_point = max(path, key=lambda x: x.refi_gap_pct_after_cure)

    feasible_months = [p.month for p in path if p.refi_feasible]
    earliest_refi_feasible_month = min(feasible_months) if feasible_months else None
    latest_safe_refi_month = max(feasible_months) if feasible_months else None

    flags, required_actions = build_scenario_flags_and_actions(
        path=path,
        scenario=scenario,
        policy=policy,
        evidence_blockers=evidence_blockers,
    )

    first_breach_driver = detect_first_breach_driver(path, policy)
    hard_equity_shortfall = calculate_hard_equity_shortfall(
        maturity_point=maturity_point,
        refi_input=refi_input,
    )

    gate = determine_scenario_gate(
        maturity_point=maturity_point,
        worst_point=worst_point,
        flags=flags,
        scenario=scenario,
        policy=policy,
        evidence_blockers=evidence_blockers,
    )

    return RefiPathScenarioResult(
        scenario_name=scenario.name,
        scenario_type=scenario.scenario_type,
        gate=gate,
        refi_margin_grade=maturity_point.refi_margin_grade,
        path=path,
        maturity_month=maturity,
        maturity_refi_gap=round(maturity_point.refi_gap_after_cure, 2),
        maturity_refi_gap_pct=round(maturity_point.refi_gap_pct_after_cure, 6),
        worst_refi_gap=round(worst_point.refi_gap_after_cure, 2),
        worst_refi_gap_pct=round(worst_point.refi_gap_pct_after_cure, 6),
        worst_refi_gap_month=worst_point.month,
        earliest_dscr_breach_month=earliest_dscr_breach_month,
        dsra_depletion_month=dsra_depletion_month,
        earliest_refi_feasible_month=earliest_refi_feasible_month,
        latest_safe_refi_month=latest_safe_refi_month,
        first_breach_driver=first_breach_driver,
        binding_constraint_at_maturity=maturity_point.binding_constraint,
        hard_equity_shortfall=round(hard_equity_shortfall, 2),
        flags=sorted(set(flags)),
        required_actions=sorted(set(required_actions)),
    )


def calculate_monthly_refi_point(
    refi_input: RefiPathInput,
    scenario: RefiPathScenario,
    policy: RefiPathPolicy,
    month: int,
    debt_balance: float,
    dsra_balance: float,
) -> MonthlyRefiPathPoint:
    annual_cash_flow = project_cash_flow(refi_input, scenario, month)
    value = project_value(refi_input, scenario, month)

    current_monthly_debt_service = calculate_current_monthly_debt_service(
        debt_balance=debt_balance,
        debt_profile=refi_input.debt,
    )

    current_dscr = safe_div(annual_cash_flow / 12.0, current_monthly_debt_service, fallback=math.inf)
    current_ltv = safe_div(debt_balance, value, fallback=math.inf)
    dsra_months_equivalent = safe_div(dsra_balance, current_monthly_debt_service, fallback=math.inf)

    ltc_current, ltc_at_completion, equity_cushion = calculate_ltc_and_equity_cushion(
        refi_input=refi_input,
        debt_balance=debt_balance,
        scenario=scenario,
    )

    market_state = get_market_appetite_state(refi_input.market, scenario, month)
    refi_window_open = is_refi_window_open(refi_input.market, month, refi_input.debt.maturity_month)
    fund_life_ok = is_fund_life_ok(refi_input, month)

    refi_coupon = max(0.0, refi_input.refi_terms.refi_coupon_rate + scenario.refi_rate_shock)
    refi_ltv_cap = clamp(
        refi_input.refi_terms.refi_ltv_cap * (1 + scenario.refi_ltv_cap_haircut),
        0.0, 1.0,
    )
    refi_dscr_floor = max(
        0.0001,
        refi_input.refi_terms.refi_dscr_floor + scenario.refi_dscr_floor_increase,
    )

    capacity_by_ltv = value * refi_ltv_cap

    refi_debt_service_constant = calculate_annual_debt_service_constant(
        coupon_rate=refi_coupon,
        amortization_rate=refi_input.refi_terms.refi_amortization_rate,
        method=refi_input.refi_terms.refi_debt_service_method,
    )
    capacity_by_dscr = safe_div(
        annual_cash_flow,
        refi_debt_service_constant * refi_dscr_floor,
        fallback=0.0,
    )

    theoretical_capacity = min(capacity_by_ltv, capacity_by_dscr)
    capacity_by_market = calculate_market_capacity(
        theoretical_capacity=theoretical_capacity,
        explicit_market_limit=refi_input.refi_terms.market_appetite_limit,
        market_state=market_state,
        scenario=scenario,
    )

    capacity_by_borrower_capacity = refi_input.refi_terms.borrower_debt_capacity
    capacity_by_fund_life = debt_balance if fund_life_ok else 0.0

    candidates: List[Tuple[BindingConstraint, float]] = [
        (BindingConstraint.LTV, capacity_by_ltv),
        (BindingConstraint.DSCR, capacity_by_dscr),
        (BindingConstraint.MARKET_APPETITE, capacity_by_market),
        (BindingConstraint.FUND_LIFE, capacity_by_fund_life),
    ]
    if capacity_by_borrower_capacity is not None:
        candidates.append((BindingConstraint.BORROWER_CAPACITY, capacity_by_borrower_capacity))
    if not refi_window_open:
        candidates.append((BindingConstraint.NO_REFI_WINDOW, 0.0))
    if scenario.force_no_refi_market:
        candidates.append((BindingConstraint.NO_REFI_MARKET, 0.0))

    binding_constraint, gross_capacity = min(candidates, key=lambda x: x[1])

    available_cure_capacity = calculate_available_cure_capacity(refi_input, scenario)

    gap_before_cure = max(0.0, debt_balance - gross_capacity)
    gap_after_cure = max(0.0, debt_balance - gross_capacity - available_cure_capacity)
    gap_pct_after_cure = safe_div(gap_after_cure, debt_balance, fallback=1.0)

    margin_pct = safe_div(gross_capacity + available_cure_capacity - debt_balance, debt_balance, fallback=-1.0)
    margin_grade = grade_refi_margin(margin_pct, policy)

    flags = build_monthly_flags(
        current_dscr=current_dscr,
        current_ltv=current_ltv,
        dsra_months_equivalent=dsra_months_equivalent,
        ltc_at_completion=ltc_at_completion,
        market_state=market_state,
        refi_window_open=refi_window_open,
        fund_life_ok=fund_life_ok,
        gap_pct_after_cure=gap_pct_after_cure,
        binding_constraint=binding_constraint,
        policy=policy,
    )

    refi_feasible = (
        gap_after_cure <= 0
        and refi_window_open
        and fund_life_ok
        and market_state != MarketAppetiteState.CLOSED
    )

    return MonthlyRefiPathPoint(
        month=month,
        debt_balance=round(debt_balance, 2),
        annual_cash_flow=round(annual_cash_flow, 2),
        collateral_or_enterprise_value=round(value, 2),
        current_monthly_debt_service=round(current_monthly_debt_service, 2),
        current_dscr=round(current_dscr, 6),
        current_ltv=round(current_ltv, 6),
        dsra_balance=round(dsra_balance, 2),
        dsra_months_equivalent=round(dsra_months_equivalent, 6),
        ltc_current=round(ltc_current, 6) if ltc_current is not None else None,
        ltc_at_completion=round(ltc_at_completion, 6) if ltc_at_completion is not None else None,
        equity_cushion_at_completion=round(equity_cushion, 2) if equity_cushion is not None else None,
        market_appetite=market_state,
        refi_window_open=refi_window_open,
        fund_life_ok=fund_life_ok,
        refi_coupon_rate=round(refi_coupon, 6),
        refi_ltv_cap=round(refi_ltv_cap, 6),
        refi_dscr_floor=round(refi_dscr_floor, 6),
        refi_capacity_by_ltv=round(capacity_by_ltv, 2),
        refi_capacity_by_dscr=round(capacity_by_dscr, 2),
        refi_capacity_by_market=round(capacity_by_market, 2),
        refi_capacity_by_borrower_capacity=round(capacity_by_borrower_capacity, 2) if capacity_by_borrower_capacity is not None else None,
        refi_capacity_by_fund_life=round(capacity_by_fund_life, 2),
        gross_refi_capacity=round(gross_capacity, 2),
        binding_constraint=binding_constraint,
        available_cure_capacity=round(available_cure_capacity, 2),
        refi_gap_before_cure=round(gap_before_cure, 2),
        refi_gap_after_cure=round(gap_after_cure, 2),
        refi_gap_pct_after_cure=round(gap_pct_after_cure, 6),
        refi_capacity_margin_pct=round(margin_pct, 6),
        refi_margin_grade=margin_grade,
        refi_feasible=refi_feasible,
        flags=sorted(set(flags)),
    )


def project_cash_flow(
    refi_input: RefiPathInput,
    scenario: RefiPathScenario,
    month: int,
) -> float:
    base = refi_input.cash_flow.annual_cash_flow
    growth = (1 + refi_input.cash_flow.monthly_growth_rate) ** month
    stressed = base * growth * (1 + scenario.cash_flow_haircut)
    stressed *= (1 - scenario.evidence_reliance_penalty)
    return max(0.0, stressed)


def project_value(
    refi_input: RefiPathInput,
    scenario: RefiPathScenario,
    month: int,
) -> float:
    base = refi_input.value.current_value
    growth = (1 + refi_input.value.monthly_value_growth_rate) ** month
    stressed = base * growth * (1 + scenario.value_haircut)
    stressed *= (1 - scenario.evidence_reliance_penalty)
    return max(0.0, stressed)


def calculate_current_monthly_debt_service(
    debt_balance: float,
    debt_profile: DebtProfile,
) -> float:
    monthly_interest = debt_balance * debt_profile.current_coupon_rate / 12.0
    monthly_principal = calculate_monthly_principal(
        debt_balance=debt_balance,
        amortization_rate=debt_profile.current_amortization_rate,
        method=debt_profile.current_debt_service_method,
    )
    return monthly_interest + monthly_principal


def calculate_monthly_principal(
    debt_balance: float,
    amortization_rate: float,
    method: DebtServiceMethod,
) -> float:
    if method == DebtServiceMethod.INTEREST_ONLY:
        return 0.0
    return debt_balance * amortization_rate / 12.0


def calculate_annual_debt_service_constant(
    coupon_rate: float,
    amortization_rate: float,
    method: DebtServiceMethod,
) -> float:
    if method == DebtServiceMethod.INTEREST_ONLY:
        return max(0.0, coupon_rate)
    return max(0.0, coupon_rate + amortization_rate)


def calculate_ltc_and_equity_cushion(
    refi_input: RefiPathInput,
    debt_balance: float,
    scenario: RefiPathScenario,
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    stack = refi_input.cost_basis

    if stack.total_project_cost is None or stack.total_project_cost <= 0:
        return None, None, None

    current_cost = stack.total_project_cost
    expected_cost_to_complete = (
        stack.expected_cost_to_complete
        if stack.expected_cost_to_complete is not None
        else stack.remaining_capex
    )
    cost_overrun = expected_cost_to_complete * max(0.0, scenario.capex_overrun_pct)
    completion_cost = current_cost + expected_cost_to_complete + cost_overrun

    current_ltc = safe_div(debt_balance, current_cost, fallback=None)

    completion_debt = debt_balance + stack.unfunded_commitments
    ltc_at_completion = safe_div(completion_debt, completion_cost, fallback=None)

    equity_cushion = completion_cost - completion_debt

    return current_ltc, ltc_at_completion, equity_cushion


def calculate_market_capacity(
    theoretical_capacity: float,
    explicit_market_limit: Optional[float],
    market_state: MarketAppetiteState,
    scenario: RefiPathScenario,
) -> float:
    if scenario.force_no_refi_market:
        return 0.0

    multiplier = {
        MarketAppetiteState.OPEN: 1.00,
        MarketAppetiteState.SELECTIVE: 0.85,
        MarketAppetiteState.WEAK: 0.55,
        MarketAppetiteState.CLOSED: 0.00,
    }[market_state]

    implied_market_capacity = theoretical_capacity * multiplier

    if explicit_market_limit is not None:
        return min(implied_market_capacity, explicit_market_limit * multiplier)

    return implied_market_capacity


def calculate_available_cure_capacity(
    refi_input: RefiPathInput,
    scenario: RefiPathScenario,
) -> float:
    cure = refi_input.cure

    borrower_cash = cure.borrower_cash_paydown_capacity * (1 + scenario.borrower_cash_haircut)
    sponsor_equity = cure.sponsor_equity_cure_capacity * (1 + scenario.sponsor_cure_haircut)
    asset_sale = cure.asset_sale_paydown_capacity * (1 + scenario.asset_sale_haircut)

    total = max(0.0, borrower_cash) + max(0.0, sponsor_equity) + max(0.0, asset_sale)

    if cure.monthly_cure_limit is not None:
        total = min(total, cure.monthly_cure_limit)

    return max(0.0, total)


def get_market_appetite_state(
    market: MarketConstraintProfile,
    scenario: RefiPathScenario,
    month: int,
) -> MarketAppetiteState:
    if scenario.market_appetite_override is not None:
        return scenario.market_appetite_override
    return market.monthly_market_appetite.get(month, market.default_market_appetite)


def is_refi_window_open(
    market: MarketConstraintProfile,
    month: int,
    maturity_month: int,
) -> bool:
    start = market.refi_window_start_month
    end = market.refi_window_end_month if market.refi_window_end_month is not None else maturity_month
    return start <= month <= end


def is_fund_life_ok(
    refi_input: RefiPathInput,
    month: int,
) -> bool:
    remaining_life = refi_input.market.fund_remaining_life_months
    if remaining_life is None:
        return True

    remaining_after_month = remaining_life - month
    if not refi_input.market.fund_reinvestment_allowed:
        return False

    return remaining_after_month >= refi_input.refi_terms.requested_refi_tenor_months


def build_monthly_flags(
    current_dscr: float,
    current_ltv: float,
    dsra_months_equivalent: float,
    ltc_at_completion: Optional[float],
    market_state: MarketAppetiteState,
    refi_window_open: bool,
    fund_life_ok: bool,
    gap_pct_after_cure: float,
    binding_constraint: BindingConstraint,
    policy: RefiPathPolicy,
) -> List[str]:
    flags: List[str] = []

    if current_dscr < 1.0:
        flags.append("CURRENT_DSCR_BELOW_1X")

    if dsra_months_equivalent < policy.min_dsra_months_for_watch:
        flags.append("DSRA_BELOW_WATCH_THRESHOLD")
    elif dsra_months_equivalent < policy.min_dsra_months_for_pass:
        flags.append("DSRA_THIN")

    if ltc_at_completion is not None:
        if ltc_at_completion >= policy.max_ltc_for_hold:
            flags.append("LTC_HOLD_LEVEL")
        elif ltc_at_completion >= policy.max_ltc_for_watch:
            flags.append("LTC_WATCH_LEVEL")
        elif ltc_at_completion >= policy.max_ltc_for_pass:
            flags.append("LTC_THIN")

    if market_state == MarketAppetiteState.CLOSED:
        flags.append("MARKET_CLOSED")
    elif market_state == MarketAppetiteState.WEAK:
        flags.append("MARKET_WEAK")
    elif market_state == MarketAppetiteState.SELECTIVE:
        flags.append("MARKET_SELECTIVE")

    if not refi_window_open:
        flags.append("OUTSIDE_REFI_WINDOW")

    if not fund_life_ok:
        flags.append("FUND_LIFE_CONSTRAINT")

    if gap_pct_after_cure >= policy.drop_gap_pct:
        flags.append("REFI_GAP_DROP_LEVEL")
    elif gap_pct_after_cure >= policy.hold_gap_pct:
        flags.append("REFI_GAP_HOLD_LEVEL")
    elif gap_pct_after_cure > policy.watch_gap_pct:
        flags.append("REFI_GAP_WATCH_LEVEL")

    flags.append(f"BINDING_CONSTRAINT_{binding_constraint.value}")

    return flags


def build_scenario_flags_and_actions(
    path: Sequence[MonthlyRefiPathPoint],
    scenario: RefiPathScenario,
    policy: RefiPathPolicy,
    evidence_blockers: Sequence[str],
) -> Tuple[List[str], List[str]]:
    flags: List[str] = []
    actions: List[str] = []

    all_month_flags = sorted(set(flag for p in path for flag in p.flags))
    flags.extend(all_month_flags)

    maturity = path[-1]
    worst = max(path, key=lambda x: x.refi_gap_pct_after_cure)

    if evidence_blockers:
        flags.append("EVIDENCE_BLOCKERS_PRESENT")
        actions.append("Resolve evidence blockers before relying on refi output externally.")

    if maturity.refi_gap_after_cure > 0:
        actions.append("Solve maturity refi gap through lower debt, committed cure, asset sale, extension, or takeout lender evidence.")

    if worst.refi_gap_after_cure > 0 and worst.month < maturity.month:
        actions.append("Review intra-period refi window; path shows refi weakness before legal maturity.")

    if "DSRA_BELOW_WATCH_THRESHOLD" in flags:
        actions.append("Increase DSRA, shorten risk window, or add cash sweep before maturity.")

    if "LTC_HOLD_LEVEL" in flags:
        actions.append("Reduce leverage, increase contributed equity, or verify cost-to-complete funding.")

    if "MARKET_CLOSED" in flags:
        actions.append("Do not underwrite to refinancing; require sale, paydown, restructuring, or extension path.")

    if "FUND_LIFE_CONSTRAINT" in flags:
        actions.append("Resolve fund tenor/reinvestment constraint or move takeout outside fund-level dependency.")

    if scenario.scenario_type in {RefiScenarioType.SEVERE, RefiScenarioType.TAIL} and maturity.refi_gap_after_cure > 0:
        actions.append("Feed refi failure into Recovery Waterfall / LGD Engine.")

    return sorted(set(flags)), sorted(set(actions))


def determine_scenario_gate(
    maturity_point: MonthlyRefiPathPoint,
    worst_point: MonthlyRefiPathPoint,
    flags: Sequence[str],
    scenario: RefiPathScenario,
    policy: RefiPathPolicy,
    evidence_blockers: Sequence[str],
) -> RefiGate:
    if evidence_blockers and policy.evidence_blockers_force_hold:
        return RefiGate.HOLD

    if "MARKET_CLOSED" in flags and policy.closed_market_blocks_refi:
        return RefiGate.HOLD

    if "FUND_LIFE_CONSTRAINT" in flags and policy.fund_life_must_cover_refi_tenor:
        return RefiGate.HOLD

    if maturity_point.refi_gap_pct_after_cure >= policy.drop_gap_pct:
        return RefiGate.DROP

    if maturity_point.refi_gap_pct_after_cure >= policy.hold_gap_pct:
        return RefiGate.HOLD

    if "LTC_HOLD_LEVEL" in flags:
        return RefiGate.HOLD

    if "DSRA_BELOW_WATCH_THRESHOLD" in flags and maturity_point.refi_gap_after_cure > 0:
        return RefiGate.HOLD

    if policy.uncommitted_cure_blocks_pass and maturity_point.available_cure_capacity > 0:
        return RefiGate.WATCH

    if maturity_point.refi_gap_pct_after_cure > policy.watch_gap_pct:
        return RefiGate.WATCH

    if maturity_point.refi_margin_grade == RefiMarginGrade.THIN:
        return RefiGate.WATCH

    if scenario.scenario_type in {RefiScenarioType.SEVERE, RefiScenarioType.TAIL} and maturity_point.refi_gap_after_cure > 0:
        return RefiGate.HOLD

    return RefiGate.PASS


def aggregate_overall_gate(
    results: Sequence[RefiPathScenarioResult],
    evidence_blockers: Sequence[str],
    policy: RefiPathPolicy,
) -> RefiGate:
    if evidence_blockers and policy.evidence_blockers_force_hold:
        return RefiGate.HOLD

    if any(r.gate == RefiGate.DROP for r in results):
        return RefiGate.DROP

    if any(r.gate == RefiGate.HOLD for r in results):
        return RefiGate.HOLD

    if any(r.gate == RefiGate.WATCH for r in results):
        return RefiGate.WATCH

    return RefiGate.PASS


def grade_refi_margin(
    margin_pct: float,
    policy: RefiPathPolicy,
) -> RefiMarginGrade:
    if margin_pct < 0:
        return RefiMarginGrade.NEGATIVE
    if margin_pct >= policy.pass_thick_margin_pct:
        return RefiMarginGrade.FAT
    if margin_pct >= policy.pass_adequate_margin_pct:
        return RefiMarginGrade.ADEQUATE
    return RefiMarginGrade.THIN


def detect_first_breach_driver(
    path: Sequence[MonthlyRefiPathPoint],
    policy: RefiPathPolicy,
) -> Optional[str]:
    for point in path:
        if point.refi_gap_pct_after_cure >= policy.drop_gap_pct:
            return f"REFI_GAP_DROP_LEVEL_MONTH_{point.month}"
        if point.refi_gap_pct_after_cure >= policy.hold_gap_pct:
            return f"REFI_GAP_HOLD_LEVEL_MONTH_{point.month}"
        if "MARKET_CLOSED" in point.flags:
            return f"MARKET_CLOSED_MONTH_{point.month}"
        if "FUND_LIFE_CONSTRAINT" in point.flags:
            return f"FUND_LIFE_CONSTRAINT_MONTH_{point.month}"
        if "DSRA_BELOW_WATCH_THRESHOLD" in point.flags:
            return f"DSRA_BELOW_THRESHOLD_MONTH_{point.month}"
        if "LTC_HOLD_LEVEL" in point.flags:
            return f"LTC_HOLD_LEVEL_MONTH_{point.month}"
    return None


def calculate_hard_equity_shortfall(
    maturity_point: MonthlyRefiPathPoint,
    refi_input: RefiPathInput,
) -> float:
    cure = refi_input.cure
    committed_cure = 0.0

    if cure.cure_committed or cure.sponsor_cure_confirmed:
        committed_cure += cure.borrower_cash_paydown_capacity
        committed_cure += cure.sponsor_equity_cure_capacity
        committed_cure += cure.asset_sale_paydown_capacity

    return max(0.0, maturity_point.refi_gap_before_cure - committed_cure)


def analyze_evidence_package(
    evidence_package: Optional[Mapping[str, Any]],
) -> Tuple[List[str], List[str], InputRelianceLevel]:
    if not evidence_package:
        return [], [], InputRelianceLevel.BASE_CASE

    blockers: List[str] = []
    warnings: List[str] = []

    gate = str(evidence_package.get("gate", "")).upper()

    for item in evidence_package.get("blockers", []) or []:
        blockers.append(extract_issue_code(item))
    for item in evidence_package.get("warnings", []) or []:
        warnings.append(extract_issue_code(item))

    if gate == "REJECT":
        blockers.append("EVIDENCE_GATE_REJECT")
        return blockers, warnings, InputRelianceLevel.REJECTED

    if gate == "HOLD":
        blockers.append("EVIDENCE_GATE_HOLD")

    base_inputs = evidence_package.get("base_case_inputs", {}) or {}
    stress_inputs = evidence_package.get("stress_case_inputs", {}) or {}
    tail_inputs = evidence_package.get("tail_only_inputs", {}) or {}
    internal_inputs = evidence_package.get("internal_review_inputs", {}) or {}

    if tail_inputs:
        return blockers, warnings, InputRelianceLevel.TAIL_ONLY
    if internal_inputs:
        return blockers, warnings, InputRelianceLevel.INTERNAL_REVIEW
    if stress_inputs:
        return blockers, warnings, InputRelianceLevel.STRESS_CASE
    if base_inputs:
        return blockers, warnings, InputRelianceLevel.BASE_CASE

    return blockers, warnings, InputRelianceLevel.INTERNAL_REVIEW


def default_refi_path_scenarios(
    reliance_level: InputRelianceLevel,
    evidence_package: Optional[Mapping[str, Any]],
) -> List[RefiPathScenario]:
    penalty = {
        InputRelianceLevel.BASE_CASE: 0.00,
        InputRelianceLevel.STRESS_CASE: 0.05,
        InputRelianceLevel.INTERNAL_REVIEW: 0.10,
        InputRelianceLevel.TAIL_ONLY: 0.15,
        InputRelianceLevel.REJECTED: 0.25,
    }[reliance_level]

    return [
        RefiPathScenario(
            name="BASE_PATH",
            scenario_type=RefiScenarioType.BASE,
            evidence_reliance_penalty=penalty,
        ),
        RefiPathScenario(
            name="MODERATE_STRESS_PATH",
            scenario_type=RefiScenarioType.MODERATE,
            cash_flow_haircut=-0.10,
            value_haircut=-0.10,
            refi_rate_shock=0.01,
            refi_ltv_cap_haircut=-0.05,
            refi_dscr_floor_increase=0.05,
            capex_overrun_pct=0.05,
            market_appetite_override=MarketAppetiteState.SELECTIVE,
            sponsor_cure_haircut=-0.20,
            borrower_cash_haircut=-0.20,
            asset_sale_haircut=-0.20,
            evidence_reliance_penalty=penalty,
        ),
        RefiPathScenario(
            name="SEVERE_STRESS_PATH",
            scenario_type=RefiScenarioType.SEVERE,
            cash_flow_haircut=-0.25,
            value_haircut=-0.25,
            refi_rate_shock=0.025,
            refi_ltv_cap_haircut=-0.15,
            refi_dscr_floor_increase=0.20,
            capex_overrun_pct=0.15,
            market_appetite_override=MarketAppetiteState.WEAK,
            sponsor_cure_haircut=-0.50,
            borrower_cash_haircut=-0.50,
            asset_sale_haircut=-0.50,
            evidence_reliance_penalty=penalty,
        ),
        RefiPathScenario(
            name="TAIL_MATURITY_WALL_PATH",
            scenario_type=RefiScenarioType.TAIL,
            cash_flow_haircut=-0.40,
            value_haircut=-0.40,
            refi_rate_shock=0.04,
            refi_ltv_cap_haircut=-0.30,
            refi_dscr_floor_increase=0.35,
            capex_overrun_pct=0.25,
            market_appetite_override=MarketAppetiteState.CLOSED,
            sponsor_cure_haircut=-0.75,
            borrower_cash_haircut=-0.75,
            asset_sale_haircut=-0.75,
            evidence_reliance_penalty=penalty,
        ),
    ]


def build_memo_summary(
    results: Sequence[RefiPathScenarioResult],
    overall_gate: RefiGate,
) -> Dict[str, Any]:
    if not results:
        return {
            "overall_gate": overall_gate.value,
            "memo_language": "No refi path results available.",
        }

    base = first_result(results, RefiScenarioType.BASE) or results[0]
    moderate = first_result(results, RefiScenarioType.MODERATE)
    severe = first_result(results, RefiScenarioType.SEVERE)
    tail = first_result(results, RefiScenarioType.TAIL)

    worst = max(results, key=lambda x: x.worst_refi_gap_pct)

    return {
        "overall_gate": overall_gate.value,
        "base_refi_gap": base.maturity_refi_gap,
        "base_refi_gap_pct": base.maturity_refi_gap_pct,
        "base_margin_grade": base.refi_margin_grade.value,
        "base_binding_constraint": base.binding_constraint_at_maturity.value,
        "moderate_refi_gap": moderate.maturity_refi_gap if moderate else None,
        "severe_refi_gap": severe.maturity_refi_gap if severe else None,
        "tail_refi_gap": tail.maturity_refi_gap if tail else None,
        "worst_scenario": worst.scenario_name,
        "worst_refi_gap": worst.worst_refi_gap,
        "worst_refi_gap_pct": worst.worst_refi_gap_pct,
        "worst_refi_gap_month": worst.worst_refi_gap_month,
        "earliest_dscr_breach_month": min_optional([x.earliest_dscr_breach_month for x in results]),
        "earliest_dsra_depletion_month": min_optional([x.dsra_depletion_month for x in results]),
        "memo_language": (
            f"Refi path analysis shows a base-case maturity refi gap of "
            f"{base.maturity_refi_gap:,.0f} "
            f"({base.maturity_refi_gap_pct:.1%} of maturity debt), "
            f"with base refi margin graded {base.refi_margin_grade.value}. "
            f"The binding base-case constraint is {base.binding_constraint_at_maturity.value}. "
            f"Under the worst tested path ({worst.scenario_name}), the refi gap reaches "
            f"{worst.worst_refi_gap:,.0f} "
            f"({worst.worst_refi_gap_pct:.1%} of debt) in month {worst.worst_refi_gap_month}. "
            f"Overall refi gate: {overall_gate.value}."
        ),
    }


def normalize_deal_master(raw: Union[DealMaster, Mapping[str, Any]]) -> DealMaster:
    if isinstance(raw, DealMaster):
        return raw
    if isinstance(raw, Mapping):
        return DealMaster.from_mapping(raw)
    raise TypeError("deal_master must be DealMaster or mapping")


def normalize_refi_path_input(raw: Union[RefiPathInput, Mapping[str, Any]]) -> RefiPathInput:
    if isinstance(raw, RefiPathInput):
        return raw
    if isinstance(raw, Mapping):
        return RefiPathInput.from_mapping(raw)
    raise TypeError("refi_path_input must be RefiPathInput or mapping")


def normalize_policy(raw: Optional[Union[RefiPathPolicy, Mapping[str, Any]]]) -> RefiPathPolicy:
    if raw is None:
        return RefiPathPolicy()
    if isinstance(raw, RefiPathPolicy):
        return raw
    if isinstance(raw, Mapping):
        return RefiPathPolicy.from_mapping(raw)
    raise TypeError("policy must be RefiPathPolicy, mapping, or None")


def normalize_scenarios(
    raw: Optional[Sequence[Union[RefiPathScenario, Mapping[str, Any]]]]
) -> List[RefiPathScenario]:
    if not raw:
        return []

    out: List[RefiPathScenario] = []
    for item in raw:
        if isinstance(item, RefiPathScenario):
            out.append(item)
        elif isinstance(item, Mapping):
            out.append(RefiPathScenario.from_mapping(item))
        else:
            raise TypeError("scenarios must contain RefiPathScenario or mapping")
    return out


def set_input_reliance_level(
    refi_input: RefiPathInput,
    reliance_level: InputRelianceLevel,
) -> RefiPathInput:
    return RefiPathInput(
        debt=refi_input.debt,
        cash_flow=refi_input.cash_flow,
        value=refi_input.value,
        refi_terms=refi_input.refi_terms,
        dsra=refi_input.dsra,
        cost_basis=refi_input.cost_basis,
        cure=refi_input.cure,
        market=refi_input.market,
        input_reliance_level=reliance_level,
        extra=refi_input.extra,
    )


def first_result(
    results: Sequence[RefiPathScenarioResult],
    scenario_type: RefiScenarioType,
) -> Optional[RefiPathScenarioResult]:
    return next((x for x in results if x.scenario_type == scenario_type), None)


def parse_enum(enum_cls: Any, value: Any, default: Any) -> Any:
    if isinstance(value, enum_cls):
        return value
    if value is None:
        return default
    try:
        return enum_cls(str(value))
    except ValueError:
        return default


def parse_optional_enum(enum_cls: Any, value: Any) -> Optional[Any]:
    if value is None:
        return None
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(str(value))
    except ValueError:
        return None


def to_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def safe_div(numerator: float, denominator: float, fallback: Any = 0.0) -> Any:
    if denominator == 0:
        return fallback
    return numerator / denominator


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def extract_issue_code(item: Any) -> str:
    if isinstance(item, Mapping):
        return str(item.get("code", "UNKNOWN_ISSUE"))
    return str(item)


def min_optional(values: Sequence[Optional[int]]) -> Optional[int]:
    clean = [x for x in values if x is not None]
    return min(clean) if clean else None

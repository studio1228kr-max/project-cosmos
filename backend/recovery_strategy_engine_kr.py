from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union
from datetime import date
import math


class RecoveryGate(str, Enum):
    PASS = "PASS"
    WATCH = "WATCH"
    HOLD = "HOLD"
    DROP = "DROP"


class RecoveryScenarioType(str, Enum):
    BASE = "BASE"
    DOWNSIDE = "DOWNSIDE"
    SEVERE = "SEVERE"
    TAIL = "TAIL"


class KoreaRecoveryStrategyType(str, Enum):
    NEGOTIATED_SALE = "NEGOTIATED_SALE"
    COURT_AUCTION = "COURT_AUCTION"
    PUBLIC_AUCTION = "PUBLIC_AUCTION"
    NOTE_SALE = "NOTE_SALE"
    PRIVATE_WORKOUT = "PRIVATE_WORKOUT"
    GOING_CONCERN_SALE = "GOING_CONCERN_SALE"
    RECEIVERSHIP_STYLE = "RECEIVERSHIP_STYLE"


class KoreaClaimType(str, Enum):
    ENFORCEMENT_COST = "ENFORCEMENT_COST"
    COURT_COST = "COURT_COST"
    ADMIN_EXPENSE = "ADMIN_EXPENSE"
    NATIONAL_TAX = "NATIONAL_TAX"
    LOCAL_TAX = "LOCAL_TAX"
    WAGE_PRIORITY = "WAGE_PRIORITY"
    RETIREMENT_BENEFIT_PRIORITY = "RETIREMENT_BENEFIT_PRIORITY"
    COMMERCIAL_TENANT_DEPOSIT = "COMMERCIAL_TENANT_DEPOSIT"
    RESIDENTIAL_TENANT_DEPOSIT = "RESIDENTIAL_TENANT_DEPOSIT"
    JEONSE_RIGHT = "JEONSE_RIGHT"
    OCCUPANCY_SETTLEMENT = "OCCUPANCY_SETTLEMENT"
    TRUST_BENEFICIARY_CLAIM = "TRUST_BENEFICIARY_CLAIM"
    SENIOR_MORTGAGE = "SENIOR_MORTGAGE"
    TARGET_FACILITY = "TARGET_FACILITY"
    PARI_PASSU_SECURED = "PARI_PASSU_SECURED"
    JUNIOR_MORTGAGE = "JUNIOR_MORTGAGE"
    PLEDGE_OR_SHARE_SECURITY = "PLEDGE_OR_SHARE_SECURITY"
    TRADE_CLAIM = "TRADE_CLAIM"
    UNSECURED = "UNSECURED"
    EQUITY = "EQUITY"
    CONTINGENT_PRIORITY = "CONTINGENT_PRIORITY"
    UNKNOWN_CLAIM = "UNKNOWN_CLAIM"


class KoreaCollateralType(str, Enum):
    REAL_ESTATE = "REAL_ESTATE"
    LAND = "LAND"
    BUILDING = "BUILDING"
    COMMERCIAL_BUILDING = "COMMERCIAL_BUILDING"
    RESIDENTIAL_BUILDING = "RESIDENTIAL_BUILDING"
    DEVELOPMENT_PROJECT = "DEVELOPMENT_PROJECT"
    NPL_CLAIM = "NPL_CLAIM"
    OPERATING_BUSINESS = "OPERATING_BUSINESS"
    SHARES = "SHARES"
    RECEIVABLES = "RECEIVABLES"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    LEASE_DEPOSIT_CLAIM = "LEASE_DEPOSIT_CLAIM"
    OTHER = "OTHER"


class CollateralLiquidity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    FROZEN = "FROZEN"


class LegalVerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    COUNSEL_REVIEWED = "COUNSEL_REVIEWED"
    PENDING = "PENDING"
    UNVERIFIED = "UNVERIFIED"
    DISPUTED = "DISPUTED"


class InputRelianceLevel(str, Enum):
    BASE_CASE = "BASE_CASE"
    STRESS_CASE = "STRESS_CASE"
    TAIL_ONLY = "TAIL_ONLY"
    INTERNAL_REVIEW = "INTERNAL_REVIEW"
    REJECTED = "REJECTED"


class BindingRecoveryConstraint(str, Enum):
    COLLATERAL_VALUE = "COLLATERAL_VALUE"
    KOREA_PRIORITY_CLAIMS = "KOREA_PRIORITY_CLAIMS"
    TAX_OR_WAGE_PRIORITY = "TAX_OR_WAGE_PRIORITY"
    TENANT_DEPOSIT = "TENANT_DEPOSIT"
    SENIOR_LIEN = "SENIOR_LIEN"
    ENFORCEMENT_COST = "ENFORCEMENT_COST"
    LEGAL_DELAY = "LEGAL_DELAY"
    OCCUPANCY_OR_EVICTION = "OCCUPANCY_OR_EVICTION"
    MARKET_LIQUIDITY = "MARKET_LIQUIDITY"
    TITLE_OR_PERFECTION = "TITLE_OR_PERFECTION"
    STRATEGY_FAILURE = "STRATEGY_FAILURE"
    NONE = "NONE"


@dataclass(frozen=True)
class DealMaster:
    deal_id: str
    deal_name: str
    asset_class: str
    deal_type: str

    currency: str = "KRW"
    jurisdiction: str = "KR"
    borrower: Optional[str] = None
    sponsor: Optional[str] = None
    strategy: Optional[str] = None

    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "DealMaster":
        required = {"deal_id", "deal_name", "asset_class", "deal_type"}
        missing = required - set(raw.keys())
        if missing:
            raise ValueError(f"deal_master missing required fields: {sorted(missing)}")

        known = {
            "deal_id", "deal_name", "asset_class", "deal_type",
            "currency", "jurisdiction", "borrower", "sponsor", "strategy",
        }

        return cls(
            deal_id=str(raw["deal_id"]),
            deal_name=str(raw["deal_name"]),
            asset_class=str(raw["asset_class"]),
            deal_type=str(raw["deal_type"]),
            currency=str(raw.get("currency", "KRW")),
            jurisdiction=str(raw.get("jurisdiction", "KR")),
            borrower=raw.get("borrower"),
            sponsor=raw.get("sponsor"),
            strategy=raw.get("strategy"),
            extra={k: v for k, v in raw.items() if k not in known},
        )


@dataclass(frozen=True)
class KoreaCollateralAsset:
    collateral_id: str
    collateral_name: str
    collateral_type: KoreaCollateralType

    base_value: float

    base_liquidation_haircut: float = 0.10
    forced_sale_haircut: float = 0.00
    liquidity: CollateralLiquidity = CollateralLiquidity.MEDIUM

    auction_failed_rounds: int = 0
    auction_round_haircut: float = 0.10

    vacancy_or_eviction_cost: float = 0.0
    eviction_delay_months: int = 0

    illegal_building_or_violation: bool = False
    violation_cure_cost: float = 0.0
    violation_value_haircut: float = 0.0

    maintenance_arrears: float = 0.0
    unpaid_public_charges: float = 0.0

    asset_specific_cost: float = 0.0
    expected_sale_months: int = 12

    eligible_proceeds_pct: float = 1.0

    legal_status: LegalVerificationStatus = LegalVerificationStatus.PENDING
    evidence_score: Optional[float] = None

    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "KoreaCollateralAsset":
        return cls(
            collateral_id=str(raw["collateral_id"]),
            collateral_name=str(raw.get("collateral_name", raw["collateral_id"])),
            collateral_type=parse_enum(
                KoreaCollateralType,
                raw.get("collateral_type"),
                KoreaCollateralType.OTHER,
            ),
            base_value=float(raw["base_value"]),
            base_liquidation_haircut=float(raw.get("base_liquidation_haircut", 0.10)),
            forced_sale_haircut=float(raw.get("forced_sale_haircut", 0.00)),
            liquidity=parse_enum(
                CollateralLiquidity,
                raw.get("liquidity"),
                CollateralLiquidity.MEDIUM,
            ),
            auction_failed_rounds=int(raw.get("auction_failed_rounds", 0)),
            auction_round_haircut=float(raw.get("auction_round_haircut", 0.10)),
            vacancy_or_eviction_cost=float(raw.get("vacancy_or_eviction_cost", 0.0)),
            eviction_delay_months=int(raw.get("eviction_delay_months", 0)),
            illegal_building_or_violation=bool(raw.get("illegal_building_or_violation", False)),
            violation_cure_cost=float(raw.get("violation_cure_cost", 0.0)),
            violation_value_haircut=float(raw.get("violation_value_haircut", 0.0)),
            maintenance_arrears=float(raw.get("maintenance_arrears", 0.0)),
            unpaid_public_charges=float(raw.get("unpaid_public_charges", 0.0)),
            asset_specific_cost=float(raw.get("asset_specific_cost", 0.0)),
            expected_sale_months=int(raw.get("expected_sale_months", 12)),
            eligible_proceeds_pct=float(raw.get("eligible_proceeds_pct", 1.0)),
            legal_status=parse_enum(
                LegalVerificationStatus,
                raw.get("legal_status"),
                LegalVerificationStatus.PENDING,
            ),
            evidence_score=to_optional_float(raw.get("evidence_score")),
            extra=dict(raw.get("extra", {})),
        )


@dataclass(frozen=True)
class KoreaClaimLine:
    claim_id: str
    claim_name: str
    claim_type: KoreaClaimType
    amount: float

    contractual_priority_rank: int

    legal_priority_rank: Optional[int] = None
    collateral_specific_rank: Optional[int] = None

    registration_date: Optional[date] = None
    legal_due_date: Optional[date] = None
    fixed_date: Optional[date] = None
    occupancy_or_delivery_date: Optional[date] = None

    senior_to_target: bool = False
    pari_passu_with_target: bool = False

    collateral_ids: List[str] = field(default_factory=list)

    is_target: bool = False
    secured: bool = True

    verified_amount: Optional[float] = None
    contingent_amount: float = 0.0

    legal_status: LegalVerificationStatus = LegalVerificationStatus.PENDING
    evidence_score: Optional[float] = None

    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "KoreaClaimLine":
        return cls(
            claim_id=str(raw["claim_id"]),
            claim_name=str(raw.get("claim_name", raw["claim_id"])),
            claim_type=parse_enum(
                KoreaClaimType,
                raw.get("claim_type"),
                KoreaClaimType.UNKNOWN_CLAIM,
            ),
            amount=float(raw["amount"]),
            contractual_priority_rank=int(raw.get("contractual_priority_rank", raw.get("priority_rank", 99))),
            legal_priority_rank=to_optional_int(raw.get("legal_priority_rank")),
            collateral_specific_rank=to_optional_int(raw.get("collateral_specific_rank")),
            registration_date=parse_date(raw.get("registration_date")),
            legal_due_date=parse_date(raw.get("legal_due_date")),
            fixed_date=parse_date(raw.get("fixed_date")),
            occupancy_or_delivery_date=parse_date(raw.get("occupancy_or_delivery_date")),
            senior_to_target=bool(raw.get("senior_to_target", False)),
            pari_passu_with_target=bool(raw.get("pari_passu_with_target", False)),
            collateral_ids=list(raw.get("collateral_ids", [])),
            is_target=bool(raw.get("is_target", False)),
            secured=bool(raw.get("secured", True)),
            verified_amount=to_optional_float(raw.get("verified_amount")),
            contingent_amount=float(raw.get("contingent_amount", 0.0)),
            legal_status=parse_enum(
                LegalVerificationStatus,
                raw.get("legal_status"),
                LegalVerificationStatus.PENDING,
            ),
            evidence_score=to_optional_float(raw.get("evidence_score")),
            extra=dict(raw.get("extra", {})),
        )


@dataclass(frozen=True)
class KoreaEnforcementPath:
    strategy_type: KoreaRecoveryStrategyType

    base_duration_months: int
    base_cost_pct: float
    base_cost_fixed: float = 0.0

    court_delay_probability: float = 0.0
    failed_auction_probability: float = 0.0
    legal_challenge_probability: float = 0.0
    injunction_or_stay_probability: float = 0.0

    bidder_depth_score: float = 0.50
    marketability_score: float = 0.50

    discount_rate: float = 0.12

    requires_borrower_cooperation: bool = False
    requires_sponsor_cooperation: bool = False
    requires_tenant_vacancy: bool = False

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "KoreaEnforcementPath":
        return cls(
            strategy_type=parse_enum(
                KoreaRecoveryStrategyType,
                raw.get("strategy_type"),
                KoreaRecoveryStrategyType.COURT_AUCTION,
            ),
            base_duration_months=int(raw.get("base_duration_months", 12)),
            base_cost_pct=float(raw.get("base_cost_pct", 0.08)),
            base_cost_fixed=float(raw.get("base_cost_fixed", 0.0)),
            court_delay_probability=float(raw.get("court_delay_probability", 0.0)),
            failed_auction_probability=float(raw.get("failed_auction_probability", 0.0)),
            legal_challenge_probability=float(raw.get("legal_challenge_probability", 0.0)),
            injunction_or_stay_probability=float(raw.get("injunction_or_stay_probability", 0.0)),
            bidder_depth_score=float(raw.get("bidder_depth_score", 0.50)),
            marketability_score=float(raw.get("marketability_score", 0.50)),
            discount_rate=float(raw.get("discount_rate", 0.12)),
            requires_borrower_cooperation=bool(raw.get("requires_borrower_cooperation", False)),
            requires_sponsor_cooperation=bool(raw.get("requires_sponsor_cooperation", False)),
            requires_tenant_vacancy=bool(raw.get("requires_tenant_vacancy", False)),
        )


@dataclass(frozen=True)
class KoreaSupportSource:
    support_id: str
    support_type: str
    amount: float

    legally_enforceable: bool = False
    committed: bool = False
    collection_probability: float = 0.50
    expected_collection_months: int = 12
    counterparty_credit_score: Optional[float] = None

    collateral_ids: List[str] = field(default_factory=list)
    claim_ids: List[str] = field(default_factory=list)

    legal_status: LegalVerificationStatus = LegalVerificationStatus.PENDING
    evidence_score: Optional[float] = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "KoreaSupportSource":
        return cls(
            support_id=str(raw["support_id"]),
            support_type=str(raw.get("support_type", "GENERIC_SUPPORT")),
            amount=float(raw["amount"]),
            legally_enforceable=bool(raw.get("legally_enforceable", False)),
            committed=bool(raw.get("committed", False)),
            collection_probability=float(raw.get("collection_probability", 0.50)),
            expected_collection_months=int(raw.get("expected_collection_months", 12)),
            counterparty_credit_score=to_optional_float(raw.get("counterparty_credit_score")),
            collateral_ids=list(raw.get("collateral_ids", [])),
            claim_ids=list(raw.get("claim_ids", [])),
            legal_status=parse_enum(
                LegalVerificationStatus,
                raw.get("legal_status"),
                LegalVerificationStatus.PENDING,
            ),
            evidence_score=to_optional_float(raw.get("evidence_score")),
        )


@dataclass(frozen=True)
class KoreaRecoveryInput:
    target_ead: float
    target_claim_id: str

    collateral_assets: List[KoreaCollateralAsset]
    claim_stack: List[KoreaClaimLine]
    enforcement_paths: List[KoreaEnforcementPath]

    support_sources: List[KoreaSupportSource] = field(default_factory=list)

    input_reliance_level: InputRelianceLevel = InputRelianceLevel.BASE_CASE

    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "KoreaRecoveryInput":
        return cls(
            target_ead=float(raw["target_ead"]),
            target_claim_id=str(raw["target_claim_id"]),
            collateral_assets=[
                KoreaCollateralAsset.from_mapping(x)
                for x in raw.get("collateral_assets", [])
            ],
            claim_stack=[
                KoreaClaimLine.from_mapping(x)
                for x in raw.get("claim_stack", [])
            ],
            enforcement_paths=[
                KoreaEnforcementPath.from_mapping(x)
                for x in raw.get("enforcement_paths", [])
            ],
            support_sources=[
                KoreaSupportSource.from_mapping(x)
                for x in raw.get("support_sources", [])
            ],
            input_reliance_level=parse_enum(
                InputRelianceLevel,
                raw.get("input_reliance_level"),
                InputRelianceLevel.BASE_CASE,
            ),
            extra=dict(raw.get("extra", {})),
        )


@dataclass(frozen=True)
class KoreaRecoveryScenario:
    name: str
    scenario_type: RecoveryScenarioType

    collateral_value_haircut: float = 0.0
    additional_forced_sale_haircut: float = 0.0

    enforcement_cost_multiplier: float = 1.0
    duration_multiplier: float = 1.0

    tax_claim_multiplier: float = 1.0
    wage_claim_multiplier: float = 1.0
    tenant_deposit_multiplier: float = 1.0
    senior_claim_multiplier: float = 1.0

    support_value_haircut: float = 0.0
    support_collection_probability_haircut: float = 0.0

    liquidity_override: Optional[CollateralLiquidity] = None

    evidence_reliance_penalty: float = 0.0

    legal_blocker: bool = False
    title_or_perfection_issue: bool = False
    refi_failure_forced_sale: bool = False

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "KoreaRecoveryScenario":
        return cls(
            name=str(raw["name"]),
            scenario_type=parse_enum(
                RecoveryScenarioType,
                raw.get("scenario_type"),
                RecoveryScenarioType.BASE,
            ),
            collateral_value_haircut=float(raw.get("collateral_value_haircut", 0.0)),
            additional_forced_sale_haircut=float(raw.get("additional_forced_sale_haircut", 0.0)),
            enforcement_cost_multiplier=float(raw.get("enforcement_cost_multiplier", 1.0)),
            duration_multiplier=float(raw.get("duration_multiplier", 1.0)),
            tax_claim_multiplier=float(raw.get("tax_claim_multiplier", 1.0)),
            wage_claim_multiplier=float(raw.get("wage_claim_multiplier", 1.0)),
            tenant_deposit_multiplier=float(raw.get("tenant_deposit_multiplier", 1.0)),
            senior_claim_multiplier=float(raw.get("senior_claim_multiplier", 1.0)),
            support_value_haircut=float(raw.get("support_value_haircut", 0.0)),
            support_collection_probability_haircut=float(raw.get("support_collection_probability_haircut", 0.0)),
            liquidity_override=parse_optional_enum(
                CollateralLiquidity,
                raw.get("liquidity_override"),
            ),
            evidence_reliance_penalty=float(raw.get("evidence_reliance_penalty", 0.0)),
            legal_blocker=bool(raw.get("legal_blocker", False)),
            title_or_perfection_issue=bool(raw.get("title_or_perfection_issue", False)),
            refi_failure_forced_sale=bool(raw.get("refi_failure_forced_sale", False)),
        )


@dataclass(frozen=True)
class KoreaRecoveryPolicy:
    min_pv_recovery_rate_for_pass: float = 1.00
    min_pv_recovery_rate_for_watch: float = 0.90
    min_pv_recovery_rate_for_hold: float = 0.80

    max_pv_lgd_for_pass: float = 0.00
    max_pv_lgd_for_watch: float = 0.10
    max_pv_lgd_for_hold: float = 0.20

    max_duration_months_for_pass: int = 18
    max_duration_months_for_watch: int = 30

    unverified_priority_claims_force_hold: bool = True
    unverified_senior_lien_force_hold: bool = True
    title_issue_force_hold: bool = True
    legal_blocker_force_hold: bool = True
    evidence_blockers_force_hold: bool = True

    uncommitted_support_blocks_pass: bool = True

    tail_lgd_drop_threshold: float = 0.25
    tail_recovery_hold_threshold: float = 0.90

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "KoreaRecoveryPolicy":
        return cls(
            min_pv_recovery_rate_for_pass=float(raw.get("min_pv_recovery_rate_for_pass", 1.00)),
            min_pv_recovery_rate_for_watch=float(raw.get("min_pv_recovery_rate_for_watch", 0.90)),
            min_pv_recovery_rate_for_hold=float(raw.get("min_pv_recovery_rate_for_hold", 0.80)),
            max_pv_lgd_for_pass=float(raw.get("max_pv_lgd_for_pass", 0.00)),
            max_pv_lgd_for_watch=float(raw.get("max_pv_lgd_for_watch", 0.10)),
            max_pv_lgd_for_hold=float(raw.get("max_pv_lgd_for_hold", 0.20)),
            max_duration_months_for_pass=int(raw.get("max_duration_months_for_pass", 18)),
            max_duration_months_for_watch=int(raw.get("max_duration_months_for_watch", 30)),
            unverified_priority_claims_force_hold=bool(raw.get("unverified_priority_claims_force_hold", True)),
            unverified_senior_lien_force_hold=bool(raw.get("unverified_senior_lien_force_hold", True)),
            title_issue_force_hold=bool(raw.get("title_issue_force_hold", True)),
            legal_blocker_force_hold=bool(raw.get("legal_blocker_force_hold", True)),
            evidence_blockers_force_hold=bool(raw.get("evidence_blockers_force_hold", True)),
            uncommitted_support_blocks_pass=bool(raw.get("uncommitted_support_blocks_pass", True)),
            tail_lgd_drop_threshold=float(raw.get("tail_lgd_drop_threshold", 0.25)),
            tail_recovery_hold_threshold=float(raw.get("tail_recovery_hold_threshold", 0.90)),
        )


@dataclass(frozen=True)
class KoreaCollateralRecovery:
    collateral_id: str
    collateral_name: str
    collateral_type: KoreaCollateralType

    base_value: float
    stressed_value: float

    liquidity: CollateralLiquidity
    liquidation_haircut: float
    auction_failure_haircut: float
    forced_sale_haircut: float
    violation_haircut: float

    gross_recovery_value: float

    vacancy_or_eviction_cost: float
    violation_cure_cost: float
    maintenance_arrears: float
    unpaid_public_charges: float
    asset_specific_cost: float

    net_recovery_value: float
    expected_sale_months: int

    legal_status: LegalVerificationStatus
    evidence_score: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["collateral_type"] = self.collateral_type.value
        data["liquidity"] = self.liquidity.value
        data["legal_status"] = self.legal_status.value
        return data


@dataclass(frozen=True)
class KoreaClaimAllocation:
    claim_id: str
    claim_name: str
    claim_type: KoreaClaimType

    amount: float
    effective_amount: float

    waterfall_rank: int
    recovery_amount: float
    unrecovered_amount: float
    recovery_rate: float
    lgd: float

    is_target: bool
    legal_status: LegalVerificationStatus
    senior_to_target: bool
    pari_passu_with_target: bool

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["claim_type"] = self.claim_type.value
        data["legal_status"] = self.legal_status.value
        return data


@dataclass(frozen=True)
class LGDDecomposition:
    starting_target_ead: float

    collateral_value_loss: float
    liquidation_haircut_loss: float
    auction_failure_loss: float
    violation_or_cure_loss: float
    eviction_and_occupancy_loss: float
    enforcement_cost_loss: float
    priority_claim_loss: float
    senior_claim_loss: float
    time_discount_loss: float
    support_shortfall_loss: float

    final_pv_loss: float
    final_pv_lgd: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KoreaStrategyResult:
    strategy_type: KoreaRecoveryStrategyType
    scenario_name: str
    scenario_type: RecoveryScenarioType

    gate: RecoveryGate
    binding_constraint: BindingRecoveryConstraint

    collateral_recoveries: List[KoreaCollateralRecovery]
    claim_allocations: List[KoreaClaimAllocation]

    gross_collateral_value: float
    gross_recovery_value: float
    net_recovery_pool: float

    committed_support_value: float
    uncommitted_support_value: float

    target_ead: float
    target_nominal_recovery: float
    target_pv_recovery: float
    target_unrecovered: float

    target_nominal_recovery_rate: float
    target_pv_recovery_rate: float
    target_lgd: float
    target_pv_lgd: float

    duration_months: int
    discount_rate: float

    lgd_decomposition: LGDDecomposition

    flags: List[str]
    required_actions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_type": self.strategy_type.value,
            "scenario_name": self.scenario_name,
            "scenario_type": self.scenario_type.value,
            "gate": self.gate.value,
            "binding_constraint": self.binding_constraint.value,
            "collateral_recoveries": [x.to_dict() for x in self.collateral_recoveries],
            "claim_allocations": [x.to_dict() for x in self.claim_allocations],
            "gross_collateral_value": self.gross_collateral_value,
            "gross_recovery_value": self.gross_recovery_value,
            "net_recovery_pool": self.net_recovery_pool,
            "committed_support_value": self.committed_support_value,
            "uncommitted_support_value": self.uncommitted_support_value,
            "target_ead": self.target_ead,
            "target_nominal_recovery": self.target_nominal_recovery,
            "target_pv_recovery": self.target_pv_recovery,
            "target_unrecovered": self.target_unrecovered,
            "target_nominal_recovery_rate": self.target_nominal_recovery_rate,
            "target_pv_recovery_rate": self.target_pv_recovery_rate,
            "target_lgd": self.target_lgd,
            "target_pv_lgd": self.target_pv_lgd,
            "duration_months": self.duration_months,
            "discount_rate": self.discount_rate,
            "lgd_decomposition": self.lgd_decomposition.to_dict(),
            "flags": self.flags,
            "required_actions": self.required_actions,
        }


@dataclass(frozen=True)
class KoreaRecoveryPackage:
    deal_master: DealMaster
    overall_gate: RecoveryGate

    strategy_results: List[KoreaStrategyResult]

    best_strategy: Optional[KoreaRecoveryStrategyType]
    base_strategy: Optional[KoreaRecoveryStrategyType]
    worst_strategy: Optional[KoreaRecoveryStrategyType]

    best_pv_recovery_rate: float
    worst_pv_lgd: float

    evidence_reliance_level: InputRelianceLevel
    evidence_blockers: List[str]
    evidence_warnings: List[str]

    refi_failure_triggered: bool
    refi_gap_amount: Optional[float]
    refi_binding_constraint: Optional[str]

    memo_summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_master": asdict(self.deal_master),
            "overall_gate": self.overall_gate.value,
            "strategy_results": [x.to_dict() for x in self.strategy_results],
            "best_strategy": self.best_strategy.value if self.best_strategy else None,
            "base_strategy": self.base_strategy.value if self.base_strategy else None,
            "worst_strategy": self.worst_strategy.value if self.worst_strategy else None,
            "best_pv_recovery_rate": self.best_pv_recovery_rate,
            "worst_pv_lgd": self.worst_pv_lgd,
            "evidence_reliance_level": self.evidence_reliance_level.value,
            "evidence_blockers": self.evidence_blockers,
            "evidence_warnings": self.evidence_warnings,
            "refi_failure_triggered": self.refi_failure_triggered,
            "refi_gap_amount": self.refi_gap_amount,
            "refi_binding_constraint": self.refi_binding_constraint,
            "memo_summary": self.memo_summary,
        }


def evaluate_korea_recovery_strategy_engine(
    deal_master: Union[DealMaster, Mapping[str, Any]],
    recovery_input: Union[KoreaRecoveryInput, Mapping[str, Any]],
    scenarios: Optional[Sequence[Union[KoreaRecoveryScenario, Mapping[str, Any]]]] = None,
    policy: Optional[Union[KoreaRecoveryPolicy, Mapping[str, Any]]] = None,
    evidence_package: Optional[Mapping[str, Any]] = None,
    refi_path_package: Optional[Mapping[str, Any]] = None,
) -> KoreaRecoveryPackage:
    dm = normalize_deal_master(deal_master)
    rec_input = normalize_recovery_input(recovery_input)
    rec_policy = normalize_policy(policy)

    evidence_blockers, evidence_warnings, reliance_level = analyze_evidence_package(evidence_package)
    rec_input = set_input_reliance_level(rec_input, reliance_level)

    refi_trigger = analyze_refi_path_package(refi_path_package)

    scenario_list = normalize_scenarios(scenarios)
    if not scenario_list:
        scenario_list = default_korea_recovery_scenarios(
            reliance_level=reliance_level,
            refi_failure_triggered=bool(refi_trigger["refi_failure_triggered"]),
            refi_binding_constraint=refi_trigger.get("refi_binding_constraint"),
        )

    strategy_results: List[KoreaStrategyResult] = []

    for scenario in scenario_list:
        for path in rec_input.enforcement_paths:
            result = run_korea_recovery_strategy(
                recovery_input=rec_input,
                enforcement_path=path,
                scenario=scenario,
                policy=rec_policy,
                evidence_blockers=evidence_blockers,
                refi_trigger=refi_trigger,
            )
            strategy_results.append(result)

    overall_gate = aggregate_gate(strategy_results, evidence_blockers, rec_policy)

    best = max(strategy_results, key=lambda x: x.target_pv_recovery_rate) if strategy_results else None
    worst = max(strategy_results, key=lambda x: x.target_pv_lgd) if strategy_results else None

    base_candidates = [
        x for x in strategy_results
        if x.scenario_type == RecoveryScenarioType.BASE
    ]
    base = max(base_candidates, key=lambda x: x.target_pv_recovery_rate) if base_candidates else None

    return KoreaRecoveryPackage(
        deal_master=dm,
        overall_gate=overall_gate,
        strategy_results=strategy_results,
        best_strategy=best.strategy_type if best else None,
        base_strategy=base.strategy_type if base else None,
        worst_strategy=worst.strategy_type if worst else None,
        best_pv_recovery_rate=round(best.target_pv_recovery_rate, 6) if best else 0.0,
        worst_pv_lgd=round(worst.target_pv_lgd, 6) if worst else 0.0,
        evidence_reliance_level=reliance_level,
        evidence_blockers=sorted(set(evidence_blockers)),
        evidence_warnings=sorted(set(evidence_warnings)),
        refi_failure_triggered=bool(refi_trigger["refi_failure_triggered"]),
        refi_gap_amount=refi_trigger.get("refi_gap_amount"),
        refi_binding_constraint=refi_trigger.get("refi_binding_constraint"),
        memo_summary=build_memo_summary(strategy_results, overall_gate, refi_trigger),
    )


def run_korea_recovery_strategy(
    recovery_input: KoreaRecoveryInput,
    enforcement_path: KoreaEnforcementPath,
    scenario: KoreaRecoveryScenario,
    policy: KoreaRecoveryPolicy,
    evidence_blockers: Sequence[str],
    refi_trigger: Mapping[str, Any],
) -> KoreaStrategyResult:
    collateral_recoveries = [
        calculate_korea_collateral_recovery(asset, enforcement_path, scenario)
        for asset in recovery_input.collateral_assets
    ]

    gross_collateral_value = sum(x.stressed_value for x in collateral_recoveries)
    gross_recovery_value = sum(x.net_recovery_value for x in collateral_recoveries)

    duration_months = calculate_strategy_duration(
        collateral_recoveries=collateral_recoveries,
        enforcement_path=enforcement_path,
        scenario=scenario,
    )

    enforcement_cost = calculate_strategy_enforcement_cost(
        gross_recovery_value=gross_recovery_value,
        enforcement_path=enforcement_path,
        scenario=scenario,
    )

    adjusted_claims = adjust_korea_claims(
        claims=recovery_input.claim_stack,
        scenario=scenario,
    )

    support_committed, support_uncommitted = calculate_korea_support(
        support_sources=recovery_input.support_sources,
        scenario=scenario,
    )

    net_recovery_pool = max(0.0, gross_recovery_value - enforcement_cost)

    claim_allocations = allocate_korea_waterfall(
        claims=adjusted_claims,
        available_pool=net_recovery_pool + support_committed + support_uncommitted,
        target_claim_id=recovery_input.target_claim_id,
    )

    target = find_target_allocation(claim_allocations, recovery_input.target_claim_id)

    target_nominal_recovery = target.recovery_amount if target else 0.0
    target_ead = recovery_input.target_ead

    pv_factor = 1 / ((1 + enforcement_path.discount_rate) ** (duration_months / 12.0))
    target_pv_recovery = target_nominal_recovery * pv_factor

    target_nominal_recovery_rate = safe_div(target_nominal_recovery, target_ead, fallback=0.0)
    target_pv_recovery_rate = safe_div(target_pv_recovery, target_ead, fallback=0.0)

    target_lgd = 1 - min(1.0, target_nominal_recovery_rate)
    target_pv_lgd = 1 - min(1.0, target_pv_recovery_rate)

    flags, actions, binding = build_flags_actions_binding(
        recovery_input=recovery_input,
        collateral_recoveries=collateral_recoveries,
        claim_allocations=claim_allocations,
        enforcement_path=enforcement_path,
        scenario=scenario,
        policy=policy,
        evidence_blockers=evidence_blockers,
        refi_trigger=refi_trigger,
        target_pv_recovery_rate=target_pv_recovery_rate,
        target_pv_lgd=target_pv_lgd,
        duration_months=duration_months,
        support_committed=support_committed,
        support_uncommitted=support_uncommitted,
    )

    gate = determine_strategy_gate(
        target_pv_recovery_rate=target_pv_recovery_rate,
        target_pv_lgd=target_pv_lgd,
        duration_months=duration_months,
        flags=flags,
        scenario=scenario,
        policy=policy,
        evidence_blockers=evidence_blockers,
    )

    decomposition = decompose_lgd(
        recovery_input=recovery_input,
        collateral_recoveries=collateral_recoveries,
        claim_allocations=claim_allocations,
        enforcement_cost=enforcement_cost,
        support_committed=support_committed,
        support_uncommitted=support_uncommitted,
        target_ead=target_ead,
        target_nominal_recovery=target_nominal_recovery,
        target_pv_recovery=target_pv_recovery,
    )

    return KoreaStrategyResult(
        strategy_type=enforcement_path.strategy_type,
        scenario_name=scenario.name,
        scenario_type=scenario.scenario_type,
        gate=gate,
        binding_constraint=binding,
        collateral_recoveries=collateral_recoveries,
        claim_allocations=claim_allocations,
        gross_collateral_value=round(gross_collateral_value, 2),
        gross_recovery_value=round(gross_recovery_value, 2),
        net_recovery_pool=round(net_recovery_pool, 2),
        committed_support_value=round(support_committed, 2),
        uncommitted_support_value=round(support_uncommitted, 2),
        target_ead=round(target_ead, 2),
        target_nominal_recovery=round(target_nominal_recovery, 2),
        target_pv_recovery=round(target_pv_recovery, 2),
        target_unrecovered=round(max(0.0, target_ead - target_nominal_recovery), 2),
        target_nominal_recovery_rate=round(target_nominal_recovery_rate, 6),
        target_pv_recovery_rate=round(target_pv_recovery_rate, 6),
        target_lgd=round(target_lgd, 6),
        target_pv_lgd=round(target_pv_lgd, 6),
        duration_months=duration_months,
        discount_rate=round(enforcement_path.discount_rate, 6),
        lgd_decomposition=decomposition,
        flags=sorted(set(flags)),
        required_actions=sorted(set(actions)),
    )


def calculate_korea_collateral_recovery(
    asset: KoreaCollateralAsset,
    enforcement_path: KoreaEnforcementPath,
    scenario: KoreaRecoveryScenario,
) -> KoreaCollateralRecovery:
    liquidity = scenario.liquidity_override or asset.liquidity

    stressed_value = asset.base_value
    stressed_value *= (1 + scenario.collateral_value_haircut)
    stressed_value *= (1 - scenario.evidence_reliance_penalty)

    if asset.illegal_building_or_violation:
        stressed_value *= (1 - asset.violation_value_haircut)

    stressed_value = max(0.0, stressed_value)

    liquidity_haircut = liquidity_to_haircut(liquidity)

    auction_failure_haircut = 0.0
    if enforcement_path.strategy_type in {
        KoreaRecoveryStrategyType.COURT_AUCTION,
        KoreaRecoveryStrategyType.PUBLIC_AUCTION,
    }:
        auction_failure_haircut = min(
            0.60,
            asset.auction_failed_rounds * asset.auction_round_haircut,
        )

    strategy_haircut = strategy_to_haircut(enforcement_path.strategy_type)

    liquidation_haircut = clamp(
        asset.base_liquidation_haircut
        + asset.forced_sale_haircut
        + scenario.additional_forced_sale_haircut
        + liquidity_haircut
        + auction_failure_haircut
        + strategy_haircut,
        0.0,
        0.95,
    )

    gross_recovery = stressed_value * (1 - liquidation_haircut)
    gross_recovery *= clamp(asset.eligible_proceeds_pct, 0.0, 1.0)

    costs = (
        asset.vacancy_or_eviction_cost
        + asset.violation_cure_cost
        + asset.maintenance_arrears
        + asset.unpaid_public_charges
        + asset.asset_specific_cost
    )

    net_recovery = max(0.0, gross_recovery - costs)

    sale_months = asset.expected_sale_months
    sale_months += asset.eviction_delay_months

    if liquidity == CollateralLiquidity.LOW:
        sale_months += 6
    elif liquidity == CollateralLiquidity.FROZEN:
        sale_months += 18

    if asset.illegal_building_or_violation:
        sale_months += 3

    return KoreaCollateralRecovery(
        collateral_id=asset.collateral_id,
        collateral_name=asset.collateral_name,
        collateral_type=asset.collateral_type,
        base_value=round(asset.base_value, 2),
        stressed_value=round(stressed_value, 2),
        liquidity=liquidity,
        liquidation_haircut=round(liquidation_haircut, 6),
        auction_failure_haircut=round(auction_failure_haircut, 6),
        forced_sale_haircut=round(scenario.additional_forced_sale_haircut, 6),
        violation_haircut=round(asset.violation_value_haircut if asset.illegal_building_or_violation else 0.0, 6),
        gross_recovery_value=round(gross_recovery, 2),
        vacancy_or_eviction_cost=round(asset.vacancy_or_eviction_cost, 2),
        violation_cure_cost=round(asset.violation_cure_cost, 2),
        maintenance_arrears=round(asset.maintenance_arrears, 2),
        unpaid_public_charges=round(asset.unpaid_public_charges, 2),
        asset_specific_cost=round(asset.asset_specific_cost, 2),
        net_recovery_value=round(net_recovery, 2),
        expected_sale_months=sale_months,
        legal_status=asset.legal_status,
        evidence_score=asset.evidence_score,
    )


def adjust_korea_claims(
    claims: Sequence[KoreaClaimLine],
    scenario: KoreaRecoveryScenario,
) -> List[KoreaClaimLine]:
    adjusted: List[KoreaClaimLine] = []

    for claim in claims:
        amount = claim.amount

        if claim.verified_amount is not None:
            amount = claim.verified_amount

        amount += claim.contingent_amount

        if claim.claim_type in {KoreaClaimType.NATIONAL_TAX, KoreaClaimType.LOCAL_TAX}:
            amount *= scenario.tax_claim_multiplier

        if claim.claim_type in {
            KoreaClaimType.WAGE_PRIORITY,
            KoreaClaimType.RETIREMENT_BENEFIT_PRIORITY,
        }:
            amount *= scenario.wage_claim_multiplier

        if claim.claim_type in {
            KoreaClaimType.COMMERCIAL_TENANT_DEPOSIT,
            KoreaClaimType.RESIDENTIAL_TENANT_DEPOSIT,
            KoreaClaimType.JEONSE_RIGHT,
        }:
            amount *= scenario.tenant_deposit_multiplier

        if claim.claim_type in {
            KoreaClaimType.SENIOR_MORTGAGE,
            KoreaClaimType.TRUST_BENEFICIARY_CLAIM,
            KoreaClaimType.PARI_PASSU_SECURED,
        }:
            amount *= scenario.senior_claim_multiplier

        adjusted.append(
            KoreaClaimLine(
                claim_id=claim.claim_id,
                claim_name=claim.claim_name,
                claim_type=claim.claim_type,
                amount=max(0.0, amount),
                contractual_priority_rank=claim.contractual_priority_rank,
                legal_priority_rank=claim.legal_priority_rank,
                collateral_specific_rank=claim.collateral_specific_rank,
                registration_date=claim.registration_date,
                legal_due_date=claim.legal_due_date,
                fixed_date=claim.fixed_date,
                occupancy_or_delivery_date=claim.occupancy_or_delivery_date,
                senior_to_target=claim.senior_to_target,
                pari_passu_with_target=claim.pari_passu_with_target,
                collateral_ids=claim.collateral_ids,
                is_target=claim.is_target,
                secured=claim.secured,
                verified_amount=claim.verified_amount,
                contingent_amount=claim.contingent_amount,
                legal_status=claim.legal_status,
                evidence_score=claim.evidence_score,
                extra=claim.extra,
            )
        )

    return adjusted


def allocate_korea_waterfall(
    claims: Sequence[KoreaClaimLine],
    available_pool: float,
    target_claim_id: str,
) -> List[KoreaClaimAllocation]:
    sorted_claims = sorted(
        claims,
        key=lambda c: (
            korea_waterfall_rank(c),
            c.contractual_priority_rank,
            c.claim_id,
        ),
    )

    remaining_pool = max(0.0, available_pool)
    allocations: List[KoreaClaimAllocation] = []

    rank_groups: Dict[int, List[KoreaClaimLine]] = {}
    for claim in sorted_claims:
        rank = korea_waterfall_rank(claim)
        rank_groups.setdefault(rank, []).append(claim)

    for rank in sorted(rank_groups.keys()):
        group = rank_groups[rank]
        total_claim = sum(c.amount for c in group)

        if total_claim <= 0:
            for claim in group:
                allocations.append(make_allocation(claim, 0.0, rank))
            continue

        group_recovery = min(remaining_pool, total_claim)

        for claim in group:
            share = claim.amount / total_claim
            allocations.append(make_allocation(claim, group_recovery * share, rank))

        remaining_pool = max(0.0, remaining_pool - group_recovery)

    return allocations


def korea_waterfall_rank(claim: KoreaClaimLine) -> int:
    if claim.legal_priority_rank is not None:
        return claim.legal_priority_rank

    if claim.collateral_specific_rank is not None:
        return claim.collateral_specific_rank

    if claim.claim_type in {
        KoreaClaimType.ENFORCEMENT_COST,
        KoreaClaimType.COURT_COST,
        KoreaClaimType.ADMIN_EXPENSE,
    }:
        return 5

    if claim.claim_type in {
        KoreaClaimType.WAGE_PRIORITY,
        KoreaClaimType.RETIREMENT_BENEFIT_PRIORITY,
    }:
        return 10

    if claim.claim_type in {
        KoreaClaimType.NATIONAL_TAX,
        KoreaClaimType.LOCAL_TAX,
    }:
        return 20 if claim.senior_to_target else 60

    if claim.claim_type in {
        KoreaClaimType.COMMERCIAL_TENANT_DEPOSIT,
        KoreaClaimType.RESIDENTIAL_TENANT_DEPOSIT,
        KoreaClaimType.JEONSE_RIGHT,
    }:
        return 30 if claim.senior_to_target else 65

    if claim.claim_type == KoreaClaimType.TRUST_BENEFICIARY_CLAIM:
        return 35 if claim.senior_to_target else 70

    if claim.claim_type == KoreaClaimType.SENIOR_MORTGAGE:
        return 40

    if claim.claim_type == KoreaClaimType.PARI_PASSU_SECURED:
        return 50

    if claim.claim_type == KoreaClaimType.TARGET_FACILITY:
        return 55

    if claim.claim_type == KoreaClaimType.JUNIOR_MORTGAGE:
        return 80

    if claim.claim_type in {
        KoreaClaimType.TRADE_CLAIM,
        KoreaClaimType.UNSECURED,
        KoreaClaimType.UNKNOWN_CLAIM,
        KoreaClaimType.CONTINGENT_PRIORITY,
    }:
        return 90

    if claim.claim_type == KoreaClaimType.EQUITY:
        return 999

    return claim.contractual_priority_rank


def make_allocation(
    claim: KoreaClaimLine,
    recovery_amount: float,
    rank: int,
) -> KoreaClaimAllocation:
    recovery = min(max(0.0, recovery_amount), claim.amount)
    unrecovered = max(0.0, claim.amount - recovery)
    recovery_rate = safe_div(recovery, claim.amount, fallback=0.0)
    lgd = 1 - min(1.0, recovery_rate)

    return KoreaClaimAllocation(
        claim_id=claim.claim_id,
        claim_name=claim.claim_name,
        claim_type=claim.claim_type,
        amount=round(claim.amount, 2),
        effective_amount=round(claim.amount, 2),
        waterfall_rank=rank,
        recovery_amount=round(recovery, 2),
        unrecovered_amount=round(unrecovered, 2),
        recovery_rate=round(recovery_rate, 6),
        lgd=round(lgd, 6),
        is_target=claim.is_target or claim.claim_id == claim.claim_id,
        legal_status=claim.legal_status,
        senior_to_target=claim.senior_to_target,
        pari_passu_with_target=claim.pari_passu_with_target,
    )


def calculate_korea_support(
    support_sources: Sequence[KoreaSupportSource],
    scenario: KoreaRecoveryScenario,
) -> Tuple[float, float]:
    committed = 0.0
    uncommitted = 0.0

    for support in support_sources:
        amount = support.amount
        amount *= (1 - clamp(scenario.support_value_haircut, 0.0, 1.0))

        probability = support.collection_probability
        probability *= (1 - clamp(scenario.support_collection_probability_haircut, 0.0, 1.0))
        probability = clamp(probability, 0.0, 1.0)

        expected_value = amount * probability

        if support.committed and support.legally_enforceable:
            committed += expected_value
        else:
            uncommitted += expected_value

    return max(0.0, committed), max(0.0, uncommitted)


def calculate_strategy_duration(
    collateral_recoveries: Sequence[KoreaCollateralRecovery],
    enforcement_path: KoreaEnforcementPath,
    scenario: KoreaRecoveryScenario,
) -> int:
    collateral_months = max(
        [c.expected_sale_months for c in collateral_recoveries],
        default=enforcement_path.base_duration_months,
    )

    duration = max(enforcement_path.base_duration_months, collateral_months)
    duration = int(math.ceil(duration * scenario.duration_multiplier))

    delay_probability = (
        enforcement_path.court_delay_probability
        + enforcement_path.legal_challenge_probability
        + enforcement_path.injunction_or_stay_probability
    )

    if delay_probability > 0.50:
        duration += 12
    elif delay_probability > 0.25:
        duration += 6

    return max(1, duration)


def calculate_strategy_enforcement_cost(
    gross_recovery_value: float,
    enforcement_path: KoreaEnforcementPath,
    scenario: KoreaRecoveryScenario,
) -> float:
    cost = enforcement_path.base_cost_fixed
    cost += gross_recovery_value * enforcement_path.base_cost_pct
    cost *= scenario.enforcement_cost_multiplier

    if enforcement_path.strategy_type in {
        KoreaRecoveryStrategyType.COURT_AUCTION,
        KoreaRecoveryStrategyType.PUBLIC_AUCTION,
    }:
        cost *= 1.10

    if enforcement_path.legal_challenge_probability > 0.25:
        cost *= 1.15

    return max(0.0, cost)


def build_flags_actions_binding(
    recovery_input: KoreaRecoveryInput,
    collateral_recoveries: Sequence[KoreaCollateralRecovery],
    claim_allocations: Sequence[KoreaClaimAllocation],
    enforcement_path: KoreaEnforcementPath,
    scenario: KoreaRecoveryScenario,
    policy: KoreaRecoveryPolicy,
    evidence_blockers: Sequence[str],
    refi_trigger: Mapping[str, Any],
    target_pv_recovery_rate: float,
    target_pv_lgd: float,
    duration_months: int,
    support_committed: float,
    support_uncommitted: float,
) -> Tuple[List[str], List[str], BindingRecoveryConstraint]:
    flags: List[str] = []
    actions: List[str] = []
    binding = BindingRecoveryConstraint.NONE

    if evidence_blockers:
        flags.append("EVIDENCE_BLOCKERS_PRESENT")
        actions.append("Resolve evidence blockers before external reliance on recovery output.")

    if scenario.legal_blocker:
        flags.append("LEGAL_BLOCKER")
        actions.append("Counsel confirmation required for enforcement route.")
        binding = BindingRecoveryConstraint.LEGAL_DELAY

    if scenario.title_or_perfection_issue:
        flags.append("TITLE_OR_PERFECTION_ISSUE")
        actions.append("Confirm lien perfection, registration, trust beneficiary rights, and competing liens.")
        binding = BindingRecoveryConstraint.TITLE_OR_PERFECTION

    for c in collateral_recoveries:
        if c.legal_status in {LegalVerificationStatus.PENDING, LegalVerificationStatus.UNVERIFIED, LegalVerificationStatus.DISPUTED}:
            flags.append("COLLATERAL_LEGAL_STATUS_NOT_VERIFIED")
            actions.append("Verify collateral registry, title, encumbrances, and enforcement feasibility.")

        if c.violation_cure_cost > 0 or c.violation_haircut > 0:
            flags.append("VIOLATION_OR_CURE_COST_PRESENT")
            binding = binding if binding != BindingRecoveryConstraint.NONE else BindingRecoveryConstraint.COLLATERAL_VALUE

        if c.vacancy_or_eviction_cost > 0:
            flags.append("EVICTION_OR_OCCUPANCY_COST_PRESENT")
            binding = binding if binding != BindingRecoveryConstraint.NONE else BindingRecoveryConstraint.OCCUPANCY_OR_EVICTION

    priority_claims = [
        x for x in claim_allocations
        if x.claim_type in {
            KoreaClaimType.NATIONAL_TAX,
            KoreaClaimType.LOCAL_TAX,
            KoreaClaimType.WAGE_PRIORITY,
            KoreaClaimType.RETIREMENT_BENEFIT_PRIORITY,
            KoreaClaimType.COMMERCIAL_TENANT_DEPOSIT,
            KoreaClaimType.RESIDENTIAL_TENANT_DEPOSIT,
            KoreaClaimType.JEONSE_RIGHT,
            KoreaClaimType.CONTINGENT_PRIORITY,
        }
    ]

    if priority_claims:
        flags.append("KOREA_PRIORITY_CLAIMS_PRESENT")
        actions.append("Verify statutory priority, legal due date, fixed date, delivery/occupancy, and claim amount.")

        if binding == BindingRecoveryConstraint.NONE:
            binding = BindingRecoveryConstraint.KOREA_PRIORITY_CLAIMS

    unverified_priority = [
        x for x in priority_claims
        if x.legal_status in {LegalVerificationStatus.PENDING, LegalVerificationStatus.UNVERIFIED, LegalVerificationStatus.DISPUTED}
    ]

    if unverified_priority:
        flags.append("UNVERIFIED_PRIORITY_CLAIMS")
        actions.append("Treat unverified priority claims as downside/tail until counsel-reviewed.")

    senior_lien_claims = [
        x for x in claim_allocations
        if x.claim_type in {
            KoreaClaimType.SENIOR_MORTGAGE,
            KoreaClaimType.TRUST_BENEFICIARY_CLAIM,
            KoreaClaimType.PARI_PASSU_SECURED,
        }
    ]

    if senior_lien_claims:
        flags.append("SENIOR_OR_PARI_PASSU_CLAIMS_PRESENT")
        if binding == BindingRecoveryConstraint.NONE:
            binding = BindingRecoveryConstraint.SENIOR_LIEN

    if support_uncommitted > 0:
        flags.append("UNCOMMITTED_SUPPORT_INCLUDED")
        actions.append("Convert sponsor/guarantee/insurance support into documented enforceable support.")

    if refi_trigger.get("refi_failure_triggered"):
        flags.append("REFI_FAILURE_TRIGGERED_RECOVERY_ANALYSIS")
        actions.append("Recovery strategy selected because refi path indicates maturity-wall or takeout failure.")

        constraint = str(refi_trigger.get("refi_binding_constraint") or "")

        if constraint == "MARKET_APPETITE":
            flags.append("REFI_MARKET_APPETITE_FAILURE")
            actions.append("Compare note sale, A&E, and negotiated sale before assuming court auction.")

        elif constraint == "LTV":
            flags.append("REFI_LTV_FAILURE")
            actions.append("Increase value haircut and test forced-sale recovery.")

        elif constraint == "DSCR":
            flags.append("REFI_DSCR_FAILURE")
            actions.append("Test going-concern impairment and cash-flow linked valuation haircut.")

        elif constraint == "FUND_LIFE":
            flags.append("REFI_FUND_LIFE_CONSTRAINT")
            actions.append("Apply time-pressure haircut or move exit away from fund-level constraint.")

    if duration_months > policy.max_duration_months_for_watch:
        flags.append("LONG_RECOVERY_DURATION")
        binding = binding if binding != BindingRecoveryConstraint.NONE else BindingRecoveryConstraint.LEGAL_DELAY

    if target_pv_recovery_rate < policy.min_pv_recovery_rate_for_hold:
        flags.append("PV_RECOVERY_DROP_LEVEL")
        actions.append("Reject or restructure; PV recovery does not protect target principal.")

    elif target_pv_recovery_rate < policy.min_pv_recovery_rate_for_watch:
        flags.append("PV_RECOVERY_HOLD_LEVEL")
        actions.append("Hold until priority claims, collateral value, or support package improves.")

    elif target_pv_recovery_rate < policy.min_pv_recovery_rate_for_pass:
        flags.append("PV_RECOVERY_WATCH_LEVEL")
        actions.append("Proceed only with recovery-risk disclosure and required CPs.")

    if scenario.scenario_type == RecoveryScenarioType.TAIL and target_pv_lgd >= policy.tail_lgd_drop_threshold:
        flags.append("TAIL_LGD_DROP_LEVEL")
        actions.append("Tail LGD exceeds house tolerance; restructure or drop.")

    if binding == BindingRecoveryConstraint.NONE:
        binding = BindingRecoveryConstraint.COLLATERAL_VALUE

    return flags, actions, binding


def determine_strategy_gate(
    target_pv_recovery_rate: float,
    target_pv_lgd: float,
    duration_months: int,
    flags: Sequence[str],
    scenario: KoreaRecoveryScenario,
    policy: KoreaRecoveryPolicy,
    evidence_blockers: Sequence[str],
) -> RecoveryGate:
    if evidence_blockers and policy.evidence_blockers_force_hold:
        return RecoveryGate.HOLD

    if "LEGAL_BLOCKER" in flags and policy.legal_blocker_force_hold:
        return RecoveryGate.HOLD

    if "TITLE_OR_PERFECTION_ISSUE" in flags and policy.title_issue_force_hold:
        return RecoveryGate.HOLD

    if "UNVERIFIED_PRIORITY_CLAIMS" in flags and policy.unverified_priority_claims_force_hold:
        return RecoveryGate.HOLD

    if "SENIOR_OR_PARI_PASSU_CLAIMS_PRESENT" in flags and policy.unverified_senior_lien_force_hold:
        return RecoveryGate.HOLD

    if scenario.scenario_type == RecoveryScenarioType.TAIL and target_pv_lgd >= policy.tail_lgd_drop_threshold:
        return RecoveryGate.DROP

    if target_pv_recovery_rate < policy.min_pv_recovery_rate_for_hold:
        return RecoveryGate.DROP

    if target_pv_recovery_rate < policy.min_pv_recovery_rate_for_watch:
        return RecoveryGate.HOLD

    if target_pv_recovery_rate < policy.min_pv_recovery_rate_for_pass:
        return RecoveryGate.WATCH

    if duration_months > policy.max_duration_months_for_watch:
        return RecoveryGate.HOLD

    if duration_months > policy.max_duration_months_for_pass:
        return RecoveryGate.WATCH

    if "UNCOMMITTED_SUPPORT_INCLUDED" in flags and policy.uncommitted_support_blocks_pass:
        return RecoveryGate.WATCH

    return RecoveryGate.PASS


def aggregate_gate(
    results: Sequence[KoreaStrategyResult],
    evidence_blockers: Sequence[str],
    policy: KoreaRecoveryPolicy,
) -> RecoveryGate:
    if evidence_blockers and policy.evidence_blockers_force_hold:
        return RecoveryGate.HOLD

    if any(x.gate == RecoveryGate.DROP for x in results):
        return RecoveryGate.DROP

    if any(x.gate == RecoveryGate.HOLD for x in results):
        return RecoveryGate.HOLD

    if any(x.gate == RecoveryGate.WATCH for x in results):
        return RecoveryGate.WATCH

    return RecoveryGate.PASS


def decompose_lgd(
    recovery_input: KoreaRecoveryInput,
    collateral_recoveries: Sequence[KoreaCollateralRecovery],
    claim_allocations: Sequence[KoreaClaimAllocation],
    enforcement_cost: float,
    support_committed: float,
    support_uncommitted: float,
    target_ead: float,
    target_nominal_recovery: float,
    target_pv_recovery: float,
) -> LGDDecomposition:
    base_collateral_value = sum(c.base_value for c in collateral_recoveries)
    stressed_collateral_value = sum(c.stressed_value for c in collateral_recoveries)
    gross_recovery_value = sum(c.gross_recovery_value for c in collateral_recoveries)

    collateral_value_loss = max(0.0, base_collateral_value - stressed_collateral_value)
    liquidation_haircut_loss = max(0.0, stressed_collateral_value - gross_recovery_value)

    auction_failure_loss = sum(
        c.stressed_value * c.auction_failure_haircut
        for c in collateral_recoveries
    )

    violation_or_cure_loss = sum(c.violation_cure_cost for c in collateral_recoveries)
    eviction_and_occupancy_loss = sum(c.vacancy_or_eviction_cost for c in collateral_recoveries)

    priority_claim_loss = sum(
        a.recovery_amount
        for a in claim_allocations
        if a.claim_type in {
            KoreaClaimType.NATIONAL_TAX,
            KoreaClaimType.LOCAL_TAX,
            KoreaClaimType.WAGE_PRIORITY,
            KoreaClaimType.RETIREMENT_BENEFIT_PRIORITY,
            KoreaClaimType.COMMERCIAL_TENANT_DEPOSIT,
            KoreaClaimType.RESIDENTIAL_TENANT_DEPOSIT,
            KoreaClaimType.JEONSE_RIGHT,
            KoreaClaimType.CONTINGENT_PRIORITY,
        }
    )

    senior_claim_loss = sum(
        a.recovery_amount
        for a in claim_allocations
        if a.claim_type in {
            KoreaClaimType.SENIOR_MORTGAGE,
            KoreaClaimType.TRUST_BENEFICIARY_CLAIM,
            KoreaClaimType.PARI_PASSU_SECURED,
        }
        and not a.is_target
    )

    time_discount_loss = max(0.0, target_nominal_recovery - target_pv_recovery)

    support_total = support_committed + support_uncommitted
    support_shortfall_loss = max(0.0, target_ead - target_nominal_recovery - support_total)

    final_pv_loss = max(0.0, target_ead - target_pv_recovery)
    final_pv_lgd = safe_div(final_pv_loss, target_ead, fallback=1.0)

    return LGDDecomposition(
        starting_target_ead=round(target_ead, 2),
        collateral_value_loss=round(collateral_value_loss, 2),
        liquidation_haircut_loss=round(liquidation_haircut_loss, 2),
        auction_failure_loss=round(auction_failure_loss, 2),
        violation_or_cure_loss=round(violation_or_cure_loss, 2),
        eviction_and_occupancy_loss=round(eviction_and_occupancy_loss, 2),
        enforcement_cost_loss=round(enforcement_cost, 2),
        priority_claim_loss=round(priority_claim_loss, 2),
        senior_claim_loss=round(senior_claim_loss, 2),
        time_discount_loss=round(time_discount_loss, 2),
        support_shortfall_loss=round(support_shortfall_loss, 2),
        final_pv_loss=round(final_pv_loss, 2),
        final_pv_lgd=round(final_pv_lgd, 6),
    )


def default_korea_recovery_scenarios(
    reliance_level: InputRelianceLevel,
    refi_failure_triggered: bool,
    refi_binding_constraint: Optional[str],
) -> List[KoreaRecoveryScenario]:
    penalty = {
        InputRelianceLevel.BASE_CASE: 0.00,
        InputRelianceLevel.STRESS_CASE: 0.05,
        InputRelianceLevel.INTERNAL_REVIEW: 0.10,
        InputRelianceLevel.TAIL_ONLY: 0.15,
        InputRelianceLevel.REJECTED: 0.25,
    }[reliance_level]

    refi_increment = 0.05 if refi_failure_triggered else 0.00

    market_appetite_increment = 0.05 if refi_binding_constraint == "MARKET_APPETITE" else 0.00
    ltv_increment = 0.05 if refi_binding_constraint == "LTV" else 0.00
    fund_time_increment = 0.05 if refi_binding_constraint == "FUND_LIFE" else 0.00

    return [
        KoreaRecoveryScenario(
            name="KR_BASE_NEGOTIATED_OR_ORDERLY",
            scenario_type=RecoveryScenarioType.BASE,
            collateral_value_haircut=-0.05 - penalty,
            additional_forced_sale_haircut=0.03,
            enforcement_cost_multiplier=1.00,
            duration_multiplier=1.00,
            tax_claim_multiplier=1.00,
            wage_claim_multiplier=1.00,
            tenant_deposit_multiplier=1.00,
            senior_claim_multiplier=1.00,
            support_value_haircut=0.10,
            support_collection_probability_haircut=0.00,
            evidence_reliance_penalty=penalty,
        ),
        KoreaRecoveryScenario(
            name="KR_DOWNSIDE_AUCTION_DELAY",
            scenario_type=RecoveryScenarioType.DOWNSIDE,
            collateral_value_haircut=-0.15 - penalty - refi_increment - market_appetite_increment,
            additional_forced_sale_haircut=0.10,
            enforcement_cost_multiplier=1.25,
            duration_multiplier=1.25 + fund_time_increment,
            tax_claim_multiplier=1.10,
            wage_claim_multiplier=1.10,
            tenant_deposit_multiplier=1.15,
            senior_claim_multiplier=1.00,
            support_value_haircut=0.25,
            support_collection_probability_haircut=0.15,
            liquidity_override=CollateralLiquidity.LOW,
            evidence_reliance_penalty=penalty,
            refi_failure_forced_sale=refi_failure_triggered,
        ),
        KoreaRecoveryScenario(
            name="KR_SEVERE_FIRE_SALE_PRIORITY_CLAIMS",
            scenario_type=RecoveryScenarioType.SEVERE,
            collateral_value_haircut=-0.30 - penalty - refi_increment - ltv_increment,
            additional_forced_sale_haircut=0.18,
            enforcement_cost_multiplier=1.50,
            duration_multiplier=1.75,
            tax_claim_multiplier=1.25,
            wage_claim_multiplier=1.25,
            tenant_deposit_multiplier=1.35,
            senior_claim_multiplier=1.05,
            support_value_haircut=0.50,
            support_collection_probability_haircut=0.35,
            liquidity_override=CollateralLiquidity.LOW,
            evidence_reliance_penalty=penalty,
            refi_failure_forced_sale=refi_failure_triggered,
        ),
        KoreaRecoveryScenario(
            name="KR_TAIL_MARKET_FREEZE_LEGAL_DELAY",
            scenario_type=RecoveryScenarioType.TAIL,
            collateral_value_haircut=-0.45 - penalty - refi_increment - market_appetite_increment - ltv_increment,
            additional_forced_sale_haircut=0.30,
            enforcement_cost_multiplier=2.00,
            duration_multiplier=2.50,
            tax_claim_multiplier=1.50,
            wage_claim_multiplier=1.50,
            tenant_deposit_multiplier=1.75,
            senior_claim_multiplier=1.10,
            support_value_haircut=0.75,
            support_collection_probability_haircut=0.60,
            liquidity_override=CollateralLiquidity.FROZEN,
            evidence_reliance_penalty=penalty,
            legal_blocker=False,
            title_or_perfection_issue=False,
            refi_failure_forced_sale=refi_failure_triggered,
        ),
    ]


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

    if evidence_package.get("tail_only_inputs", {}):
        return blockers, warnings, InputRelianceLevel.TAIL_ONLY

    if evidence_package.get("internal_review_inputs", {}):
        return blockers, warnings, InputRelianceLevel.INTERNAL_REVIEW

    if evidence_package.get("stress_case_inputs", {}):
        return blockers, warnings, InputRelianceLevel.STRESS_CASE

    return blockers, warnings, InputRelianceLevel.BASE_CASE


def analyze_refi_path_package(
    refi_path_package: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    if not refi_path_package:
        return {
            "refi_failure_triggered": False,
            "refi_gap_amount": None,
            "refi_binding_constraint": None,
        }

    overall_gate = str(refi_path_package.get("overall_gate", "")).upper()
    memo = refi_path_package.get("memo_summary", {}) or {}

    refi_gap = (
        memo.get("worst_refi_gap")
        or memo.get("tail_refi_gap")
        or memo.get("severe_refi_gap")
        or memo.get("base_refi_gap")
    )

    binding = (
        memo.get("worst_binding_constraint")
        or memo.get("base_binding_constraint")
    )

    failure = overall_gate in {"HOLD", "DROP"} or bool(refi_gap and float(refi_gap) > 0)

    return {
        "refi_failure_triggered": failure,
        "refi_gap_amount": float(refi_gap) if refi_gap is not None else None,
        "refi_binding_constraint": binding,
    }


def set_input_reliance_level(
    recovery_input: KoreaRecoveryInput,
    reliance_level: InputRelianceLevel,
) -> KoreaRecoveryInput:
    return KoreaRecoveryInput(
        target_ead=recovery_input.target_ead,
        target_claim_id=recovery_input.target_claim_id,
        collateral_assets=recovery_input.collateral_assets,
        claim_stack=recovery_input.claim_stack,
        enforcement_paths=recovery_input.enforcement_paths,
        support_sources=recovery_input.support_sources,
        input_reliance_level=reliance_level,
        extra=recovery_input.extra,
    )


def build_memo_summary(
    results: Sequence[KoreaStrategyResult],
    overall_gate: RecoveryGate,
    refi_trigger: Mapping[str, Any],
) -> Dict[str, Any]:
    if not results:
        return {
            "overall_gate": overall_gate.value,
            "memo_language": "No Korea recovery strategy results available.",
        }

    best = max(results, key=lambda x: x.target_pv_recovery_rate)
    worst = max(results, key=lambda x: x.target_pv_lgd)

    base_candidates = [x for x in results if x.scenario_type == RecoveryScenarioType.BASE]
    base = max(base_candidates, key=lambda x: x.target_pv_recovery_rate) if base_candidates else best

    return {
        "overall_gate": overall_gate.value,

        "base_strategy": base.strategy_type.value,
        "base_pv_recovery_rate": base.target_pv_recovery_rate,
        "base_pv_lgd": base.target_pv_lgd,
        "base_binding_constraint": base.binding_constraint.value,

        "best_strategy": best.strategy_type.value,
        "best_pv_recovery_rate": best.target_pv_recovery_rate,

        "worst_strategy": worst.strategy_type.value,
        "worst_scenario": worst.scenario_name,
        "worst_pv_lgd": worst.target_pv_lgd,
        "worst_binding_constraint": worst.binding_constraint.value,

        "refi_failure_triggered": refi_trigger.get("refi_failure_triggered"),
        "refi_gap_amount": refi_trigger.get("refi_gap_amount"),
        "refi_binding_constraint": refi_trigger.get("refi_binding_constraint"),

        "lgd_decomposition_worst": worst.lgd_decomposition.to_dict(),

        "memo_language": (
            f"Korea recovery strategy analysis indicates base strategy "
            f"{base.strategy_type.value} with PV recovery rate "
            f"{base.target_pv_recovery_rate:.1%} and PV LGD {base.target_pv_lgd:.1%}. "
            f"The best tested strategy is {best.strategy_type.value} "
            f"with PV recovery rate {best.target_pv_recovery_rate:.1%}. "
            f"Under the worst tested case ({worst.scenario_name} / {worst.strategy_type.value}), "
            f"PV LGD reaches {worst.target_pv_lgd:.1%}. "
            f"Binding constraint: {worst.binding_constraint.value}. "
            f"Overall recovery gate: {overall_gate.value}."
        ),
    }


def normalize_deal_master(raw: Union[DealMaster, Mapping[str, Any]]) -> DealMaster:
    if isinstance(raw, DealMaster):
        return raw
    if isinstance(raw, Mapping):
        return DealMaster.from_mapping(raw)
    raise TypeError("deal_master must be DealMaster or mapping")


def normalize_recovery_input(raw: Union[KoreaRecoveryInput, Mapping[str, Any]]) -> KoreaRecoveryInput:
    if isinstance(raw, KoreaRecoveryInput):
        return raw
    if isinstance(raw, Mapping):
        return KoreaRecoveryInput.from_mapping(raw)
    raise TypeError("recovery_input must be KoreaRecoveryInput or mapping")


def normalize_policy(raw: Optional[Union[KoreaRecoveryPolicy, Mapping[str, Any]]]) -> KoreaRecoveryPolicy:
    if raw is None:
        return KoreaRecoveryPolicy()
    if isinstance(raw, KoreaRecoveryPolicy):
        return raw
    if isinstance(raw, Mapping):
        return KoreaRecoveryPolicy.from_mapping(raw)
    raise TypeError("policy must be KoreaRecoveryPolicy, mapping, or None")


def normalize_scenarios(
    raw: Optional[Sequence[Union[KoreaRecoveryScenario, Mapping[str, Any]]]]
) -> List[KoreaRecoveryScenario]:
    if not raw:
        return []

    out: List[KoreaRecoveryScenario] = []

    for item in raw:
        if isinstance(item, KoreaRecoveryScenario):
            out.append(item)
        elif isinstance(item, Mapping):
            out.append(KoreaRecoveryScenario.from_mapping(item))
        else:
            raise TypeError("scenarios must contain KoreaRecoveryScenario or mapping")

    return out


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


def parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"Cannot parse date from {value!r}")


def to_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def to_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    return int(value)


def safe_div(numerator: float, denominator: float, fallback: Any = 0.0) -> Any:
    if denominator == 0:
        return fallback
    return numerator / denominator


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def liquidity_to_haircut(liquidity: CollateralLiquidity) -> float:
    return {
        CollateralLiquidity.HIGH: 0.03,
        CollateralLiquidity.MEDIUM: 0.08,
        CollateralLiquidity.LOW: 0.15,
        CollateralLiquidity.FROZEN: 0.30,
    }[liquidity]


def strategy_to_haircut(strategy: KoreaRecoveryStrategyType) -> float:
    return {
        KoreaRecoveryStrategyType.NEGOTIATED_SALE: 0.03,
        KoreaRecoveryStrategyType.COURT_AUCTION: 0.10,
        KoreaRecoveryStrategyType.PUBLIC_AUCTION: 0.12,
        KoreaRecoveryStrategyType.NOTE_SALE: 0.18,
        KoreaRecoveryStrategyType.PRIVATE_WORKOUT: 0.05,
        KoreaRecoveryStrategyType.GOING_CONCERN_SALE: 0.06,
        KoreaRecoveryStrategyType.RECEIVERSHIP_STYLE: 0.08,
    }[strategy]


def find_target_allocation(
    allocations: Sequence[KoreaClaimAllocation],
    target_claim_id: str,
) -> Optional[KoreaClaimAllocation]:
    for allocation in allocations:
        if allocation.claim_id == target_claim_id:
            return allocation
    return next((x for x in allocations if x.is_target), None)


def extract_issue_code(item: Any) -> str:
    if isinstance(item, Mapping):
        return str(item.get("code", "UNKNOWN_ISSUE"))
    return str(item)
